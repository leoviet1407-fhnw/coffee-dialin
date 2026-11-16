"""Seed data: the PHIN range (always) and a small demo set (only for an empty database).

Open question from the README: roast levels, bag sizes and product links are
placeholders until PHIN confirms them; change them here in one place.
"""

from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from .models import Brew, Coffee, Product, Recipe

PRODUCTS = [
    {"id": "hanoi-haze", "name": "Hanoi Haze", "origin": "100% Vietnamese Arabica", "roast_level": "light",
     "bag_size_g": 250, "shop_url": "https://phinkafi.ch"},
    {"id": "da-lat-dawn", "name": "Da Lat Dawn", "origin": "Robusta & Arabica blend", "roast_level": "medium",
     "bag_size_g": 250, "shop_url": "https://phinkafi.ch"},
    {"id": "saigon-drip", "name": "Saigon Drip", "origin": "100% Vietnamese Robusta", "roast_level": "dark",
     "bag_size_g": 250, "shop_url": "https://phinkafi.ch"},
]


def seed_products(sessions: sessionmaker) -> None:
    """Insert or update the PHIN range, so changing PRODUCTS above takes effect on restart."""
    with sessions.begin() as s:
        for p in PRODUCTS:
            s.merge(Product(**p))


def seed_demo(sessions: sessionmaker, today: date) -> None:
    """Two coffees with a few brews, so the app is not empty on first start."""
    with sessions.begin() as s:
        if s.scalar(select(func.count()).select_from(Coffee)):
            return  # never touch a database that already has the user's data
        now = datetime.now().astimezone().replace(microsecond=0)

        saigon = Coffee(product_id="saigon-drip", name="Saigon Drip", origin="100% Vietnamese Robusta",
                        roast_level="dark", roast_date=today - timedelta(days=11), bag_size_g=250, grams_left=214)
        saigon.brews = [
            Brew(method="phin", dose_g=18, water_ml=140, water_temp_c=94, drip_time_s=400, grind_setting="5",
                 taste="bitter", notes="Clogged, very dark.", created_at=now - timedelta(days=2)),
            Brew(method="phin", dose_g=18, water_ml=140, water_temp_c=94, drip_time_s=190, grind_setting="7",
                 taste="sour", notes="Too quick.", created_at=now - timedelta(days=1)),
        ]

        dalat = Coffee(product_id="da-lat-dawn", name="Da Lat Dawn", origin="Robusta & Arabica blend",
                       roast_level="medium", roast_date=today - timedelta(days=20), bag_size_g=250, grams_left=40)
        shot = Brew(method="espresso", dose_g=18, yield_g=36, shot_time_s=28, grind_setting="2.4",
                    taste="balanced", rating=5, notes="Chocolate, sweet.", created_at=now - timedelta(days=3))
        dalat.brews = [
            Brew(method="espresso", dose_g=18, yield_g=36, shot_time_s=19, grind_setting="3.0",
                 taste="sour", created_at=now - timedelta(days=3, minutes=20)),
            shot,
        ]
        s.add_all([saigon, dalat])
        s.flush()
        s.add(Recipe(coffee=dalat, method="espresso", brew=shot))
