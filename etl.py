"""Procesamiento (ETL) del dashboard.

Convierte las tablas crudas del parque en una tabla diaria con:
  * visitas por día (variable objetivo base),
  * variables predictoras: mes, día de la semana, fin de semana, festivo,
    cerca de festivo, número de eventos externos programados,
  * la etiqueta `baja_afluencia` (1 = el día tuvo menos visitas que el
    promedio de su mismo mes, según la definición del informe).

Supuestos de nombres de columna (ver README, sección "Adaptar al dataset"):
  visitas:    fecha_visita
  temporada:  nombre, fecha_inicio, fecha_fin
  eventos:    fecha
  tarifa:     (opcional) valor, fecha_inicio, fecha_fin
"""
import logging

import holidays
import pandas as pd

from config import HOLIDAY_COUNTRY

logger = logging.getLogger(__name__)


def _assign_by_date_range(diario: pd.DataFrame, source: pd.DataFrame,
                          value_col: str, start_col: str, end_col: str,
                          out_col: str, default) -> bool:
    """Asigna a cada día el valor de la fila cuyo rango de fechas lo contiene.

    Returns:
        True si la asignación se hizo; False si faltan columnas en `source`.
    """
    if not {value_col, start_col, end_col}.issubset(source.columns):
        return False

    diario[out_col] = default
    for _, row in source.iterrows():
        inicio = pd.to_datetime(row[start_col])
        fin = pd.to_datetime(row[end_col])
        mask = diario["fecha"].between(inicio, fin)
        diario.loc[mask, out_col] = row[value_col]
    return True


def _add_calendar_features(diario: pd.DataFrame) -> pd.DataFrame:
    anios = sorted(diario["fecha"].dt.year.unique().tolist())
    festivos = holidays.country_holidays(HOLIDAY_COUNTRY, years=anios)
    fechas_festivas = pd.DatetimeIndex(pd.to_datetime(list(festivos.keys())))

    diario["mes"] = diario["fecha"].dt.month
    diario["dia_semana"] = diario["fecha"].dt.dayofweek
    diario["fin_de_semana"] = diario["dia_semana"].isin([5, 6]).astype(int)
    diario["es_festivo"] = diario["fecha"].isin(fechas_festivas).astype(int)

    def junto_a_festivo(fecha: pd.Timestamp) -> bool:
        return any((fecha + pd.Timedelta(days=k)) in fechas_festivas for k in (-1, 1))

    adyacente = diario["fecha"].apply(junto_a_festivo)
    diario["cerca_festivo"] = (adyacente & (diario["es_festivo"] == 0)).astype(int)
    return diario


def build_daily_dataset(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Construye la tabla diaria completa con variables y etiqueta.

    Args:
        tables: diccionario de tablas devuelto por data_loader.

    Returns:
        DataFrame con una fila por día (incluye días con cero visitas).
    """
    visitas = tables["visitas"].copy()
    visitas["fecha_visita"] = pd.to_datetime(visitas["fecha_visita"]).dt.normalize()

    rango = pd.date_range(visitas["fecha_visita"].min(), visitas["fecha_visita"].max(), freq="D")
    conteo = visitas.groupby("fecha_visita").size().reindex(rango, fill_value=0)
    diario = conteo.rename("visitas").rename_axis("fecha").reset_index()

    if "temporada" in tables:
        ok = _assign_by_date_range(diario, tables["temporada"], "nombre",
                                   "fecha_inicio", "fecha_fin", "temporada", "Sin temporada")
        if not ok:
            logger.warning("Tabla 'temporada' sin columnas de fecha: se omite la variable temporada.")
            diario["temporada"] = "Sin temporada"
    else:
        diario["temporada"] = "Sin temporada"

    if "eventos" in tables:
        por_dia = pd.to_datetime(tables["eventos"]["fecha"]).dt.normalize().value_counts()
        diario["eventos"] = diario["fecha"].map(por_dia).fillna(0).astype(int)
    else:
        diario["eventos"] = 0

    if "tarifa" in tables:
        ok = _assign_by_date_range(diario, tables["tarifa"], "valor",
                                   "fecha_inicio", "fecha_fin", "tarifa_vigente", 0)
        if not ok:
            logger.warning(
                "La tabla 'tarifa' no tiene fechas de vigencia; la variable tarifa_vigente "
                "se excluye del modelo. Agregue fecha_inicio y fecha_fin para usarla."
            )

    diario = _add_calendar_features(diario)

    promedio_mes = diario.groupby("mes")["visitas"].transform("mean")
    diario["baja_afluencia"] = (diario["visitas"] < promedio_mes).astype(int)

    logger.info("Tabla diaria: %d días, %d días de baja afluencia",
                len(diario), diario["baja_afluencia"].sum())
    return diario
