"""Comprobaciones de los conceptos importantes del sistema genético-difuso."""

from argparse import Namespace

import numpy as np
import pandas as pd
import pytest

import riego_simple.main as proyecto


def casos_positivos_train():
    train, test, purgados = proyecto.leer_y_dividir_datos()
    return train[train.litros_nominales_riego_24h > 0], test, purgados


def test_pertenencias_son_grados_validos_y_forman_particion():
    grados = proyecto.tres_grados(np.array([-100, -20, 0, 20, 100]), -20, 0, 20)
    assert np.all((0 <= grados) & (grados <= 1))
    assert np.allclose(grados.sum(axis=1), 1)
    assert grados[0].tolist() == [1, 0, 0]
    assert grados[2].tolist() == [0, 1, 0]


def test_son_nueve_reglas_y_nueve_consecuentes_ternarios():
    assert proyecto.REGLAS_BASE.tolist() == [1, 2, 2, 0, 1, 2, 0, 0, 1]
    train, _, _ = casos_positivos_train()
    assert proyecto.fuzzificar(train)[2].shape == (len(train), 9)
    assert set(proyecto.REGLAS_BASE).issubset({0, 1, 2})


def test_centroide_mamdani_devuelve_litros_continuos():
    activaciones = np.zeros((1, 9))
    activaciones[0, 0] = 1
    universo = np.array([0.0, 1.0, 2.0])
    conjuntos = np.array([[1.0, 0.5, 0.0], [0.0, 1.0, 0.0], [0.0, 0.5, 1.0]])
    reglas = np.zeros(9, dtype=int)
    litros = proyecto.inferir_mamdani(activaciones, reglas, universo, conjuntos)
    assert litros.shape == (1,)
    assert litros[0] == pytest.approx(1 / 3)
    reglas[0] = 2
    assert proyecto.inferir_mamdani(activaciones, reglas, universo, conjuntos)[0] == pytest.approx(5 / 3)


def test_volumen_suma_solapamientos_y_excluye_fertirrigacion():
    eventos = pd.DataFrame({
        "sector": [1, 1, 1, 2],
        "start": pd.to_datetime(["2025-06-01 05:50", "2025-06-02 05:50",
                                 "2025-06-01 08:00", "2025-06-01 09:00"]),
        "end": pd.to_datetime(["2025-06-01 06:10", "2025-06-02 06:10",
                               "2025-06-01 08:30", "2025-06-01 09:30"]),
        "type": ["standard_irrigation", "standard_irrigation", "fertigation",
                 "standard_irrigation"],
    })
    numero, litros = proyecto.resumir_riego_ventana(eventos, pd.Timestamp("2025-06-01 06:00"), 1)
    assert numero == 2
    assert litros == pytest.approx(20 * 1.1)


def test_corte_y_purga_se_aplican_antes_de_filtrar_positivos():
    train, test, purgados = proyecto.leer_y_dividir_datos()
    assert (len(train), purgados, len(test)) == (473, 4, 230)
    assert train.fecha.max() == pd.Timestamp("2025-06-26 06:00")
    assert test.fecha.min() == proyecto.FECHA_CORTE
    assert (train.medicion <= train.fecha).all()
    assert (test.medicion <= test.fecha).all()
    assert (train.litros_nominales_riego_24h > 0).sum() == 142
    assert (test.litros_nominales_riego_24h > 0).sum() == 56


def test_madp_y_caudal_sector_cinco_son_distintos():
    train, test, _ = proyecto.leer_y_dividir_datos()
    datos = pd.concat([train, test])
    assert proyecto.MADP_POR_SECTOR[5] == 70
    assert proyecto.CAUDAL_POR_SECTOR[5] == 0.4
    assert set(datos.loc[datos.sector == 5, "madp_sector"]) == {70}
    assert np.allclose(datos.humedad_relativa_madp, datos.humedad_suelo - datos.madp_sector)


def test_conjuntos_de_salida_usan_unicamente_train():
    train, _, _ = casos_positivos_train()
    litros = train.litros_nominales_riego_24h.to_numpy(float)
    universo, conjuntos, puntos = proyecto.preparar_salida(litros)
    assert np.allclose(puntos, np.quantile(litros, [0.25, 0.5, 0.75]))
    assert universo[0] == 0
    assert universo[-1] == max(litros)
    assert conjuntos.shape == (3, len(universo))


def test_mutacion_cambia_cada_gen_a_otro_valor_valido(monkeypatch):
    monkeypatch.setattr(proyecto, "PROB_MUTACION", 1.0)
    original = np.array([0, 1, 2] * 3)
    mutado = proyecto.mutar(original, np.random.default_rng(42))
    assert len(mutado) == 9
    assert np.all(mutado != original)
    assert set(mutado).issubset({0, 1, 2})
    assert original.tolist() == [0, 1, 2] * 3


def test_ga_es_reproducible_y_mejora_o_iguala_la_mejor_aptitud():
    train, _, _ = casos_positivos_train()
    reales = train.litros_nominales_riego_24h.to_numpy(float)
    activaciones = proyecto.fuzzificar(train)[2]
    universo, conjuntos, _ = proyecto.preparar_salida(reales)
    primero, historia1 = proyecto.ejecutar_ga(activaciones, reales, universo, conjuntos)
    segundo, historia2 = proyecto.ejecutar_ga(activaciones, reales, universo, conjuntos)
    assert len(primero) == 9 and set(primero).issubset({0, 1, 2})
    assert np.array_equal(primero, segundo)
    assert historia1.equals(historia2)
    assert historia1.mejor_fitness.is_monotonic_increasing


def test_ga_y_conjuntos_de_salida_reciben_solo_train(monkeypatch, tmp_path, capsys):
    train, test, _ = proyecto.leer_y_dividir_datos()
    train_positivos = train[train.litros_nominales_riego_24h > 0]
    reales_train = train_positivos.litros_nominales_riego_24h.to_numpy(float)
    preparar_original = proyecto.preparar_salida
    ga_original = proyecto.ejecutar_ga
    llamadas = {"salida": 0, "ga": 0}

    def vigilar_salida(litros):
        assert np.array_equal(litros, reales_train)
        llamadas["salida"] += 1
        return preparar_original(litros)

    def vigilar_ga(activaciones, litros, universo, conjuntos):
        assert len(activaciones) == len(train_positivos)
        assert np.array_equal(litros, reales_train)
        llamadas["ga"] += 1
        return ga_original(activaciones, litros, universo, conjuntos)

    monkeypatch.setattr(proyecto, "preparar_salida", vigilar_salida)
    monkeypatch.setattr(proyecto, "ejecutar_ga", vigilar_ga)
    monkeypatch.setattr(proyecto, "CARPETA_RESULTADOS", tmp_path)
    proyecto.ejecutar(Namespace(preparar=False, sector=None, humedad=None, dias=None))
    capsys.readouterr()
    assert len(test) > 0
    assert llamadas == {"salida": 1, "ga": 1}


def test_fitness_y_metricas_de_regresion_son_calculados_correctamente():
    reales = np.array([10.0, 20.0, 30.0])
    estimados = np.array([8.0, 18.0, 35.0])
    assert proyecto.calcular_mae(reales, estimados) == pytest.approx(3.0)
    metricas = proyecto.evaluar_modelo("ejemplo", reales, estimados)
    assert metricas["mae_litros"] == pytest.approx(3.0)
    assert metricas["rmse_litros"] == pytest.approx(np.sqrt(11))
    assert metricas["medae_litros"] == pytest.approx(2.0)


def test_consulta_manual_devuelve_litros_y_grados():
    train, _, _ = casos_positivos_train()
    universo, conjuntos, _ = proyecto.preparar_salida(train.litros_nominales_riego_24h.to_numpy())
    caso = proyecto.consultar_caso(2, 42, 0.8, proyecto.REGLAS_BASE, universo, conjuntos)
    assert caso["madp"] == 40
    assert caso["humedad_relativa"] == 2
    assert caso["litros_base"] > 0
    assert caso["litros_ga"] == caso["litros_base"]
    assert caso["reglas_activadas"]
    assert np.allclose(caso["grados_humedad"].sum(), 1)


def test_preparacion_reproduce_csv_cuando_existe_dataset_original():
    eventos = proyecto.ORIGEN / "irrigation_events" / "final_irrigation_events.csv"
    sensores = [proyecto.ORIGEN / "merged" / f"dataset_zone_{sector}.csv"
                for sector in proyecto.MADP_POR_SECTOR]
    if not eventos.exists() or any(not ruta.exists() for ruta in sensores):
        pytest.skip("Dataset original de Arnesano no incluido en el paquete ligero")

    incluido = pd.read_csv(proyecto.ARCHIVO_DATOS, parse_dates=["fecha", "medicion"])
    primera = proyecto.preparar_datos()
    segunda = proyecto.preparar_datos()
    pd.testing.assert_frame_equal(incluido, primera, check_dtype=False)
    pd.testing.assert_frame_equal(primera, segunda, check_dtype=False)
    pd.testing.assert_frame_equal(segunda, pd.read_csv(proyecto.ARCHIVO_DATOS,
                                  parse_dates=["fecha", "medicion"]), check_dtype=False)
