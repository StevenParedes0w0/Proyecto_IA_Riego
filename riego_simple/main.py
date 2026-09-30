"""Estima volumen nominal de riego con Mamdani y un algoritmo genético.

Ejecutar desde la raíz: python riego_simple/main.py
Este archivo se lee de arriba hacia abajo para facilitar su defensa oral.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# 1. CONFIGURACIÓN
# ============================================================
CARPETA = Path(__file__).resolve().parent
ARCHIVO_DATOS = CARPETA / "datos_riego.csv"
CARPETA_RESULTADOS = CARPETA / "resultados"
ORIGEN = CARPETA.parent / "datasets" / "arnesano_2025" / "02_processed_data"

# Este corte se fijó en la versión anterior. No se mueve según las métricas nuevas.
FECHA_CORTE = pd.Timestamp("2025-06-28 06:00:00")
MADP_POR_SECTOR = {1: 40, 2: 40, 3: 60, 4: 80, 5: 70}
CAUDAL_POR_SECTOR = {1: 1.1, 2: 1.1, 3: 1.1, 4: 1.1, 5: 0.4}  # L/min
ETIQUETAS_HUMEDAD = ("Baja", "Media", "Alta")
ETIQUETAS_DIAS = ("Reciente", "Intermedio", "Lejano")
ETIQUETAS_SALIDA = ("Baja", "Media", "Alta")

# Cada número es el conjunto difuso de salida de una regla: 0=Baja, 1=Media, 2=Alta.
# Orden: humedad Baja/Media/Alta × días Reciente/Intermedio/Lejano.
REGLAS_BASE = np.array([1, 2, 2, 0, 1, 2, 0, 0, 1], dtype=int)

TAMANO_POBLACION = 30
GENERACIONES = 50
PROB_MUTACION = 0.08
SEMILLA = 42


# ============================================================
# 2. PREPARACIÓN DE DATOS
# ============================================================
def resumir_riego_ventana(eventos: pd.DataFrame, inicio: pd.Timestamp, sector: int) -> tuple[int, float]:
    """Suma duración solapada × caudal nominal, solo para riego estándar."""
    fin_ventana = inicio + pd.Timedelta(days=1)
    cantidad_eventos = 0
    litros = 0.0
    for evento in eventos.itertuples(index=False):
        if evento.type != "standard_irrigation" or evento.sector != sector:
            continue
        inicio_solapado = max(inicio, evento.start)
        fin_solapado = min(fin_ventana, evento.end)
        minutos = max(0.0, (fin_solapado - inicio_solapado).total_seconds() / 60)
        if minutos > 0:
            cantidad_eventos += 1
            litros += minutos * CAUDAL_POR_SECTOR[sector]
    return cantidad_eventos, litros


def preparar_datos() -> pd.DataFrame:
    """Reconstruye una observación por sector y día con información previa a las 06:00."""
    archivo_eventos = ORIGEN / "irrigation_events" / "final_irrigation_events.csv"
    if not archivo_eventos.exists():
        raise FileNotFoundError(f"Falta la fuente original: {archivo_eventos}")
    eventos = pd.read_csv(archivo_eventos, parse_dates=["start", "end"])
    estandar = eventos[eventos["type"].eq("standard_irrigation")]
    ultimo_dia = estandar["end"].max().normalize()
    filas = []

    for sector, madp in MADP_POR_SECTOR.items():
        sensores = pd.read_csv(
            ORIGEN / "merged" / f"dataset_zone_{sector}.csv",
            usecols=["ts", "soil_moisture"],
        )
        # ts marca el INICIO de un promedio de diez minutos; solo existe al terminar.
        sensores["ts"] = pd.to_datetime(sensores["ts"]) + pd.Timedelta(minutes=10)
        sensores = sensores[sensores["soil_moisture"].between(0, 100)].sort_values("ts")

        eventos_sector = eventos[eventos["sector"].eq(sector)]
        estandar_sector = estandar[estandar["sector"].eq(sector)]
        finales = np.sort(estandar_sector["end"].to_numpy(dtype="datetime64[ns]"))
        fechas = pd.date_range(
            sensores["ts"].min().normalize(), ultimo_dia - pd.Timedelta(days=1), freq="D"
        ) + pd.Timedelta(hours=6)
        decisiones = pd.merge_asof(
            pd.DataFrame({"fecha": fechas}),
            sensores.rename(columns={"ts": "medicion"}),
            left_on="fecha", right_on="medicion", direction="backward",
            tolerance=pd.Timedelta(hours=8),
        ).dropna(subset=["soil_moisture"])

        for fila in decisiones.itertuples(index=False):
            ahora = fila.fecha
            # Si alguna válvula ya está abierta, esta fila no es una decisión nueva.
            abierta = ((eventos_sector["start"] < ahora) & (eventos_sector["end"] > ahora)).any()
            if abierta:
                continue

            anterior = np.searchsorted(finales, np.datetime64(ahora), side="right") - 1
            dias_sin_riego = (
                min(30.0, float((np.datetime64(ahora) - finales[anterior]) / np.timedelta64(1, "D")))
                if anterior >= 0 else 30.0
            )
            numero_eventos, litros = resumir_riego_ventana(eventos_sector, ahora, sector)
            humedad = float(fila.soil_moisture)
            filas.append({
                "fecha": ahora,
                "medicion": fila.medicion,
                "sector": sector,
                "humedad_suelo": humedad,
                "madp_sector": madp,
                "humedad_relativa_madp": humedad - madp,
                "dias_sin_riego": dias_sin_riego,
                "numero_eventos_riego_24h": numero_eventos,
                "litros_nominales_riego_24h": litros,
            })

    datos = pd.DataFrame(filas).sort_values(["fecha", "sector"]).reset_index(drop=True)
    datos.to_csv(ARCHIVO_DATOS, index=False)
    return datos


# ============================================================
# 3. DIVISIÓN TEMPORAL
# ============================================================
def leer_y_dividir_datos() -> tuple[pd.DataFrame, pd.DataFrame, int]:
    """Divide TODA la cronología antes de seleccionar los casos con riego."""
    if not ARCHIVO_DATOS.exists():
        raise FileNotFoundError(f"Falta {ARCHIVO_DATOS}. Ejecute con --preparar.")
    datos = pd.read_csv(ARCHIVO_DATOS, parse_dates=["fecha", "medicion"])
    necesarias = [
        "fecha", "medicion", "sector", "humedad_suelo", "madp_sector",
        "humedad_relativa_madp", "dias_sin_riego", "numero_eventos_riego_24h",
        "litros_nominales_riego_24h",
    ]
    if datos[necesarias].isna().any().any():
        raise ValueError("El CSV contiene valores faltantes en columnas necesarias.")
    if (datos["medicion"] > datos["fecha"]).any():
        raise ValueError("Hay una medición posterior a las 06:00.")
    if not datos["sector"].isin(MADP_POR_SECTOR).all():
        raise ValueError("Hay un sector sin MADP o caudal documentado.")
    if (datos["litros_nominales_riego_24h"] < 0).any():
        raise ValueError("El volumen nominal no puede ser negativo.")
    if ((datos["numero_eventos_riego_24h"] == 0) !=
            (datos["litros_nominales_riego_24h"] == 0)).any():
        raise ValueError("Número de eventos y litros no coinciden.")

    # La etiqueta del 27 de junio observa hasta el 28; por ello se purga ese día.
    train = datos[datos["fecha"] < FECHA_CORTE - pd.Timedelta(days=1)].copy()
    test = datos[datos["fecha"] >= FECHA_CORTE].copy()
    purgados = len(datos) - len(train) - len(test)
    if not len(train) or not len(test) or purgados == 0:
        raise ValueError("La división temporal o su día de purga están vacíos.")
    return train, test, purgados


# ============================================================
# 4. FUNCIONES DE PERTENENCIA
# ============================================================
def tres_grados(valores: np.ndarray, bajo: float, centro: float, alto: float) -> np.ndarray:
    """Rampa Baja, triángulo Media y rampa Alta: grados, no probabilidades."""
    valores = np.asarray(valores, dtype=float)
    baja = np.clip((centro - valores) / (centro - bajo), 0, 1)
    alta = np.clip((valores - centro) / (alto - centro), 0, 1)
    media = 1 - baja - alta
    return np.column_stack([baja, media, alta])


def fuzzificar(datos: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Activa las nueve reglas con AND = mínimo de dos pertenencias."""
    humedad = tres_grados(datos["humedad_relativa_madp"].to_numpy(), -20, 0, 20)
    dias = tres_grados(datos["dias_sin_riego"].to_numpy(), 0.5, 1.5, 4.5)
    activaciones = np.minimum(humedad[:, :, None], dias[:, None, :]).reshape(len(datos), 9)
    return humedad, dias, activaciones


def preparar_salida(litros_train: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Define conjuntos Baja/Media/Alta SOLO con los litros positivos de TRAIN."""
    if len(litros_train) == 0 or np.any(litros_train <= 0):
        raise ValueError("La salida requiere casos positivos de entrenamiento.")
    q25, q50, q75 = np.quantile(litros_train, [0.25, 0.50, 0.75])
    if not q25 < q50 < q75:
        raise ValueError("Los cuantiles de TRAIN no permiten tres conjuntos distintos.")
    universo = np.linspace(0, float(np.max(litros_train)), 501)
    conjuntos = tres_grados(universo, q25, q50, q75).T
    return universo, conjuntos, np.array([q25, q50, q75])


# ============================================================
# 5. INFERENCIA MAMDANI CONTINUA
# ============================================================
def inferir_mamdani(
    activaciones: np.ndarray, cromosoma: np.ndarray,
    universo: np.ndarray, conjuntos_salida: np.ndarray,
) -> np.ndarray:
    """Implica por min, agrega por max y defuzzifica directamente en litros."""
    if len(cromosoma) != 9 or not np.isin(cromosoma, [0, 1, 2]).all():
        raise ValueError("El cromosoma requiere nueve consecuentes de {0,1,2}.")
    grados_salida = np.column_stack([
        np.max(np.where(cromosoma == termino, activaciones, 0), axis=1)
        for termino in range(3)
    ])
    # Cada gen elige un conjunto Baja/Media/Alta; min trunca y max une reglas.
    agregada = np.maximum.reduce([
        np.minimum(grados_salida[:, termino, None], conjuntos_salida[termino])
        for termino in range(3)
    ])
    area = agregada.sum(axis=1)
    return np.divide(
        (agregada * universo).sum(axis=1), area,
        out=np.zeros(len(area)), where=area > 0,
    )


# ============================================================
# 6. ALGORITMO GENÉTICO
# ============================================================
def calcular_mae(reales: np.ndarray, estimados: np.ndarray) -> float:
    return float(np.mean(np.abs(reales - estimados)))


def calcular_fitness(
    cromosoma: np.ndarray, activaciones: np.ndarray, reales: np.ndarray,
    universo: np.ndarray, conjuntos_salida: np.ndarray,
) -> float:
    # Menos error absoluto en litros -> fitness mayor; solo se usa TRAIN.
    estimados = inferir_mamdani(activaciones, cromosoma, universo, conjuntos_salida)
    return 1.0 / (1.0 + calcular_mae(reales, estimados))


def mutar(cromosoma: np.ndarray, azar: np.random.Generator) -> np.ndarray:
    """Si un gen muta, se reemplaza por uno de los OTROS dos consecuentes."""
    hijo = cromosoma.copy()
    cambia = azar.random(9) < PROB_MUTACION
    hijo[cambia] = (hijo[cambia] + azar.integers(1, 3, size=int(cambia.sum()))) % 3
    return hijo


def ejecutar_ga(
    activaciones: np.ndarray, reales: np.ndarray,
    universo: np.ndarray, conjuntos_salida: np.ndarray,
) -> tuple[np.ndarray, pd.DataFrame]:
    """Ruleta, cruce de un punto, mutación ternaria y elitismo sobre nueve genes."""
    azar = np.random.default_rng(SEMILLA)
    poblacion = azar.integers(0, 3, size=(TAMANO_POBLACION, 9))
    mejor = poblacion[0].copy()
    mejor_fitness = -1.0
    historial = []

    for generacion in range(GENERACIONES + 1):
        fitness = np.array([
            calcular_fitness(individuo, activaciones, reales, universo, conjuntos_salida)
            for individuo in poblacion
        ])
        indice = int(np.argmax(fitness))
        if fitness[indice] > mejor_fitness:
            mejor, mejor_fitness = poblacion[indice].copy(), float(fitness[indice])
        historial.append({
            "generacion": generacion,
            "mejor_fitness": mejor_fitness,
            "mejor_mae_litros_train": 1 / mejor_fitness - 1,
            "fitness_promedio": float(fitness.mean()),
        })
        if generacion == GENERACIONES:
            break

        nueva = [mejor.copy()]  # Elitismo: conservar el mejor sin mutarlo.
        while len(nueva) < TAMANO_POBLACION:
            padre1 = poblacion[azar.choice(len(poblacion), p=fitness / fitness.sum())]
            padre2 = poblacion[azar.choice(len(poblacion), p=fitness / fitness.sum())]
            punto = int(azar.integers(1, 9))
            hijo = np.concatenate([padre1[:punto], padre2[punto:]])
            nueva.append(mutar(hijo, azar))
        poblacion = np.array(nueva)

    return mejor, pd.DataFrame(historial)


# ============================================================
# 7. EVALUACIÓN Y CONSULTA MANUAL
# ============================================================
def evaluar_modelo(nombre: str, reales: np.ndarray, estimados: np.ndarray) -> dict:
    errores = reales - estimados
    return {
        "modelo": nombre,
        "mae_litros": float(np.mean(np.abs(errores))),
        "rmse_litros": float(np.sqrt(np.mean(errores ** 2))),
        "medae_litros": float(np.median(np.abs(errores))),
    }


def tabla_reglas(reglas_ga: np.ndarray) -> pd.DataFrame:
    filas = []
    for humedad in range(3):
        for dias in range(3):
            numero = 3 * humedad + dias
            filas.append({
                "regla": f"R{numero + 1}",
                "humedad": ETIQUETAS_HUMEDAD[humedad],
                "dias_sin_riego": ETIQUETAS_DIAS[dias],
                "consecuente_base": ETIQUETAS_SALIDA[REGLAS_BASE[numero]],
                "consecuente_ga": ETIQUETAS_SALIDA[reglas_ga[numero]],
            })
    return pd.DataFrame(filas)


def consultar_caso(
    sector: int, humedad_actual: float, dias_sin_riego: float,
    reglas_ga: np.ndarray, universo: np.ndarray, conjuntos_salida: np.ndarray,
) -> dict:
    """Explica grados, reglas activadas y dos estimaciones condicionales en litros."""
    madp = MADP_POR_SECTOR[sector]
    caso = pd.DataFrame({
        "humedad_relativa_madp": [humedad_actual - madp],
        "dias_sin_riego": [min(dias_sin_riego, 30)],
    })
    grados_h, grados_d, activaciones = fuzzificar(caso)
    activadas = []
    for indice, grado in enumerate(activaciones[0]):
        if grado > 0:
            activadas.append({
                "regla": f"R{indice + 1}",
                "humedad": ETIQUETAS_HUMEDAD[indice // 3],
                "dias": ETIQUETAS_DIAS[indice % 3],
                "grado": float(grado),
                "base": ETIQUETAS_SALIDA[REGLAS_BASE[indice]],
                "ga": ETIQUETAS_SALIDA[reglas_ga[indice]],
            })
    return {
        "madp": madp, "humedad_relativa": humedad_actual - madp,
        "grados_humedad": grados_h[0], "grados_dias": grados_d[0],
        "reglas_activadas": activadas,
        "litros_base": float(inferir_mamdani(activaciones, REGLAS_BASE, universo, conjuntos_salida)[0]),
        "litros_ga": float(inferir_mamdani(activaciones, reglas_ga, universo, conjuntos_salida)[0]),
    }


# ============================================================
# 8. PROGRAMA PRINCIPAL
# ============================================================
def ejecutar(args: argparse.Namespace) -> None:
    if args.preparar:
        datos = preparar_datos()
        print(f"Datos preparados: {len(datos)} decisiones en {ARCHIVO_DATOS}")

    train_todo, test_todo, purgados = leer_y_dividir_datos()
    # El corte y la purga se aplican ANTES de filtrar casos con riego.
    train = train_todo[train_todo["litros_nominales_riego_24h"] > 0].copy()
    test = test_todo[test_todo["litros_nominales_riego_24h"] > 0].copy()
    if train.empty or test.empty:
        raise ValueError("Se necesitan casos de cantidad en TRAIN y TEST.")

    reales_train = train["litros_nominales_riego_24h"].to_numpy(float)
    reales_test = test["litros_nominales_riego_24h"].to_numpy(float)
    universo, conjuntos_salida, puntos = preparar_salida(reales_train)
    activaciones_train = fuzzificar(train)[2]
    reglas_ga, historial = ejecutar_ga(activaciones_train, reales_train, universo, conjuntos_salida)

    # TEST aparece por primera vez en inferencia, nunca en funciones o selección del GA.
    activaciones_test = fuzzificar(test)[2]
    pred_base = inferir_mamdani(activaciones_test, REGLAS_BASE, universo, conjuntos_salida)
    pred_ga = inferir_mamdani(activaciones_test, reglas_ga, universo, conjuntos_salida)
    pred_mediana = np.full(len(test), np.median(reales_train))
    pred_media = np.full(len(test), np.mean(reales_train))
    predicciones = {
        "Mamdani Base": pred_base,
        "Mamdani + GA": pred_ga,
        "Mediana TRAIN": pred_mediana,
        "Media TRAIN": pred_media,
    }
    metricas = pd.DataFrame([
        evaluar_modelo(nombre, reales_test, estimados)
        for nombre, estimados in predicciones.items()
    ])
    tabla_pred = test[["fecha", "sector", "litros_nominales_riego_24h"]].copy()
    tabla_pred = tabla_pred.rename(columns={"litros_nominales_riego_24h": "litros_nominales_objetivo"})
    tabla_pred["litros_base"] = pred_base
    tabla_pred["litros_ga"] = pred_ga
    tabla_pred["litros_mediana_train"] = pred_mediana
    tabla_pred["litros_media_train"] = pred_media

    filas_sector = []
    for sector in MADP_POR_SECTOR:
        mascara = test["sector"].to_numpy() == sector
        cantidad = int(mascara.sum())
        filas_sector.append({
            "sector": sector,
            "casos_test": cantidad,
            "litros_nominales_promedio": float(np.mean(reales_test[mascara])) if cantidad else np.nan,
            "mae_base_litros": calcular_mae(reales_test[mascara], pred_base[mascara]) if cantidad else np.nan,
            "mae_ga_litros": calcular_mae(reales_test[mascara], pred_ga[mascara]) if cantidad else np.nan,
        })
    por_sector = pd.DataFrame(filas_sector)

    CARPETA_RESULTADOS.mkdir(exist_ok=True)
    tabla_reglas(reglas_ga).to_csv(CARPETA_RESULTADOS / "reglas.csv", index=False)
    historial.to_csv(CARPETA_RESULTADOS / "historial_ga.csv", index=False)
    tabla_pred.to_csv(CARPETA_RESULTADOS / "predicciones.csv", index=False)
    metricas.to_csv(CARPETA_RESULTADOS / "metricas.csv", index=False)
    por_sector.to_csv(CARPETA_RESULTADOS / "metricas_por_sector.csv", index=False)

    print("=" * 60)
    print(" ESTIMACIÓN CONDICIONAL DE VOLUMEN NOMINAL DE RIEGO")
    print("=" * 60)
    print(f"Cronología: {len(train_todo) + len(test_todo) + purgados} casos | "
          f"TRAIN {len(train_todo)} | purgados {purgados} | TEST {len(test_todo)}")
    print(f"Casos con riego estándar: TRAIN {len(train)} | TEST {len(test)}")
    print(f"Corte de prueba: {FECHA_CORTE.date()}")
    print(f"Volumen nominal TRAIN: Q25 {puntos[0]:.2f} | mediana {puntos[1]:.2f} | "
          f"Q75 {puntos[2]:.2f} | máximo {universo[-1]:.2f} L")
    print(f"Cromosoma GA: {''.join(map(str, reglas_ga))} (9 genes ternarios)")
    print(f"MAE de entrenamiento GA: {calcular_mae(reales_train, inferir_mamdani(activaciones_train, reglas_ga, universo, conjuntos_salida)):.2f} L")
    print("\nMétricas de prueba condicional (litros):")
    print(metricas.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    print("\nCantidad por sector en TRAIN y TEST:")
    conteos = pd.DataFrame({
        "sector": list(MADP_POR_SECTOR),
        "train": [int((train["sector"] == s).sum()) for s in MADP_POR_SECTOR],
        "test": [int((test["sector"] == s).sum()) for s in MADP_POR_SECTOR],
    })
    print(conteos.to_string(index=False))
    print("\nError por sector en TEST:")
    print(por_sector.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    print(f"\nResultados: {CARPETA_RESULTADOS}")

    if args.sector is not None or args.humedad is not None or args.dias is not None:
        if args.sector is None or args.humedad is None or args.dias is None:
            raise ValueError("Indique juntos --sector, --humedad y --dias.")
        if (args.sector not in MADP_POR_SECTOR or not 0 <= args.humedad <= 100
                or args.dias < 0):
            raise ValueError("Use sector 1–5, humedad 0–100 y días >= 0.")
        caso = consultar_caso(args.sector, args.humedad, args.dias,
                              reglas_ga, universo, conjuntos_salida)
        print("\nConsulta manual de volumen nominal, condicional a un riego estándar")
        print(f"Sector {args.sector} | Humedad {args.humedad:.1f} | "
              f"MADP {caso['madp']} | Humedad relativa {caso['humedad_relativa']:.1f}")
        print(f"Días desde último riego estándar terminado: {args.dias:.2f}")
        print("Grados de humedad:", dict(zip(
            ETIQUETAS_HUMEDAD, [round(float(x), 3) for x in caso["grados_humedad"]]
        )))
        print("Grados de días:", dict(zip(
            ETIQUETAS_DIAS, [round(float(x), 3) for x in caso["grados_dias"]]
        )))
        print("Reglas activadas:")
        print(pd.DataFrame(caso["reglas_activadas"]).to_string(index=False))
        print(f"Mamdani Base: {caso['litros_base']:.2f} L")
        print(f"Mamdani + GA: {caso['litros_ga']:.2f} L")
        print("La consulta estima cantidad condicional a un riego; no decide si debe iniciarse.")


if __name__ == "__main__":
    analizador = argparse.ArgumentParser(description="Estimar volumen nominal condicional de riego")
    analizador.add_argument("--preparar", action="store_true", help="Reconstruye CSV desde Arnesano")
    analizador.add_argument("--sector", type=int, help="Sector 1–5 para consulta manual")
    analizador.add_argument("--humedad", type=float, help="Humedad de suelo 0–100")
    analizador.add_argument("--dias", type=float, help="Días desde el último riego estándar terminado")
    ejecutar(analizador.parse_args())
