"""Modelo predictivo: regresión logística para clasificar días de baja afluencia.

Flujo:
  1. train(): calcula la exactitud con validación cruzada (5 particiones), que es
     más estable con pocos datos; además calcula métricas en una partición de
     prueba y el punto de referencia (decir siempre la clase mayoritaria).
     Al final reentrena con todos los datos para el simulador.
  2. predict_proba(): devuelve la probabilidad de baja afluencia de un escenario.
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from config import ACCURACY_THRESHOLD, CV_FOLDS, RANDOM_STATE, TEST_SIZE

TARGET = "baja_afluencia"
CATEGORICAL_CANDIDATES = ["mes", "dia_semana"]
NUMERIC_CANDIDATES = ["fin_de_semana", "es_festivo", "cerca_festivo", "eventos"]


@dataclass
class ModelResult:
    """Resultado del entrenamiento, listo para usar en el dashboard."""
    pipeline: Pipeline
    features: list[str]
    categorical: list[str]
    numeric: list[str]
    defaults: dict
    metrics: dict
    confusion: np.ndarray
    coefficients: pd.DataFrame = field(default_factory=pd.DataFrame)


def _build_pipeline(categorical: list[str], numeric: list[str]) -> Pipeline:
    """Pipeline nuevo y sin entrenar: preprocesamiento + regresión logística."""
    preprocess = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), categorical),
        ("num", StandardScaler(), numeric),
    ])
    return Pipeline([
        ("preprocess", preprocess),
        ("clf", LogisticRegression(max_iter=1000, random_state=RANDOM_STATE)),
    ])


def train(df: pd.DataFrame) -> ModelResult:
    """Entrena el modelo y calcula las métricas de desempeño.

    Args:
        df: tabla diaria generada por etl.build_daily_dataset.
    """
    categorical = [c for c in CATEGORICAL_CANDIDATES if c in df.columns]
    numeric = [c for c in NUMERIC_CANDIDATES if c in df.columns]
    features = categorical + numeric
    X, y = df[features], df[TARGET]

    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    cv_scores = cross_val_score(_build_pipeline(categorical, numeric), X, y, cv=cv, scoring="accuracy")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, stratify=y, random_state=RANDOM_STATE)
    holdout = _build_pipeline(categorical, numeric).fit(X_train, y_train)
    y_pred = holdout.predict(X_test)

    baseline = max(y.mean(), 1 - y.mean())

    cv_mean = float(cv_scores.mean())
    metrics = {
        "exactitud_cv": cv_mean,
        "exactitud_cv_desv": float(cv_scores.std()),
        "exactitud_prueba": accuracy_score(y_test, y_pred),
        "muestra_entrenamiento": len(y_train),
        "muestra_prueba": len(y_test),
        "recall": recall_score(y_test, y_pred, zero_division=0),
        "precision": precision_score(y_test, y_pred, zero_division=0),
        "f1": f1_score(y_test, y_pred, zero_division=0),
        "baseline": float(baseline),
        "cumple_umbral": accuracy_score(y_test, y_pred) >= ACCURACY_THRESHOLD,
        "muestra": len(df),
    }
    confusion = confusion_matrix(y_test, y_pred)

    final = _build_pipeline(categorical, numeric).fit(X, y)
    names = final.named_steps["preprocess"].get_feature_names_out()
    coefficients = pd.DataFrame({
        "variable": names,
        "coeficiente": final.named_steps["clf"].coef_[0],
    }).sort_values("coeficiente", key=np.abs, ascending=False)

    defaults = {c: df[c].mode().iat[0] for c in categorical}
    defaults.update({c: float(df[c].median()) for c in numeric})

    return ModelResult(pipeline=final, features=features, categorical=categorical,
                       numeric=numeric, defaults=defaults, metrics=metrics,
                       confusion=confusion, coefficients=coefficients)


def predict_proba(result: ModelResult, escenario: dict) -> float:
    """Probabilidad de que el escenario sea un día de baja afluencia."""
    valores = {**result.defaults, **escenario}
    fila = pd.DataFrame([{f: valores[f] for f in result.features}])
    return float(result.pipeline.predict_proba(fila)[0, 1])
