"""Dashboard interactivo del parque Piedras del Tunjo (Dash + Plotly).

Secciones:
  1. Indicadores clave (KPIs) del período filtrado.
  2. Serie diaria de visitas, marcando los días de baja afluencia.
  3. Visitas por mes; al hacer clic en un mes se abre el detalle diario (drill-down).
  4. Simulador de escenarios con la regresión logística del informe.

Ejecución:  python app.py   y luego abrir http://127.0.0.1:8050
"""
import logging

import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html

from config import ACCURACY_THRESHOLD, APP_HOST, APP_PORT, PALETTE
from data_loader import load_tables
from etl import build_daily_dataset
from model import predict_proba, train

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

DAY_NAMES = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves",
             4: "Viernes", 5: "Sábado", 6: "Domingo"}
MONTH_NAMES = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
               7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}

TABLES = load_tables()
DIARIO = build_daily_dataset(TABLES)
MODELO = train(DIARIO)
TEMPORADAS = sorted(DIARIO["temporada"].astype(str).unique())

FECHA_MIN = DIARIO["fecha"].min()
FECHA_MAX = DIARIO["fecha"].max()

CARD = {"background": PALETTE["card"], "borderRadius": "10px", "padding": "16px 20px",
        "boxShadow": "0 1px 3px rgba(0,0,0,0.08)", "flex": "1", "minWidth": "180px"}
SECTION = {"background": PALETTE["card"], "borderRadius": "10px", "padding": "16px 20px",
           "boxShadow": "0 1px 3px rgba(0,0,0,0.08)", "marginBottom": "18px"}


def filtrar(start, end, temporada, dia) -> "pd.DataFrame":
    """Aplica los filtros de fecha, temporada y día de la semana."""
    df = DIARIO
    if start:
        df = df[df["fecha"] >= start]
    if end:
        df = df[df["fecha"] <= end]
    if temporada and temporada != "Todas":
        df = df[df["temporada"] == temporada]
    if dia is not None and dia != "Todos":
        df = df[df["dia_semana"] == int(dia)]
    return df


def formato_miles(valor: int) -> str:
    return f"{int(valor):,}".replace(",", ".")


def fig_serie(df):
    """Serie diaria de visitas con los días de baja afluencia resaltados."""
    fig = px.line(df, x="fecha", y="visitas", labels={"fecha": "Fecha", "visitas": "Visitas"})
    fig.update_traces(line_color=PALETTE["primary"], name="Visitas diarias")
    baja = df[df["baja_afluencia"] == 1]
    fig.add_scatter(x=baja["fecha"], y=baja["visitas"], mode="markers", name="Baja afluencia",
                    marker={"color": PALETTE["alert"], "size": 7})
    fig.update_layout(template="simple_white", legend={"orientation": "h", "y": -0.2})
    return fig


def fig_mensual(df):
    """Visitas totales por mes. Cada barra es clicable para el drill-down."""
    mensual = (df.assign(periodo=df["fecha"].dt.strftime("%Y-%m"))
                 .groupby("periodo", as_index=False)
                 .agg(visitas=("visitas", "sum"), dias_baja=("baja_afluencia", "sum")))
    fig = px.bar(mensual, x="periodo", y="visitas", hover_data={"dias_baja": True},
                 labels={"periodo": "Mes", "visitas": "Visitas", "dias_baja": "Días de baja afluencia"})
    fig.update_traces(marker_color=PALETTE["primary"])
    fig.update_layout(template="simple_white")
    return fig


def fig_detalle_mes(df, periodo: str):
    """Drill-down: visitas diarias del mes elegido, coloreadas por tipo de día."""
    dias = df[df["fecha"].dt.strftime("%Y-%m") == periodo].copy()
    dias["tipo"] = dias["baja_afluencia"].map({1: "Baja afluencia", 0: "Afluencia normal"})
    fig = px.bar(dias, x="fecha", y="visitas", color="tipo",
                 color_discrete_map={"Baja afluencia": PALETTE["alert"],
                                     "Afluencia normal": PALETTE["primary"]},
                 labels={"fecha": "Día", "visitas": "Visitas", "tipo": ""})
    fig.update_layout(template="simple_white", legend={"orientation": "h", "y": -0.25})
    return fig


MESES = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
         7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
ETIQUETAS_NUMERICAS = {"fin_de_semana": "Fin de semana", "es_festivo": "Festivo",
                       "cerca_festivo": "Cerca de festivo", "eventos": "Eventos externos"}


def nombre_variable(nombre: str) -> str:
    """Convierte el nombre técnico de un coeficiente en una etiqueta legible."""
    base = nombre.split("__", 1)[-1]
    if base.startswith("mes_"):
        return "Mes: " + MESES[int(base[4:])]
    if base.startswith("dia_semana_"):
        return "Día: " + DAY_NAMES[int(base[11:])]
    return ETIQUETAS_NUMERICAS.get(base, base)


def fig_coeficientes():
    """Las 10 variables con mayor influencia en el modelo."""
    top = MODELO.coefficients.head(10).copy()
    top["variable"] = top["variable"].map(nombre_variable)
    top = top.iloc[::-1]
    fig = px.bar(top, x="coeficiente", y="variable", orientation="h",
                 labels={"coeficiente": "Coeficiente (efecto sobre baja afluencia)", "variable": ""})
    fig.update_traces(marker_color=PALETTE["accent"])
    fig.update_layout(template="simple_white")
    return fig


def fig_probabilidad(prob: float):
    """Medidor de la probabilidad de baja afluencia del escenario."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=prob * 100,
        number={"suffix": " %"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": PALETTE["alert"] if prob >= 0.5 else PALETTE["primary"]},
            "steps": [{"range": [0, 50], "color": PALETTE["soft"]}, {"range": [50, 100], "color": PALETTE["soft_alert"]}],
        },
    ))
    fig.update_layout(height=260, margin={"t": 30, "b": 10, "l": 20, "r": 20})
    return fig


def texto_recomendacion(prob: float) -> str:
    if prob >= 0.5:
        return ("Probable baja afluencia: se recomienda activar una tarifa promocional "
                "o descuento para este día.")
    return "Afluencia esperada normal o alta: no es necesario activar la promoción."


def controles_escenario():
    d = MODELO.defaults
    return html.Div([
        html.Div([
            html.Label("Mes"),
            dcc.Dropdown(id="sc-mes", value=int(d["mes"]),
                         options=[{"label": v, "value": k} for k, v in MONTH_NAMES.items()], clearable=False),
        ], style={"flex": "1", "minWidth": "180px"}),
        html.Div([
            html.Label("Día de la semana"),
            dcc.Dropdown(id="sc-dia", value=int(d["dia_semana"]),
                         options=[{"label": v, "value": k} for k, v in DAY_NAMES.items()], clearable=False),
        ], style={"flex": "1", "minWidth": "180px"}),
        html.Div([
            html.Label("¿Es festivo?"),
            dcc.Dropdown(id="sc-festivo", value=1 if d["es_festivo"] >= 0.5 else 0,
                         options=[{"label": "Sí", "value": 1}, {"label": "No", "value": 0}], clearable=False),
        ], style={"flex": "1", "minWidth": "140px"}),
        html.Div([
            html.Label("¿Cerca de festivo (día antes o después)?"),
            dcc.Dropdown(id="sc-cerca", value=0,
                         options=[{"label": "Sí", "value": 1}, {"label": "No", "value": 0}], clearable=False),
        ], style={"flex": "1", "minWidth": "140px"}),
        html.Div([
            html.Label("Eventos externos ese día"),
            dcc.Input(id="sc-eventos", type="number", value=0, min=0, step=1, style={"width": "100%"}),
        ], style={"flex": "1", "minWidth": "160px"}),
    ], style={"display": "flex", "gap": "14px", "flexWrap": "wrap"})


def construir_layout():
    m = MODELO.metrics
    color_exactitud = PALETTE["primary"] if m["cumple_umbral"] else PALETTE["alert"]
    estado_meta = (f"Meta de {ACCURACY_THRESHOLD:.0%} alcanzada" if m["cumple_umbral"]
                   else f"Meta de {ACCURACY_THRESHOLD:.0%} no alcanzada con los datos disponibles")

    return html.Div(style={"background": PALETTE["background"], "minHeight": "100vh",
                           "padding": "24px", "fontFamily": "Segoe UI, Roboto, Arial, sans-serif"}, children=[
        html.H1("Parque Arqueológico Piedras del Tunjo",
                style={"color": PALETTE["primary"], "marginBottom": "4px"}),
        html.P("Dashboard para mejorar las visitas en temporadas bajas: identifique los días de "
               "baja afluencia y active acciones a tiempo.",
               style={"color": PALETTE["neutral"], "marginTop": "0"}),

        html.Div(style=SECTION, children=[
            html.Div(style={"display": "flex", "gap": "14px", "flexWrap": "wrap"}, children=[
                html.Div([html.Label("Rango de fechas"),
                          dcc.DatePickerRange(id="filtro-fechas",
                                              min_date_allowed=FECHA_MIN.date(),
                                              max_date_allowed=FECHA_MAX.date(),
                                              start_date=FECHA_MIN.date(), end_date=FECHA_MAX.date(),
                                              display_format="DD/MM/YYYY")],
                         style={"minWidth": "260px"}),
                html.Div([html.Label("Temporada"),
                          dcc.Dropdown(id="filtro-temporada", value="Todas", clearable=False,
                                       options=[{"label": "Todas", "value": "Todas"}] +
                                               [{"label": t, "value": t} for t in TEMPORADAS])],
                         style={"minWidth": "220px", "flex": "1"}),
                html.Div([html.Label("Día de la semana"),
                          dcc.Dropdown(id="filtro-dia", value="Todos", clearable=False,
                                       options=[{"label": "Todos", "value": "Todos"}] +
                                               [{"label": v, "value": k} for k, v in DAY_NAMES.items()])],
                         style={"minWidth": "220px", "flex": "1"}),
            ]),
        ]),

        html.Div(style={"display": "flex", "gap": "14px", "flexWrap": "wrap", "marginBottom": "18px"}, children=[
            html.Div(style=CARD, children=[html.Div("Visitas (período)", style={"color": PALETTE["neutral"]}),
                                           html.H2(id="kpi-visitas", style={"margin": "4px 0"})]),
            html.Div(style=CARD, children=[html.Div("Días analizados", style={"color": PALETTE["neutral"]}),
                                           html.H2(id="kpi-dias", style={"margin": "4px 0"})]),
            html.Div(style=CARD, children=[html.Div("Días de baja afluencia", style={"color": PALETTE["neutral"]}),
                                           html.H2(id="kpi-baja", style={"margin": "4px 0", "color": PALETTE["alert"]})]),
            html.Div(style=CARD, children=[
                html.Div("Exactitud del modelo (prueba, 30 %)", style={"color": PALETTE["neutral"]}),
                html.H2(f"{m['exactitud_prueba']:.1%}",
                        style={"margin": "4px 0", "color": color_exactitud}),
                html.Div(f"Referencia: {m['baseline']:.1%} · Validación cruzada: {m['exactitud_cv']:.1%} ± {m['exactitud_cv_desv']:.1%}",
                         style={"color": PALETTE["neutral"], "fontSize": "13px"}),
                html.Div(estado_meta, style={"color": color_exactitud, "fontSize": "13px", "fontWeight": "600"}),
            ]),
        ]),

        html.Div(style=SECTION, children=[
            html.H3("Visitas diarias", style={"marginTop": "0"}),
            dcc.Graph(id="fig-serie", config={"displaylogo": False}),
        ]),

        html.Div(style=SECTION, children=[
            html.H3("Visitas por mes", style={"marginTop": "0"}),
            html.P("Haga clic en una barra para ver el detalle diario de ese mes.",
                   style={"color": PALETTE["neutral"], "marginTop": "0"}),
            dcc.Graph(id="fig-mensual", config={"displaylogo": False}),
            html.H4(id="titulo-drill"),
            dcc.Graph(id="fig-drill", config={"displaylogo": False}),
        ]),

        html.Div(style=SECTION, children=[
            html.H3("Simulador de escenarios", style={"marginTop": "0"}),
            controles_escenario(),
            html.Div(style={"display": "flex", "gap": "18px", "flexWrap": "wrap", "marginTop": "18px"}, children=[
                html.Div(style={"flex": "1", "minWidth": "300px"}, children=[
                    dcc.Graph(id="fig-prob", config={"displaylogo": False}),
                    html.H4(id="sc-resultado", style={"textAlign": "center", "margin": "0"}),
                    html.P(id="sc-recomendacion", style={"textAlign": "center", "color": PALETTE["neutral"]}),
                ]),
                html.Div(style={"flex": "1", "minWidth": "300px"}, children=[
                    html.H4("Variables con mayor influencia", style={"marginTop": "0"}),
                    dcc.Graph(figure=fig_coeficientes(), config={"displaylogo": False}),
                ]),
            ]),
        ]),
    ])


app = Dash(__name__, title="Dashboard Piedras del Tunjo")
server = app.server
app.layout = construir_layout()


FILTROS = [
    Input("filtro-fechas", "start_date"),
    Input("filtro-fechas", "end_date"),
    Input("filtro-temporada", "value"),
    Input("filtro-dia", "value"),
]


@app.callback(
    Output("kpi-visitas", "children"),
    Output("kpi-dias", "children"),
    Output("kpi-baja", "children"),
    Output("fig-serie", "figure"),
    Output("fig-mensual", "figure"),
    *FILTROS,
)
def actualizar_resumen(start, end, temporada, dia):
    df = filtrar(start, end, temporada, dia)
    if df.empty:
        vacia = go.Figure()
        return "0", "0", "0 (0 %)", vacia, vacia

    dias_baja = int(df["baja_afluencia"].sum())
    pct = dias_baja / len(df)
    return (formato_miles(df["visitas"].sum()),
            formato_miles(len(df)),
            f"{formato_miles(dias_baja)} ({pct:.0%})",
            fig_serie(df),
            fig_mensual(df))


@app.callback(
    Output("fig-drill", "figure"),
    Output("titulo-drill", "children"),
    Input("fig-mensual", "clickData"),
    *FILTROS,
)
def actualizar_drill(click, start, end, temporada, dia):
    df = filtrar(start, end, temporada, dia)
    if df.empty:
        return go.Figure(), "Sin datos para los filtros seleccionados"

    periodos = df["fecha"].dt.strftime("%Y-%m")
    periodo = click["points"][0]["x"] if click else periodos.iloc[-1]
    if periodo not in set(periodos):
        periodo = periodos.iloc[-1]

    anio, mes = periodo.split("-")
    titulo = f"Detalle diario: {MONTH_NAMES[int(mes)]} {anio}"
    return fig_detalle_mes(df, periodo), titulo


@app.callback(
    Output("sc-resultado", "children"),
    Output("sc-recomendacion", "children"),
    Output("fig-prob", "figure"),
    Input("sc-mes", "value"),
    Input("sc-dia", "value"),
    Input("sc-festivo", "value"),
    Input("sc-cerca", "value"),
    Input("sc-eventos", "value"),
)
def simular(mes, dia, festivo, cerca, eventos):
    escenario = {
        "mes": mes,
        "dia_semana": dia,
        "fin_de_semana": int(dia in (5, 6)),
        "es_festivo": festivo,
        "cerca_festivo": cerca,
        "eventos": eventos or 0,
    }
    prob = predict_proba(MODELO, escenario)
    if prob >= 0.5:
        resultado = f"Probable baja afluencia: {prob:.0%}"
    else:
        resultado = f"Probable afluencia normal: {1 - prob:.0%}"
    return resultado, texto_recomendacion(prob), fig_probabilidad(prob)


if __name__ == "__main__":
    app.run(host=APP_HOST, port=APP_PORT, debug=False)
