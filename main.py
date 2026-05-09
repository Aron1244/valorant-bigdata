from faker import Faker
import pandas as pd
import random

# Inicializar Faker
fake = Faker()

# Configuración de datos
skins = [
    "Reaver Vandal",
    "Prime Phantom",
    "Oni Katana",
    "Elderflame Operator",
    "Ion Sheriff",
    "RGX Blade",
    "Glitchpop Phantom",
    "Prelude to Chaos Vandal"
]

regions = ["LAS", "LAN", "NA", "EU", "BR", "AP"]

payment_methods = [
    "Credit Card",
    "PayPal",
    "Valorant Points Card"
]

# Rarezas con probabilidades
rarity_weights = {
    "Select": 40,
    "Deluxe": 30,
    "Premium": 20,
    "Ultra": 10
}

# Precios según rareza
rarity_prices = {
    "Select": [875],
    "Deluxe": [1275],
    "Premium": [1775],
    "Ultra": [2475, 4350]
}

# Lista final
data = []

# Generar 10.000 registros
for purchase_id in range(1, 15001):

    rarity = random.choices(
        list(rarity_weights.keys()),
        weights=list(rarity_weights.values())
    )[0]

    price = random.choice(rarity_prices[rarity])

    purchase = {
        "purchase_id": purchase_id,
        "user_id": random.randint(100000, 999999),
        "skin_name": random.choice(skins),
        "rarity": rarity,
        "price_vp": price,
        "region": random.choice(regions),
        "payment_method": random.choice(payment_methods),
        "purchase_date": fake.date_time_this_year()
    }

    data.append(purchase)

# Crear DataFrame
df = pd.DataFrame(data)

# Guardar CSV
csv_name = "valorant_store.csv"
df.to_csv(csv_name, index=False)

print(f"\nCSV generado correctamente: {csv_name}")

# Leer el CSV nuevamente
df_read = pd.read_csv(csv_name)

# Mostrar primeras 5 filas
print("\nPrimeras 5 tuplas:\n")
print(df_read.head())