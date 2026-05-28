# Valorant Store Synthetic Dataset

Proyecto académico de Big Data enfocado en la generación de datos sintéticos para una tienda ficticia inspirada en Valorant.

El objetivo del proyecto es simular un entorno real de análisis de datos utilizando múltiples tablas relacionadas para posteriormente realizar procesos de:

- Ingesta de datos
- ETL (Extract, Transform, Load)
- Modelado dimensional
- Star Schema
- Análisis exploratorio
- Visualización de datos
- Procesamiento en Google Cloud Platform (GCP)

---

# Tecnologías utilizadas

- Python
- Pandas
- Faker

---

# Dataset generado

El proyecto genera automáticamente datasets sintéticos en formato CSV para simular una plataforma de ventas de skins de Valorant.

## Tablas generadas

| Tabla | Descripción |
|---|---|
| users.csv | Información de usuarios/jugadores |
| skins.csv | Catálogo de skins |
| transactions.csv | Historial de compras |
| regions.csv | Regiones de juego |
| payment_methods.csv | Métodos de pago |
| daily_store.csv | Rotación diaria de tienda |

---

# Relaciones del modelo

```text
regions
   |
users ---- transactions ---- skins
                |
        payment_methods
                |
          daily_store
```

---

# Características del dataset

El script genera:

- 10.000 transacciones
- 2.000 usuarios
- 50 skins
- Regiones y métodos de pago relacionados
- Fechas aleatorias realistas
- Relaciones entre tablas
- Datos compatibles con ETL y Data Warehouse

---

# Crear entorno virtual

```bash
python -m venv venv
```

---

# Activar entorno virtual

## Linux/macOS

```bash
source venv/bin/activate
```

## Windows PowerShell

```bash
.\venv\Scripts\Activate.ps1
```

---

# Instalar dependencias

```bash
pip install -r requirements.txt
```

---

# Ejecutar el proyecto

```bash
python main.py
```

---

# Resultado esperado

El script generará automáticamente los siguientes archivos:

```text
data/
├── users.csv
├── skins.csv
├── transactions.csv
├── regions.csv
├── payment_methods.csv
└── daily_store.csv
```

Además, el programa mostrará en consola las primeras filas de la tabla `transactions`.

---

# Estructura del proyecto

```text
.
├── data/
│   ├── users.csv
│   ├── skins.csv
│   ├── transactions.csv
│   ├── regions.csv
│   ├── payment_methods.csv
│   └── daily_store.csv
│
├── main.py
├── requirements.txt
├── README.md
└── .gitignore
```

---

# Objetivos del proyecto

Este dataset fue diseñado para ser utilizado en:

- Procesos ETL
- Ingesta en BigQuery
- Data Warehousing
- Star Schema Modeling
- Dashboards y visualización
- Análisis de comportamiento de usuarios
- Simulación de entornos Big Data

---

# GCP Pipeline - BigQuery Data Warehouse

## Arquitectura General

```text
Cloud Storage (Data Lake)
        ↓
   BigQuery Raw Tables
        ↓
   ETL / Star Schema
        ↓
   Analytics Layer
        ↓
 Looker Studio Dashboard
```

---

# Configuración y Carga en GCP

## 1. Verificar configuración activa

```bash
gcloud config list
```

## 2. Verificar región del bucket

```bash
gcloud storage buckets describe gs://valorant-bigdata-2026-1
```

## 3. Crear dataset en BigQuery

```bash
bq mk --dataset --location=US-EAST1 valorant_dw
```

## 4. Verificar datasets

```bash
bq ls
```

## 5. Ver estructura raw en Cloud Storage

```bash
gcloud storage ls gs://valorant-bigdata-2026-1/raw/
gcloud storage ls gs://valorant-bigdata-2026-1/raw/users/
gcloud storage ls gs://valorant-bigdata-2026-1/raw/skins/
gcloud storage ls gs://valorant-bigdata-2026-1/raw/transactions/
gcloud storage ls gs://valorant-bigdata-2026-1/raw/regions/
gcloud storage ls gs://valorant-bigdata-2026-1/raw/daily_store/
gcloud storage ls gs://valorant-bigdata-2026-1/raw/payment_methods/
```

> **Nota:** `payment_methods` contiene un archivo JSON en lugar de CSV, por lo que requiere conversión a NDJSON antes de cargar a BigQuery (ver paso 7).

## 6. Carga de CSVs a BigQuery

```bash
# Users
bq load --skip_leading_rows=1 --autodetect --source_format=CSV valorant_dw.users gs://valorant-bigdata-2026-1/raw/users/users.csv

# Skins
bq load --skip_leading_rows=1 --autodetect --source_format=CSV valorant_dw.skins gs://valorant-bigdata-2026-1/raw/skins/skins.csv

# Transactions
bq load --skip_leading_rows=1 --autodetect --source_format=CSV valorant_dw.transactions gs://valorant-bigdata-2026-1/raw/transactions/transactions.csv

# Regions
bq load --skip_leading_rows=1 --autodetect --source_format=CSV valorant_dw.regions gs://valorant-bigdata-2026-1/raw/regions/regions.csv

# Daily Store
bq load --skip_leading_rows=1 --autodetect --source_format=CSV valorant_dw.daily_store gs://valorant-bigdata-2026-1/raw/daily_store/daily_store.csv

# Payment Methods
bq load --skip_leading_rows=1 --autodetect --source_format=CSV valorant_dw.payment_methods gs://valorant-bigdata-2026-1/raw/payment_methods/payment_methods.csv
```

---

## 7. Transformación JSON → NDJSON

```bash
# Descargar JSON
gcloud storage cp gs://valorant-bigdata-2026-1/raw/payment_methods/payment_methods.json ./payment_methods.json

# Convertir JSON Array a NDJSON
jq -c '.[]' payment_methods.json > payment_methods_ndjson.json

# Verificar conversión
head payment_methods_ndjson.json

# Subir archivo convertido
gcloud storage cp payment_methods_ndjson.json gs://valorant-bigdata-2026-1/raw/payment_methods/
```

---

## 8. Cargar JSON a BigQuery

```bash
bq load \
  --autodetect \
  --source_format=NEWLINE_DELIMITED_JSON \
  valorant_dw.payment_methods \
  gs://valorant-bigdata-2026-1/raw/payment_methods/payment_methods_ndjson.json
```

---

## 9. Verificar tablas en BigQuery

```bash
bq ls valorant_dw
```

---

## 10. Verificar datos cargados

```bash
bq head valorant_dw.users
bq head valorant_dw.transactions
bq head valorant_dw.payment_methods
bq head valorant_dw.skins
bq head valorant_dw.regions
```

---

## 11. Crear Modelo Estrella (Star Schema)

```bash
# Dim Users
bq query --use_legacy_sql=false '
CREATE OR REPLACE TABLE valorant_dw.dim_users AS
SELECT DISTINCT
    user_id,
    username,
    region_id,
    level,
    total_hours_played,
    rank,
    registration_date,
    last_login
FROM valorant_dw.users;
'

# Dim Regions
bq query --use_legacy_sql=false '
CREATE OR REPLACE TABLE valorant_dw.dim_regions AS
SELECT DISTINCT
    region_id,
    region_name,
    avg_player_spending
FROM valorant_dw.regions;
'

# Dim Payment Methods
bq query --use_legacy_sql=false '
CREATE OR REPLACE TABLE valorant_dw.dim_payment_methods AS
SELECT DISTINCT
    payment_method_id,
    method_name
FROM valorant_dw.payment_methods;
'

# Dim Skins
bq query --use_legacy_sql=false '
CREATE OR REPLACE TABLE valorant_dw.dim_skins AS
SELECT DISTINCT
    skin_id,
    skin_name,
    weapon,
    rarity,
    base_price_vp,
    collection,
    release_date
FROM valorant_dw.skins;
'

# Fact Transactions
bq query --use_legacy_sql=false '
CREATE OR REPLACE TABLE valorant_dw.fact_transactions AS
SELECT
    transaction_id,
    user_id,
    skin_id,
    payment_method_id,
    purchase_date,
    final_price_vp,
    discount_percent,
    bundle_purchase
FROM valorant_dw.transactions;
'
```

---

## 12. Crear Tabla Analítica Final

```bash
bq query --use_legacy_sql=false '
CREATE OR REPLACE TABLE valorant_dw.analytics_sales AS
SELECT
    ft.transaction_id,
    du.username,
    dr.region_name,
    du.rank,
    ds.skin_name,
    ds.weapon,
    ds.rarity,
    ds.collection,
    dpm.method_name AS payment_method,
    ft.purchase_date,
    ft.final_price_vp,
    ft.discount_percent,
    ft.bundle_purchase
FROM valorant_dw.fact_transactions ft
JOIN valorant_dw.dim_users du
    ON ft.user_id = du.user_id
JOIN valorant_dw.dim_regions dr
    ON du.region_id = dr.region_id
JOIN valorant_dw.dim_skins ds
    ON ft.skin_id = ds.skin_id
JOIN valorant_dw.dim_payment_methods dpm
    ON ft.payment_method_id = dpm.payment_method_id;
'
```

---

## 13. Verificar resultado ETL final

```bash
bq head valorant_dw.analytics_sales
```

---

## 14. Consultas Analíticas

```bash
# Total ventas por región
bq query --use_legacy_sql=false '
SELECT
    region_name,
    COUNT(*) AS total_sales,
    SUM(final_price_vp) AS total_vp
FROM valorant_dw.analytics_sales
GROUP BY region_name
ORDER BY total_vp DESC;
'
```

---

## 15. Manejo de errores ETL

Crear tabla de log de errores:

```bash
bq query --use_legacy_sql=false '
CREATE OR REPLACE TABLE valorant_dw.etl_log (
    job_id STRING,
    table_name STRING,
    check_type STRING,
    description STRING,
    error_count INT64,
    run_time TIMESTAMP
);'
```

### Validaciones con registro en log

```bash
# Null check - Users
bq query --use_legacy_sql=false "INSERT INTO valorant_dw.etl_log SELECT \"job_001\", \"users\", \"null_check\", \"nulls in critical columns\", (SELECT COUNT(*) FROM valorant_dw.users WHERE user_id IS NULL OR username IS NULL), CURRENT_TIMESTAMP();"

# Null check - Transactions
bq query --use_legacy_sql=false "INSERT INTO valorant_dw.etl_log SELECT \"job_001\", \"transactions\", \"null_check\", \"nulls in critical columns\", (SELECT COUNT(*) FROM valorant_dw.transactions WHERE transaction_id IS NULL OR user_id IS NULL OR skin_id IS NULL), CURRENT_TIMESTAMP();"

# Duplicate check - Users
bq query --use_legacy_sql=false "INSERT INTO valorant_dw.etl_log SELECT \"job_001\", \"users\", \"duplicate_check\", \"duplicate user_ids\", (SELECT COUNT(*) - COUNT(DISTINCT user_id) FROM valorant_dw.users), CURRENT_TIMESTAMP();"

# Range check - Transactions
bq query --use_legacy_sql=false "INSERT INTO valorant_dw.etl_log SELECT \"job_001\", \"transactions\", \"range_check\", \"negative or zero prices\", (SELECT COUNT(*) FROM valorant_dw.transactions WHERE final_price_vp <= 0), CURRENT_TIMESTAMP();"
```

### Verificar errores registrados

```bash
bq query --use_legacy_sql=false 'SELECT * FROM valorant_dw.etl_log;'
```

---

# Dashboard en Looker Studio

Conectar la tabla `valorant_dw.analytics_sales` desde [lookerstudio.google.com](https://lookerstudio.google.com) para crear visualizaciones interactivas.

### Gráficos recomendados

| Gráfico | Dimensión | Métrica |
|---------|-----------|---------|
| Ventas por región | region_name | final_price_vp (SUM) |
| Ingresos en el tiempo | purchase_date | final_price_vp (SUM) |
| Top skins más vendidas | skin_name | transaction_id (COUNT) |
| Ventas por rareza | rarity | final_price_vp (SUM) |
| Método de pago preferido | payment_method | transaction_id (COUNT) |

---

# Posibles mejoras futuras

- Generación de millones de registros
- Exportación a JSON o Parquet
- Simulación de eventos especiales
- Integración con BigQuery
- Automatización ETL
- Machine Learning sobre comportamiento de usuarios
- Dashboards en Looker Studio
- Dockerización del proyecto

---
