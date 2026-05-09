# Valorant Store Synthetic Dataset

Proyecto académico de Big Data enfocado en la generación de datos sintéticos para una tienda ficticia inspirada en Valorant.

El objetivo es simular compras de skins y transacciones de usuarios para posteriormente realizar procesos de:

- Ingesta de datos
- ETL
- Análisis exploratorio
- Visualización
- Procesamiento en Google Cloud Platform (GCP)

---

# Tecnologías utilizadas

- Python
- Pandas
- Faker

---

# Características del dataset

El script genera:

- 10.000 registros de compras
- IDs de usuarios aleatorios
- Skins ficticias
- Rarezas
- Regiones
- Métodos de pago
- Fechas de compra

El resultado se exporta automáticamente a un archivo CSV.

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

El script generará:

```text
valorant_store.csv
```

Además mostrará en consola las primeras 5 filas del dataset generado.

---

# Estructura del proyecto

```text
.
├── main.py
├── requirements.txt
├── README.md
└── valorant_store.csv
```

---

# Posibles mejoras futuras

- Generación de millones de registros
- Separación en múltiples tablas
- Simulación de eventos especiales
- Exportación a JSON o Parquet
- Integración con BigQuery
- Dashboards en Looker Studio
- Procesamiento ETL automatizado

---
