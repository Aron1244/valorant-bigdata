"""
Valorant Charity Vote API
=========================
Arquitectura:
  API (Cloud Run) ──> Cloud Storage (Data Lake / NDJSON raw)
                   ──> BigQuery (load from GCS)
                   ──> Looker Studio (dashboard)

Procesos de streaming:
  - LIMPIEZA: sanitización de inputs, validación de tipos/longitud
  - VALIDACIÓN: skin_id/charity_id existentes, voto único por player
  - ENRIQUECIMIENTO: device_type, session_minutes, derived flags
  - NORMALIZACIÓN: tablas separadas por entidad
  - DEDUPLICACIÓN: player_has_voted, upsert pattern
  - AGREGACIÓN: dashboard endpoint, analytics views
  - LOG: api_log table + GCS backup
"""

import json
import os
import random
import re
import time
import uuid
from datetime import datetime, timezone
from threading import Thread, Lock

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from faker import Faker
from pydantic import BaseModel, field_validator

try:
    from google.cloud import bigquery, storage
    from google.cloud.exceptions import NotFound
    GCS_AVAILABLE = True
    BQ_AVAILABLE = True
except ImportError:
    GCS_AVAILABLE = False
    BQ_AVAILABLE = False

# ─── Configuración ───────────────────────────────────────────────────────────

PROJECT_ID = os.getenv("GCP_PROJECT", os.getenv("GOOGLE_CLOUD_PROJECT", ""))
DATASET_ID = os.getenv("BQ_DATASET", "valorant_dw")
LOCATION = os.getenv("BQ_LOCATION", "us-east4")
BUCKET_NAME = os.getenv("GCS_BUCKET", "valorant-bigdata-2026-1")
GCS_PREFIX = os.getenv("GCS_PREFIX", "streaming")

AUTO_PURCHASE_INTERVAL = float(os.getenv("AUTO_PURCHASE_INTERVAL", "10"))
MIN_VOTES_FOR_AUTO = int(os.getenv("MIN_VOTES_FOR_AUTO", "5"))

# ─── Datos de referencia ─────────────────────────────────────────────────────

CHARITIES = [
    {"charity_id": 1, "charity_name": "UNICEF", "description": "Ayuda humanitaria para la infancia a nivel global"},
    {"charity_id": 2, "charity_name": "WWF", "description": "Conservación de la vida silvestre y la naturaleza"},
    {"charity_id": 3, "charity_name": "Save the Children", "description": "Derechos y protección de la infancia"},
    {"charity_id": 4, "charity_name": "Médicos Sin Fronteras", "description": "Asistencia médica en zonas de crisis"},
    {"charity_id": 5, "charity_name": "Cruz Roja", "description": "Ayuda humanitaria en emergencias y desastres"},
]

VOTING_SKINS = [
    {"skin_id": 1, "skin_name": "Reaver Vandal", "weapon": "Vandal", "rarity": "Premium",
     "base_price_vp": 1775, "description": "Letal Vandal colección Reaver. Estética sombría con llamas violetas."},
    {"skin_id": 2, "skin_name": "Prime Phantom", "weapon": "Phantom", "rarity": "Premium",
     "base_price_vp": 1775, "description": "Futurista Phantom colección Prime. Diseño elegante con patrones dorados."},
]

# ─── Función de limpieza ─────────────────────────────────────────────────────

def sanitize_input(value: str, max_length: int = 100) -> str:
    if not value:
        return ""
    cleaned = str(value).strip()
    cleaned = re.sub(r"[<>\"'\\;/]|--|\bOR\b|\bAND\b|\bDROP\b|\bDELETE\b", "", cleaned, flags=re.IGNORECASE)
    return cleaned[:max_length]

# ─── Modelos Pydantic ────────────────────────────────────────────────────────

class VoteRequest(BaseModel):
    player_id: str
    skin_id: int
    charity_id: int

    @field_validator("player_id")
    @classmethod
    def clean_player_id(cls, v):
        cleaned = sanitize_input(v, max_length=50)
        if len(cleaned) < 3:
            raise ValueError("player_id debe tener al menos 3 caracteres")
        if not re.match(r"^[a-zA-Z0-9_\-]+$", cleaned):
            raise ValueError("player_id solo acepta letras, números, guiones y guión bajo")
        return cleaned

    @field_validator("skin_id")
    @classmethod
    def validate_skin_id(cls, v):
        if v < 1:
            raise ValueError("skin_id debe ser positivo")
        return v

    @field_validator("charity_id")
    @classmethod
    def validate_charity_id(cls, v):
        if v < 1:
            raise ValueError("charity_id debe ser positivo")
        return v

class ManualPurchaseRequest(BaseModel):
    count: int = 1

    @field_validator("count")
    @classmethod
    def validate_count(cls, v):
        if v < 1:
            raise ValueError("count debe ser >= 1")
        if v > 100:
            raise ValueError("count máximo es 100")
        return v

# ─── Inicializar App ─────────────────────────────────────────────────────────

app = FastAPI(title="Valorant Charity Vote API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

fake = Faker()
bq_client = None
gcs_client = None
_clients_lock = Lock()
_auto_thread = None
_stop_auto = False

# ─── Clientes GCP ────────────────────────────────────────────────────────────

def get_bq():
    global bq_client
    if not BQ_AVAILABLE:
        return None
    if bq_client is None:
        with _clients_lock:
            if bq_client is None:
                bq_client = bigquery.Client(project=PROJECT_ID or None)
    return bq_client

def get_gcs():
    global gcs_client
    if not GCS_AVAILABLE:
        return None
    if gcs_client is None:
        with _clients_lock:
            if gcs_client is None:
                gcs_client = storage.Client(project=PROJECT_ID or None)
    return gcs_client

# ─── GCS: Data Lake ──────────────────────────────────────────────────────────

def gcs_upload(table: str, row: dict) -> bool:
    """Escribe 1 registro NDJSON a Cloud Storage (Data Lake)."""
    if not GCS_AVAILABLE:
        print(f"[GCS WARN] google-cloud-storage no disponible, saltando GCS")
        return False
    try:
        client = get_gcs()
        now = datetime.now(timezone.utc)
        prefix = f"{GCS_PREFIX}/{table}/year={now.year}/month={now.month:02d}/day={now.day:02d}"
        filename = f"{row.get(table + '_id', uuid.uuid4().hex)}.ndjson"
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(f"{prefix}/{filename}")
        blob.upload_from_string(json.dumps(row, ensure_ascii=False) + "\n")
        return True
    except Exception as e:
        print(f"[GCS ERROR] {e}")
        return False

def gcs_load_to_bq(table: str, source_uri: str = None) -> bool:
    """Carga archivos NDJSON de GCS a BigQuery (consume lo pendiente)."""
    if not BQ_AVAILABLE:
        return False
    try:
        client = get_bq()
        table_id = f"{PROJECT_ID}.{DATASET_ID}.{table}"
        if source_uri:
            uris = [source_uri]
        else:
            prefix = f"{GCS_PREFIX}/{table}/"
            bucket = get_gcs().bucket(BUCKET_NAME)
            blobs = list(bucket.list_blobs(prefix=prefix))
            if not blobs:
                return False
            uris = [f"gs://{BUCKET_NAME}/{b.name}" for b in blobs if b.name.endswith(".ndjson")]
            if not uris:
                return False
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            autodetect=False,
        )
        job = client.load_table_from_uri(uris, table_id, job_config=job_config)
        job.result()
        print(f"[BQ LOAD] {len(uris)} archivos cargados a {table_id} ({job.output_rows} filas)")
        return True
    except Exception as e:
        print(f"[BQ LOAD ERROR] {e}")
        return False

# ─── BigQuery ────────────────────────────────────────────────────────────────

def ensure_tables():
    if not BQ_AVAILABLE:
        return
    client = get_bq()

    tables_def = {
        "charities": [bigquery.SchemaField("charity_id", "INT64"),
                       bigquery.SchemaField("charity_name", "STRING"),
                       bigquery.SchemaField("description", "STRING")],
        "voting_skins": [bigquery.SchemaField("skin_id", "INT64"),
                          bigquery.SchemaField("skin_name", "STRING"),
                          bigquery.SchemaField("weapon", "STRING"),
                          bigquery.SchemaField("rarity", "STRING"),
                          bigquery.SchemaField("base_price_vp", "INT64"),
                          bigquery.SchemaField("description", "STRING")],
        "votes": [bigquery.SchemaField("vote_id", "STRING"),
                   bigquery.SchemaField("player_id", "STRING"),
                   bigquery.SchemaField("skin_id", "INT64"),
                   bigquery.SchemaField("charity_id", "INT64"),
                   bigquery.SchemaField("voted_at", "TIMESTAMP"),
                   bigquery.SchemaField("device_type", "STRING"),
                   bigquery.SchemaField("session_minutes", "INT64"),
                   bigquery.SchemaField("is_premium_player", "BOOL"),
                   bigquery.SchemaField("vote_hour", "INT64"),
                   bigquery.SchemaField("vote_day_of_week", "INT64")],
        "purchases": [bigquery.SchemaField("purchase_id", "STRING"),
                       bigquery.SchemaField("player_id", "STRING"),
                       bigquery.SchemaField("skin_id", "INT64"),
                       bigquery.SchemaField("charity_id", "INT64"),
                       bigquery.SchemaField("amount_vp", "INT64"),
                       bigquery.SchemaField("purchased_at", "TIMESTAMP"),
                       bigquery.SchemaField("donation_percent", "FLOAT64"),
                       bigquery.SchemaField("payment_method", "STRING"),
                       bigquery.SchemaField("is_discounted", "BOOL"),
                       bigquery.SchemaField("purchase_hour", "INT64")],
        "api_log": [bigquery.SchemaField("log_id", "STRING"),
                     bigquery.SchemaField("event_type", "STRING"),
                     bigquery.SchemaField("description", "STRING"),
                     bigquery.SchemaField("created_at", "TIMESTAMP")],
    }

    for tname, schema in tables_def.items():
        tid = f"{PROJECT_ID}.{DATASET_ID}.{tname}"
        try:
            client.get_table(tid)
            print(f"[OK] Tabla {tid} existe")
        except NotFound:
            t = bigquery.Table(tid, schema=schema)
            client.create_table(t)
            print(f"[OK] Tabla {tid} creada")

def load_ref_data():
    if not BQ_AVAILABLE:
        return
    client = get_bq()
    refs = {"charities": CHARITIES, "voting_skins": VOTING_SKINS}
    for tname, rows in refs.items():
        tid = f"{PROJECT_ID}.{DATASET_ID}.{tname}"
        q = f"SELECT COUNT(*) as c FROM `{tid}`"
        if list(client.query(q).result())[0].c == 0:
            errors = client.insert_rows_json(tid, rows)
            if errors:
                print(f"[ERROR] insertando {tname}: {errors}")
            else:
                print(f"[OK] Datos de referencia cargados en {tname}")

def log_event(event_type: str, description: str):
    log_id = str(uuid.uuid4())
    row = {"log_id": log_id, "event_type": event_type,
           "description": description, "created_at": datetime.now(timezone.utc).isoformat()}
    gcs_upload("api_log", row)
    if BQ_AVAILABLE:
        try:
            get_bq().insert_rows_json(f"{PROJECT_ID}.{DATASET_ID}.api_log", [row])
        except Exception as e:
            print(f"[LOG ERROR] {e}")
    print(f"[LOG] {event_type}: {description}")

def player_has_voted(player_id: str) -> bool:
    if not BQ_AVAILABLE:
        return False
    q = f"SELECT COUNT(*) as c FROM `{PROJECT_ID}.{DATASET_ID}.votes` WHERE player_id = @pid"
    jc = bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter("pid", "STRING", player_id)])
    return list(get_bq().query(q, job_config=jc).result())[0].c > 0

# ─── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "name": "Valorant Charity Vote API",
        "architecture": "API → Cloud Storage (Data Lake NDJSON) → BigQuery → Looker Studio",
        "endpoints": {
            "GET  /api/skins": "Ver las 2 skins en votación",
            "GET  /api/charities": "Ver las 5 beneficencias disponibles",
            "POST /api/vote": "Emitir voto (player_id, skin_id, charity_id)",
            "GET  /api/vote/results": "Resultados de votación en vivo",
            "GET  /api/vote/charity-leaderboard": "Charity más votada",
            "POST /api/purchase": "Simular compra de la skin ganadora",
            "POST /api/purchase/bulk": "Simular N compras",
            "POST /api/auto-purchase/start": "Iniciar compras automáticas",
            "POST /api/auto-purchase/stop": "Detener compras automáticas",
            "GET  /api/dashboard": "Resumen agregado para dashboard",
            "GET  /api/gcs/list": "Listar archivos en GCS Data Lake",
            "GET  /api/gcs/load": "Forzar carga de GCS a BigQuery",
        },
        "status": {
            "gcs": "disponible" if GCS_AVAILABLE else "no disponible",
            "bigquery": "disponible" if BQ_AVAILABLE else "no disponible",
            "bucket": BUCKET_NAME,
            "auto_purchase": "activo" if (_auto_thread and _auto_thread.is_alive()) else "inactivo",
        },
    }

@app.get("/api/skins")
def get_skins():
    return {"skins": VOTING_SKINS}

@app.get("/api/charities")
def get_charities():
    return {"charities": CHARITIES}

@app.post("/api/vote")
def vote(req: VoteRequest):
    skin_ids = [s["skin_id"] for s in VOTING_SKINS]
    if req.skin_id not in skin_ids:
        raise HTTPException(400, f"skin_id inválido. Opciones: {skin_ids}")
    charity_ids = [c["charity_id"] for c in CHARITIES]
    if req.charity_id not in charity_ids:
        raise HTTPException(400, f"charity_id inválido. Opciones: {charity_ids}")
    if player_has_voted(req.player_id):
        raise HTTPException(409, f"El jugador '{req.player_id}' ya votó")

    vote_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # ─── ENRIQUECIMIENTO: añadir campos derivados ───────────────────────
    row = {
        "vote_id": vote_id,
        "player_id": req.player_id,
        "skin_id": req.skin_id,
        "charity_id": req.charity_id,
        "voted_at": now.isoformat(),
        "device_type": random.choice(["PC", "Console", "Mobile"]),
        "session_minutes": random.randint(5, 120),
        "is_premium_player": random.choice([True, False]),
        "vote_hour": now.hour,
        "vote_day_of_week": now.weekday(),
    }

    # 1. Data Lake: escribir a Cloud Storage
    gcs_ok = gcs_upload("votes", row)

    # 2. Cargar a BigQuery desde GCS
    if gcs_ok:
        bq_ok = gcs_load_to_bq("votes")
    elif BQ_AVAILABLE:
        bq_ok = True
        try:
            get_bq().insert_rows_json(f"{PROJECT_ID}.{DATASET_ID}.votes", [row])
        except Exception as e:
            log_event("ERROR", f"Insertando voto directo: {e}")
            raise HTTPException(500, "Error al registrar voto")
    else:
        bq_ok = False

    skin_name = next(s["skin_name"] for s in VOTING_SKINS if s["skin_id"] == req.skin_id)
    charity_name = next(c["charity_name"] for c in CHARITIES if c["charity_id"] == req.charity_id)
    log_event("VOTE", f"player={req.player_id} votó por {skin_name} → {charity_name}")

    return {"vote_id": vote_id, "player_id": req.player_id, "skin_id": req.skin_id,
            "charity_id": req.charity_id, "skin_name": skin_name, "charity_name": charity_name,
            "device_type": row["device_type"], "is_premium_player": row["is_premium_player"],
            "message": f"Voto registrado. Elegiste {skin_name}, fondos irán a {charity_name}. ¡Gracias!",
            "_trace": {"gcs": gcs_ok, "bq": bq_ok}}

@app.get("/api/vote/results")
def vote_results():
    if not BQ_AVAILABLE:
        return {"skins": VOTING_SKINS, "total_votes": 0, "winner": None}
    q = f"""SELECT v.skin_id, s.skin_name, COUNT(*) as votes
            FROM `{PROJECT_ID}.{DATASET_ID}.votes` v
            JOIN `{PROJECT_ID}.{DATASET_ID}.voting_skins` s ON v.skin_id = s.skin_id
            GROUP BY v.skin_id, s.skin_name ORDER BY votes DESC"""
    rows = list(get_bq().query(q).result())
    result_map = {r.skin_id: {"skin_id": r.skin_id, "skin_name": r.skin_name, "votes": r.votes} for r in rows}
    for s in VOTING_SKINS:
        result_map.setdefault(s["skin_id"], {"skin_id": s["skin_id"], "skin_name": s["skin_name"], "votes": 0})
    skin_results = list(result_map.values())
    total = sum(s["votes"] for s in skin_results)
    for s in skin_results:
        s["percentage"] = round(s["votes"] / total * 100, 1) if total > 0 else 0
    winner = max(skin_results, key=lambda x: x["votes"])
    return {"skins": skin_results, "total_votes": total,
            "winner": winner["skin_name"] if winner["votes"] > 0 else None}

@app.get("/api/vote/charity-leaderboard")
def charity_leaderboard():
    if not BQ_AVAILABLE:
        return {"charities": []}
    q = f"""SELECT c.charity_name, COUNT(v.vote_id) as votes
            FROM `{PROJECT_ID}.{DATASET_ID}.charities` c
            LEFT JOIN `{PROJECT_ID}.{DATASET_ID}.votes` v ON c.charity_id = v.charity_id
            GROUP BY c.charity_name ORDER BY votes DESC"""
    return {"charities": [{"charity": r.charity_name, "votes": r.votes}
                          for r in get_bq().query(q).result()]}

# ─── Purchases ──────────────────────────────────────────────────────────────

def generate_purchase() -> dict:
    client = get_bq()
    q = f"""SELECT v.skin_id, s.skin_name, s.base_price_vp, COUNT(*) as votes
            FROM `{PROJECT_ID}.{DATASET_ID}.votes` v
            JOIN `{PROJECT_ID}.{DATASET_ID}.voting_skins` s ON v.skin_id = s.skin_id
            GROUP BY v.skin_id, s.skin_name, s.base_price_vp
            ORDER BY votes DESC LIMIT 1"""
    result = list(client.query(q).result())
    if not result:
        return None
    winner = result[0]
    charity = random.choice(CHARITIES)
    purchase_id = str(uuid.uuid4())
    player_id = f"buyer-{fake.user_name()}-{random.randint(100, 999)}"
    amount = winner.base_price_vp + random.choice([0, 0, 75, 125, 200, 300])
    now = datetime.now(timezone.utc)

    # ─── ENRIQUECIMIENTO ───────────────────────────────────────────────
    row = {
        "purchase_id": purchase_id,
        "player_id": player_id,
        "skin_id": winner.skin_id,
        "charity_id": charity["charity_id"],
        "amount_vp": amount,
        "purchased_at": now.isoformat(),
        "donation_percent": round(random.uniform(5, 25), 1),
        "payment_method": random.choice(["Credit Card", "PayPal", "Valorant Points Card"]),
        "is_discounted": random.choice([True, False]),
        "purchase_hour": now.hour,
    }

    gcs_ok = gcs_upload("purchases", row)
    if gcs_ok:
        gcs_load_to_bq("purchases")
    elif BQ_AVAILABLE:
        try:
            client.insert_rows_json(f"{PROJECT_ID}.{DATASET_ID}.purchases", [row])
        except Exception as e:
            log_event("ERROR", f"Insertando compra: {e}")
            return None
    log_event("PURCHASE", f"{player_id} compró {winner.skin_name} x {amount}VP → {charity['charity_name']}")
    return {"purchase_id": purchase_id, "player_id": player_id, "skin_id": winner.skin_id,
            "charity_id": charity["charity_id"], "amount_vp": amount,
            "donation_percent": row["donation_percent"],
            "message": f"Compra de {winner.skin_name} x {amount}VP. Donación a {charity['charity_name']}."}

@app.post("/api/purchase")
def purchase():
    if not BQ_AVAILABLE:
        raise HTTPException(503, "BigQuery no disponible")
    q = f"SELECT COUNT(*) as c FROM `{PROJECT_ID}.{DATASET_ID}.votes`"
    if list(get_bq().query(q).result())[0].c == 0:
        raise HTTPException(400, "No hay votos registrados. Vota primero.")
    r = generate_purchase()
    if not r:
        raise HTTPException(500, "Error generando compra")
    return r

@app.post("/api/purchase/bulk")
def purchase_bulk(req: ManualPurchaseRequest):
    if not BQ_AVAILABLE:
        raise HTTPException(503, "BigQuery no disponible")
    results = []
    for _ in range(req.count):
        r = generate_purchase()
        if r:
            results.append(r)
        time.sleep(0.05)
    return {"generated": len(results), "purchases": results[:10],
            "note": f"Mostrando {min(10, len(results))} de {len(results)}" if len(results) > 10 else None}

# ─── Dashboard ──────────────────────────────────────────────────────────────

@app.get("/api/dashboard")
def dashboard():
    if not BQ_AVAILABLE:
        return {"error": "BigQuery no disponible"}
    client = get_bq()
    def scalar(q):
        return list(client.query(q).result())[0]

    tv = scalar(f"SELECT COUNT(*) as c FROM `{PROJECT_ID}.{DATASET_ID}.votes`").c
    tp = scalar(f"SELECT COUNT(*) as c FROM `{PROJECT_ID}.{DATASET_ID}.purchases`").c
    tvp = scalar(f"SELECT COALESCE(SUM(amount_vp),0) as s FROM `{PROJECT_ID}.{DATASET_ID}.purchases`").s

    vs = [{"skin_name": r.skin_name, "votes": r.votes}
          for r in client.query(f"""SELECT s.skin_name, COUNT(*) as votes
              FROM `{PROJECT_ID}.{DATASET_ID}.votes` v
              JOIN `{PROJECT_ID}.{DATASET_ID}.voting_skins` s ON v.skin_id = s.skin_id
              GROUP BY s.skin_name""").result()]

    dc = [{"charity": r.charity_name, "total_vp": r.total_vp}
          for r in client.query(f"""SELECT c.charity_name, COALESCE(SUM(p.amount_vp),0) as total_vp
              FROM `{PROJECT_ID}.{DATASET_ID}.purchases` p
              RIGHT JOIN `{PROJECT_ID}.{DATASET_ID}.charities` c ON p.charity_id = c.charity_id
              GROUP BY c.charity_name ORDER BY total_vp DESC""").result()]

    return {"total_votes": tv, "total_purchases": tp, "total_vp_donated": tvp,
            "votes_by_skin": vs, "donations_by_charity": dc}

# ─── GCS Management ─────────────────────────────────────────────────────────

@app.get("/api/gcs/list")
def gcs_list(prefix: str = None):
    if not GCS_AVAILABLE:
        return {"error": "GCS no disponible"}
    p = prefix or GCS_PREFIX
    blobs = list(get_gcs().bucket(BUCKET_NAME).list_blobs(prefix=p))
    return {"bucket": BUCKET_NAME, "prefix": p, "files": len(blobs),
            "recent": [{"name": b.name, "size": b.size, "updated": str(b.updated)}
                       for b in blobs[-20:]]}

@app.post("/api/gcs/load")
def gcs_force_load(table: str = None):
    tables = [table] if table else ["votes", "purchases", "api_log"]
    results = {}
    for t in tables:
        results[t] = gcs_load_to_bq(t)
    return {"loaded": results}

# ─── Auto-Purchase ──────────────────────────────────────────────────────────

def _auto_worker():
    global _stop_auto
    while not _stop_auto:
        try:
            if BQ_AVAILABLE:
                q = f"SELECT COUNT(*) as c FROM `{PROJECT_ID}.{DATASET_ID}.votes`"
                total = list(get_bq().query(q).result())[0].c
                if total >= MIN_VOTES_FOR_AUTO:
                    generate_purchase()
        except Exception as e:
            print(f"[AUTO] {e}")
        for _ in range(int(AUTO_PURCHASE_INTERVAL)):
            if _stop_auto:
                break
            time.sleep(1)

@app.post("/api/auto-purchase/start")
def start_auto():
    global _auto_thread, _stop_auto
    if _auto_thread and _auto_thread.is_alive():
        return {"status": "already_running"}
    _stop_auto = False
    _auto_thread = Thread(target=_auto_worker, daemon=True)
    _auto_thread.start()
    log_event("AUTO_START", f"Auto-purchase cada {AUTO_PURCHASE_INTERVAL}s")
    return {"status": "started", "interval": AUTO_PURCHASE_INTERVAL, "min_votes": MIN_VOTES_FOR_AUTO}

@app.post("/api/auto-purchase/stop")
def stop_auto():
    global _stop_auto
    _stop_auto = True
    log_event("AUTO_STOP", "Auto-purchase detenido")
    return {"status": "stopped"}

@app.get("/api/logs")
def get_logs(limit: int = 50):
    if not BQ_AVAILABLE:
        return {"logs": []}
    q = f"SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.api_log` ORDER BY created_at DESC LIMIT {limit}"
    return {"logs": [dict(r.items()) for r in get_bq().query(q).result()]}

# ─── Startup ─────────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup():
    print("=" * 60)
    print("  VALORANT CHARITY VOTE API")
    print(f"  Arquitectura: API → GCS ({BUCKET_NAME}) → BigQuery → Looker Studio")
    print("=" * 60)
    print(f"  Proyecto: {PROJECT_ID}")
    print(f"  Bucket:   {BUCKET_NAME} / {GCS_PREFIX}/")
    print(f"  Dataset:  {DATASET_ID}")
    if BQ_AVAILABLE:
        try:
            ensure_tables()
            load_ref_data()
        except Exception as e:
            print(f"  [ERROR] Setup BQ: {e}")
    print(f"  Auto-purchase: cada {AUTO_PURCHASE_INTERVAL}s, min {MIN_VOTES_FOR_AUTO} votos")
    print("=" * 60)
