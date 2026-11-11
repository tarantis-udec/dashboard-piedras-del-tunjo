"""Capa de carga de datos.

Lee las tablas del parque desde:
  * una carpeta con un CSV por tabla (caso por defecto: data/),
  * un único archivo Excel (cada hoja es una tabla),
  * una base SQL, si PARQUE_DB_URL está definida.

Los CSV exportados desde MySQL en Colombia suelen venir separados por ';'
y en codificación Latin-1; el lector detecta ambos casos.

Este módulo solo lee datos; no transforma nada (eso es responsabilidad de etl.py).
"""
import logging
from pathlib import Path

import pandas as pd

from config import DATA_DIR, DATA_PATH, DB_URL

logger = logging.getLogger(__name__)

ENCODINGS = ("utf-8-sig", "latin-1")
SEPARATORS = (";", ",")


def _normalize_name(name: str) -> str:
    """Convierte un nombre de hoja o tabla a minúsculas sin espacios."""
    return str(name).strip().lower().replace(" ", "_")


def read_csv_flexible(path: Path) -> pd.DataFrame:
    """Lee un CSV probando codificaciones y separadores comunes.

    Se usa la primera combinación que produzca más de una columna.
    Todas las columnas se leen como texto; etl.py convierte lo que necesite.
    """
    for encoding in ENCODINGS:
        for sep in SEPARATORS:
            try:
                df = pd.read_csv(path, sep=sep, encoding=encoding, dtype=str)
            except UnicodeDecodeError:
                break
            except pd.errors.ParserError:
                continue
            if df.shape[1] > 1:
                df.columns = [c.strip().strip('"') for c in df.columns]
                return df
    raise ValueError(f"No se pudo leer el CSV: {path.name} (revise separador o codificación)")


def load_from_folder(folder: Path = DATA_DIR) -> dict[str, pd.DataFrame]:
    """Carga cada CSV de la carpeta como tabla; el nombre de tabla es el nombre del archivo."""
    archivos = sorted(folder.glob("*.csv"))
    if not archivos:
        raise FileNotFoundError(
            f"No hay archivos .csv en: {folder}\n"
            "Copie los CSV exportados de MySQL a esa carpeta o ajuste PARQUE_DATA_DIR."
        )
    tables = {_normalize_name(a.stem): read_csv_flexible(a) for a in archivos}
    logger.info("Tablas cargadas desde %s: %s", folder, list(tables))
    return tables


def load_from_excel(path: Path = DATA_PATH) -> dict[str, pd.DataFrame]:
    """Carga todas las hojas de un Excel; cada hoja es una tabla."""
    if not path.exists():
        raise FileNotFoundError(f"No se encontró el archivo Excel: {path}")
    raw = pd.read_excel(path, sheet_name=None, dtype=str)
    tables = {_normalize_name(k): v for k, v in raw.items()}
    logger.info("Tablas cargadas desde Excel: %s", list(tables))
    return tables


def load_from_sql(db_url: str = DB_URL) -> dict[str, pd.DataFrame]:
    """Carga todas las tablas de una base SQL usando SQLAlchemy."""
    from sqlalchemy import create_engine, inspect

    engine = create_engine(db_url)
    tables = {_normalize_name(n): pd.read_sql_table(n, engine)
              for n in inspect(engine).get_table_names()}
    logger.info("Tablas cargadas desde SQL: %s", list(tables))
    return tables


def load_tables() -> dict[str, pd.DataFrame]:
    """Punto de entrada único.

    Prioridad: base SQL (si PARQUE_DB_URL está definida), luego Excel
    (si PARQUE_DATA_FILE termina en .xlsx/.xls), y en cualquier otro caso la carpeta de CSV.
    """
    if DB_URL:
        return load_from_sql()
    if DATA_PATH.suffix.lower() in {".xlsx", ".xls"}:
        return load_from_excel(DATA_PATH)
    return load_from_folder(DATA_DIR)
