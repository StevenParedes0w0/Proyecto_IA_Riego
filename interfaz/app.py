"""Panel web local para el proyecto de riego.

Uso:
    python interfaz/app.py
    http://127.0.0.1:8000

El panel no entrena de nuevo. Lee los CSV de `riego_simple/resultados`,
usa las funciones de `riego_simple/main.py` y muestra resultados del proyecto.
"""

from __future__ import annotations

import argparse
import html
import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from string import Template
from urllib.parse import parse_qs, unquote, urlparse

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Rutas del proyecto. Todas se calculan desde este archivo para poder ejecutar
# la app desde la raiz sin depender del directorio actual.
# ---------------------------------------------------------------------------
RAIZ = Path(__file__).resolve().parents[1]
RIEGO_DIR = RAIZ / "riego_simple"
RESULTADOS_DIR = RIEGO_DIR / "resultados"
IMAGENES_DIR = RAIZ / "Informe-Riego-Simple" / "imagenes" / "origen_datos"


# ---------------------------------------------------------------------------
# Importa el motor real del proyecto. No se duplican formulas: la interfaz llama
# a las mismas funciones usadas para preparar datos, fuzzificar e inferir.
# ---------------------------------------------------------------------------
sys.path.insert(0, str(RIEGO_DIR))
import main as proyecto  # noqa: E402


# ---------------------------------------------------------------------------
# Graficas disponibles. Cada tupla: archivo, titulo corto, descripcion corta.
# ---------------------------------------------------------------------------
GRAFICAS = [
    ("01_histograma_volumen_train_test.png", "Volumen TRAIN vs TEST", "Objetivo positivo"),
    ("02_histograma_humedad_train_test.png", "Humedad relativa", "Entrada 1"),
    ("03_histograma_recencia_train_test.png", "Dias sin riego", "Entrada 2"),
    ("04_casos_por_sector.png", "Casos por sector", "Distribucion"),
    ("05_objetivo_vs_estimacion_test.png", "Objetivo vs estimacion", "TEST"),
    ("06_comparacion_mae_test.png", "MAE por modelo", "Error global"),
    ("07_mae_por_sector_test.png", "MAE por sector", "Error sectorial"),
    ("08_objetivos_en_el_tiempo_test.png", "Objetivos en el tiempo", "TEST"),
    ("09_evolucion_ga_train.png", "Evolucion GA", "TRAIN"),
    ("10_funciones_pertenencia_entradas.png", "Pertenencias", "Entradas"),
    ("11_conjuntos_salida_train.png", "Salida difusa", "Litros"),
]


# ---------------------------------------------------------------------------
# Lectura segura de CSV de resultados.
# ---------------------------------------------------------------------------
def leer_csv(nombre: str, **kwargs) -> pd.DataFrame:
    """Lee un CSV de resultados y avisa cómo generarlo si aún no existe.

    Recibe el nombre del archivo y opciones que `pandas.read_csv` pueda usar.
    Devuelve sus filas y columnas como una tabla de pandas.
    """
    # Los resultados siempre se buscan en la carpeta conocida del proyecto.
    ruta = RESULTADOS_DIR / nombre
    if not ruta.exists():
        raise FileNotFoundError(f"Falta {ruta}. Ejecute python riego_simple/main.py")
    return pd.read_csv(ruta, **kwargs)


# ---------------------------------------------------------------------------
# Convierte un DataFrame a una tabla HTML compacta. Redondea flotantes para que
# las tablas sean legibles en pantalla.
# ---------------------------------------------------------------------------
def tabla(df: pd.DataFrame, filas: int = 12) -> str:
    """Convierte las primeras filas de una tabla en HTML seguro y legible.

    Redondea solo los números decimales para que ocupen menos espacio.
    El resultado es una cadena HTML que luego se inserta en la página.
    """
    # Se copia para dar formato sin modificar la tabla original.
    vista = df.head(filas).copy()
    # Se muestran tres decimales; los valores ausentes quedan como celdas vacías.
    for col in vista.select_dtypes(include=["float", "float64", "float32"]).columns:
        vista[col] = vista[col].map(lambda x: "" if pd.isna(x) else f"{x:.3f}")
    return vista.to_html(index=False, classes="tabla", border=0, escape=True)


# ---------------------------------------------------------------------------
# Lee `reglas.csv` y reconstruye el cromosoma GA: Baja=0, Media=1, Alta=2.
# ---------------------------------------------------------------------------
def cromosoma_ga(reglas: pd.DataFrame) -> np.ndarray:
    """Traduce las etiquetas de las reglas a los números usados por el GA.

    Baja corresponde a 0, Media a 1 y Alta a 2. Devuelve los nueve
    consecuentes como un arreglo de enteros en el orden del archivo de reglas.
    """
    # `map` reemplaza cada palabra por el número que representa esa etiqueta.
    return reglas["consecuente_ga"].map({"Baja": 0, "Media": 1, "Alta": 2}).to_numpy(int)


# ---------------------------------------------------------------------------
# Resumen del split temporal. Primero se separa todo, luego se cuentan positivos.
# ---------------------------------------------------------------------------
def resumen_split() -> dict[str, int]:
    """Cuenta observaciones de TRAIN, purga, TEST y riegos de cada periodo.

    La división se obtiene del código principal, para que el panel use el
    mismo corte cronológico. Devuelve los conteos que aparecen en las tarjetas.
    """
    # El motor aplica aquí la separación cronológica y devuelve la purga como número.
    train, test, purga = proyecto.leer_y_dividir_datos()
    # Un caso positivo es una observación cuyo volumen nominal objetivo es mayor que cero.
    train_pos = train[train["litros_nominales_riego_24h"] > 0]
    test_pos = test[test["litros_nominales_riego_24h"] > 0]
    return {
        "total": len(train) + len(test) + purga,
        "train": len(train),
        "purga": purga,
        "test": len(test),
        "train_pos": len(train_pos),
        "test_pos": len(test_pos),
    }


# ---------------------------------------------------------------------------
# Tarjeta simple para el resumen.
# ---------------------------------------------------------------------------
def card(titulo: str, valor: str | int | float) -> str:
    """Construye una tarjeta HTML y escapa el texto para mostrarlo como dato."""
    return f"<div class='card'><span>{html.escape(titulo)}</span><b>{html.escape(str(valor))}</b></div>"


# ---------------------------------------------------------------------------
# Grafico SVG simple de funciones de pertenencia.
# Recibe una malla x, tres curvas y uno o mas marcadores verticales.
# ---------------------------------------------------------------------------
def grafico_pertenencia_svg(
    titulo: str,
    xs: np.ndarray,
    curvas: np.ndarray,
    etiquetas: tuple[str, str, str],
    marcadores: list[tuple[float, str]],
) -> str:
    """Dibuja tres funciones de pertenencia y marca los valores consultados.

    Recibe los puntos del eje horizontal, las tres curvas, sus nombres y los
    valores que deben señalarse. Devuelve un pequeño gráfico SVG como texto.
    """
    # El área del dibujo deja márgenes para los ejes y las etiquetas.
    ancho, alto = 300, 125
    izq, der, sup, inf = 26, 10, 14, 22
    xmin, xmax = float(xs.min()), float(xs.max())
    colores = ("#24527a", "#2d7d58", "#b34a4a")

    def px(x: float) -> float:
        # Convierte un valor de entrada a su posición horizontal en el SVG.
        return izq + (x - xmin) / (xmax - xmin) * (ancho - izq - der)

    def py(y: float) -> float:
        # Convierte un grado entre 0 y 1 a la posición vertical del SVG.
        return sup + (1 - y) * (alto - sup - inf)

    # Cada curva se dibuja uniendo los puntos consecutivos con una línea.
    paths = []
    for i, etiqueta in enumerate(etiquetas):
        puntos = " ".join(f"{px(float(x)):.1f},{py(float(y)):.1f}" for x, y in zip(xs, curvas[:, i]))
        paths.append(f"<polyline points='{puntos}' fill='none' stroke='{colores[i]}' stroke-width='2'/>")

    # Las líneas punteadas muestran dónde cae el dato que se está consultando.
    lineas = []
    for valor, etiqueta in marcadores:
        valor = max(xmin, min(xmax, float(valor)))
        x = px(valor)
        lineas.append(
            f"<line x1='{x:.1f}' y1='{sup}' x2='{x:.1f}' y2='{alto-inf}' "
            f"stroke='#111827' stroke-dasharray='4 3' stroke-width='1.2'/>"
            f"<text x='{min(x+4, ancho-58):.1f}' y='{sup+10}' font-size='9' fill='#111827'>{html.escape(etiqueta)}</text>"
        )

    # La leyenda conserva los mismos colores que las tres curvas.
    leyenda = "".join(
        f"<span><i style='background:{colores[i]}'></i>{html.escape(etiquetas[i])}</span>"
        for i in range(3)
    )
    return f"""
    <div class="svgbox">
      <b>{html.escape(titulo)}</b>
      <svg viewBox="0 0 {ancho} {alto}" role="img">
        <line x1="{izq}" y1="{alto-inf}" x2="{ancho-der}" y2="{alto-inf}" stroke="#94a3b8"/>
        <line x1="{izq}" y1="{sup}" x2="{izq}" y2="{alto-inf}" stroke="#94a3b8"/>
        <text x="6" y="{sup+4}" font-size="9" fill="#64748b">1</text>
        <text x="6" y="{alto-inf}" font-size="9" fill="#64748b">0</text>
        {''.join(paths)}
        {''.join(lineas)}
      </svg>
      <div class="leyenda">{leyenda}</div>
    </div>
    """


def grafico_salida_agregada_svg(
    universo: np.ndarray,
    curva_base: np.ndarray,
    curva_ga: np.ndarray,
    litros_base: float,
    litros_ga: float,
) -> str:
    """Dibuja las dos curvas agregadas y señala dónde cae cada centroide."""
    ancho, alto = 760, 230
    izquierda, derecha, arriba, abajo = 48, 18, 18, 34
    minimo, maximo = float(universo.min()), float(universo.max())

    def x_svg(litros: float) -> float:
        return izquierda + (litros - minimo) / (maximo - minimo) * (ancho - izquierda - derecha)

    def y_svg(grado: float) -> float:
        return arriba + (1 - grado) * (alto - arriba - abajo)

    def puntos_svg(curva: np.ndarray) -> str:
        return " ".join(
            f"{x_svg(float(x)):.1f},{y_svg(float(y)):.1f}"
            for x, y in zip(universo, curva)
        )

    puntos_base = puntos_svg(curva_base)
    puntos_ga = puntos_svg(curva_ga)
    # El relleno deja ver qué forma agregada se usa para calcular cada centroide.
    relleno_base = f"{izquierda},{y_svg(0)} {puntos_base} {ancho-derecha},{y_svg(0)}"
    relleno_ga = f"{izquierda},{y_svg(0)} {puntos_ga} {ancho-derecha},{y_svg(0)}"
    marcas = []
    for litros, etiqueta, color in (
        (litros_base, "Base", "#24527a"), (litros_ga, "GA", "#d97706"),
    ):
        x = x_svg(litros)
        marcas.append(
            f"<line x1='{x:.1f}' y1='{arriba}' x2='{x:.1f}' y2='{alto-abajo}' "
            f"stroke='{color}' stroke-dasharray='5 4' stroke-width='2'/>"
            f"<text x='{min(x+5, ancho-65):.1f}' y='{arriba+13}' fill='{color}' font-size='12'>"
            f"{etiqueta}: {litros:.2f} L</text>"
        )
    return f"""
    <div class="salida-agregada">
      <svg viewBox="0 0 {ancho} {alto}" role="img" aria-label="Curvas agregadas de Base y GA con sus centroides">
        <line x1="{izquierda}" y1="{alto-abajo}" x2="{ancho-derecha}" y2="{alto-abajo}" stroke="#64748b"/>
        <line x1="{izquierda}" y1="{arriba}" x2="{izquierda}" y2="{alto-abajo}" stroke="#64748b"/>
        <text x="8" y="{arriba+4}" font-size="11" fill="#64748b">1</text>
        <text x="8" y="{alto-abajo}" font-size="11" fill="#64748b">0</text>
        <polygon points="{relleno_base}" fill="#24527a" fill-opacity=".12"/>
        <polygon points="{relleno_ga}" fill="#d97706" fill-opacity=".16"/>
        <polyline points="{puntos_base}" fill="none" stroke="#24527a" stroke-width="3"/>
        <polyline points="{puntos_ga}" fill="none" stroke="#d97706" stroke-width="3"/>
        {''.join(marcas)}
        <text x="{izquierda}" y="{alto-8}" font-size="11" fill="#64748b">0 L</text>
        <text x="{ancho-derecha-55}" y="{alto-8}" font-size="11" fill="#64748b">{maximo:.0f} L</text>
      </svg>
      <p><span class="leyenda-salida base"></span> Mamdani Base
         <span class="leyenda-salida ga"></span> Mamdani + GA</p>
    </div>
    """


# ---------------------------------------------------------------------------
# Consulta Mamdani.
#
# Esta es la parte que calcula la consulta mostrada en la interfaz:
# 1. toma sector, humedad y dias del formulario;
# 2. valida que respeten los rangos del proyecto;
# 3. reconstruye la salida difusa usando SOLO TRAIN;
# 4. llama a `proyecto.consultar_caso()`, que internamente hace:
#    humedad_relativa = humedad_actual - MADP,
#    fuzzificacion de humedad y dias,
#    activacion de las 9 reglas,
#    inferencia Mamdani Base y Mamdani + GA.
# ---------------------------------------------------------------------------
def bloque_consulta(qs: dict[str, list[str]], reglas_ga: np.ndarray) -> str:
    """Prepara los datos del formulario, ejecuta Mamdani y arma su explicación.

    Recibe los parámetros de la URL y el cromosoma aprendido por el GA.
    Devuelve un aviso si los datos no son válidos; en otro caso devuelve HTML
    con entradas, salidas, grados de pertenencia, gráficos y reglas activadas.
    """
    # Valores por defecto: reproducen el ejemplo usado en la defensa/documentacion.
    try:
        # El formulario envía texto; aquí se convierte a los tipos numéricos.
        sector = int(qs.get("sector", ["2"])[0])
        humedad = float(qs.get("humedad", ["42"])[0])
        dias = float(qs.get("dias", ["0.8"])[0])
    except ValueError:
        return "<p class='alerta'>Valores no validos.</p>"

    if sector not in proyecto.MADP_POR_SECTOR or not 0 <= humedad <= 100 or not 0 <= dias <= 30:
        return "<p class='alerta'>Rangos: sector 1-5, humedad 0-100, dias 0-30.</p>"

    # Se vuelve a leer el split oficial para evitar usar TEST en el armado de
    # conjuntos de salida. Esta misma restriccion existe en `riego_simple/main.py`.
    # Se conserva solo TRAIN para que los conjuntos de salida no aprendan de TEST.
    train, _, _ = proyecto.leer_y_dividir_datos()

    # La salida de cantidad se calibra solo con casos positivos de TRAIN.
    # Los ceros sirven para el corte temporal, pero no para estimar cantidad.
    positivos = train[train["litros_nominales_riego_24h"] > 0]
    reales = positivos["litros_nominales_riego_24h"].to_numpy(float)

    # `universo` es la malla de litros; `conjuntos` son Bajo/Medio/Alto de salida.
    universo, conjuntos, cuantiles_salida = proyecto.preparar_salida(reales)

    # Aqui ocurre la consulta Mamdani real. No se calcula a mano en la interfaz:
    # se reutiliza la funcion defendida en el codigo principal del proyecto.
    caso = proyecto.consultar_caso(sector, humedad, dias, reglas_ga, universo, conjuntos)

    # Reproduce las nueve fuerzas AND de esta entrada: mínimo de ambos grados.
    activaciones = np.minimum(
        caso["grados_humedad"][:, None], caso["grados_dias"][None, :],
    ).reshape(1, 9)
    # Solicita al motor los pasos internos de Base y GA, no estimaciones nuevas.
    detalle_base = proyecto.desglosar_inferencia_mamdani(
        activaciones, proyecto.REGLAS_BASE, universo, conjuntos,
    )
    detalle_ga = proyecto.desglosar_inferencia_mamdani(
        activaciones, reglas_ga, universo, conjuntos,
    )

    # Traduce los arreglos numericos de pertenencia a texto legible.
    # La inferencia espera los grados de las etiquetas Baja, Media y Alta.
    h = " | ".join(
        f"{proyecto.ETIQUETAS_HUMEDAD[i]}={caso['grados_humedad'][i]:.3f}" for i in range(3)
    )
    d = " | ".join(
        f"{proyecto.ETIQUETAS_DIAS[i]}={caso['grados_dias'][i]:.3f}" for i in range(3)
    )
    # Convierte la lista de reglas que activó Mamdani en una tabla para el panel.
    # Detalla las nueve combinaciones, incluso las que tienen fuerza cero.
    filas_reglas = []
    for indice, fuerza in enumerate(activaciones[0]):
        indice_h, indice_d = indice // 3, indice % 3
        filas_reglas.append({
            "Regla": f"R{indice + 1}",
            "Cálculo de fuerza": (
                f"min({proyecto.ETIQUETAS_HUMEDAD[indice_h]}={caso['grados_humedad'][indice_h]:.3f}, "
                f"{proyecto.ETIQUETAS_DIAS[indice_d]}={caso['grados_dias'][indice_d]:.3f}) "
                f"= {fuerza:.3f}"
            ),
            "Consecuente Base": proyecto.ETIQUETAS_SALIDA[proyecto.REGLAS_BASE[indice]],
            "Consecuente GA": proyecto.ETIQUETAS_SALIDA[reglas_ga[indice]],
        })
    reglas_html = tabla(pd.DataFrame(filas_reglas), 9)

    # Escribe la sustitución numérica usada en las seis funciones de entrada.
    def filas_pertenencia(etiquetas, grados, valor, puntos):
        bajo, centro, alto = puntos
        grado_bajo = float(grados[0])
        grado_alto = float(grados[2])
        return [
            {
                "Conjunto": etiquetas[0],
                "Sustitución": f"clip(({centro:g} - {valor:g}) / ({centro:g} - ({bajo:g})), 0, 1) = {grado_bajo:.3f}",
                "Grado": grado_bajo,
            },
            {
                "Conjunto": etiquetas[1],
                "Sustitución": f"1 - {grado_bajo:.3f} - {grado_alto:.3f} = {float(grados[1]):.3f}",
                "Grado": float(grados[1]),
            },
            {
                "Conjunto": etiquetas[2],
                "Sustitución": f"clip(({valor:g} - {centro:g}) / ({alto:g} - {centro:g}), 0, 1) = {grado_alto:.3f}",
                "Grado": grado_alto,
            },
        ]

    calculos_entrada = pd.DataFrame(
        filas_pertenencia(proyecto.ETIQUETAS_HUMEDAD, caso["grados_humedad"],
                          caso["humedad_relativa"], (-20, 0, 20))
        + filas_pertenencia(proyecto.ETIQUETAS_DIAS, caso["grados_dias"], dias,
                            (0.5, 1.5, 4.5))
    )
    entradas_html = tabla(calculos_entrada, 6)

    # Muestra la fuerza máxima que llega a cada conjunto de salida en cada método.
    fuerzas_salida = pd.DataFrame({
        "Conjunto de salida": proyecto.ETIQUETAS_SALIDA,
        "Fuerza Base": detalle_base["grados_salida"][0],
        "Fuerza GA": detalle_ga["grados_salida"][0],
    })
    # Explica qué fuerzas de reglas entran en cada operación máximo.
    for termino, etiqueta in enumerate(proyecto.ETIQUETAS_SALIDA):
        calculos = []
        for nombre, cromosoma, detalle in (
            ("Base", proyecto.REGLAS_BASE, detalle_base),
            ("GA", reglas_ga, detalle_ga),
        ):
            partes = [
                f"R{regla + 1}={activaciones[0, regla]:.3f}"
                for regla in range(9) if cromosoma[regla] == termino
            ]
            calculos.append(
                f"max({', '.join(partes)}) = {detalle['grados_salida'][0, termino]:.3f}"
            )
        fuerzas_salida.loc[termino, "Cálculo Base"] = calculos[0]
        fuerzas_salida.loc[termino, "Cálculo GA"] = calculos[1]
    fuerzas_html = tabla(fuerzas_salida, 3)

    # Presenta los puntos que definen Baja/Media/Alta y se aprendieron con TRAIN.
    calibracion_html = tabla(pd.DataFrame({
        "Cuantil de TRAIN": ["Q25: Baja", "Q50: Media", "Q75: Alta"],
        "Litros": cuantiles_salida,
    }), 3)

    # Presenta numerador y denominador reales de la fórmula discreta del centroide.
    centroide_html = "".join([
        f"<p><b>Mamdani Base:</b> {detalle_base['numerador'][0]:,.3f} / "
        f"{detalle_base['denominador'][0]:,.3f} = {detalle_base['litros'][0]:.2f} L</p>",
        f"<p><b>Mamdani + GA:</b> {detalle_ga['numerador'][0]:,.3f} / "
        f"{detalle_ga['denominador'][0]:,.3f} = {detalle_ga['litros'][0]:.2f} L</p>",
    ])
    # Abre una tabla plegable con cada uno de los 501 términos de las sumas.
    puntos_centroide = pd.DataFrame({
        "Litros": universo,
        "Grado agregado Base": detalle_base["curva_agregada"][0],
        "Litros x grado Base": universo * detalle_base["curva_agregada"][0],
        "Grado agregado GA": detalle_ga["curva_agregada"][0],
        "Litros x grado GA": universo * detalle_ga["curva_agregada"][0],
    })
    puntos_centroide_html = puntos_centroide.to_html(
        index=False, classes="tabla", border=0, escape=True,
        float_format=lambda valor: f"{valor:.9f}",
    )
    grafico_salida = grafico_salida_agregada_svg(
        universo, detalle_base["curva_agregada"][0], detalle_ga["curva_agregada"][0],
        float(detalle_base["litros"][0]), float(detalle_ga["litros"][0]),
    )

    # Graficos de inferencia para la consulta actual.
    # Las mallas dibujan las curvas suaves; los marcadores identifican esta consulta.
    xs_h = np.linspace(-30, 30, 180)
    curvas_h = proyecto.tres_grados(xs_h, -20, 0, 20)
    xs_d = np.linspace(0, 8, 180)
    curvas_d = proyecto.tres_grados(xs_d, 0.5, 1.5, 4.5)
    grafo_h = grafico_pertenencia_svg(
        "Humedad relativa", xs_h, curvas_h, proyecto.ETIQUETAS_HUMEDAD,
        [(caso["humedad_relativa"], f"x={caso['humedad_relativa']:.1f}")],
    )
    grafo_d = grafico_pertenencia_svg(
        "Dias sin riego", xs_d, curvas_d, proyecto.ETIQUETAS_DIAS,
        [(dias, f"x={dias:.1f}")],
    )
    grafo_s = grafico_pertenencia_svg(
        "Salida en litros", universo, conjuntos.T, proyecto.ETIQUETAS_SALIDA,
        [(caso["litros_base"], "Base"), (caso["litros_ga"], "GA")],
    )

    return f"""
    <div class="resultado">
      <h3>Calculo Mamdani</h3>
      <div class="mini">
        {card("MADP", caso["madp"])}
        {card("Humedad relativa", f"{caso['humedad_relativa']:.2f}")}
        {card("Base", f"{caso['litros_base']:.2f} L")}
        {card("GA", f"{caso['litros_ga']:.2f} L")}
      </div>
      <p><b>Humedad:</b> {html.escape(h)}</p>
      <p><b>Dias:</b> {html.escape(d)}</p>
      <h3>Curvas de pertenencia</h3>
      <div class="svggrid">{grafo_h}{grafo_d}{grafo_s}</div>
      <h3>Reglas activadas</h3>
      <div class="scroll">{reglas_html}</div>
      <details class="pasos-calculo">
        <summary>Ver el cálculo completo de Base y GA</summary>
        <h4>1. Conversión de entradas a grados</h4>
        <p>Humedad relativa: {humedad:g} - {caso['madp']:g} = {caso['humedad_relativa']:g}. Días sin riego: {dias:g}.</p>
        <div class="scroll">{entradas_html}</div>
        <h4>2. Fuerza de cada regla: mínimo entre ambos grados</h4>
        <div class="scroll">{reglas_html}</div>
        <h4>Fuerza que recibe cada conjunto de salida</h4>
        <div class="scroll">{fuerzas_html}</div>
        <h4>3. Conjuntos de salida calibrados con TRAIN</h4>
        <div class="scroll">{calibracion_html}</div>
        <p>Para cada punto L de la malla: Baja recortada = min(αBaja, μBaja(L)); Media recortada = min(αMedia, μMedia(L)); Alta recortada = min(αAlta, μAlta(L)); μ agregada(L) = max(Baja recortada, Media recortada, Alta recortada).</p>
        <h4>4. Curvas agregadas y centroides</h4>
        {grafico_salida}
        <h4>5. Numerador / denominador = centroide</h4>
        <p>Centroide = Σ(L × μ agregada(L)) / Σ(μ agregada(L)); se evalúan los 501 puntos de la malla. Los productos y grados de cada punto están abajo.</p>
        {centroide_html}
        <details class="puntos-detalle"><summary>Mostrar los 501 términos numéricos de las sumas</summary>
          <div class="scroll">{puntos_centroide_html}</div>
        </details>
      </details>
    </div>
    """


# ---------------------------------------------------------------------------
# Galeria de graficas. Cada imagen abre una vista ampliada con CSS :target.
# ---------------------------------------------------------------------------
def bloque_graficas() -> tuple[str, str]:
    """Crea las miniaturas de las gráficas disponibles y sus vistas ampliadas.

    Devuelve dos fragmentos HTML: las tarjetas de la galería y sus ventanas
    ampliadas. Si falta una imagen, omite solo esa gráfica.
    """
    # Las tarjetas y las ventanas se construyen por separado para insertarlas
    # en dos zonas distintas de la página.
    cards, modales = [], []
    for i, (archivo, titulo, detalle) in enumerate(GRAFICAS, 1):
        if not (IMAGENES_DIR / archivo).exists():
            continue
        mid = f"g{i}"
        cards.append(f"""
        <article class="graf">
          <a href="#{mid}"><img src="/img/{html.escape(archivo)}" alt="{html.escape(titulo)}"></a>
          <b>{html.escape(titulo)}</b><span>{html.escape(detalle)}</span>
        </article>
        """)
        modales.append(f"""
        <div id="{mid}" class="modal">
          <a class="fondo" href="#graficas"></a>
          <div class="visor">
            <a class="cerrar" href="#graficas">Cerrar</a>
            <h3>{html.escape(titulo)}</h3>
            <img src="/img/{html.escape(archivo)}" alt="{html.escape(titulo)}">
          </div>
        </div>
        """)
    if not cards:
        return "<p class='alerta'>Faltan graficas. Ejecute python riego_simple/generar_graficas.py</p>", ""
    return "\n".join(cards), "\n".join(modales)


# ---------------------------------------------------------------------------
# Template HTML. Usa tabs con JS pequeno; no hay frameworks externos.
# ---------------------------------------------------------------------------
PLANTILLA = Template("""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Riego simple</title>
<style>
/* Colores y estilos generales para que el panel sea legible en distintas pantallas. */
:root { --bg:#f8fafc; --ink:#17202a; --muted:#667085; --line:#e2e8f0; --brand:#244b68; }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font-family:Arial, Helvetica, sans-serif; }
header { background:#1f3f5b; color:white; padding:22px 32px; }
header h1 { margin:0; font-size:25px; }
header p { margin:6px 0 0; opacity:.9; }
nav { position:sticky; top:0; z-index:5; display:flex; gap:8px; padding:10px 18px; background:white; border-bottom:1px solid var(--line); overflow:auto; }
nav button { border:1px solid var(--line); background:white; color:var(--brand); border-radius:999px; padding:8px 12px; cursor:pointer; font-weight:700; }
nav button.activo, nav button:hover { background:#edf4fa; }
main { max-width:1080px; margin:auto; padding:18px; }
section { display:none; background:white; border:1px solid var(--line); border-radius:8px; padding:18px; }
section.activa { display:block; }
h2 { margin:0 0 14px; color:var(--brand); }
h3 { margin:18px 0 10px; }
.cards, .mini, .ficha { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; }
.card, .dato { border:1px solid var(--line); border-radius:8px; padding:12px; background:#fbfdff; }
.card span, .dato span, .graf span { display:block; color:var(--muted); font-size:12px; margin-bottom:5px; }
.card b { font-size:20px; }
.dato b { font-size:14px; }
.grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:14px; }
.scroll { overflow:auto; border:1px solid var(--line); border-radius:8px; }
.tabla { width:100%; border-collapse:collapse; font-size:14px; }
.tabla th, .tabla td { border-bottom:1px solid var(--line); padding:8px; text-align:left; }
.tabla th { background:#f1f5f9; color:var(--brand); }
form { display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:10px; align-items:end; }
label { display:grid; gap:5px; color:var(--muted); font-size:14px; }
input, select, button { height:38px; border:1px solid var(--line); border-radius:6px; padding:8px; }
form button { background:var(--brand); color:white; font-weight:700; cursor:pointer; }
.resultado { margin-top:16px; border-top:1px solid var(--line); padding-top:12px; }
.svggrid { display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:10px; margin:8px 0 14px; }
.svgbox { border:1px solid var(--line); border-radius:8px; padding:9px; background:#fbfdff; }
.svgbox b { display:block; font-size:13px; margin-bottom:2px; }
.svgbox svg { width:100%; display:block; cursor:zoom-in; }
.pasos-calculo { margin-top:18px; border:1px solid var(--line); border-radius:8px; padding:12px; }
.pasos-calculo summary { color:var(--brand); font-weight:700; cursor:pointer; }
.pasos-calculo h4 { margin:18px 0 8px; }
.pasos-calculo p { line-height:1.5; }
.puntos-detalle { margin-top:12px; }
.puntos-detalle .scroll { max-height:65vh; }
.salida-agregada { overflow:auto; border:1px solid var(--line); border-radius:8px; padding:8px; background:#fbfdff; }
.salida-agregada svg { display:block; min-width:620px; width:100%; }
.salida-agregada p { margin:4px 0; color:var(--muted); font-size:13px; }
.leyenda-salida { display:inline-block; width:11px; height:11px; margin-left:12px; border-radius:50%; }
.leyenda-salida.base { background:#24527a; }
.leyenda-salida.ga { background:#d97706; }
.visor-curva { position:fixed; inset:0; z-index:50; background:rgba(8,15,25,.94); color:white; }
.visor-curva[hidden] { display:none; }
.visor-curva-cabecera { position:absolute; inset:0 0 auto; height:58px; display:flex; align-items:center; gap:10px; padding:10px 16px; background:#17202a; }
.visor-curva-cabecera strong { margin-right:auto; }
.visor-curva button { min-width:40px; height:38px; border:1px solid #64748b; background:#263849; color:white; font-size:18px; cursor:pointer; }
.visor-curva .curva-cerrar { min-width:74px; font-size:14px; }
.visor-curva-pista { color:#d1d5db; font-size:12px; }
.curva-viewport { position:absolute; inset:58px 0 0; overflow:hidden; touch-action:none; cursor:grab; }
.curva-viewport.arrastrando { cursor:grabbing; }
.curva-ampliada { position:absolute; left:50%; top:50%; width:min(92vw, 1400px); transform:translate(-50%, -50%) scale(1); transform-origin:center; }
.curva-ampliada svg { display:block; width:100%; height:auto; background:#fbfdff; border-radius:8px; }
.leyenda { display:flex; flex-wrap:wrap; gap:8px; color:var(--muted); font-size:11px; }
.leyenda span { display:inline-flex; align-items:center; gap:4px; }
.leyenda i { width:9px; height:9px; border-radius:50%; display:inline-block; }
.galeria { display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:12px; }
.graf { border:1px solid var(--line); border-radius:8px; padding:10px; }
.graf img { width:100%; display:block; border-radius:6px; border:1px solid var(--line); margin-bottom:8px; }
.modal { display:none; position:fixed; inset:0; z-index:20; padding:22px; }
.modal:target { display:grid; place-items:center; }
.fondo { position:absolute; inset:0; background:rgba(15,23,42,.72); }
.visor { position:relative; max-width:1100px; max-height:92vh; overflow:auto; background:white; border-radius:8px; padding:16px; }
.visor img { width:100%; border:1px solid var(--line); border-radius:6px; }
.cerrar { float:right; background:var(--brand); color:white; border-radius:6px; padding:8px 10px; text-decoration:none; }
.alerta { color:#a33; font-weight:700; }
code { background:#eef2f7; padding:2px 5px; border-radius:4px; }
</style>
</head>
<body>
<!-- Encabezado fijo con el nombre del sistema y los dos métodos comparados. -->
<header><h1>Sistema genetico-difuso de riego</h1><p>Panel de resultados del modelo Mamdani + GA.</p></header>
<!-- Los botones cambian entre paneles sin cargar otra página. -->
<nav>
  $tabs
</nav>
<main>
  <!-- Tarjetas con el tamaño de la partición temporal y el cromosoma aprendido. -->
  <section id="resumen" class="$resumen_cls">
    <h2>Resumen</h2>
    <div class="cards">$resumen_cards</div>
    <div class="ficha">
      <div class="dato"><span>Problema</span><b>Volumen nominal de riego estandar en 24 h</b></div>
      <div class="dato"><span>Entradas</span><b>Humedad relativa al MADP; dias sin riego</b></div>
      <div class="dato"><span>Salida</span><b>Litros nominales defuzzificados</b></div>
      <div class="dato"><span>Resultado</span><b>GA mejora Base; mediana TRAIN queda menor en MAE</b></div>
    </div>
  </section>

  <!-- Formulario para probar una entrada nueva con el motor Mamdani. -->
  <section id="consulta" class="$consulta_cls">
    <h2>Consulta Mamdani</h2>
    <form method="get" action="/#consulta">
      <label>Sector<select name="sector">$sector_opts</select></label>
      <label>Humedad (0-100)<input name="humedad" type="text" inputmode="decimal" maxlength="5" data-max="100" data-max-digits="3" required value="$humedad_val"></label>
      <label>Dias (0-30)<input name="dias" type="text" inputmode="decimal" maxlength="5" data-max="30" data-max-digits="3" required value="$dias_val"></label>
      <button type="submit">Calcular</button>
    </form>
    $consulta
  </section>

  <!-- Resultados agregados, resultados por sector y reglas aprendidas. -->
  <section id="metricas" class="$metricas_cls">
    <h2>Metricas y reglas</h2>
    <div class="grid"><div><h3>Metricas</h3><div class="scroll">$metricas</div></div><div><h3>Por sector</h3><div class="scroll">$por_sector</div></div></div>
    <h3>Reglas</h3><div class="scroll">$reglas</div>
  </section>

  <!-- Predicciones individuales del periodo reservado para la prueba. -->
  <section id="testeo" class="$testeo_cls">
    <h2>Predicciones de TEST</h2><div class="scroll">$predicciones</div>
  </section>

  <!-- Galería creada a partir de las figuras generadas desde los datos. -->
  <section id="graficas" class="$graficas_cls">
    <h2>Graficas</h2><div class="galeria">$graficas</div>
  </section>

  <!-- Parámetros principales para ubicar los valores que usa el modelo. -->
  <section id="ficha" class="$ficha_cls">
    <h2>Ficha tecnica</h2>
    <div class="ficha">
      <div class="dato"><span>Humedad</span><b>-20, 0, 20</b></div>
      <div class="dato"><span>Dias</span><b>0.5, 1.5, 4.5</b></div>
      <div class="dato"><span>Salida</span><b>Q25, Q50, Q75 de TRAIN</b></div>
      <div class="dato"><span>GA</span><b>30 individuos, 50 generaciones</b></div>
      <div class="dato"><span>Mutacion</span><b>0.08 por gen</b></div>
      <div class="dato"><span>Caudal</span><b>1.1 L/min; sector 5: 0.4 L/min</b></div>
    </div>
  </section>
</main>
$modales
<!-- Visor compartido para ampliar cualquiera de las curvas de pertenencia. -->
<div id="visor-curva" class="visor-curva" role="dialog" aria-modal="true" aria-label="Curva de pertenencia ampliada" hidden>
  <div class="visor-curva-cabecera">
    <strong id="visor-curva-titulo">Curva de pertenencia</strong>
    <span class="visor-curva-pista">Rueda del ratón para zoom; arrastra para mover</span>
    <button type="button" id="curva-menos" aria-label="Alejar">−</button>
    <button type="button" id="curva-porcentaje" aria-label="Restablecer zoom">100%</button>
    <button type="button" id="curva-mas" aria-label="Acercar">+</button>
    <button type="button" id="curva-cerrar" class="curva-cerrar">Cerrar</button>
  </div>
  <div id="curva-viewport" class="curva-viewport">
    <div id="curva-ampliada" class="curva-ampliada"></div>
  </div>
</div>
<script>
// Muestra el panel solicitado y actualiza el botón que queda resaltado.
function ver(id) {
  document.querySelectorAll('main section').forEach(s => s.classList.toggle('activa', s.id === id));
  document.querySelectorAll('nav button').forEach(b => b.classList.toggle('activo', b.dataset.panel === id));
}
// Asigna la acción de cambio a cada botón de navegación.
document.querySelectorAll('nav button').forEach(b => b.onclick = () => ver(b.dataset.panel));
// Limpia la entrada mientras se escribe y limita sus dígitos y valor máximo.
document.querySelectorAll('input[data-max-digits]').forEach(campo => {
  campo.addEventListener('input', () => {
    // Acepta coma decimal y quita caracteres que no sean dígitos o punto.
    let v = campo.value.replace(',', '.').replace(/[^0-9.]/g, '');
    let p = v.split('.');
    // Si se escribieron varios puntos, conserva el primero como separador decimal.
    if (p.length > 2) v = p[0] + '.' + p.slice(1).join('');
    // Evita que el valor exceda la cantidad de dígitos permitida por el campo.
    while (v.replace(/\\D/g, '').length > Number(campo.dataset.maxDigits)) v = v.slice(0, -1);
    // Al pasar el máximo permitido, reemplaza el dato por ese límite.
    if (v && !v.endsWith('.') && Number(v) > Number(campo.dataset.max)) v = campo.dataset.max;
    campo.value = v;
  });
});

// Abre la curva seleccionada en pantalla completa y conserva su título.
const visorCurva = document.getElementById('visor-curva');
const curvaViewport = document.getElementById('curva-viewport');
const curvaAmpliada = document.getElementById('curva-ampliada');
const botonZoom = document.getElementById('curva-porcentaje');
let escalaCurva = 1;
let moverX = 0;
let moverY = 0;
let arrastre = null;

function actualizarCurva() {
  // Aplica zoom y desplazamiento sin modificar los puntos ni los datos del SVG.
  curvaAmpliada.style.transform = `translate(calc(-50% + ${moverX}px), calc(-50% + ${moverY}px)) scale(${escalaCurva})`;
  botonZoom.textContent = `${Math.round(escalaCurva * 100)}%`;
}

function cambiarZoom(cantidad) {
  // Evita que la imagen se vuelva demasiado pequeña o salga de control al ampliarla.
  escalaCurva = Math.max(0.5, Math.min(6, escalaCurva * cantidad));
  actualizarCurva();
}

document.querySelectorAll('.svgbox svg').forEach(svg => {
  svg.setAttribute('tabindex', '0');
  svg.setAttribute('aria-label', 'Abrir curva de pertenencia ampliada');
  svg.addEventListener('click', () => {
    const caja = svg.closest('.svgbox');
    document.getElementById('visor-curva-titulo').textContent = caja.querySelector('b').textContent;
    curvaAmpliada.replaceChildren(svg.cloneNode(true));
    escalaCurva = 1;
    moverX = 0;
    moverY = 0;
    actualizarCurva();
    visorCurva.hidden = false;
    document.body.style.overflow = 'hidden';
    document.getElementById('curva-cerrar').focus();
  });
  // Permite abrir el visor con Enter o la barra espaciadora, además del clic.
  svg.addEventListener('keydown', evento => {
    if (evento.key === 'Enter' || evento.key === ' ') {
      evento.preventDefault();
      svg.click();
    }
  });
});

function cerrarVisorCurva() {
  visorCurva.hidden = true;
  document.body.style.overflow = '';
  curvaAmpliada.replaceChildren();
}

document.getElementById('curva-cerrar').addEventListener('click', cerrarVisorCurva);
document.getElementById('curva-mas').addEventListener('click', () => cambiarZoom(1.25));
document.getElementById('curva-menos').addEventListener('click', () => cambiarZoom(0.8));
botonZoom.addEventListener('click', () => {
  escalaCurva = 1;
  moverX = 0;
  moverY = 0;
  actualizarCurva();
});

// La rueda amplía/reduce y conserva el puntero como referencia del zoom.
curvaViewport.addEventListener('wheel', evento => {
  evento.preventDefault();
  cambiarZoom(evento.deltaY < 0 ? 1.12 : 0.89);
}, { passive: false });

// Arrastrar con mouse o dedo permite recorrer la curva cuando está ampliada.
curvaViewport.addEventListener('pointerdown', evento => {
  arrastre = { x: evento.clientX - moverX, y: evento.clientY - moverY };
  curvaViewport.classList.add('arrastrando');
  curvaViewport.setPointerCapture(evento.pointerId);
});
curvaViewport.addEventListener('pointermove', evento => {
  if (!arrastre) return;
  moverX = evento.clientX - arrastre.x;
  moverY = evento.clientY - arrastre.y;
  actualizarCurva();
});
curvaViewport.addEventListener('pointerup', () => {
  arrastre = null;
  curvaViewport.classList.remove('arrastrando');
});

// Escape cierra el visor para volver rápidamente a la consulta.
document.addEventListener('keydown', evento => {
  if (evento.key === 'Escape' && !visorCurva.hidden) cerrarVisorCurva();
});
</script>
</body>
</html>""")


# ---------------------------------------------------------------------------
# Renderiza toda la pagina. Aqui se cargan CSV, se arma el cromosoma, se crean
# tablas, tarjetas, tabs y bloques visuales.
# ---------------------------------------------------------------------------
def renderizar_pagina(query: str = "") -> str:
    """Lee los resultados, rellena la plantilla y devuelve la página completa.

    `query` contiene los parámetros GET del formulario cuando se ejecuta una
    consulta. Devuelve el HTML listo para enviarse al navegador.
    """
    # Parametros GET del formulario: sector, humedad y dias.
    qs = parse_qs(query)

    # Conteos del dataset preparado: total, TRAIN, TEST y casos positivos.
    resumen = resumen_split()

    # CSV ya producidos por `python riego_simple/main.py`.
    metricas = leer_csv("metricas.csv")
    por_sector = leer_csv("metricas_por_sector.csv")
    reglas = leer_csv("reglas.csv")
    historial = leer_csv("historial_ga.csv")
    predicciones = leer_csv("predicciones.csv", parse_dates=["fecha"])

    # `reglas.csv` guarda etiquetas; aqui se reconstruye el vector numerico
    # necesario para consultar Mamdani + GA.
    reglas_ga = cromosoma_ga(reglas)
    cromosoma = "".join(str(x) for x in reglas_ga)

    # Mejor generacion segun fitness maximo en `historial_ga.csv`.
    mejor = historial.loc[historial["mejor_fitness"].idxmax()]

    # Bloques visuales auxiliares: graficas ampliables y consulta Mamdani.
    graficas, modales = bloque_graficas()
    consulta = bloque_consulta(qs, reglas_ga)

    # Si se calcularon parametros, la pantalla inicial queda en Consulta.
    activa = "consulta" if qs else "resumen"
    paneles = [
        ("resumen", "Resumen"),
        ("consulta", "Consulta"),
        ("metricas", "Metricas"),
        ("testeo", "Testeo"),
        ("graficas", "Graficas"),
        ("ficha", "Ficha"),
    ]
    tabs = "".join(
        f"<button type='button' data-panel='{pid}' class='{'activo' if pid == activa else ''}'>{nombre}</button>"
        for pid, nombre in paneles
    )
    clases = {f"{pid}_cls": "activa" if pid == activa else "" for pid, _ in paneles}

    # Tarjetas superiores del resumen. Son datos de trazabilidad para exposicion.
    resumen_cards = "".join([
        card("Total", resumen["total"]),
        card("TRAIN", resumen["train"]),
        card("Purga", resumen["purga"]),
        card("TEST", resumen["test"]),
        card("TRAIN +", resumen["train_pos"]),
        card("TEST +", resumen["test_pos"]),
        card("Cromosoma", cromosoma),
        card("Mejor gen.", int(mejor["generacion"])),
    ])

    # Opciones del selector de sector; conserva el valor elegido tras calcular.
    sector_actual = qs.get("sector", ["2"])[0]
    sector_opts = "".join(
        f"<option value='{s}' {'selected' if str(s) == sector_actual else ''}>{s}</option>"
        for s in range(1, 6)
    )

    # Sustituye todos los marcadores de la plantilla HTML.
    return PLANTILLA.safe_substitute(
        tabs=tabs,
        resumen_cards=resumen_cards,
        sector_opts=sector_opts,
        humedad_val=html.escape(qs.get("humedad", ["42"])[0]),
        dias_val=html.escape(qs.get("dias", ["0.8"])[0]),
        consulta=consulta,
        metricas=tabla(metricas, 8),
        por_sector=tabla(por_sector, 8),
        reglas=tabla(reglas, 12),
        predicciones=tabla(predicciones, 10),
        graficas=graficas,
        modales=modales,
        **clases,
    )


# ---------------------------------------------------------------------------
# Servidor HTTP minimo. La raiz entrega HTML y /img/nombre.png entrega graficas.
# ---------------------------------------------------------------------------
class AppHandler(BaseHTTPRequestHandler):
    """Atiende las páginas del panel y sirve las imágenes de sus gráficas."""

    def do_GET(self) -> None:  # noqa: N802
        """Resuelve las peticiones GET de la página principal y de las imágenes."""
        # Se separa la ruta de sus parámetros, por ejemplo humedad y días.
        url = urlparse(self.path)
        if url.path.startswith("/img/"):
            self.servir_imagen(url.path.removeprefix("/img/"))
            return
        if url.path in {"", "/"}:
            self.enviar_html(renderizar_pagina(url.query))
            return
        self.send_error(404, "Ruta no encontrada")

    def enviar_html(self, contenido: str) -> None:
        """Envía una página HTML con cabeceras y codificación UTF-8."""
        # Primero se transforma el texto en bytes porque HTTP transmite bytes.
        data = contenido.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def servir_imagen(self, nombre: str) -> None:
        """Envía una imagen de la carpeta permitida o responde que no existe."""
        # Path(...).name evita rutas externas como /img/../../archivo.
        ruta = IMAGENES_DIR / Path(unquote(nombre)).name
        if not ruta.exists() or ruta.parent != IMAGENES_DIR:
            self.send_error(404, "Imagen no encontrada")
            return
        data = ruta.read_bytes()
        # El tipo MIME permite al navegador reconocer PNG, SVG u otro formato.
        tipo = mimetypes.guess_type(str(ruta))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, formato: str, *args) -> None:
        """Muestra en consola cada solicitud recibida por el servidor local."""
        print(f"[interfaz] {self.address_string()} - {formato % args}")


# ---------------------------------------------------------------------------
# Punto de entrada. Permite cambiar host/puerto si 8000 esta ocupado.
# ---------------------------------------------------------------------------
def main() -> None:
    """Lee host y puerto, inicia el servidor y lo cierra al recibir Ctrl+C."""
    # Estos argumentos permiten elegir una dirección o un puerto alternativo.
    parser = argparse.ArgumentParser(description="Panel local del proyecto de riego.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    # El servidor admite solicitudes concurrentes y entrega el panel local.
    servidor = ThreadingHTTPServer((args.host, args.port), AppHandler)
    print(f"Panel disponible en http://{args.host}:{args.port}")
    print("Ctrl+C para detener.")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nPanel detenido.")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    # Solo inicia el servidor al ejecutar directamente este archivo.
    main()
