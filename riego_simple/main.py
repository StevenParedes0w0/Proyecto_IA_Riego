"""Estima volumen nominal de riego con Mamdani y un algoritmo genético.

Ejecutar desde la raíz: python riego_simple/main.py
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

# Instante fijo que separa el periodo usado para aprender (TRAIN) del periodo
# posterior usado para evaluar (TEST). Se mantiene fijo para que los resultados
# no cambien por probar cortes distintos hasta encontrar uno favorable.
FECHA_CORTE = pd.Timestamp("2025-06-28 06:00:00")
# MADP significa punto de referencia sectorial para humedad del suelo.
# Cada valor permite convertir la lectura absoluta del sensor en una diferencia.
MADP_POR_SECTOR = {1: 40, 2: 40, 3: 60, 4: 80, 5: 70}
# Caudal nominal documentado para convertir minutos de válvula abierta a litros.
CAUDAL_POR_SECTOR = {1: 1.1, 2: 1.1, 3: 1.1, 4: 1.1, 5: 0.4}  # L/min
# Nombres legibles asociados a los índices 0, 1 y 2 de cada variable difusa.
ETIQUETAS_HUMEDAD = ("Baja", "Media", "Alta")
ETIQUETAS_DIAS = ("Reciente", "Intermedio", "Lejano")
ETIQUETAS_SALIDA = ("Baja", "Media", "Alta")

# Consecuente lingüístico de cada una de las nueve reglas; 0=Baja, 1=Media, 2=Alta.
# El índice se calcula como 3 × índice_de_humedad + índice_de_recencia, de modo
# que el orden es: humedad Baja/Media/Alta y, dentro de cada una, días
# Reciente/Intermedio/Lejano. Esta es la referencia manual que también se evalúa.
REGLAS_BASE = np.array([1, 2, 2, 0, 1, 2, 0, 0, 1], dtype=int)

# Hiperparámetros del algoritmo genético: cantidad de individuos, transiciones
# evolutivas, probabilidad de cambiar cada gen y semilla reproducible del azar.
TAMANO_POBLACION = 30
GENERACIONES = 50
PROB_MUTACION = 0.08
SEMILLA = 42


# ============================================================
# 2. PREPARACIÓN DE DATOS
# ============================================================
def resumir_riego_ventana(eventos: pd.DataFrame, inicio: pd.Timestamp, sector: int) -> tuple[int, float]:
    """Revisa los eventos y suma los litros nominales de las próximas 24 horas.

    Recibe la tabla de eventos, la fecha y hora desde donde empieza el periodo,
    y el número de sector que se quiere revisar. Devuelve dos resultados:
    cuántos riegos estándar encontró y cuántos litros nominales suman.
    """
    # Define el periodo que vamos a revisar: desde el inicio hasta el día siguiente.
    fin_ventana = inicio + pd.Timedelta(days=1)
    cantidad_eventos = 0
    litros = 0.0
    # Revisa uno por uno los eventos registrados.
    for evento in eventos.itertuples(index=False):
        # Ignora la fertirrigación y los eventos que pertenecen a otro sector.
        if evento.type != "standard_irrigation" or evento.sector != sector:
            continue
        # Si el evento empieza antes del periodo, usa el inicio del periodo.
        inicio_solapado = max(inicio, evento.start)
        # Si termina después del periodo, cuenta solo hasta el final del periodo.
        fin_solapado = min(fin_ventana, evento.end)
        # Calcula cuánto duró la parte del riego dentro del periodo, en minutos.
        # Si las fechas no se cruzan, deja la duración en cero y no la cuenta.
        minutos = max(0.0, (fin_solapado - inicio_solapado).total_seconds() / 60)
        if minutos > 0:
            # Cuenta el evento solo si tuvo una duración mayor que cero en el periodo.
            cantidad_eventos += 1
            # Convierte minutos a litros nominales usando el caudal del sector.
            litros += minutos * CAUDAL_POR_SECTOR[sector]
    # Devuelve cuántos eventos se contaron y cuántos litros nominales suman.
    return cantidad_eventos, litros


def preparar_datos() -> pd.DataFrame:
    """Construye y guarda el CSV de observaciones diarias por sector.

    Combina la telemetría de humedad con los eventos de válvula: selecciona una
    medición ya terminada a las 06:00, calcula la recencia del último riego
    estándar y reconstruye el volumen nominal estándar de las 24 horas futuras.
    Los datos se ordenan y se escriben en datos_riego.csv para el pipeline.
    """
    # Define las rutas de las tablas procesadas suministradas por el dataset.
    archivo_eventos = ORIGEN / "irrigation_events" / "final_irrigation_events.csv"
    if not archivo_eventos.exists():
        raise FileNotFoundError(f"Falta la fuente original: {archivo_eventos}")
    # Lee eventos y convierte inicio/fin de texto a fechas para operar con tiempos.
    eventos = pd.read_csv(archivo_eventos, parse_dates=["start", "end"])
    # Filtra solo riegos estándar para determinar el último día y la recencia.
    estandar = eventos[eventos["type"].eq("standard_irrigation")]
    ultimo_dia = estandar["end"].max().normalize()
    filas = []

    # Procesa cada sector con su MADP específico y su propio archivo de sensores.
    for sector, madp in MADP_POR_SECTOR.items():
        # Carga solo timestamp y humedad para limitar memoria y columnas innecesarias.
        sensores = pd.read_csv(
            ORIGEN / "merged" / f"dataset_zone_{sector}.csv",
            usecols=["ts", "soil_moisture"],
        )
        # ts marca el INICIO de un promedio de diez minutos; solo existe al terminar.
        # Cada ts identifica el inicio de un bloque promedio de 10 minutos; al
        # sumarle 10 se marca el instante en que ese promedio ya está completo.
        sensores["ts"] = pd.to_datetime(sensores["ts"]) + pd.Timedelta(minutes=10)
        # Elimina humedad fuera del rango físico esperado y ordena para merge_asof.
        sensores = sensores[sensores["soil_moisture"].between(0, 100)].sort_values("ts")

        # Obtiene eventos del sector actual y, de ellos, los riegos estándar.
        eventos_sector = eventos[eventos["sector"].eq(sector)]
        estandar_sector = estandar[estandar["sector"].eq(sector)]
        # Guarda finales como arreglo cronológico NumPy para búsqueda binaria rápida.
        finales = np.sort(estandar_sector["end"].to_numpy(dtype="datetime64[ns]"))
        # Genera decisiones a las 06:00 desde la primera observación hasta el
        # último día posible; no crea objetivos cuyo horizonte exceda los eventos.
        fechas = pd.date_range(
            sensores["ts"].min().normalize(), ultimo_dia - pd.Timedelta(days=1), freq="D"
        ) + pd.Timedelta(hours=6)
        # Para cada decisión asocia la lectura más reciente anterior o igual a ella.
        # direction='backward' impide tomar sensores futuros y tolerance=8 h limita
        # la antigüedad máxima aceptada de la medición.
        decisiones = pd.merge_asof(
            pd.DataFrame({"fecha": fechas}),
            sensores.rename(columns={"ts": "medicion"}),
            left_on="fecha", right_on="medicion", direction="backward",
            tolerance=pd.Timedelta(hours=8),
        ).dropna(subset=["soil_moisture"])

        # Evalúa individualmente las fechas que sí encontraron una lectura válida.
        for fila in decisiones.itertuples(index=False):
            ahora = fila.fecha
            # Busca si un evento de cualquier tipo del sector cubre la hora actual;
            # en tal caso no se considera una nueva decisión de riego.
            abierta = ((eventos_sector["start"] < ahora) & (eventos_sector["end"] > ahora)).any()
            if abierta:
                continue

            # searchsorted encuentra la posición de inserción de la fecha en finales.
            # Restar 1 obtiene el último fin de riego no posterior a la decisión.
            anterior = np.searchsorted(finales, np.datetime64(ahora), side="right") - 1
            # Calcula días desde ese fin; si supera 30, satura en 30. Si aún no
            # hubo riego estándar previo, usa directamente el máximo de 30 días.
            dias_sin_riego = (
                min(30.0, float((np.datetime64(ahora) - finales[anterior]) / np.timedelta64(1, "D")))
                if anterior >= 0 else 30.0
            )
            # Llama al resumen de eventos de las siguientes 24 horas para este sector.
            numero_eventos, litros = resumir_riego_ventana(eventos_sector, ahora, sector)
            humedad = float(fila.soil_moisture)
            # Almacena entradas de decisión, referencia MADP, estado temporal y
            # etiqueta objetivo reconstruida. La humedad relativa es humedad-MADP.
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

    # Convierte los diccionarios a tabla, ordena por tiempo/sector y reinicia índices.
    datos = pd.DataFrame(filas).sort_values(["fecha", "sector"]).reset_index(drop=True)
    # Escribe CSV sin índice artificial y devuelve la misma tabla al llamador.
    datos.to_csv(ARCHIVO_DATOS, index=False)
    return datos


# ============================================================
# 3. DIVISIÓN TEMPORAL
# ============================================================
def leer_y_dividir_datos() -> tuple[pd.DataFrame, pd.DataFrame, int]:
    """Valida el CSV y devuelve TRAIN, TEST y el número de filas purgadas.

    Conserva primero tanto las observaciones con objetivo cero como las positivas
    para definir correctamente el corte cronológico; el llamador filtra positivos
    después, cuando vaya a entrenar una regresión condicional a que haya riego.
    """
    if not ARCHIVO_DATOS.exists():
        raise FileNotFoundError(f"Falta {ARCHIVO_DATOS}. Ejecute con --preparar.")
    # Convierte las dos columnas temporales a datetime durante la lectura.
    datos = pd.read_csv(ARCHIVO_DATOS, parse_dates=["fecha", "medicion"])
    # Lista cerrada de campos requeridos por validaciones y etapas posteriores.
    necesarias = [
        "fecha", "medicion", "sector", "humedad_suelo", "madp_sector",
        "humedad_relativa_madp", "dias_sin_riego", "numero_eventos_riego_24h",
        "litros_nominales_riego_24h",
    ]
    # isna identifica faltantes; any por eje y el segundo any producen un solo sí/no.
    if datos[necesarias].isna().any().any():
        raise ValueError("El CSV contiene valores faltantes en columnas necesarias.")
    # Evita fuga temporal: una medición futura no puede alimentar una decisión 06:00.
    if (datos["medicion"] > datos["fecha"]).any():
        raise ValueError("Hay una medición posterior a las 06:00.")
    # Comprueba pertenencia de cada sector al diccionario de parámetros conocidos.
    if not datos["sector"].isin(MADP_POR_SECTOR).all():
        raise ValueError("Hay un sector sin MADP o caudal documentado.")
    if (datos["litros_nominales_riego_24h"] < 0).any():
        raise ValueError("El volumen nominal no puede ser negativo.")
    # Verifica coherencia: cero eventos debe corresponder exactamente a cero litros.
    if ((datos["numero_eventos_riego_24h"] == 0) !=
            (datos["litros_nominales_riego_24h"] == 0)).any():
        raise ValueError("Número de eventos y litros no coinciden.")

    # La etiqueta del 27 de junio mira 24 h hasta el corte; se excluye por completo.
    # TRAIN termina antes de ese día y TEST comienza en el instante de corte.
    train = datos[datos["fecha"] < FECHA_CORTE - pd.Timedelta(days=1)].copy()
    test = datos[datos["fecha"] >= FECHA_CORTE].copy()
    # Resta tamaños para contar la frontera temporal no asignada a ningún bloque.
    purgados = len(datos) - len(train) - len(test)
    if not len(train) or not len(test) or purgados == 0:
        raise ValueError("La división temporal o su día de purga están vacíos.")
    # Devuelve copias particionadas y el conteo de filas intermedias descartadas.
    return train, test, purgados


# ============================================================
# 4. FUNCIONES DE PERTENENCIA
# ============================================================
def tres_grados(valores: np.ndarray, bajo: float, centro: float, alto: float) -> np.ndarray:
    """Calcula grados difusos Baja, Media y Alta para cada valor recibido.

    Baja y Alta son hombros lineales saturados por np.clip. Media completa la
    partición restando ambos hombros a 1. El resultado tiene forma (n, 3) y cada
    fila representa grados de pertenencia, no probabilidades.
    """
    # Asegura operaciones numéricas NumPy incluso si llega una lista de Python.
    valores = np.asarray(valores, dtype=float)
    # En el lado bajo el grado decrece de uno a cero entre bajo y centro.
    baja = np.clip((centro - valores) / (centro - bajo), 0, 1)
    # En el lado alto el grado crece de cero a uno entre centro y alto.
    alta = np.clip((valores - centro) / (alto - centro), 0, 1)
    # El término medio da grado completo en centro y cero fuera de los hombros.
    media = 1 - baja - alta
    # Apila cada término en una columna: [Baja, Media, Alta].
    return np.column_stack([baja, media, alta])


def fuzzificar(datos: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Convierte entradas numéricas en grados y calcula las nueve activaciones.

    Calcula tres grados de humedad y tres de recencia por fila. El producto
    cartesiano combina cada término de humedad con cada término temporal; mínimo
    implementa el AND difuso de Mamdani. Devuelve grados de ambas entradas y una
    matriz (filas, 9) de activaciones en el orden usado por los cromosomas.
    """
    # Obtiene los tres conjuntos difusos de la entrada relativa al MADP.
    humedad = tres_grados(datos["humedad_relativa_madp"].to_numpy(), -20, 0, 20)
    # Obtiene los tres conjuntos de días desde el fin del último riego.
    dias = tres_grados(datos["dias_sin_riego"].to_numpy(), 0.5, 1.5, 4.5)
    # Agrega un eje para cada variable, calcula el mínimo por combinación y aplana
    # los ejes de términos para producir nueve reglas por observación.
    activaciones = np.minimum(humedad[:, :, None], dias[:, None, :]).reshape(len(datos), 9)
    return humedad, dias, activaciones


def preparar_salida(litros_train: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Construye universo y conjuntos difusos de salida usando solo TRAIN.

    Los cuantiles 25, 50 y 75 fijan los puntos de Baja/Media/Alta; el universo
    discreto va desde cero hasta el máximo de litros positivos de entrenamiento.
    Devuelve universo, matriz de conjuntos (3, puntos) y los tres cuantiles.
    """
    # Rechaza conjuntos vacíos o valores no positivos: esta salida modela cantidad
    # de riego condicional, y las observaciones sin riego se excluyen del ajuste.
    if len(litros_train) == 0 or np.any(litros_train <= 0):
        raise ValueError("La salida requiere casos positivos de entrenamiento.")
    # Calcula cuartil inferior, mediana y cuartil superior de TRAIN solamente.
    q25, q50, q75 = np.quantile(litros_train, [0.25, 0.50, 0.75])
    if not q25 < q50 < q75:
        raise ValueError("Los cuantiles de TRAIN no permiten tres conjuntos distintos.")
    # Divide el intervalo posible en 501 puntos para integrar el centroide.
    universo = np.linspace(0, float(np.max(litros_train)), 501)
    # tres_grados devuelve (puntos, conjuntos); la transposición deja una fila
    # independiente por término lingüístico para que la inferencia la indexe.
    conjuntos = tres_grados(universo, q25, q50, q75).T
    return universo, conjuntos, np.array([q25, q50, q75])


# ============================================================
# 5. INFERENCIA MAMDANI CONTINUA
# ============================================================
def inferir_mamdani(
    activaciones: np.ndarray, cromosoma: np.ndarray,
    universo: np.ndarray, conjuntos_salida: np.ndarray,
) -> np.ndarray:
    """Ejecuta inferencia Mamdani y calcula un centroide de salida por observación.

    Para cada término de salida, toma la activación máxima entre las reglas que
    concluyen ese término. Recorta su función de pertenencia con mínimo, agrega
    los términos con máximo y obtiene el centroide discreto ponderado en litros.
    """
    # Evita índices inválidos y cromosomas con longitud o valores inesperados.
    if len(cromosoma) != 9 or not np.isin(cromosoma, [0, 1, 2]).all():
        raise ValueError("El cromosoma requiere nueve consecuentes de {0,1,2}.")
    # Selecciona activaciones cuyas reglas concluyen el término indicado y asigna
    # cero al resto; max resume la fuerza conjunta de reglas con misma conclusión.
    grados_salida = np.column_stack([
        np.max(np.where(cromosoma == termino, activaciones, 0), axis=1)
        for termino in range(3)
    ])
    # Para cada salida: np.minimum recorta pertenencias a la fuerza de activación;
    # np.maximum.reduce une Baja, Media y Alta conservando la envolvente superior.
    agregada = np.maximum.reduce([
        np.minimum(grados_salida[:, termino, None], conjuntos_salida[termino])
        for termino in range(3)
    ])
    # Suma grados de todos los puntos: denominador del centroide discreto.
    area = agregada.sum(axis=1)
    # Multiplica cada grado por su litro, suma numeradores y divide por el área.
    # np.divide usa cero como salida si no hay regla activa, evitando división 0/0.
    return np.divide(
        (agregada * universo).sum(axis=1), area,
        out=np.zeros(len(area)), where=area > 0,
    )


# ============================================================
# 6. ALGORITMO GENÉTICO
# ============================================================
def calcular_mae(reales: np.ndarray, estimados: np.ndarray) -> float:
    """Promedia la magnitud del error fila a fila, conservando unidad litros."""
    # Resta elemento a elemento, toma valor absoluto, promedia y convierte a float.
    return float(np.mean(np.abs(reales - estimados)))


def calcular_fitness(
    cromosoma: np.ndarray, activaciones: np.ndarray, reales: np.ndarray,
    universo: np.ndarray, conjuntos_salida: np.ndarray,
) -> float:
    """Convierte el MAE de TRAIN a aptitud: menor error equivale a más fitness."""
    # Menos error absoluto en litros -> fitness mayor; solo se usa TRAIN.
    estimados = inferir_mamdani(activaciones, cromosoma, universo, conjuntos_salida)
    return 1.0 / (1.0 + calcular_mae(reales, estimados))


def mutar(cromosoma: np.ndarray, azar: np.random.Generator) -> np.ndarray:
    """Copia un cromosoma y cambia genes con la probabilidad configurada.

    azar produce una máscara independiente para cada una de las nueve posiciones.
    A cada posición mutada se le suma 1 o 2 módulo 3: así nunca conserva su valor
    previo y sigue perteneciendo al dominio {0, 1, 2}.
    """
    # Copia evita modificar al padre almacenado en la población original.
    hijo = cromosoma.copy()
    # Genera nueve números uniformes y marca los que quedan bajo probabilidad.
    cambia = azar.random(9) < PROB_MUTACION
    # Cuenta mutaciones; sortea desplazamiento 1 o 2; módulo 3 da otro consecuente.
    hijo[cambia] = (hijo[cambia] + azar.integers(1, 3, size=int(cambia.sum()))) % 3
    return hijo


def ejecutar_ga(
    activaciones: np.ndarray, reales: np.ndarray,
    universo: np.ndarray, conjuntos_salida: np.ndarray,
) -> tuple[np.ndarray, pd.DataFrame]:
    """Busca consecuentes de nueve reglas mediante evolución genética.

    Cada cromosoma contiene nueve genes ternarios. En cada generación se calcula
    el fitness en TRAIN, se conserva el mejor histórico y se crea la población
    siguiente usando elitismo, selección por ruleta, cruce de un punto y mutación.
    Devuelve el mejor cromosoma hallado y una fila de trazabilidad por generación.
    """
    # Generador local determinista: la misma semilla reproduce toda la búsqueda.
    azar = np.random.default_rng(SEMILLA)
    # Crea una matriz 30×9 con valores aleatorios 0, 1 o 2.
    poblacion = azar.integers(0, 3, size=(TAMANO_POBLACION, 9))
    mejor = poblacion[0].copy()
    mejor_fitness = -1.0
    historial = []

    # Incluye generación cero (población inicial) y la generación final 50.
    for generacion in range(GENERACIONES + 1):
        # Evalúa cada individuo contra las mismas activaciones, etiquetas y motor.
        fitness = np.array([
            calcular_fitness(individuo, activaciones, reales, universo, conjuntos_salida)
            for individuo in poblacion
        ])
        # argmax devuelve la posición del mayor fitness de la generación actual.
        indice = int(np.argmax(fitness))
        if fitness[indice] > mejor_fitness:
            mejor, mejor_fitness = poblacion[indice].copy(), float(fitness[indice])
        # Registra mejor aptitud histórica, su conversión inversa a MAE y el
        # fitness medio de la generación; estos datos se guardan luego en CSV.
        historial.append({
            "generacion": generacion,
            "mejor_fitness": mejor_fitness,
            "mejor_mae_litros_train": 1 / mejor_fitness - 1,
            "fitness_promedio": float(fitness.mean()),
        })
        if generacion == GENERACIONES:
            break

        # Inserta primero una copia intacta del mejor para garantizar elitismo.
        nueva = [mejor.copy()]
        while len(nueva) < TAMANO_POBLACION:
            # Selecciona cada padre aleatoriamente con probabilidad proporcional
            # a su fitness; np.choice opera sobre los índices de la población.
            padre1 = poblacion[azar.choice(len(poblacion), p=fitness / fitness.sum())]
            padre2 = poblacion[azar.choice(len(poblacion), p=fitness / fitness.sum())]
            # Elige corte interior 1..8 y concatena prefijo del primer padre con
            # sufijo del segundo, manteniendo exactamente nueve genes.
            punto = int(azar.integers(1, 9))
            hijo = np.concatenate([padre1[:punto], padre2[punto:]])
            # Mutar devuelve un nuevo hijo sin cambiar los padres de la población.
            nueva.append(mutar(hijo, azar))
        # Convierte la lista de nuevos cromosomas a matriz para la siguiente vuelta.
        poblacion = np.array(nueva)

    # Devuelve una copia del mejor candidato y la tabla de evolución completa.
    return mejor, pd.DataFrame(historial)


# ============================================================
# 7. EVALUACIÓN Y CONSULTA MANUAL
# ============================================================
def evaluar_modelo(nombre: str, reales: np.ndarray, estimados: np.ndarray) -> dict:
    """Calcula MAE, RMSE y MedAE para comparar predicciones con objetivos."""
    # El signo identifica sobre/subestimación; métricas posteriores usan magnitudes.
    errores = reales - estimados
    # MAE promedia absolutos; RMSE penaliza más errores grandes; MedAE usa mediana.
    return {
        "modelo": nombre,
        "mae_litros": float(np.mean(np.abs(errores))),
        "rmse_litros": float(np.sqrt(np.mean(errores ** 2))),
        "medae_litros": float(np.median(np.abs(errores))),
    }


def tabla_reglas(reglas_ga: np.ndarray) -> pd.DataFrame:
    """Construye tabla legible que alinea regla, antecedentes y consecuentes."""
    filas = []
    # Dos bucles recorren las tres etiquetas de cada una de las dos entradas.
    for humedad in range(3):
        for dias in range(3):
            # Convierte el par de índices a la posición lineal del cromosoma.
            numero = 3 * humedad + dias
            # Guarda textos de antecedentes y los consecuentes de base y GA.
            filas.append({
                "regla": f"R{numero + 1}",
                "humedad": ETIQUETAS_HUMEDAD[humedad],
                "dias_sin_riego": ETIQUETAS_DIAS[dias],
                "consecuente_base": ETIQUETAS_SALIDA[REGLAS_BASE[numero]],
                "consecuente_ga": ETIQUETAS_SALIDA[reglas_ga[numero]],
            })
    # Pasa la lista de diccionarios a columnas de una tabla pandas.
    return pd.DataFrame(filas)


def consultar_caso(
    sector: int, humedad_actual: float, dias_sin_riego: float,
    reglas_ga: np.ndarray, universo: np.ndarray, conjuntos_salida: np.ndarray,
) -> dict:
    """Evalúa una consulta individual y explica cómo llega a ambas estimaciones.

    Convierte humedad absoluta a diferencia respecto del MADP del sector,
    limita la recencia al máximo operativo, fuzzifica el caso, enumera reglas
    activas y llama dos veces al motor Mamdani: con reglas manuales y con GA.
    """
    # Busca el punto de referencia de humedad para el sector solicitado.
    madp = MADP_POR_SECTOR[sector]
    # El motor recibe las mismas dos columnas de entrada que durante el aprendizaje.
    caso = pd.DataFrame({
        "humedad_relativa_madp": [humedad_actual - madp],
        "dias_sin_riego": [min(dias_sin_riego, 30)],
    })
    # Reutiliza exactamente el proceso de fuzzificación empleado por el pipeline.
    grados_h, grados_d, activaciones = fuzzificar(caso)
    activadas = []
    # Examina las nueve fuerzas calculadas y omite las reglas con grado cero.
    for indice, grado in enumerate(activaciones[0]):
        if grado > 0:
            # Traduce índices a nombres de regla, antecedentes y conclusión.
            activadas.append({
                "regla": f"R{indice + 1}",
                "humedad": ETIQUETAS_HUMEDAD[indice // 3],
                "dias": ETIQUETAS_DIAS[indice % 3],
                "grado": float(grado),
                "base": ETIQUETAS_SALIDA[REGLAS_BASE[indice]],
                "ga": ETIQUETAS_SALIDA[reglas_ga[indice]],
            })
    # Empaqueta los grados y metadatos junto con ambas salidas Mamdani en litros.
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
    """Coordina preparación opcional, entrenamiento, evaluación y consulta.

    Esta función conecta las piezas: obtiene datos, separa periodos, filtra
    cantidades positivas, configura conjuntos, ejecuta el GA, compara modelos,
    guarda cinco CSV y, si se pidieron los argumentos, explica una consulta.
    """
    # La preparación desde archivos fuente solo se ejecuta cuando se solicita.
    if args.preparar:
        datos = preparar_datos()
        print(f"Datos preparados: {len(datos)} decisiones en {ARCHIVO_DATOS}")

    # Llama la validación/partición que incluye tanto días con como sin riego.
    train_todo, test_todo, purgados = leer_y_dividir_datos()
    # Solo después del corte cronológico conserva los objetivos de cantidad positiva.
    train = train_todo[train_todo["litros_nominales_riego_24h"] > 0].copy()
    test = test_todo[test_todo["litros_nominales_riego_24h"] > 0].copy()
    if train.empty or test.empty:
        raise ValueError("Se necesitan casos de cantidad en TRAIN y TEST.")

    # Extrae etiquetas numéricas NumPy para cálculos matriciales en el modelo.
    reales_train = train["litros_nominales_riego_24h"].to_numpy(float)
    reales_test = test["litros_nominales_riego_24h"].to_numpy(float)
    # Deriva escala y pertenencias de salida exclusivamente del objetivo TRAIN.
    universo, conjuntos_salida, puntos = preparar_salida(reales_train)
    # Fuzzifica TRAIN y toma la tercera salida: matriz de nueve activaciones.
    activaciones_train = fuzzificar(train)[2]
    # El algoritmo devuelve las conclusiones optimizadas y su historial evolutivo.
    reglas_ga, historial = ejecutar_ga(activaciones_train, reales_train, universo, conjuntos_salida)

    # TEST aparece por primera vez en inferencia, nunca en funciones o selección del GA.
    # TEST se usa aquí por primera vez, una vez congelados parámetros y reglas.
    activaciones_test = fuzzificar(test)[2]
    # Ambos modelos comparten los mismos datos, conjuntos y centroide; solo cambia
    # el vector de consecuentes usado para interpretar las nueve reglas.
    pred_base = inferir_mamdani(activaciones_test, REGLAS_BASE, universo, conjuntos_salida)
    pred_ga = inferir_mamdani(activaciones_test, reglas_ga, universo, conjuntos_salida)
    # Construye dos referencias simples que siempre predicen estadísticas de TRAIN:
    # una repite la mediana y otra repite la media para todas las filas de TEST.
    pred_mediana = np.full(len(test), np.median(reales_train))
    pred_media = np.full(len(test), np.mean(reales_train))
    predicciones = {
        "Mamdani Base": pred_base,
        "Mamdani + GA": pred_ga,
        "Mediana TRAIN": pred_mediana,
        "Media TRAIN": pred_media,
    }
    # Calcula las tres métricas para cada método y arma una tabla comparativa.
    metricas = pd.DataFrame([
        evaluar_modelo(nombre, reales_test, estimados)
        for nombre, estimados in predicciones.items()
    ])
    # Copia fecha, sector y objetivo; conserva la identidad de cada caso evaluado.
    tabla_pred = test[["fecha", "sector", "litros_nominales_riego_24h"]].copy()
    tabla_pred = tabla_pred.rename(columns={"litros_nominales_riego_24h": "litros_nominales_objetivo"})
    tabla_pred["litros_base"] = pred_base
    tabla_pred["litros_ga"] = pred_ga
    tabla_pred["litros_mediana_train"] = pred_mediana
    tabla_pred["litros_media_train"] = pred_media

    # Resume error por sector; un sector vacío recibe NaN, no un error artificial cero.
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

    # Crea la carpeta de salida si no existe y reemplaza los CSV de la corrida actual.
    CARPETA_RESULTADOS.mkdir(exist_ok=True)
    tabla_reglas(reglas_ga).to_csv(CARPETA_RESULTADOS / "reglas.csv", index=False)
    historial.to_csv(CARPETA_RESULTADOS / "historial_ga.csv", index=False)
    tabla_pred.to_csv(CARPETA_RESULTADOS / "predicciones.csv", index=False)
    metricas.to_csv(CARPETA_RESULTADOS / "metricas.csv", index=False)
    por_sector.to_csv(CARPETA_RESULTADOS / "metricas_por_sector.csv", index=False)

    # Presenta un resumen de la partición, solución GA y resultados reproducibles.
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

    # La consulta es opcional; si se entrega cualquier argumento de consulta,
    # exige recibir el grupo completo sector-humedad-días y validar su dominio.
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
    # argparse construye la interfaz de línea de comandos y convierte cada
    # argumento textual al tipo indicado (int o float) antes de llamar al pipeline.
    analizador = argparse.ArgumentParser(description="Estimar volumen nominal condicional de riego")
    analizador.add_argument("--preparar", action="store_true", help="Reconstruye CSV desde Arnesano")
    analizador.add_argument("--sector", type=int, help="Sector 1–5 para consulta manual")
    analizador.add_argument("--humedad", type=float, help="Humedad de suelo 0–100")
    analizador.add_argument("--dias", type=float, help="Días desde el último riego estándar terminado")
    ejecutar(analizador.parse_args())
