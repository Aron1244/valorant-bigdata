import json
import os
import random
from datetime import datetime, timedelta

import pandas as pd
from faker import Faker

# =========================
# CONFIGURACIÓN INICIAL
# =========================

fake = Faker()

# Crear carpeta data si no existe
os.makedirs("data", exist_ok=True)

# =========================
# REGIONS
# =========================

regions_data = [
    {"region_id": 1, "region_name": "LAS", "avg_player_spending": 35},
    {"region_id": 2, "region_name": "LAN", "avg_player_spending": 30},
    {"region_id": 3, "region_name": "NA", "avg_player_spending": 70},
    {"region_id": 4, "region_name": "EU", "avg_player_spending": 65},
    {"region_id": 5, "region_name": "BR", "avg_player_spending": 40},
    {"region_id": 6, "region_name": "AP", "avg_player_spending": 50},
]

regions_df = pd.DataFrame(regions_data)
regions_df.to_csv("data/regions.csv", index=False)

# =========================
# PAYMENT METHODS
# =========================

payment_methods_data = [
    {"payment_method_id": 1, "method_name": "Credit Card"},
    {"payment_method_id": 2, "method_name": "PayPal"},
    {"payment_method_id": 3, "method_name": "Valorant Points Card"},
]

payment_methods_df = pd.DataFrame(payment_methods_data)
payment_methods_df.to_csv("data/payment_methods.csv", index=False)

with open("data/payment_methods.json", "w", encoding="utf-8") as f:
    json.dump(payment_methods_data, f, indent=2, ensure_ascii=False)

# =========================
# SKINS
# =========================

skins_list = [
    ("Reaver Vandal", "Vandal", "Premium", 1775),
    ("Prime Phantom", "Phantom", "Premium", 1775),
    ("Oni Katana", "Melee", "Ultra", 4350),
    ("Elderflame Operator", "Operator", "Ultra", 2475),
    ("Ion Sheriff", "Sheriff", "Premium", 1775),
    ("RGX Blade", "Melee", "Ultra", 4350),
    ("Glitchpop Phantom", "Phantom", "Premium", 1775),
    ("Prelude to Chaos Vandal", "Vandal", "Ultra", 2475),
    ("Spline Classic", "Classic", "Deluxe", 1275),
    ("Smite Knife", "Melee", "Select", 875),
]

skins_data = []

for i in range(1, 51):
    skin = random.choice(skins_list)

    skins_data.append(
        {
            "skin_id": i,
            "skin_name": skin[0],
            "weapon": skin[1],
            "rarity": skin[2],
            "base_price_vp": skin[3],
            "collection": fake.word().capitalize(),
            "release_date": fake.date_between(start_date="-3y", end_date="today"),
        }
    )

skins_df = pd.DataFrame(skins_data)
skins_df.to_csv("data/skins.csv", index=False)

# =========================
# USERS
# =========================

ranks = [
    "Iron",
    "Bronze",
    "Silver",
    "Gold",
    "Platinum",
    "Diamond",
    "Ascendant",
    "Immortal",
    "Radiant",
]

users_data = []

for i in range(1, 2001):
    region = random.choice(regions_data)

    users_data.append(
        {
            "user_id": i,
            "username": fake.user_name(),
            "region_id": region["region_id"],
            "level": random.randint(1, 500),
            "total_hours_played": random.randint(10, 5000),
            "rank": random.choice(ranks),
            "registration_date": fake.date_between(start_date="-4y", end_date="-30d"),
            "last_login": fake.date_time_between(start_date="-30d", end_date="now"),
        }
    )

users_df = pd.DataFrame(users_data)
users_df.to_csv("data/users.csv", index=False)

# =========================
# TRANSACTIONS
# =========================

transactions_data = []

for i in range(1, 10001):
    user = random.choice(users_data)
    skin = random.choice(skins_data)
    payment = random.choice(payment_methods_data)

    discount = random.choice([0, 0, 0, 10, 15, 20])

    final_price = int(skin["base_price_vp"] * (1 - discount / 100))

    transactions_data.append(
        {
            "transaction_id": i,
            "user_id": user["user_id"],
            "skin_id": skin["skin_id"],
            "payment_method_id": payment["payment_method_id"],
            "purchase_date": fake.date_time_this_year(),
            "final_price_vp": final_price,
            "discount_percent": discount,
            "bundle_purchase": random.choice([True, False]),
        }
    )

transactions_df = pd.DataFrame(transactions_data)
transactions_df.to_csv("data/transactions.csv", index=False)

# =========================
# DAILY STORE
# =========================

daily_store_data = []

start_date = datetime.now() - timedelta(days=365)

store_id = 1

for day in range(365):
    current_date = start_date + timedelta(days=day)

    featured_skins = random.sample(skins_data, 4)

    for skin in featured_skins:
        daily_store_data.append(
            {
                "store_id": store_id,
                "date": current_date.date(),
                "skin_id": skin["skin_id"],
                "featured": random.choice([True, False]),
            }
        )

        store_id += 1

daily_store_df = pd.DataFrame(daily_store_data)
daily_store_df.to_csv("data/daily_store.csv", index=False)

# =========================
# MOSTRAR RESULTADOS
# =========================

print("\nArchivos generados correctamente.\n")

files = [
    "regions.csv",
    "payment_methods.csv",
    "payment_methods.json",
    "skins.csv",
    "users.csv",
    "transactions.csv",
    "daily_store.csv",
]

for file in files:
    print(f"[OK] data/{file}")

# Mostrar primeras filas de transactions
print("\nPrimeras 5 filas de transactions:\n")
print(transactions_df.head())
