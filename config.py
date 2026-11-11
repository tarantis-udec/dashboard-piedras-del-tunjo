"""Configuración central del dashboard.

Las rutas se resuelven de forma relativa a este archivo y pueden sobrescribirse
con variables de entorno. No se guardan credenciales en el código: la conexión a
una base de datos, si se usa, se define con PARQUE_DB_URL (ver .env.example).
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = Path(os.getenv("PARQUE_DATA_DIR", BASE_DIR / "data"))
DATA_FILE = os.getenv("PARQUE_DATA_FILE", "")
DATA_PATH = DATA_DIR / DATA_FILE if DATA_FILE else DATA_DIR

DB_URL = os.getenv("PARQUE_DB_URL", "")

ACCURACY_THRESHOLD = 0.75
PROBABILITY_THRESHOLD = 0.5  # probabilidad a partir de la cual un día se clasifica como baja afluencia
TEST_SIZE = 0.30
CV_FOLDS = 5
RANDOM_STATE = 42
HOLIDAY_COUNTRY = "CO"

APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT = int(os.getenv("APP_PORT", "8050"))

PALETTE = {
    "primary": "#6B3FA0",
    "accent": "#9B7BC4",
    "alert": "#C2185B",
    "neutral": "#5E5670",
    "background": "#F7F5FB",
    "card": "#FFFFFF",
    "soft": "#EFE9F7",
    "soft_alert": "#FBE4EE",
}
