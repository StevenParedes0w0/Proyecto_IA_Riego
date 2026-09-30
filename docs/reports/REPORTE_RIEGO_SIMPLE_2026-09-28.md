# Reporte final de implementación: estimación condicional de volumen nominal de riego

Actualizado: 29 de septiembre de 2026. Rama de trabajo: `develop`.

## 1. Decisión final y alcance

Se reemplazó el objetivo binario anterior por una **estimación continua en litros nominales**. Dada una observación de un sector a las 06:00 y **condicionado a que ocurra al menos un riego estándar observado en las 24 horas siguientes**, el motor Mamdani estima el volumen nominal asociado. La versión anterior de clasificación no era matemáticamente inválida; se adoptó el objetivo de cantidad por la finalidad académica indicada por el usuario y el profesor.

El sistema no decide iniciar el riego. Una consulta manual de dos entradas produce litros condicionales; no determina si se cumplirá la condición de que haya riego. El valor objetivo tampoco es un volumen medido por contador: es una **reconstrucción nominal**, basada en la duración de eventos publicados y el caudal nominal por sector. Ninguna cifra demuestra dosis óptima, ahorro de agua o rendimiento agronómico.

La estructura explicable es:

```text
Arnesano 2025 -> sector-día a las 06:00 -> humedad relativa al MADP + días sin riego
-> grados de pertenencia -> 9 reglas Mamdani -> salida difusa Baja/Media/Alta
-> centroide en litros
                         GA: busca solo los 9 consecuentes de las reglas
```

El programa principal permanece en `riego_simple/main.py`, con funciones y comentarios en español y sin capas de arquitectura adicionales.

## 2. Fuente y procedencia

- Dataset efectivo: [*Soil Moisture, Irrigation Actuator and Weather Dataset from a Multi-Sector Precision-Irrigation*](https://data.mendeley.com/datasets/c837v6p8ph/1).
- Versión utilizada: **1**, identificada también como 1.0 en el `README.md` local.
- DOI: **10.17632/c837v6p8ph.1**.
- Publicación del registro: 6 de septiembre de 2026. Licencia: CC BY 4.0.
- Campaña estudiada: Arnesano, Italia, temporada 2025; una finca, cinco sectores.
- Archivos consumidos: `datasets/arnesano_2025/02_processed_data/merged/dataset_zone_{1..5}.csv` y `irrigation_events/final_irrigation_events.csv`.

La tabla de eventos publicada contiene 432 eventos `standard_irrigation` y 357 de fertirrigación. El proyecto usa **solo** los primeros como objetivo de cantidad. La documentación local de la fuente declara caudales nominales de 1,1 L/min para sectores 1–4 y 0,4 L/min para sector 5; los mismos valores aparecen en `datasets/arnesano_2025/03_code/config.py`. Son caudales nominales, no una medición independiente de los litros efectivamente entregados.

La reconstrucción publicada de algunos eventos inferidos empleó humedad como filtro de plausibilidad. Esto puede generar circularidad parcial entre una entrada del modelo y el target. Se conserva como limitación explícita.

## 3. Unidad de observación y cálculo del target

Se forma una fila por sector y día con decisión fija a las 06:00. La serie `merged` contiene promedios en celdas de diez minutos; su marca `ts` corresponde al inicio de la celda. Por ello se suman diez minutos y solo se utiliza una celda ya completada a las 06:00, con antigüedad máxima de ocho horas. Se descarta humedad ausente o fuera de 0–100 y un caso si alguna válvula ya estaba abierta. No se usa la serie `preprocessed` interpolada, que podría incorporar mediciones posteriores.

El target recorre la ventana `[06:00, 06:00 + 24 h)`. Para cada evento estándar se considera únicamente la duración que solapa esa ventana, y se suman los litros nominales de todos los eventos de la fila:

```text
minutos_solapados = max(0, min(fin_ventana, fin_evento)
                         - max(inicio_ventana, inicio_evento)) en minutos

litros_nominales_riego_24h = Σ minutos_solapados × caudal_nominal_sector_L_min
```

El CSV conserva `numero_eventos_riego_24h` y `litros_nominales_riego_24h`, además de fecha, medición, sector y entradas. Hay 707 filas cronológicas; 198 tienen volumen nominal positivo en TRAIN o TEST. Entre las 198 positivas, 95 contienen más de un evento estándar en la ventana. Los casos con cero se conservan en el CSV para fijar el corte temporal, pero no entran al modelo condicional de cantidad.

### MADP y caudal no son lo mismo

La humedad relativa se calcula como `humedad_suelo - MADP_POR_SECTOR[sector]`. Los MADP son `40, 40, 60, 80, 70` para sectores 1 a 5. En el sector 5, **MADP = 70**, mientras que **50** es un umbral distinto usado en la reconstrucción publicada de algunos inicios. El sector 5 también tiene un **caudal nominal de 0,4 L/min**, frente a 1,1 L/min en los demás sectores. El caudal se usa para formar el target, no como tercera entrada del sistema difuso.

## 4. División temporal congelada

Se mantuvo el corte anterior del **28 de junio de 2025 a las 06:00**. No se buscó un corte más favorable tras observar las distribuciones. Primero se dividieron las 707 filas completas y se purgó el 27 de junio porque la etiqueta de 24 horas de ese día llega hasta la frontera de prueba. Solo después se filtraron, dentro de TRAIN y TEST por separado, los casos con litros nominales positivos.

| Conjunto | Filas cronológicas | Casos con riego estándar | Periodo |
|---|---:|---:|---|
| TRAIN | 473 | 142 | 12 de febrero–26 de junio de 2025 |
| Purga | 4 | No se usan | 27 de junio |
| TEST | 230 | 56 | 28 de junio–22 de agosto de 2025 |

La prueba mide un periodo posterior de **la misma temporada 2025**. No representa validación interanual ni externa. TEST no participa en la definición de funciones de salida, reglas base, GA, seed, corte ni universo de salida.

## 5. Variables y funciones de pertenencia

Las dos entradas son:

1. `humedad_relativa_madp` en puntos de la escala del sensor, con conjuntos difusos Baja, Media y Alta, definidos por `−20, 0, 20`.
2. `dias_sin_riego` desde el último **riego estándar terminado**, con tope de 30 días y conjuntos Reciente, Intermedio y Lejano, definidos por `0,5; 1,5; 4,5`.

Para tres puntos `b < c < a`, la función visible `tres_grados` implementa:

```text
μ_Baja(x)  = clip((c − x)/(c − b), 0, 1)
μ_Alta(x)  = clip((x − c)/(a − c), 0, 1)
μ_Media(x) = 1 − μ_Baja(x) − μ_Alta(x)
```

Son **grados de pertenencia**, no probabilidades. Baja, Media, Alta, Reciente, Intermedio y Lejano son **conjuntos difusos**, no clases supervisadas. Con tres términos por entrada hay `3 × 3 = 9` reglas.

La variable de salida es volumen nominal estimado en litros. Sus conjuntos Baja, Media y Alta utilizan **solo los litros positivos de TRAIN**: Q25 = **119,30 L**, Q50 = **233,75 L**, Q75 = **363,825 L**. El universo discreto de salida va de **0 a 746,90 L**, máximo de TRAIN, en 501 puntos. Baja es hombro izquierdo con pertenencia completa hasta Q25; Media es triangular entre Q25 y Q75, con pico en Q50; Alta es hombro derecho desde Q50, con pertenencia completa desde Q75. Estos puntos no se actualizaron al mirar TEST.

## 6. Motor Mamdani y bases de reglas

El motor común para Base y GA ejecuta: fuzzificación; activación de cada regla con `AND = min`; elección del conjunto de salida por el consecuente; truncamiento `min`; unión de conclusiones `max`; y centroide `Σ(y·μ_agregada)/Σμ_agregada`. El resultado es una cantidad continua en **litros**. No hay umbral de clasificación ni salida Regar/NoRegar.

La base manual fija responde a la intuición de más volumen con menos humedad y más tiempo transcurrido. Se estableció antes de evaluar TEST:

| Regla | Humedad | Días | Base manual | GA final |
|---|---|---|---|---|
| R1 | Baja | Reciente | Media | Media |
| R2 | Baja | Intermedio | Alta | Alta |
| R3 | Baja | Lejano | Alta | Baja |
| R4 | Media | Reciente | Baja | Media |
| R5 | Media | Intermedio | Media | Baja |
| R6 | Media | Lejano | Alta | Media |
| R7 | Alta | Reciente | Baja | Media |
| R8 | Alta | Intermedio | Baja | Alta |
| R9 | Alta | Lejano | Media | Media |

Los números de los consecuentes son `0 = Baja`, `1 = Media`, `2 = Alta`. El cromosoma Base es `122012001` y el cromosoma GA reproducible es **`120101121`**. Ambos recorren el mismo motor Mamdani; solo cambia el conjunto de salida asignado a cada regla.

## 7. Algoritmo genético

El GA mantiene nueve genes ternarios, población 30, 50 generaciones, semilla 42, ruleta, cruce de un punto, mutación independiente por gen de 0,08 y elitismo. Si un gen muta, toma uno de los otros dos valores posibles. No modifica entradas, funciones de pertenencia, operadores Mamdani ni el target.

El criterio de entrenamiento es el error absoluto medio (MAE) de litros nominales sobre los 142 casos positivos de TRAIN:

```text
MAE_TRAIN = media(|litros_nominales_objetivo − litros_estimados|)
fitness = 1 / (1 + MAE_TRAIN)
```

El mejor cromosoma obtuvo **MAE TRAIN = 145,112091 L** y fitness **0,00684406057**. `historial_ga.csv` registra la mejor aptitud y la aptitud media en las 51 evaluaciones de generación 0 a 50. La selección del GA no utiliza TEST.

No se mantuvo la búsqueda exhaustiva en la ejecución normal. El nuevo espacio contiene `3^9 = 19 683` configuraciones; ya no son las 512 bases binarias anteriores. La enumeración es opcional didácticamente, pero su ausencia simplifica la defensa y no afecta al entrenamiento genético.

## 8. Diagnóstico del nuevo target

Antes de interpretar las métricas, se verificó la escala de las cantidades positivas. Las diferencias entre periodos son marcadas:

| Periodo | Casos | Mínimo (L) | Q25 (L) | Mediana (L) | Q75 (L) | Media (L) | Máximo (L) |
|---|---:|---:|---:|---:|---:|---:|---:|
| TRAIN | 142 | 7,20 | 119,30 | 233,75 | 363,83 | 258,41 | 746,90 |
| TEST | 56 | 6,00 | 21,73 | 31,90 | 99,28 | 102,50 | 545,60 |

La mediana de TEST es **201,85 L menor** que la de TRAIN. Este desplazamiento se documenta, pero no se usa para cambiar el corte, los cuantiles ni el cromosoma. Los conteos por sector también cambian:

| Sector | TRAIN con riego | Mediana TRAIN (L) | Media TRAIN (L) | TEST con riego | Mediana TEST (L) | Media TEST (L) |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 29 | 147,40 | 180,78 | 4 | 51,15 | 83,05 |
| 2 | 44 | 302,50 | 298,48 | 2 | 102,85 | 102,85 |
| 3 | 5 | 183,70 | 218,24 | 0 | — | — |
| 4 | 46 | 320,10 | 349,92 | 40 | 38,50 | 127,52 |
| 5 | 18 | 22,60 | 62,87 | 10 | 7,80 | 10,12 |

El sector 4 concentra **40/56 = 71,43 %** de las filas positivas de TEST. El sector 3 no puede evaluarse condicionalmente en TEST. El caudal menor del sector 5 y la distinta actividad de riego generan escalas difíciles de explicar con dos entradas y una sola tabla de nueve reglas.

## 9. Resultados de prueba y comparación justa

Todas las métricas siguientes usan únicamente los **56 casos positivos de TEST**. MAE es la media de los errores absolutos, RMSE la raíz del error cuadrático medio y MedAE la mediana de los errores absolutos. Las referencias constantes se obtienen exclusivamente de TRAIN: mediana 233,75 L y media 258,41 L.

| Modelo | MAE (L) | RMSE (L) | MedAE (L) |
|---|---:|---:|---:|
| Mamdani Base | 277,48 | 301,86 | 301,69 |
| Mamdani + GA | 241,44 | 258,69 | 254,57 |
| Mediana TRAIN | **188,98** | **197,86** | **207,35** |
| Media TRAIN | 206,42 | 215,01 | 230,91 |

El GA mejora la base Mamdani en **36,03 L de MAE** (aproximadamente 13,0 % respecto a la base), pero su MAE es **52,46 L peor** que usar siempre la mediana de TRAIN. También pierde frente a esa referencia en RMSE y MedAE. No hay evidencia de que estas dos entradas basten para explicar el volumen nominal del periodo posterior. La evaluación no respalda superioridad predictiva del sistema difuso frente a una constante sencilla.

| Sector | Casos TEST | Volumen medio objetivo (L) | MAE Base (L) | MAE GA (L) |
|---|---:|---:|---:|---:|
| 1 | 4 | 83,05 | 310,32 | 205,30 |
| 2 | 2 | 102,85 | 149,35 | 136,11 |
| 3 | 0 | — | — | — |
| 4 | 40 | 127,52 | 253,99 | 231,65 |
| 5 | 10 | 10,12 | 383,93 | 316,13 |

Las métricas de sectores 1 y 2 descansan en muy pocos casos. El sector 5 presenta un error especialmente alto respecto a su media objetivo de 10,12 L. El error global está dominado por la composición del conjunto de prueba y no debe ocultar estas diferencias.

## 10. Salidas y demostración

La ejecución normal guarda cinco archivos en `riego_simple/resultados/`:

1. `reglas.csv`: nombres legibles y consecuentes Base/GA.
2. `historial_ga.csv`: mejor fitness, MAE TRAIN y fitness medio por generación.
3. `predicciones.csv`: solo filas de TEST con riego, volumen nominal objetivo y cuatro estimaciones.
4. `metricas.csv`: MAE, RMSE y MedAE de Base, GA, mediana y media de TRAIN.
5. `metricas_por_sector.csv`: casos, volumen medio y MAE Base/GA por sector.

Se retiraron `ablacion.csv` y `comparacion_ga_exhaustiva.csv`, que correspondían a la clasificación binaria anterior. Ningún CSV nuevo contiene métricas o decisiones de esa clasificación.

La consulta `python riego_simple/main.py --sector 2 --humedad 42 --dias 0.8` imprime MADP 40 y humedad relativa 2. Los grados de humedad son Baja 0,0, Media 0,9, Alta 0,1; los de días son Reciente 0,7, Intermedio 0,3, Lejano 0,0. El motor devuelve **137,99 L** para Base y **266,37 L** para GA; son dos estimaciones condicionales y no decisiones de iniciar el riego. También se imprimen las reglas activadas y sus consecuentes.

## 11. Verificación técnica

Comandos exigidos desde la raíz:

```bash
python riego_simple/main.py --preparar
python riego_simple/main.py
python riego_simple/main.py --sector 2 --humedad 42 --dias 0.8
python -m pytest -q
```

Los tests comprueban la aritmética de pertenencias, nueve reglas y nueve genes ternarios, centroide sintético continuo, duración solapada × caudal nominal, exclusión de fertirrigación, corte y purga, cuantiles solo de TRAIN, mutación ternaria, reproducibilidad, métricas de regresión, consulta y regeneración tabular determinista. La prueba de reconstrucción se omite con `pytest.skip` únicamente en el paquete ligero que no incluye los datasets originales.

Resultado de verificación: `python -m pytest -q` desde la raíz completa **96 pruebas superadas**, ya que `pytest.ini` incluye ahora `riego_simple/` en la recolección. En el ZIP ligero extraído, el mismo comando produjo **12 superadas y 1 omitida** por ausencia intencional de los archivos grandes. `--preparar`, la ejecución normal y la consulta manual terminaron correctamente. El PDF final se compiló sin advertencias de desbordamiento y se revisó visualmente.

El informe académico editable y su PDF están en `Informe-Riego-Simple/`. El ZIP técnico ligero `riego_simple_volumen_nominal_2026-09-29.zip` contiene solo el programa, README, dependencias, CSV preparado, resultados y tests; no incluye el dataset extenso ni el informe.

## 12. Limitaciones y conclusión

- La condición futura de que haya riego se conoce en el conjunto histórico, pero no la decide este sistema a las 06:00. Una aplicación operativa requeriría que el operador ya haya decidido regar o un componente adicional fuera de este alcance.
- El target es nominal: multiplicación de duración reconstruida por caudal declarado. No equivale a volumen medido por contador.
- Una finca, una temporada y holdout intra-temporada no sustentan generalización a otros años, fincas o políticas.
- Los sectores difieren en cultivo/sustrato, caudal y actividad; el modelo usa una sola superficie de reglas y no incorpora el sector como entrada.
- El sector 3 carece de positivos en TEST y los sectores 1 y 2 tienen muy pocos.
- Algunos eventos inferidos de la fuente se validaron con humedad; puede existir circularidad parcial entre entrada y target.
- La mediana de TRAIN supera al GA en todas las métricas principales de TEST. Dos entradas pueden ser insuficientes para anticipar la duración de aperturas futuras.

La versión queda **terminada como demostración académica reproducible** de fuzzificación, inferencia Mamdani continua y optimización genética de consecuentes. Su capacidad predictiva para litros nominales en esta prueba es limitada y se presenta sin maquillarla. No se añadieron variables, modelos ni cambios de corte tras conocer TEST.
