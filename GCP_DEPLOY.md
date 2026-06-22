# Guía de Despliegue en GCP

## 1. Subir archivos a Cloud Shell

Subir desde el menú **⋮ → Upload**:

- `voting_api.py`
- `Dockerfile`
- `requirements.txt`
- `setup_bq.sql`

## 2. Configurar BigQuery

```bash
bq mk --dataset --location=US-EAST4 valorant_dw

cat setup_bq.sql | bq query --nouse_legacy_sql
```

## 3. Habilitar servicios

```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com
```

## 4. Buildear y desplegar API

```bash
gcloud builds submit --tag gcr.io/qwiklabs-gcp-03-5128b7abbcbe/valorant-vote-api

gcloud run deploy valorant-vote-api \
  --image gcr.io/qwiklabs-gcp-03-5128b7abbcbe/valorant-vote-api \
  --platform managed --region us-east4 --allow-unauthenticated \
  --set-env-vars "GCP_PROJECT=qwiklabs-gcp-03-5128b7abbcbe,BQ_DATASET=valorant_dw,GCS_BUCKET=valorant-bigdata-2026-1,AUTO_PURCHASE_INTERVAL=15,MIN_VOTES_FOR_AUTO=5" \
  --min-instances 1
```

## 5. Probar API

```bash
API_URL="https://valorant-vote-api-649228708290.us-east4.run.app"
curl -s $API_URL/
```

## 6. Generar voto de prueba

```bash
curl -s -X POST "$API_URL/api/vote" \
  -H "Content-Type: application/json" \
  -d '{"player_id": "test-001", "skin_id": 1, "charity_id": 2}' | python3 -m json.tool

# Ver archivos en GCS Data Lake
curl -s "$API_URL/api/gcs/list" | python3 -m json.tool
```

## 7. Activar compras automáticas

```bash
curl -s -X POST "$API_URL/api/auto-purchase/start"
```

## 8. Tráfico pesado para el video (40 votos cada 5s)

```bash
while true; do
  for i in $(seq 1 40); do
    PLAYER="player-$(date +%s)-$i-$(cat /dev/urandom | tr -dc 'a-z0-9' | fold -w 4 | head -1)"
    SKIN=$(( (RANDOM % 2) + 1 ))
    CHARITY=$(( (RANDOM % 5) + 1 ))
    curl -s -X POST "$API_URL/api/vote" \
      -H "Content-Type: application/json" \
      -d "{\"player_id\": \"$PLAYER\", \"skin_id\": $SKIN, \"charity_id\": $CHARITY}" > /dev/null
  done
  echo "[$(date)] 40 votos enviados ✓"
  sleep 5
done
```

## 9. Dashboards en Looker Studio

1. Abrir [lookerstudio.google.com](https://lookerstudio.google.com)
2. **Crear → Informe en blanco**
3. Agregar datos → **BigQuery** → `qwiklabs-gcp-03-5128b7abbcbe` → `valorant_dw` → `analytics_voting`
4. Agregar gráficos: barra (`skin_name`, `COUNT(vote_id)`), serie temporal, tarjetas
5. Para refrescar: en la URL del navegador agregar `?refresh=15`
