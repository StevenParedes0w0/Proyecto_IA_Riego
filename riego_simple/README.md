# Sistema genético-difuso para estimación de volumen nominal de riego

## Qué hace

El sistema estima **cuántos litros nominales se asocian a riegos estándar observados** dentro de las 24 horas posteriores a las 06:00 de un sector y día. Es una estimación **condicional a que ocurra un riego**. No decide si debe iniciarse, no calcula una dosis agronómica óptima y no demuestra ahorro de agua.

Las entradas disponibles a las 06:00 son la humedad del suelo relativa al MADP del sector y los días desde el último riego estándar terminado. Cada entrada tiene tres conjuntos difusos. Sus nueve combinaciones forman nueve reglas Mamdani. Una base manual fija sirve de comparación; el algoritmo genético (GA) busca únicamente los nueve consecuentes `Baja/Media/Alta`. Los grados entre 0 y 1 son **grados de pertenencia**, no probabilidades. Los términos lingüísticos son **conjuntos difusos**, no clases.

## Ejecutar desde la raíz

```bash
python -m pip install -r riego_simple/requirements.txt
python riego_simple/main.py
python riego_simple/generar_graficas.py
python riego_simple/main.py --sector 2 --humedad 42 --dias 0.8
python -m pytest -q
```

El comando `python riego_simple/generar_graficas.py` crea histogramas y gráficas
directamente desde `datos_riego.csv` y las salidas recientes del modelo. Guarda
los PNG en `Informe-Riego-Simple/imagenes/origen_datos/`. Para reconstruir primero
el CSV desde las fuentes procesadas de Arnesano, ejecute `python riego_simple/main.py --preparar`.

`datos_riego.csv` está incluido; la ejecución normal y la consulta manual funcionan sin el dataset extenso. Para reconstruirlo cuando se dispone de `datasets/arnesano_2025/02_processed_data/`:

```bash
python riego_simple/main.py --preparar
```

La suite del paquete ligero omite únicamente la prueba de reconstrucción cuando falta esa fuente. El informe académico editable y su PDF están en `Informe-Riego-Simple/`.

La entrega técnica compacta de esta versión es `riego_simple_volumen_nominal_2026-09-29.zip`. Contiene solo este programa, el CSV preparado, las pruebas y cinco tablas de resultados; no incluye los datos originales extensos ni los informes.

## Datos y target

Fuente efectiva: [*Soil Moisture, Irrigation Actuator and Weather Dataset from a Multi-Sector Precision-Irrigation*](https://data.mendeley.com/datasets/c837v6p8ph/1), **versión 1**, DOI **10.17632/c837v6p8ph.1**, publicada el 6 de septiembre de 2026, licencia CC BY 4.0. El `README.md` local indica versión 1.0. Se usan las series `merged/dataset_zone_{1..5}.csv` y `irrigation_events/final_irrigation_events.csv`.

La marca `ts` de cada celda de sensor de diez minutos indica su inicio. El programa la desplaza diez minutos para usar únicamente celdas terminadas a más tardar a las 06:00 (con antigüedad máxima de ocho horas). Excluye valores de humedad fuera de 0–100 y filas con una válvula ya abierta. La ventana objetivo es `[06:00, 06:00 + 24 h)`; se incluyen solo eventos `standard_irrigation` y se excluye la fertirrigación.

El **volumen nominal objetivo** se reconstruye así, contando únicamente los minutos de solapamiento con la ventana:

```text
litros_nominales_riego_24h = Σ minutos de cada riego estándar × caudal nominal del sector
```

Los caudales documentados son 1,1 L/min para sectores 1–4 y 0,4 L/min para sector 5. No es una medición independiente de un contador: depende de duración reconstruida y caudal nominal.

Los MADP son `{1: 40, 2: 40, 3: 60, 4: 80, 5: 70}` y la primera entrada es `humedad_suelo - MADP_POR_SECTOR[sector]`. Para el sector 5, MADP 70 es distinto del umbral 50 usado por la fuente en la reconstrucción de algunos inicios de evento.

## División y aprendizaje

La cronología completa conserva **707** filas. El corte se fijó previamente en el **28 de junio de 2025** y no se movió al cambiar el objetivo: 473 filas iniciales forman TRAIN, cuatro filas del 27 de junio se purgan por el horizonte de 24 horas y 230 filas posteriores forman TEST. **Después** de separar, se seleccionan solo filas con `litros_nominales_riego_24h > 0`: **142** en TRAIN y **56** en TEST.

Las entradas usan tres conjuntos por variable: humedad Baja/Media/Alta con puntos `−20, 0, 20` y días Reciente/Intermedio/Lejano con `0,5; 1,5; 4,5`. La salida Mamdani está en litros, con conjuntos Baja/Media/Alta definidos usando exclusivamente los cuartiles de litros positivos de TRAIN: Q25 = 119,30 L; mediana = 233,75 L; Q75 = 363,83 L. El universo va de 0 al máximo de TRAIN, 746,90 L. El motor usa AND `min`, implicación `min`, agregación `max` y defuzzificación por centroide. Su resultado es directamente una cantidad continua en litros.

La base manual tiene consecuentes `[1,2,2,0,1,2,0,0,1]`, donde `0 = Baja`, `1 = Media` y `2 = Alta`. El GA usa **nueve genes ternarios**, población 30, 50 generaciones, semilla 42, ruleta, cruce de un punto, mutación independiente de 0,08 y elitismo. El fitness, calculado solo en TRAIN, es:

```text
fitness = 1 / (1 + MAE_en_litros_de_TRAIN)
```

Mamdani Base y Mamdani + GA comparten exactamente el mismo motor y las mismas funciones de pertenencia. Solo cambian los nueve consecuentes. La búsqueda exhaustiva se retiró de la ejecución normal porque el nuevo espacio tiene `3^9 = 19 683` combinaciones y no es necesaria para explicar el GA.

## Resultados de TEST

| Modelo | MAE (L) | RMSE (L) | MedAE (L) |
|---|---:|---:|---:|
| Mamdani Base | 277,48 | 301,86 | 301,69 |
| Mamdani + GA | 241,44 | 258,69 | 254,57 |
| Mediana de TRAIN | **188,98** | **197,86** | **207,35** |
| Media de TRAIN | 206,42 | 215,01 | 230,91 |

El GA mejora la base Mamdani, pero **no supera la mediana de TRAIN**. El cromosoma final reproducible es `120101121` y el MAE de TRAIN del GA es 145,11 L. La diferencia entre periodos es grande: la mediana del volumen nominal positivo baja de 233,75 L en TRAIN a 31,90 L en TEST. La prueba solo mide un periodo posterior de la misma temporada 2025.

| Sector | Casos TEST con riego | Volumen nominal medio (L) | MAE Base (L) | MAE GA (L) |
|---|---:|---:|---:|---:|
| 1 | 4 | 83,05 | 310,32 | 205,30 |
| 2 | 2 | 102,85 | 149,35 | 136,11 |
| 3 | 0 | — | — | — |
| 4 | 40 | 127,52 | 253,99 | 231,65 |
| 5 | 10 | 10,12 | 383,93 | 316,13 |

El sector 4 concentra 40 de los 56 casos de TEST y el sector 3 carece de casos. El sector 5 usa un caudal nominal distinto. Una sola superficie de reglas con dos entradas no explica bien todas estas escalas. Además, la reconstrucción publicada de algunos eventos inferidos aplicó humedad como filtro de plausibilidad. Los resultados no demuestran generalización a otras temporadas, fincas o políticas de riego.

## Dónde mirar el código y las salidas

Todo el recorrido principal está en [main.py](main.py): configuración, preparación, división temporal, pertenencias, Mamdani, GA, evaluación y consulta manual. En `resultados/` hay solo cinco CSV: `reglas.csv`, `historial_ga.csv`, `predicciones.csv`, `metricas.csv` y `metricas_por_sector.csv`.
