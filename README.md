# Dashboard – Parque Arqueológico Piedras del Tunjo

Dashboard interactivo en Python que responde las preguntas de negocio del informe del proyecto de Business Analytics:

> **¿Qué días tendrán baja afluencia en cualquier temporada, para activar acciones a tiempo?**

Para cada día se clasifica si será de baja afluencia (menos visitas que el promedio de su mismo mes) con una **regresión logística**, y el usuario puede simular escenarios cambiando las variables predictoras.

---

## 1. Estructura del proyecto

```
dashboard_parque_tunjo/
├── app.py            # Interfaz visual (Dash/Plotly): filtros, gráficos, drill-down, simulador
├── data_loader.py    # Capa de carga: Excel, CSV o base SQL
├── etl.py            # Procesamiento: tabla diaria, variables predictoras y etiqueta
├── model.py          # Modelo: entrenamiento, métricas y predicción de escenarios
├── config.py         # Rutas, parámetros del modelo, paleta de colores
├── requirements.txt  # Dependencias
├── .env.example      # Ejemplo de variables de entorno
├── data/             # Coloque aquí el archivo del dataset
└── README.md
```



---

## 2. Requisitos

- Python 3.10 o superior
- Sistema operativo: Windows, macOS o Linux

---

## 3. Instalación

Desde la carpeta del proyecto:

```bash
# 1. Crear y activar un entorno virtual
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 2. Instalar dependencias
pip install -r requirements.txt
```

---


## 4. Ejecución

```bash
python app.py
```

Luego abra **http://127.0.0.1:8050** en el navegador.

Al iniciar, la aplicación carga los datos, construye la tabla diaria y entrena el modelo. Verá en la consola el número de tablas cargadas y los días de baja afluencia detectados. Si algo falta, el mensaje de error indica qué archivo o columna revisar.

---

## 5. Qué contiene el dashboard

| Sección | Qué responde |
|---|---|
| **Filtros** (fecha, temporada, día de la semana) | Restringen todos los gráficos y los indicadores |
| **Indicadores clave** | Visitas del período, días analizados, días de baja afluencia y exactitud del modelo frente a la meta del 75 % |
| **Visitas diarias** | Cuándo ocurren los días de baja afluencia (puntos rojos) |
| **Visitas por mes + drill-down** | Clic en un mes para ver su detalle diario |
| **Simulador de escenarios** | Probabilidad de baja afluencia según mes, día, temporada, festivo, puente y eventos externos, con una recomendación de acción |
| **Variables con mayor influencia** | Qué variables empujan hacia más o menos baja afluencia |

### Lectura del simulador

- Si la probabilidad es **≥ 50 %**, el sistema recomienda activar una tarifa promocional o descuento para ese día (acción definida en el informe).
- Las variables que no se modifiquen toman el valor típico de los datos (la moda para las categóricas y la mediana para las numéricas).

---

## 6. Metodología 

- **Variable objetivo:** `baja_afluencia` = 1 si las visitas del día son menores que el promedio de visitas de su mismo mes; 0 en otro caso.
- **Variables predictoras:** mes, temporada, día de la semana, festivo (festivos de Colombia), puente (lunes o viernes junto a un festivo), número de eventos externos del día y tarifa vigente (solo si la tabla de tarifas tiene fechas de vigencia).
- **Modelo:** regresión logística con variables de mes, temporada, día de la semana, festivo, puente y eventos externos.
- **Evaluación:** exactitud con validación cruzada de 5 particiones (estimación principal, con su desviación), precisión, recall y F1 en una partición de prueba, y el punto de referencia (predecir siempre la clase más frecuente). La meta del 75 % se compara con la exactitud de validación cruzada. Con 301 visitas el modelo **no alcanza la meta**; ver el informe para la discusión de limitaciones.
- **Simulador:** el modelo final se reentrena con todos los datos.

-
