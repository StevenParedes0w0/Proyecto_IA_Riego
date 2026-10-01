"""Pruebas automatizadas de datos, inferencia difusa, GA y consultas del proyecto.

Cada función cuyo nombre empieza por ``test_`` es descubierta por pytest. Las
aserciones comparan cálculos con resultados conocidos para detectar cambios
inesperados sin depender de una inspección manual de la salida de consola.
"""

from argparse import Namespace

import numpy as np
import pandas as pd
import pytest

import riego_simple.main as proyecto


def casos_positivos_train():
    """Devuelve TRAIN con cantidad positiva, TEST completo y filas purgadas.

    Reutiliza la división oficial del sistema y filtra positivos solo para el
    entrenamiento condicional. Se usa como preparación común de varias pruebas.
    """
    # Carga, valida y particiona el CSV con las mismas reglas del programa real.
    train, test, purgados = proyecto.leer_y_dividir_datos()
    # Conserva de TRAIN las filas cuyo target de litros es mayor que cero.
    return train[train.litros_nominales_riego_24h > 0], test, purgados


def test_pertenencias_son_grados_validos_y_forman_particion():
    """Comprueba límites, suma unitaria y puntos centrales de la partición difusa."""
    # Incluye extremos externos y puntos bajo, centro y alto de la función.
    grados = proyecto.tres_grados(np.array([-100, -20, 0, 20, 100]), -20, 0, 20)
    # Cada grado debe estar acotado entre cero y uno.
    assert np.all((0 <= grados) & (grados <= 1))
    # Para cualquier entrada, los grados de los tres conjuntos suman uno.
    assert np.allclose(grados.sum(axis=1), 1)
    # En el borde bajo solo pertenece plenamente a Baja.
    assert grados[0].tolist() == [1, 0, 0]
    # En el centro, Media tiene grado uno y las otras dos grado cero.
    assert grados[2].tolist() == [0, 1, 0]


def test_son_nueve_reglas_y_nueve_consecuentes_ternarios():
    """Verifica la forma y codificación del sistema de nueve reglas."""
    # Protege la base manual contra cambios accidentales de consecuentes u orden.
    assert proyecto.REGLAS_BASE.tolist() == [1, 2, 2, 0, 1, 2, 0, 0, 1]
    # Usa datos reales para comprobar que cada observación active nueve genes/reglas.
    train, _, _ = casos_positivos_train()
    # La matriz debe tener una fila por observación y nueve columnas, una por regla.
    assert proyecto.fuzzificar(train)[2].shape == (len(train), 9)
    # Todos los consecuentes de la base deben ser uno de los tres códigos permitidos.
    assert set(proyecto.REGLAS_BASE).issubset({0, 1, 2})


def test_centroide_mamdani_devuelve_litros_continuos():
    """Comprueba que inferir_mamdani use el centroide y mapee el gen correcto."""
    # Solo R1 se activa; el universo y conjuntos pequeños permiten calcular a mano.
    activaciones = np.zeros((1, 9))
    activaciones[0, 0] = 1
    universo = np.array([0.0, 1.0, 2.0])
    conjuntos = np.array([[1.0, 0.5, 0.0], [0.0, 1.0, 0.0], [0.0, 0.5, 1.0]])
    reglas = np.zeros(9, dtype=int)
    # Conclusión Baja, cuyo agregado [1, 0.5, 0] tiene centroide ponderado 1/3.
    litros = proyecto.inferir_mamdani(activaciones, reglas, universo, conjuntos)
    # Una observación de entrada debe producir exactamente una estimación.
    assert litros.shape == (1,)
    # Comprueba el centroide calculado a mano para el conjunto Baja.
    assert litros[0] == pytest.approx(1 / 3)
    # Cambiar R1 a Alta debe mover el centroide al conjunto del extremo derecho.
    reglas[0] = 2
    # El resultado coincide con el centroide del conjunto Alto del ejemplo.
    assert proyecto.inferir_mamdani(activaciones, reglas, universo, conjuntos)[0] == pytest.approx(5 / 3)


def test_volumen_suma_solapamientos_y_excluye_fertirrigacion():
    """Comprueba recorte temporal, filtro por sector y tipo de evento."""
    # Incluye dos eventos estándar del sector 1, una fertirrigación del mismo
    # sector y un riego estándar de otro sector para aislar cada filtro.
    eventos = pd.DataFrame({
        "sector": [1, 1, 1, 2],
        "start": pd.to_datetime(["2025-06-01 05:50", "2025-06-02 05:50",
                                 "2025-06-01 08:00", "2025-06-01 09:00"]),
        "end": pd.to_datetime(["2025-06-01 06:10", "2025-06-02 06:10",
                               "2025-06-01 08:30", "2025-06-01 09:30"]),
        "type": ["standard_irrigation", "standard_irrigation", "fertigation",
                 "standard_irrigation"],
    })
    # La ventana empieza a las 06:00: de los eventos válidos se cuentan 10+10 min.
    numero, litros = proyecto.resumir_riego_ventana(eventos, pd.Timestamp("2025-06-01 06:00"), 1)
    # Se esperan dos eventos con 20 minutos combinados a 1,1 L/min.
    # Verifica tanto el número de eventos como la conversión final a litros.
    assert numero == 2
    assert litros == pytest.approx(20 * 1.1)


def test_corte_y_purga_se_aplican_antes_de_filtrar_positivos():
    """Verifica las fechas de corte, el tamaño de bloques y ausencia de futuro."""
    # Lee la cronología completa; incluye filas cero para que el corte se valide antes.
    train, test, purgados = proyecto.leer_y_dividir_datos()
    # Los cuatro conteos prueban los tamaños de TRAIN, purga y TEST.
    assert (len(train), purgados, len(test)) == (473, 4, 230)
    # TRAIN termina antes del día purgado; TEST empieza justo en la fecha fijada.
    assert train.fecha.max() == pd.Timestamp("2025-06-26 06:00")
    assert test.fecha.min() == proyecto.FECHA_CORTE
    # Ningún bloque puede contener una medición tomada después de la decisión 06:00.
    assert (train.medicion <= train.fecha).all()
    assert (test.medicion <= test.fecha).all()
    # Comprueba cantidades condicionales positivas después de validar partición.
    assert (train.litros_nominales_riego_24h > 0).sum() == 142
    assert (test.litros_nominales_riego_24h > 0).sum() == 56


def test_madp_y_caudal_sector_cinco_son_distintos():
    """Asegura que el parámetro particular del sector 5 no se generalice mal."""
    # Combina ambas particiones porque los parámetros sectoriales aplican a todas.
    train, test, _ = proyecto.leer_y_dividir_datos()
    datos = pd.concat([train, test])
    # Comprueba los parámetros documentados del quinto sector.
    assert proyecto.MADP_POR_SECTOR[5] == 70
    assert proyecto.CAUDAL_POR_SECTOR[5] == 0.4
    assert set(datos.loc[datos.sector == 5, "madp_sector"]) == {70}
    # La entrada relativa debe reconstruirse exactamente como humedad menos MADP.
    assert np.allclose(datos.humedad_relativa_madp, datos.humedad_suelo - datos.madp_sector)


def test_conjuntos_de_salida_usan_unicamente_train():
    """Verifica que cuantiles, máximo y universo de salida provienen de TRAIN."""
    train, _, _ = casos_positivos_train()
    litros = train.litros_nominales_riego_24h.to_numpy(float)
    # Ejecuta la construcción para los litros positivos de TRAIN.
    universo, conjuntos, puntos = proyecto.preparar_salida(litros)
    # Los puntos devueltos coinciden con cuartiles calculados directamente.
    assert np.allclose(puntos, np.quantile(litros, [0.25, 0.5, 0.75]))
    # El universo de salida comienza en cero y termina en el máximo de TRAIN.
    assert universo[0] == 0
    assert universo[-1] == max(litros)
    # Debe existir una función (fila) por cada conjunto Baja, Media y Alta.
    assert conjuntos.shape == (3, len(universo))


def test_mutacion_cambia_cada_gen_a_otro_valor_valido(monkeypatch):
    """Fuerza mutación para comprobar dominio, cambio y copia del padre."""
    # Hace que todos los genes muten para comprobar inequívocamente el operador.
    monkeypatch.setattr(proyecto, "PROB_MUTACION", 1.0)
    original = np.array([0, 1, 2] * 3)
    # Usa una semilla determinista para que la prueba sea reproducible.
    mutado = proyecto.mutar(original, np.random.default_rng(42))
    # El hijo conserva los nueve genes del cromosoma.
    assert len(mutado) == 9
    # Con mutación forzada, cada gen debe cambiar y seguir siendo 0, 1 o 2.
    assert np.all(mutado != original)
    assert set(mutado).issubset({0, 1, 2})
    # El operador devuelve hijo nuevo y no modifica el cromosoma original.
    assert original.tolist() == [0, 1, 2] * 3


def test_ga_es_reproducible_y_mejora_o_iguala_la_mejor_aptitud():
    """Prueba aleatoriedad reproducible, longitud y elitismo del algoritmo."""
    # Prepara activaciones, etiquetas, universo y salidas únicamente desde TRAIN.
    train, _, _ = casos_positivos_train()
    reales = train.litros_nominales_riego_24h.to_numpy(float)
    activaciones = proyecto.fuzzificar(train)[2]
    universo, conjuntos, _ = proyecto.preparar_salida(reales)
    # Ejecuta dos búsquedas separadas con la semilla interna fija del proyecto.
    primero, historia1 = proyecto.ejecutar_ga(activaciones, reales, universo, conjuntos)
    segundo, historia2 = proyecto.ejecutar_ga(activaciones, reales, universo, conjuntos)
    # El mejor candidato es un cromosoma válido de nueve genes.
    assert len(primero) == 9 and set(primero).issubset({0, 1, 2})
    # La semilla fija debe devolver la misma solución en ambas ejecuciones.
    assert np.array_equal(primero, segundo)
    # También debe repetirse exactamente el historial de generaciones.
    assert historia1.equals(historia2)
    # Como se conserva el mejor histórico, la aptitud registrada nunca disminuye.
    assert historia1.mejor_fitness.is_monotonic_increasing


def test_ga_y_conjuntos_de_salida_reciben_solo_train(monkeypatch, tmp_path, capsys):
    """Intercepta llamadas para detectar fuga de TEST hacia el ajuste del GA."""
    # Guarda las tablas y funciones originales antes de reemplazarlas por vigilantes.
    train, test, _ = proyecto.leer_y_dividir_datos()
    train_positivos = train[train.litros_nominales_riego_24h > 0]
    reales_train = train_positivos.litros_nominales_riego_24h.to_numpy(float)
    preparar_original = proyecto.preparar_salida
    ga_original = proyecto.ejecutar_ga
    llamadas = {"salida": 0, "ga": 0}

    # Esta función sustituta falla si preparar_salida recibe datos distintos de TRAIN.
    def vigilar_salida(litros):
        assert np.array_equal(litros, reales_train)
        llamadas["salida"] += 1
        return preparar_original(litros)

    # Esta sustituta verifica entradas de entrenamiento y luego llama el GA real.
    def vigilar_ga(activaciones, litros, universo, conjuntos):
        assert len(activaciones) == len(train_positivos)
        assert np.array_equal(litros, reales_train)
        llamadas["ga"] += 1
        return ga_original(activaciones, litros, universo, conjuntos)

    monkeypatch.setattr(proyecto, "preparar_salida", vigilar_salida)
    monkeypatch.setattr(proyecto, "ejecutar_ga", vigilar_ga)
    # Redirige CSV a carpeta temporal para que la prueba no altere resultados versionados.
    monkeypatch.setattr(proyecto, "CARPETA_RESULTADOS", tmp_path)
    # Ejecuta el flujo completo y captura la consola para no llenar el reporte de pytest.
    proyecto.ejecutar(Namespace(preparar=False, sector=None, humedad=None, dias=None))
    capsys.readouterr()
    # Asegura que el conjunto de prueba no esté vacío y que ambas rutinas vigiladas
    # se hayan llamado exactamente una vez durante el pipeline.
    assert len(test) > 0
    assert llamadas == {"salida": 1, "ga": 1}


def test_fitness_y_metricas_de_regresion_son_calculados_correctamente():
    """Comprueba MAE, RMSE y MedAE con tres pares de datos calculables a mano."""
    # Los errores absolutos son [2, 2, 5], así MAE=3 y MedAE=2.
    reales = np.array([10.0, 20.0, 30.0])
    estimados = np.array([8.0, 18.0, 35.0])
    assert proyecto.calcular_mae(reales, estimados) == pytest.approx(3.0)
    # Las métricas devueltas deben coincidir con los cálculos conocidos.
    metricas = proyecto.evaluar_modelo("ejemplo", reales, estimados)
    assert metricas["mae_litros"] == pytest.approx(3.0)
    # Los errores cuadrados promedian 11, por lo que RMSE es la raíz de ese valor.
    assert metricas["rmse_litros"] == pytest.approx(np.sqrt(11))
    assert metricas["medae_litros"] == pytest.approx(2.0)


def test_consulta_manual_devuelve_litros_y_grados():
    """Verifica conversión de humedad, inferencia y explicación de consulta."""
    # Crea la salida con TRAIN y consulta el sector 2 con entradas plausibles.
    train, _, _ = casos_positivos_train()
    universo, conjuntos, _ = proyecto.preparar_salida(train.litros_nominales_riego_24h.to_numpy())
    # Pasa reglas base; por ello la comparación Base/GA debe producir lo mismo.
    caso = proyecto.consultar_caso(2, 42, 0.8, proyecto.REGLAS_BASE, universo, conjuntos)
    # La consulta resta MADP 40 a humedad 42 y devuelve dos estimaciones válidas.
    assert caso["madp"] == 40
    assert caso["humedad_relativa"] == 2
    assert caso["litros_base"] > 0
    assert caso["litros_ga"] == caso["litros_base"]
    # Debe listar reglas con grado positivo y sus grados de humedad deben sumar uno.
    assert caso["reglas_activadas"]
    assert np.allclose(caso["grados_humedad"].sum(), 1)


def test_preparacion_reproduce_csv_cuando_existe_dataset_original():
    """Si están las fuentes originales, comprueba que prepararlas sea reproducible."""
    # Arma las rutas de eventos y cinco sensores fuente.
    eventos = proyecto.ORIGEN / "irrigation_events" / "final_irrigation_events.csv"
    sensores = [proyecto.ORIGEN / "merged" / f"dataset_zone_{sector}.csv"
                for sector in proyecto.MADP_POR_SECTOR]
    if not eventos.exists() or any(not ruta.exists() for ruta in sensores):
        # Saltar evita fallar si se distribuyó el paquete técnico sin fuentes grandes.
        pytest.skip("Dataset original de Arnesano no incluido en el paquete ligero")

    # Lee la salida empaquetada para compararla con dos reconstrucciones consecutivas.
    incluido = pd.read_csv(proyecto.ARCHIVO_DATOS, parse_dates=["fecha", "medicion"])
    # Cada llamada reconstruye y sobrescribe el CSV usando el preprocesamiento actual.
    primera = proyecto.preparar_datos()
    segunda = proyecto.preparar_datos()
    # Compara datos completos, ignorando solo diferencias de tipo inferido por pandas.
    pd.testing.assert_frame_equal(incluido, primera, check_dtype=False)
    # Dos reconstrucciones seguidas deben producir el mismo contenido.
    pd.testing.assert_frame_equal(primera, segunda, check_dtype=False)
    pd.testing.assert_frame_equal(segunda, pd.read_csv(proyecto.ARCHIVO_DATOS,
                                  parse_dates=["fecha", "medicion"]), check_dtype=False)
