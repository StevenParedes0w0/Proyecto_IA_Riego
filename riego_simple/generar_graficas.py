"""Genera gráficas PNG directamente desde los datos y resultados del proyecto.

Ejecutar desde la raíz del repositorio después de correr main.py:
    python riego_simple/generar_graficas.py

Las imágenes se guardan en Informe-Riego-Simple/imagenes/origen_datos/.
"""

from pathlib import Path

# Selecciona un backend de Matplotlib que solo genera archivos, sin interfaz gráfica.
import matplotlib

matplotlib.use("Agg")  # Permite guardar imágenes sin abrir ventanas.
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Importa el motor que comparte esta carpeta: reutiliza sus rutas, validaciones,
# división temporal, funciones difusas y parámetros en vez de duplicarlos.
import main as proyecto

# Calcula las rutas a partir del archivo actual, no del directorio desde el que
# se ejecute Python; así los guardados encuentran el mismo destino desde raíz.
RAIZ = Path(__file__).resolve().parent.parent
# La salida tabular del modelo se encuentra junto a main.py.
CARPETA_RESULTADOS = proyecto.CARPETA_RESULTADOS
# Las figuras técnicas se guardan separadas de los recursos de portada del informe.
CARPETA_IMAGENES = RAIZ / "Informe-Riego-Simple" / "imagenes" / "origen_datos"
# Nombre exacto del target reconstruido por el preprocesamiento.
NOMBRE_OBJETIVO = "litros_nominales_riego_24h"

# Ajustes visuales compartidos por todas las figuras: tamaño, resolución,
# tipografía y cuadrícula tenue para facilitar lectura de escalas.
plt.rcParams.update({
    "figure.figsize": (9, 5.5),
    "figure.dpi": 120,
    "savefig.dpi": 180,
    "font.size": 10,
    "axes.grid": True,
    "grid.alpha": 0.25,
})


def guardar(figura: plt.Figure, nombre: str) -> None:
    """Crea la carpeta destino, escribe un PNG y libera la figura de memoria.

    Recibe el objeto Figure ya dibujado y el nombre final del archivo. La
    resolución de salida y el ajuste de márgenes se configuran antes de guardar.
    """
    # parents=True crea también carpetas intermedias y exist_ok evita error si ya existe.
    CARPETA_IMAGENES.mkdir(parents=True, exist_ok=True)
    # Combina carpeta y nombre para obtener una ruta portable en Windows/Linux.
    ruta = CARPETA_IMAGENES / nombre
    # tight_layout recoloca títulos y etiquetas; savefig rasteriza a PNG con fondo blanco.
    figura.tight_layout()
    figura.savefig(ruta, bbox_inches="tight", facecolor="white")
    # Cierra la figura tras guardarla para no acumular objetos gráficos en memoria.
    plt.close(figura)
    # Informa la ruta relativa de salida al usuario que ejecuta el script.
    print(f"Imagen generada: {ruta.relative_to(RAIZ)}")


def datos_y_resultados() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Carga TRAIN/TEST positivos y el historial guardado por el modelo.

    Llama al mismo lector y divisor del programa principal, filtra objetivos
    positivos después de separar el tiempo, verifica que estén las salidas de la
    última ejecución y devuelve las tablas requeridas por los gráficos.
    """
    # La función compartida valida columnas, mediciones, sectores y la purga temporal.
    train_todo, test_todo, _ = proyecto.leer_y_dividir_datos()
    # Las figuras modelan cantidad condicional: quita las filas sin riego en cada bloque.
    train = train_todo[train_todo[NOMBRE_OBJETIVO] > 0].copy()
    test = test_todo[test_todo[NOMBRE_OBJETIVO] > 0].copy()
    # Estos archivos los crea main.py; cada uno alimenta una gráfica específica.
    archivos = ["historial_ga.csv", "predicciones.csv", "metricas.csv", "metricas_por_sector.csv"]
    # Construye la lista de resultados requeridos que aún no existen.
    faltantes = [nombre for nombre in archivos if not (CARPETA_RESULTADOS / nombre).exists()]
    if faltantes:
        raise FileNotFoundError(
            "Primero ejecute `python riego_simple/main.py`; faltan: " + ", ".join(faltantes)
        )
    # Devuelve dos particiones para histogramas y el historial para evolución del GA.
    return (
        train,
        test,
        pd.read_csv(CARPETA_RESULTADOS / "historial_ga.csv"),
    )


def graficar_histogramas(train: pd.DataFrame, test: pd.DataFrame) -> None:
    """Genera tres histogramas de datos y un gráfico de conteos por sector.

    Usa observaciones positivas de TRAIN y TEST. La superposición permite
    comparar forma y dispersión; las barras por sector muestran el desbalance.
    """
    # Relaciona cada columna del CSV con la etiqueta horizontal y el PNG resultante.
    series = [
        (NOMBRE_OBJETIVO, "Volumen nominal positivo asociado al riego (L)",
         "01_histograma_volumen_train_test.png"),
        ("humedad_relativa_madp", "Humedad relativa al MADP", 
         "02_histograma_humedad_train_test.png"),
        ("dias_sin_riego", "Días desde el último riego estándar terminado",
         "03_histograma_recencia_train_test.png"),
    ]
    for columna, etiqueta, nombre in series:
        # Crea eje nuevo para que cada magnitud tenga su propia escala.
        figura, eje = plt.subplots()
        # Dibuja barras semitransparentes: azul para aprendizaje, naranja para prueba.
        eje.hist(train[columna], bins=24, alpha=0.65, label="TRAIN", color="#2878B5")
        eje.hist(test[columna], bins=24, alpha=0.60, label="TEST", color="#E07A2D")
        # Define título y nombres de ejes; leyenda identifica los periodos.
        eje.set(title=f"Distribución de {etiqueta.lower()}", xlabel=etiqueta, ylabel="Frecuencia")
        eje.legend()
        guardar(figura, nombre)

    # El cuarto gráfico cuenta únicamente los casos positivos por sector.
    figura, eje = plt.subplots()
    # Ubica TRAIN y TEST a ambos lados del centro de cada sector para compararlos.
    sectores = np.arange(1, 6)
    eje.bar(sectores - 0.18, train.groupby("sector").size().reindex(sectores, fill_value=0),
            width=0.36, label="TRAIN", color="#2878B5")
    eje.bar(sectores + 0.18, test.groupby("sector").size().reindex(sectores, fill_value=0),
            width=0.36, label="TEST", color="#E07A2D")
    eje.set(title="Casos positivos por sector", xlabel="Sector",
            ylabel="Observaciones positivas", xticks=sectores)
    eje.legend()
    guardar(figura, "04_casos_por_sector.png")


def graficar_modelo(test: pd.DataFrame) -> None:
    """Genera dispersión de predicciones, comparación de errores y serie temporal.

    Las predicciones y métricas se leen de los CSV producidos por main.py; por eso
    esta función no vuelve a entrenar el modelo ni usa TEST para ajustar parámetros.
    """
    # Convierte fecha a datetime para que el archivo quede preparado para ejes de tiempo.
    predicciones = pd.read_csv(CARPETA_RESULTADOS / "predicciones.csv", parse_dates=["fecha"])
    # Crea un eje para comparar predicción GA con objetivo reconstruido por muestra.
    figura, eje = plt.subplots()
    colores = {1: "#2878B5", 2: "#E07A2D", 3: "#3A9D5D", 4: "#8B5FBF", 5: "#C74B50"}
    # Agrupa por sector y dibuja una serie de puntos con color identificador.
    for sector, casos in predicciones.groupby("sector"):
        eje.scatter(casos["litros_nominales_objetivo"], casos["litros_ga"],
                    s=34, alpha=0.8, label=f"Sector {sector}", color=colores[int(sector)])
    # Usa el mayor dato en ambos ejes para que la diagonal tenga escala común.
    limite = max(predicciones["litros_nominales_objetivo"].max(), predicciones["litros_ga"].max())
    # La recta y=x representa predicción idéntica al objetivo, solo como referencia.
    eje.plot([0, limite], [0, limite], "k--", linewidth=1, label="Estimación perfecta")
    eje.set(title="Volumen nominal observado y estimado por Mamdani + GA",
            xlabel="Objetivo reconstruido en TEST (L)", ylabel="Estimación del modelo (L)")
    eje.legend(ncol=2)
    guardar(figura, "05_objetivo_vs_estimacion_test.png")

    # Lee la tabla agregada con MAE, RMSE y MedAE; esta figura compara MAE.
    metricas = pd.read_csv(CARPETA_RESULTADOS / "metricas.csv")
    figura, eje = plt.subplots()
    barras = eje.bar(metricas["modelo"], metricas["mae_litros"], color=[
        "#2878B5", "#3A9D5D", "#777777", "#A0A0A0"
    ])
    # Imprime el valor numérico encima de cada barra para lectura sin estimar escala.
    eje.bar_label(barras, fmt="%.1f", padding=3)
    eje.set(title="Error absoluto medio en el periodo TEST", ylabel="MAE (L)")
    eje.tick_params(axis="x", labelrotation=15)
    guardar(figura, "06_comparacion_mae_test.png")

    # Carga la evaluación por sector, que mantiene NaN si no hubo casos positivos.
    por_sector = pd.read_csv(CARPETA_RESULTADOS / "metricas_por_sector.csv")
    # Asigna posiciones separadas para dibujar pares de barras de cada sector.
    posiciones = np.arange(len(por_sector))
    ancho = 0.36
    figura, eje = plt.subplots()
    # Dibuja lado a lado los errores de reglas manuales y reglas optimizadas por GA.
    eje.bar(posiciones - ancho / 2, por_sector["mae_base_litros"], ancho,
            label="Mamdani Base", color="#2878B5")
    eje.bar(posiciones + ancho / 2, por_sector["mae_ga_litros"], ancho,
            label="Mamdani + GA", color="#3A9D5D")
    eje.set(title="MAE de TEST por sector", xlabel="Sector", ylabel="MAE (L)",
            xticks=posiciones, xticklabels=por_sector["sector"].astype(str))
    eje.legend()
    guardar(figura, "07_mae_por_sector_test.png")

    # Representa cada objetivo positivo según fecha para exponer variación temporal.
    figura, eje = plt.subplots()
    eje.plot(test["fecha"], test[NOMBRE_OBJETIVO], marker="o", linestyle="none",
             alpha=0.75, color="#2878B5")
    eje.set(title="Volumen nominal positivo observado durante TEST",
            xlabel="Fecha de decisión (06:00)", ylabel="Volumen objetivo (L)")
    figura.autofmt_xdate()
    guardar(figura, "08_objetivos_en_el_tiempo_test.png")


def graficar_aprendizaje(train: pd.DataFrame, historial: pd.DataFrame) -> None:
    """Genera curva de aprendizaje y visualizaciones de las funciones difusas.

    El historial muestra el mejor MAE TRAIN en cada generación. Las entradas usan
    los puntos configurados en main.py; los conjuntos de salida se vuelven a
    construir llamando la función del proyecto sobre los litros positivos TRAIN.
    """
    # Cada fila del historial se origina en evaluar la población del GA sobre TRAIN.
    figura, eje = plt.subplots()
    eje.plot(historial["generacion"], historial["mejor_mae_litros_train"],
             label="Mejor MAE TRAIN", color="#2878B5")
    eje.set(title="Evolución del algoritmo genético sobre TRAIN",
            xlabel="Generación", ylabel="MAE en TRAIN (L)")
    eje.legend()
    guardar(figura, "09_evolucion_ga_train.png")

    # Dos paneles independientes: uno para humedad relativa y otro para recencia.
    figura, ejes = plt.subplots(1, 2, figsize=(11, 4.8))
    # Las mallas x solo definen resolución visual; las curvas vienen de tres_grados.
    humedad = np.linspace(-30, 30, 400)
    dias = np.linspace(0, 8, 400)
    colores = ["#2878B5", "#3A9D5D", "#C74B50"]
    # Itera Baja/Media/Alta; cada columna de tres_grados es un término difuso.
    for i, etiqueta in enumerate(proyecto.ETIQUETAS_HUMEDAD):
        ejes[0].plot(humedad, proyecto.tres_grados(humedad, -20, 0, 20)[:, i],
                     label=etiqueta, color=colores[i])
    # Repite el trazado para Reciente/Intermedio/Lejano con otros puntos de quiebre.
    for i, etiqueta in enumerate(proyecto.ETIQUETAS_DIAS):
        ejes[1].plot(dias, proyecto.tres_grados(dias, 0.5, 1.5, 4.5)[:, i],
                     label=etiqueta, color=colores[i])
    ejes[0].set(title="Humedad relativa al MADP", xlabel="Diferencia respecto al MADP", ylabel="Pertenencia")
    ejes[1].set(title="Recencia del riego estándar", xlabel="Días desde el último riego", ylabel="Pertenencia")
    # Limita los grados al intervalo difuso [0,1] y añade leyenda a ambos paneles.
    for eje in ejes:
        eje.set_ylim(-0.03, 1.05)
        eje.legend()
    guardar(figura, "10_funciones_pertenencia_entradas.png")

    # Extrae la etiqueta positiva TRAIN; el conjunto de salida no mira TEST.
    positivos_train = train[NOMBRE_OBJETIVO].to_numpy(float)
    # Reutiliza los cuantiles, universo y pertenencias que usa el motor Mamdani.
    universo, conjuntos, _ = proyecto.preparar_salida(positivos_train)
    figura, eje = plt.subplots()
    for i, etiqueta in enumerate(proyecto.ETIQUETAS_SALIDA):
        eje.plot(universo, conjuntos[i], label=etiqueta, color=colores[i])
    eje.set(title="Conjuntos difusos de salida definidos con TRAIN",
            xlabel="Volumen nominal (L)", ylabel="Pertenencia", ylim=(-0.03, 1.05))
    eje.legend()
    guardar(figura, "11_conjuntos_salida_train.png")


def main() -> None:
    """Punto de entrada: carga fuentes y llama a los tres grupos de gráficas."""
    # Primero valida que existen los datos/modelo; luego dibuja distribuciones,
    # resultados y parámetros difusos en archivos PNG separados.
    train, test, historial = datos_y_resultados()
    graficar_histogramas(train, test)
    graficar_modelo(test)
    graficar_aprendizaje(train, historial)
    print(f"\nListo: {CARPETA_IMAGENES.relative_to(RAIZ)}")


if __name__ == "__main__":
    # Evita generar archivos si este módulo solo se importa desde otro programa.
    main()
