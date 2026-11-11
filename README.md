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

Cada módulo tiene una sola responsabilidad: cambiar la fuente de datos solo toca `data_loader.py`; cambiar una regla de negocio solo toca `etl.py`; cambiar el algoritmo solo toca `model.py`.

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

## 4. Datos

1. Copie en la carpeta `data/` un CSV por tabla exportado desde MySQL (`visitas.csv`, `temporada.csv`, `eventos.csv`, `tarifa.csv`, `empleados.csv`, `visitantes.csv`, `manillas.csv`). El nombre del archivo es el nombre de la tabla. Los CSV pueden venir separados por `;` o `,` y en UTF-8 o Latin-1; el lector detecta ambos casos.
   Si prefiere usar un Excel con una hoja por tabla, defina `PARQUE_DATA_FILE=mi_archivo.xlsx`.
2. Si el archivo tiene otro nombre o está en otra carpeta, configure variables de entorno (ver siguiente sección). Las rutas son relativas a la carpeta del proyecto, así que no es necesario usar rutas absolutas de su equipo.

### Variables de entorno (opcional)

| Variable | Para qué sirve | Valor por defecto |
|---|---|---|
| `PARQUE_DATA_DIR` | Carpeta con los CSV | `data/` |
| `PARQUE_DATA_FILE` | Nombre de un archivo Excel (si se deja vacío, se leen los CSV de la carpeta) | vacío |
| `PARQUE_DB_URL` | Cadena de conexión a una base SQL (tiene prioridad sobre el archivo) | vacía |
| `APP_HOST` / `APP_PORT` | Dirección y puerto del servidor | `127.0.0.1` / `8050` |

Para usarlas, expórtelas en la terminal antes de ejecutar, por ejemplo:

```bash
# macOS / Linux
export PARQUE_DATA_FILE="mi_dataset.xlsx"
# Windows (PowerShell)
$env:PARQUE_DATA_FILE="mi_dataset.xlsx"
```

> Para no escribir las variables cada vez, puede copiar `.env.example` a `.env`, o usar `python-dotenv`. Nunca suba credenciales a un repositorio.

#### Conexión a base SQL (opcional)

```bash
export PARQUE_DB_URL="mysql+pymysql://usuario:clave@localhost:3306/parque_tunjo"
```

Requiere el driver de su motor (por ejemplo `pymysql` para MySQL). Instálelo con `pip install pymysql`.

---

## 5. Ejecución

```bash
python app.py
```

Luego abra **http://127.0.0.1:8050** en el navegador.

Al iniciar, la aplicación carga los datos, construye la tabla diaria y entrena el modelo. Verá en la consola el número de tablas cargadas y los días de baja afluencia detectados. Si algo falta, el mensaje de error indica qué archivo o columna revisar.

---

## 6. Qué contiene el dashboard

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

## 7. Metodología (resumen)

- **Variable objetivo:** `baja_afluencia` = 1 si las visitas del día son menores que el promedio de visitas de su mismo mes; 0 en otro caso.
- **Variables predictoras:** mes, temporada, día de la semana, festivo (festivos de Colombia), puente (lunes o viernes junto a un festivo), número de eventos externos del día y tarifa vigente (solo si la tabla de tarifas tiene fechas de vigencia).
- **Modelo:** regresión logística con variables de mes, temporada, día de la semana, festivo, puente y eventos externos.
- **Evaluación:** exactitud con validación cruzada de 5 particiones (estimación principal, con su desviación), precisión, recall y F1 en una partición de prueba, y el punto de referencia (predecir siempre la clase más frecuente). La meta del 75 % se compara con la exactitud de validación cruzada. Con 301 visitas el modelo **no alcanza la meta**; ver el informe para la discusión de limitaciones.
- **Simulador:** el modelo final se reentrena con todos los datos.

---

## 8. Adaptar al dataset

El código asume estos nombres de columna. Si su archivo usa otros, cámbielos en el Excel o ajuste `etl.py`:

| Tabla | Columnas que usa el dashboard |
|---|---|
| `visitas` | `fecha_visita` (obligatoria) |
| `temporada` | `nombre`, `fecha_inicio`, `fecha_fin` |
| `eventos` | `fecha` |
| `tarifa` | `valor`, `fecha_inicio`, `fecha_fin` (opcionales) |

Los nombres de hoja se normalizan a minúsculas, así que `Visitas` y `visitas` son equivalentes.

### Limitaciones conocidas

- **Número de empleados de turno:** la tabla `empleados` no tiene fechas de turno, por lo que esta variable del informe **no se incluye** en el modelo. Para incluirla, agregue una tabla de turnos con fecha y el número de personas asignadas, y agregue la columna en `etl.py`.
- **Tarifa vigente:** si la tabla `tarifa` no tiene fechas de inicio y fin, la variable se omite y se muestra una advertencia en consola.
- Con 301 visitas (391 días, la mayoría con una o ninguna visita), la exactitud se mueve entre 61 % y 66 % según la forma de validar. Las diferencias entre modelos son pequeñas y no son estadísticamente concluyentes.
- La columna `nivel` de `visitas` es la clasificación de la temporada y ya queda representada por la variable temporada, así que no se usa por separado.

---

## 9. Solución de problemas

| Problema | Solución |
|---|---|
| `No se encontró el dataset en...` | Revise que el archivo esté en `data/` o ajuste `PARQUE_DATA_FILE` / `PARQUE_DATA_DIR`. |
| `KeyError: 'fecha_visita'` | La columna tiene otro nombre. Renómbrela o ajuste `etl.py`. |
| `ModuleNotFoundError` | Active el entorno virtual y ejecute `pip install -r requirements.txt`. |
| El puerto 8050 está ocupado | Ejecute con `APP_PORT=8051 python app.py`. |
