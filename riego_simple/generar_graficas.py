"""Genera gráficas PNG directamente desde los datos y resultados del proyecto.

Ejecutar desde la raíz del repositorio después de correr main.py:
    python riego_simple/generar_graficas.py

Las imágenes se guardan en Informe-Riego-Simple/imagenes/origen_datos/.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # Permite guardar imágenes sin abrir ventanas.
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import main as proyecto


RAIZ = Path(__file__).resolve().parent.parent
CARPETA_RESULTADOS = proyecto.CARPETA_RESULTADOS
CARPETA_IMAGENES = RAIZ / "Informe-Riego-Simple" / "imagenes" / "origen_datos"
NOMBRE_OBJETIVO = "litros_nominales_riego_24h"

plt.rcParams.update({
    "figure.figsize": (9, 5.5),
    "figure.dpi": 120,
    "savefig.dpi": 180,
    "font.size": 10,
    "axes.grid": True,
    "grid.alpha": 0.25,
})


def guardar(figura: plt.Figure, nombre: str) -> None:
    """Guarda una figura y cierra su ventana para liberar memoria."""
    CARPETA_IMAGENES.mkdir(parents=True, exist_ok=True)
    ruta = CARPETA_IMAGENES / nombre
    figura.tight_layout()
    figura.savefig(ruta, bbox_inches="tight", facecolor="white")
    plt.close(figura)
    print(f"Imagen generada: {ruta.relative_to(RAIZ)}")


def datos_y_resultados() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Lee la partición temporal del CSV y las salidas de la última ejecución."""
    train_todo, test_todo, _ = proyecto.leer_y_dividir_datos()
    train = train_todo[train_todo[NOMBRE_OBJETIVO] > 0].copy()
    test = test_todo[test_todo[NOMBRE_OBJETIVO] > 0].copy()
    archivos = ["historial_ga.csv", "predicciones.csv", "metricas.csv", "metricas_por_sector.csv"]
    faltantes = [nombre for nombre in archivos if not (CARPETA_RESULTADOS / nombre).exists()]
    if faltantes:
        raise FileNotFoundError(
            "Primero ejecute `python riego_simple/main.py`; faltan: " + ", ".join(faltantes)
        )
    return (
        train,
        test,
        pd.read_csv(CARPETA_RESULTADOS / "historial_ga.csv"),
    )


def graficar_histogramas(train: pd.DataFrame, test: pd.DataFrame) -> None:
    """Compara distribuciones observadas de volumen, humedad y recencia."""
    series = [
        (NOMBRE_OBJETIVO, "Volumen nominal positivo asociado al riego (L)",
         "01_histograma_volumen_train_test.png"),
        ("humedad_relativa_madp", "Humedad relativa al MADP", 
         "02_histograma_humedad_train_test.png"),
        ("dias_sin_riego", "Días desde el último riego estándar terminado",
         "03_histograma_recencia_train_test.png"),
    ]
    for columna, etiqueta, nombre in series:
        figura, eje = plt.subplots()
        eje.hist(train[columna], bins=24, alpha=0.65, label="TRAIN", color="#2878B5")
        eje.hist(test[columna], bins=24, alpha=0.60, label="TEST", color="#E07A2D")
        eje.set(title=f"Distribución de {etiqueta.lower()}", xlabel=etiqueta, ylabel="Frecuencia")
        eje.legend()
        guardar(figura, nombre)

    figura, eje = plt.subplots()
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
    """Grafica predicciones y métricas de la salida evaluada en TEST."""
    predicciones = pd.read_csv(CARPETA_RESULTADOS / "predicciones.csv", parse_dates=["fecha"])
    figura, eje = plt.subplots()
    colores = {1: "#2878B5", 2: "#E07A2D", 3: "#3A9D5D", 4: "#8B5FBF", 5: "#C74B50"}
    for sector, casos in predicciones.groupby("sector"):
        eje.scatter(casos["litros_nominales_objetivo"], casos["litros_ga"],
                    s=34, alpha=0.8, label=f"Sector {sector}", color=colores[int(sector)])
    limite = max(predicciones["litros_nominales_objetivo"].max(), predicciones["litros_ga"].max())
    eje.plot([0, limite], [0, limite], "k--", linewidth=1, label="Estimación perfecta")
    eje.set(title="Volumen nominal observado y estimado por Mamdani + GA",
            xlabel="Objetivo reconstruido en TEST (L)", ylabel="Estimación del modelo (L)")
    eje.legend(ncol=2)
    guardar(figura, "05_objetivo_vs_estimacion_test.png")

    metricas = pd.read_csv(CARPETA_RESULTADOS / "metricas.csv")
    figura, eje = plt.subplots()
    barras = eje.bar(metricas["modelo"], metricas["mae_litros"], color=[
        "#2878B5", "#3A9D5D", "#777777", "#A0A0A0"
    ])
    eje.bar_label(barras, fmt="%.1f", padding=3)
    eje.set(title="Error absoluto medio en el periodo TEST", ylabel="MAE (L)")
    eje.tick_params(axis="x", labelrotation=15)
    guardar(figura, "06_comparacion_mae_test.png")

    por_sector = pd.read_csv(CARPETA_RESULTADOS / "metricas_por_sector.csv")
    posiciones = np.arange(len(por_sector))
    ancho = 0.36
    figura, eje = plt.subplots()
    eje.bar(posiciones - ancho / 2, por_sector["mae_base_litros"], ancho,
            label="Mamdani Base", color="#2878B5")
    eje.bar(posiciones + ancho / 2, por_sector["mae_ga_litros"], ancho,
            label="Mamdani + GA", color="#3A9D5D")
    eje.set(title="MAE de TEST por sector", xlabel="Sector", ylabel="MAE (L)",
            xticks=posiciones, xticklabels=por_sector["sector"].astype(str))
    eje.legend()
    guardar(figura, "07_mae_por_sector_test.png")

    figura, eje = plt.subplots()
    eje.plot(test["fecha"], test[NOMBRE_OBJETIVO], marker="o", linestyle="none",
             alpha=0.75, color="#2878B5")
    eje.set(title="Volumen nominal positivo observado durante TEST",
            xlabel="Fecha de decisión (06:00)", ylabel="Volumen objetivo (L)")
    figura.autofmt_xdate()
    guardar(figura, "08_objetivos_en_el_tiempo_test.png")


def graficar_aprendizaje(train: pd.DataFrame, historial: pd.DataFrame) -> None:
    """Muestra el progreso del GA y las funciones difusas definidas por el modelo."""
    figura, eje = plt.subplots()
    eje.plot(historial["generacion"], historial["mejor_mae_litros_train"],
             label="Mejor MAE TRAIN", color="#2878B5")
    eje.set(title="Evolución del algoritmo genético sobre TRAIN",
            xlabel="Generación", ylabel="MAE en TRAIN (L)")
    eje.legend()
    guardar(figura, "09_evolucion_ga_train.png")

    figura, ejes = plt.subplots(1, 2, figsize=(11, 4.8))
    humedad = np.linspace(-30, 30, 400)
    dias = np.linspace(0, 8, 400)
    colores = ["#2878B5", "#3A9D5D", "#C74B50"]
    for i, etiqueta in enumerate(proyecto.ETIQUETAS_HUMEDAD):
        ejes[0].plot(humedad, proyecto.tres_grados(humedad, -20, 0, 20)[:, i],
                     label=etiqueta, color=colores[i])
    for i, etiqueta in enumerate(proyecto.ETIQUETAS_DIAS):
        ejes[1].plot(dias, proyecto.tres_grados(dias, 0.5, 1.5, 4.5)[:, i],
                     label=etiqueta, color=colores[i])
    ejes[0].set(title="Humedad relativa al MADP", xlabel="Diferencia respecto al MADP", ylabel="Pertenencia")
    ejes[1].set(title="Recencia del riego estándar", xlabel="Días desde el último riego", ylabel="Pertenencia")
    for eje in ejes:
        eje.set_ylim(-0.03, 1.05)
        eje.legend()
    guardar(figura, "10_funciones_pertenencia_entradas.png")

    positivos_train = train[NOMBRE_OBJETIVO].to_numpy(float)
    universo, conjuntos, _ = proyecto.preparar_salida(positivos_train)
    figura, eje = plt.subplots()
    for i, etiqueta in enumerate(proyecto.ETIQUETAS_SALIDA):
        eje.plot(universo, conjuntos[i], label=etiqueta, color=colores[i])
    eje.set(title="Conjuntos difusos de salida definidos con TRAIN",
            xlabel="Volumen nominal (L)", ylabel="Pertenencia", ylim=(-0.03, 1.05))
    eje.legend()
    guardar(figura, "11_conjuntos_salida_train.png")


def main() -> None:
    """Genera el conjunto completo de gráficas reproducibles del proyecto."""
    train, test, historial = datos_y_resultados()
    graficar_histogramas(train, test)
    graficar_modelo(test)
    graficar_aprendizaje(train, historial)
    print(f"\nListo: {CARPETA_IMAGENES.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
