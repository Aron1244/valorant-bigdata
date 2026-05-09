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
