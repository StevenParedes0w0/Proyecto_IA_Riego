# Guion para la defensa oral del sistema de riego

**Duración sugerida:** 12–15 minutos, más preguntas.  
**Proyecto:** Sistema genético-difuso para estimar volumen nominal de riego.  
**Rama preparada:** `feat/comentarios`.

Este guion sirve para exponer el problema, seguir el flujo real del programa,
mostrar fragmentos concretos de código y ejecutar una demostración reproducible.
Los números consignados abajo corresponden a la ejecución verificada en esta rama.

## Antes de entrar a la defensa

Abre el repositorio en el editor y deja listas estas pestañas:

1. `riego_simple/main.py`, que contiene preparación, lógica difusa, algoritmo genético y evaluación.
2. `riego_simple/generar_graficas.py`, que dibuja desde los datos y los resultados CSV.
3. `riego_simple/resultados/metricas.csv`, `metricas_por_sector.csv` y `reglas.csv`.
4. La carpeta `Informe-Riego-Simple/imagenes/origen_datos/`, con las gráficas generadas por código.

Abre también una terminal en la raíz del repositorio. Si es un equipo nuevo, instala
dependencias una sola vez:

```bash
python -m pip install -r riego_simple/requirements.txt
```

El CSV preparado `riego_simple/datos_riego.csv` está incluido. Por eso la
demostración normal no depende de leer nuevamente todos los archivos originales.
Si el docente pide reconstruir ese CSV y las fuentes procesadas están disponibles,
se puede ejecutar `python riego_simple/main.py --preparar`.

## Apertura: problema, objetivo y alcance

**Di esto:**

> El problema que abordamos es describir y estimar la cantidad nominal asociada a
> eventos de riego estándar, usando información disponible a las seis de la mañana
> para cada sector y día. El sistema toma la humedad del suelo relativa al MADP del
> sector y los días desde que terminó el último riego estándar. Combina reglas
> difusas de Mamdani con un algoritmo genético que ajusta las conclusiones de esas
> reglas. El resultado es una estimación condicional de litros nominales.

> Es importante delimitar el objetivo: el sistema no decide si se debe regar ni
> cuánto debería regarse desde un punto de vista agronómico. Tampoco mide litros
> reales con un caudalímetro. Reconstruimos el objetivo desde la duración registrada
> de eventos estándar y el caudal nominal documentado para cada sector.

**Si pregunta “¿cuál es la problemática concreta?” responde:**

> Hay telemetría de humedad y registros de eventos para cinco sectores. Queremos
> estudiar si dos entradas sencillas, transformadas en términos lingüísticos,
> permiten estimar el volumen nominal asociado a riegos estándar posteriores. La
> dificultad es que los sectores tienen caudales distintos, hay una distribución
> temporal desigual y los resultados varían entre TRAIN y TEST.

**Abre `main.py`, líneas 27–49.** Señala `FECHA_CORTE`, `MADP_POR_SECTOR`,
`CAUDAL_POR_SECTOR`, las etiquetas, `REGLAS_BASE` y los parámetros del GA.

**Explica:**

- `FECHA_CORTE` fija una partición temporal. No se busca el corte que dé la mejor métrica.
- `MADP_POR_SECTOR` guarda el punto de referencia de humedad de cada sector.
- `CAUDAL_POR_SECTOR` permite expresar una duración en litros nominales por minuto.
- `REGLAS_BASE` define las nueve conclusiones manuales iniciales en orden fijo.
- El GA usa población de 30, 50 generaciones, probabilidad de mutación 0,08 y semilla 42.

## Datos y construcción del objetivo

**Abre `main.py`, líneas 55–85, y luego 88–184.** Empieza por
`resumir_riego_ventana` y continúa con `preparar_datos`.

**Di:**

> Una fila representa una observación de un sector en una fecha de decisión a las
> 06:00. La telemetría se muestrea en bloques de diez minutos. Como la marca de
> tiempo identifica el inicio del bloque, el programa suma diez minutos para
> considerar la medición disponible solo cuando el bloque terminó. Después asocia
> la medición válida más reciente, nunca una futura, con una antigüedad máxima de
> ocho horas.

> Para construir el objetivo, recorta cada evento a la ventana de las 24 horas que
> empieza a las 06:00. Solo incluye eventos estándar del mismo sector. Suma los
> minutos de solapamiento y los multiplica por el caudal nominal del sector. Así se
> obtienen litros nominales asociados al evento, no litros medidos de forma independiente.

**Recorre el código con el cursor:**

1. En `resumir_riego_ventana`, el filtro `type` y `sector` excluye fertirrigación y eventos de otras zonas.
2. `max(inicio, evento.start)` y `min(fin_ventana, evento.end)` delimitan el solapamiento temporal.
3. `total_seconds() / 60` convierte la duración a minutos; al multiplicarla por `CAUDAL_POR_SECTOR[sector]` se obtiene volumen nominal.
4. En `preparar_datos`, `merge_asof(..., direction="backward")` elige la última lectura anterior o igual a la decisión. `tolerance` evita aceptar lecturas antiguas.
5. `np.searchsorted` encuentra el último fin de riego estándar previo y permite calcular `dias_sin_riego`; el valor se limita a 30 días.
6. Si ya hay una válvula abierta a la hora de decisión, la fila se omite porque no representa un nuevo instante de decisión.
7. Al final se crea un `DataFrame`, se ordena por fecha y sector, y se guarda el CSV.

**Si pregunta cómo son las entradas y la etiqueta:**

> La primera entrada es `humedad_suelo - MADP` del sector; la segunda es `dias_sin_riego`.
> El objetivo es `litros_nominales_riego_24h`: litros reconstruidos de riego estándar
> durante las siguientes 24 horas. Los días sin riego permanecen en el CSV y se
> usan para respetar la cronología, pero el ajuste de cantidad es condicional y
> conserva los objetivos positivos.

## División temporal y prevención de fuga

**Abre `main.py`, líneas 186–231.** Señala las comprobaciones de datos y las dos
condiciones que crean TRAIN y TEST.

**Di:**

> Primero valido el CSV: que no falten campos, que la medición no sea posterior a
> la decisión, que el sector tenga parámetros, que no existan litros negativos y
> que el conteo de eventos concuerde con volumen cero o positivo. Luego separo toda
> la cronología. El 27 de junio se purga porque su etiqueta mira las 24 horas
> siguientes y alcanzaría la frontera del periodo de prueba.

> En este dataset quedan 707 filas cronológicas: 473 en TRAIN, cuatro purgadas y
> 230 en TEST. Después del corte temporal se filtran los casos con volumen positivo:
> 142 para TRAIN y 56 para TEST. Es una prueba de periodo posterior dentro de la
> temporada 2025 de Arnesano; no es validación entre años o fincas.

La prueba verifica que las mediciones de ambos bloques no superen la hora de
decisión y que se mantengan exactamente esos conteos.

## Lógica difusa y motor Mamdani

**Abre `main.py`, líneas 234–332.** Sigue en este orden:
`tres_grados` → `fuzzificar` → `preparar_salida` → `inferir_mamdani`.

**Di:**

> La humedad relativa se representa con tres conjuntos: Baja, Media y Alta, cuyos
> puntos de referencia son −20, 0 y 20. La recencia se representa como Reciente,
> Intermedio y Lejano, con puntos 0,5, 1,5 y 4,5 días. Una entrada puede tener
> pertenencia parcial a más de un conjunto; estos valores son grados de pertenencia,
> no probabilidades.

> El producto cartesiano de tres términos de humedad y tres de recencia forma
> nueve reglas. Para combinar antecedentes uso el mínimo, que implementa AND
> difuso. Cada consecuente selecciona Baja, Media o Alta para la salida en litros.

**Explica las operaciones del código:**

- `tres_grados` usa `np.clip` para limitar los hombros a `[0, 1]`; `np.column_stack` crea una columna por conjunto.
- `fuzzificar` añade ejes con `[:, :, None]` y `[:, None, :]` para comparar todas las combinaciones humedad-recencia. `np.minimum` calcula el grado de cada regla; `reshape` las pone en el orden fijo de nueve genes.
- `preparar_salida` calcula Q25, mediana y Q75 exclusivamente en litros positivos de TRAIN. Crea 501 puntos entre cero y el máximo TRAIN para representar las funciones difusas de salida. TEST no define sus cuantiles ni su universo.
- `inferir_mamdani` primero comprueba que hay nueve genes y que cada uno vale 0, 1 o 2. Agrupa la máxima activación por consecuente, recorta cada conjunto de salida con mínimo, agrega los recortes mediante máximo y calcula el centroide discreto ponderando cada punto en litros.

**Frase de resumen para defender la integración:**

> Mamdani convierte dos entradas numéricas en grados, activa reglas, agrega
> conjuntos de salida y defuzzifica directamente a litros nominales. El motor es
> común para la base manual y para el cromosoma hallado por el GA.

## Algoritmo genético

**Abre `main.py`, líneas 335–428.** Muestra `calcular_mae`, `calcular_fitness`,
`mutar` y `ejecutar_ga`.

**Di:**

> El genoma no cambia las funciones de pertenencia ni el motor de inferencia.
> Cambia únicamente la conclusión lingüística de cada una de las nueve reglas.
> Cada gen tiene tres alternativas, Baja, Media o Alta; por eso el espacio contiene
> \(3^9 = 19\,683\) cromosomas posibles.

**Describe el ciclo apuntando al código:**

1. `np.random.default_rng(SEMILLA)` crea el generador seudoaleatorio reproducible.
2. `azar.integers(0, 3, size=(30, 9))` crea una población inicial de 30 cromosomas.
3. `calcular_fitness` llama `inferir_mamdani` para cada individuo usando activaciones y litros de TRAIN. Convierte el error a aptitud con `1 / (1 + MAE)`; menor MAE significa mayor fitness.
4. `np.argmax` localiza el mejor candidato de cada generación. El código compara ese candidato con el mejor histórico y lo guarda si mejora.
5. El historial registra generación, mejor fitness, MAE correspondiente y fitness medio. El bucle recorre generación cero hasta generación 50.
6. Elitismo copia al mejor sin alterarlo. La ruleta selecciona padres con probabilidad proporcional al fitness.
7. El cruce de un punto conserva un prefijo de un padre y agrega el sufijo del otro. `mutar` decide por gen si aplica cambio y suma 1 o 2 módulo 3 para elegir uno de los otros dos valores.
8. Devuelve el mejor cromosoma y una tabla de historial.

**Muestra el resultado real de `reglas.csv`:**

| Regla | Antecedentes | Base | Consecuente GA |
|---|---|---|---|
| R1 | Humedad Baja, Reciente | Media | Media |
| R2 | Humedad Baja, Intermedio | Alta | Alta |
| R3 | Humedad Baja, Lejano | Alta | Baja |
| R4 | Humedad Media, Reciente | Baja | Media |
| R5 | Humedad Media, Intermedio | Media | Baja |
| R6 | Humedad Media, Lejano | Alta | Media |
| R7 | Humedad Alta, Reciente | Baja | Media |
| R8 | Humedad Alta, Intermedio | Baja | Alta |
| R9 | Humedad Alta, Lejano | Media | Media |

> El cromosoma final `120101121` representa esas nueve conclusiones en orden.
> Por ejemplo, el tercer gen es 0, que significa que R3 concluye Baja. El cuarto
> gen es 1, por lo que R4 concluye Media.

## Evaluación y resultados

**Abre `main.py`, líneas 431–462, y después 509–614.** Explica que la evaluación
mantiene separados los datos de prueba.

**Di:**

> Una vez fijados los conjuntos de salida y optimizados los consecuentes con TRAIN,
> paso TEST por fuzzificación e inferencia. Comparo Mamdani Base, Mamdani + GA,
> predicción constante de mediana TRAIN y predicción constante de media TRAIN.
> Calculo MAE, RMSE y MedAE. Además, guardo las predicciones por fila, el historial,
> las reglas y resultados globales y por sector en cinco CSV.

**Muestra `metricas.csv` o la salida del comando:**

| Modelo | MAE (L) | RMSE (L) | MedAE (L) |
|---|---:|---:|---:|
| Mamdani Base | 277,48 | 301,86 | 301,69 |
| Mamdani + GA | 241,44 | 258,69 | 254,57 |
| Mediana TRAIN | **188,98** | **197,86** | **207,35** |
| Media TRAIN | 206,42 | 215,01 | 230,91 |

**Interpreta los resultados sin exagerarlos:**

> El GA reduce el MAE con respecto a la base Mamdani manual: pasa de 277,48 a
> 241,44 litros en TEST. Sin embargo, la mediana de TRAIN logra 188,98 litros de
> MAE, así que el algoritmo genético no es el mejor de las cuatro referencias.
> Presento esto tal como salió: es evidencia de que optimizar la base manual no
> garantiza superar un baseline sencillo.

Luego abre `metricas_por_sector.csv` y explica:

| Sector | Casos positivos TEST | Objetivo medio (L) | MAE Base (L) | MAE GA (L) |
|---:|---:|---:|---:|---:|
| 1 | 4 | 83,05 | 310,32 | 205,30 |
| 2 | 2 | 102,85 | 149,35 | 136,11 |
| 3 | 0 | — | — | — |
| 4 | 40 | 127,52 | 253,99 | 231,65 |
| 5 | 10 | 10,12 | 383,93 | 316,13 |

> El sector 4 concentra 40 de los 56 casos positivos de prueba. El sector 3 no
> tiene casos positivos y por eso sus métricas quedan vacías, no las reemplazo
> por cero. El sector 5 tiene una escala de volumen pequeña, pero el error sigue
> siendo alto. La agregación general esconde esta heterogeneidad; por eso muestro
> también el desglose por sector.

**Limitación que conviene decir antes de que se la pregunten:**

> El experimento utiliza una temporada y una finca: mide transferencia a un
> periodo cronológico posterior de esa misma temporada. No demuestra generalización
> a otras temporadas, fincas ni políticas de riego. Además, el objetivo es volumen
> nominal reconstruido, no volumen real medido ni recomendación agronómica.

## Demostración en terminal

Haz los pasos en este orden desde la raíz. No hace falta volver a crear el entorno
si las dependencias ya están instaladas.

### 1. Ejecutar el pipeline y mostrar resultados

```bash
python riego_simple/main.py
```

Mientras corre, di:

> Este comando carga el CSV, valida y separa temporalmente, obtiene los casos
> positivos, deriva los conjuntos de salida de TRAIN, aprende las reglas con el
> GA, evalúa cuatro modelos sobre TEST, escribe los CSV y presenta el resumen.

Se debe ver una salida equivalente a:

```text
Cronología: 707 casos | TRAIN 473 | purgados 4 | TEST 230
Casos con riego estándar: TRAIN 142 | TEST 56
Cromosoma GA: 120101121 (9 genes ternarios)
MAE de entrenamiento GA: 145.11 L

Mamdani Base      MAE 277.48 | RMSE 301.86 | MedAE 301.69
Mamdani + GA      MAE 241.44 | RMSE 258.69 | MedAE 254.57
Mediana TRAIN     MAE 188.98 | RMSE 197.86 | MedAE 207.35
Media TRAIN       MAE 206.42 | RMSE 215.01 | MedAE 230.91
```

Aclara que el MAE 145,11 corresponde a ajuste en TRAIN, no a rendimiento de prueba.

### 2. Mostrar una consulta explicable

```bash
python riego_simple/main.py --sector 2 --humedad 42 --dias 0.8
```

Explica la entrada mientras aparece:

- MADP del sector 2 = 40; por tanto, humedad relativa = 42 − 40 = 2.
- Para humedad relativa 2, los grados son Baja 0, Media 0,9, Alta 0,1.
- Para 0,8 días, los grados son Reciente 0,7, Intermedio 0,3, Lejano 0.
- Se activan R4 con grado 0,7; R5 con 0,3; R7 con 0,1; R8 con 0,1.
- Con la base manual, el volumen nominal estimado es 137,99 L; con reglas GA, 266,37 L.

> La diferencia se debe a que cambian las conclusiones de algunas reglas, no la
> forma de los conjuntos ni el centroide. El resultado sigue siendo condicional a
> un riego estándar y no significa que el sistema ordene aplicar esa cantidad.

### 3. Generar y abrir gráficas

```bash
python riego_simple/generar_graficas.py
```

Abre `Informe-Riego-Simple/imagenes/origen_datos/`. Hay once PNG: histogramas de
volumen, humedad y recencia; conteos por sector; objetivo frente a predicción;
MAE global y por sector; objetivos sobre el tiempo; evolución del GA; conjuntos
difusos de las entradas y conjuntos de salida. El script lee el CSV y los cinco
resultados del modelo: no recorta las páginas del informe.

**Enseña especialmente:**

1. `01_histograma_volumen_train_test.png`, para comparar distribuciones temporales.
2. `05_objetivo_vs_estimacion_test.png`, para ver errores y diferencias sectoriales.
3. `06_comparacion_mae_test.png`, para contrastar modelo y baselines.
4. `09_evolucion_ga_train.png`, para mostrar la búsqueda y su convergencia.
5. `10_funciones_pertenencia_entradas.png` y `11_conjuntos_salida_train.png`, para conectar código matemático con representación visual.

### 4. Verificar pruebas

```bash
python -m pytest -q
```

Resultado verificado: `13 passed`. Si el docente pregunta qué cubren, abre
`riego_simple/test_main.py`: partición difusa, nueve reglas, centroide, cálculo
de solapamiento, corte/purga temporal, parámetros sectoriales, procedencia de
conjuntos TRAIN, mutación, reproducibilidad del GA, prevención de fuga a TEST,
métricas, consulta manual y reproducibilidad del preprocesamiento si el dataset
original está disponible.

## Mapa rápido de código para navegar durante preguntas

| Archivo y líneas | Qué mostrar |
|---|---|
| `riego_simple/main.py:27–49` | Corte, MADP, caudales, reglas base e hiperparámetros. |
| `riego_simple/main.py:55–85` | Intersección de eventos con las 24 horas y conversión a litros nominales. |
| `riego_simple/main.py:88–184` | Sensores, tiempos, recencia, filas por día-sector y CSV preparado. |
| `riego_simple/main.py:186–231` | Validaciones, purga de frontera y separación TRAIN/TEST. |
| `riego_simple/main.py:234–295` | Funciones de pertenencia, fuzzificación y cuantiles de TRAIN. |
| `riego_simple/main.py:297–332` | AND/implicación/agregación Mamdani y centroide. |
| `riego_simple/main.py:335–428` | Fitness, operadores genéticos, elitismo e historial. |
| `riego_simple/main.py:431–507` | Métricas, tabla de reglas y consulta explicable. |
| `riego_simple/main.py:509–641` | Flujo principal, archivos CSV, resumen y argumentos de consulta. |
| `riego_simple/main.py:643–fin` | Interfaz de terminal construida con `argparse`. |
| `riego_simple/generar_graficas.py:45–90` | Guardado de PNG y lectura de datos/resultados. |
| `riego_simple/generar_graficas.py:92–193` | Histogramas, desempeño, sectores y serie temporal. |
| `riego_simple/generar_graficas.py:194–fin` | Evolución GA, pertenencias y punto de entrada del graficador. |
| `riego_simple/test_main.py:1–fin` | Pruebas automatizadas y qué comportamiento protege cada una. |

Para mostrar un tramo rápidamente en VS Code, usa `Ctrl+P`, escribe el archivo y
pulsa `Ctrl+G` seguido del número de línea; en otros editores, usa el panel
**Outline/Esquema** para navegar por funciones.

## Preguntas probables y respuestas defendibles

### “¿El sistema decide cuándo hay que regar?”

No. Estima la cantidad nominal asociada a observaciones donde se registró un riego
estándar durante las siguientes 24 horas. No predice ocurrencia frente a no
ocurrencia, no modela una acción agronómica y no activa válvulas.

### “¿Por qué se llama volumen nominal?”

Porque el objetivo se reconstruye sumando duración de eventos por caudal nominal
documentado. No proviene de un medidor independiente de litros reales.

### “¿Dónde aplicó Mamdani?”

En `main.py:297–332`, función `inferir_mamdani`: resume activaciones por término
de salida, aplica implicación por mínimo, agregación por máximo y defuzzificación
por centroide. Se llama al evaluar cada cromosoma y para producir predicciones Base,
GA y consulta manual.

### “¿Dónde aplicó el algoritmo genético?”

En `main.py:351–428`: `mutar` y `ejecutar_ga`. Cada individuo es un vector de nueve
consecuentes ternarios; fitness se calcula en TRAIN a partir del error de
`inferir_mamdani`. Ruleta selecciona, cruce recombina, mutación altera y elitismo
preserva el mejor.

### “¿Qué optimiza exactamente el GA?”

Los nueve consecuentes Baja/Media/Alta. No cambia entradas, umbrales, conjuntos,
operadores Mamdani, datos de prueba ni parámetros sectoriales.

### “¿Por qué no reporta solo una métrica?”

MAE se interpreta directamente en litros; RMSE da más peso a errores grandes y
MedAE muestra el error absoluto central. También desgloso por sector para no
ocultar la concentración de TEST en el sector 4.

### “¿El GA mejoró el resultado?”

Frente a la base manual en MAE sí: 277,48 → 241,44 L. Frente a la mediana TRAIN no:
la mediana alcanza 188,98 L. Por ello la conclusión es limitada: el GA mejoró la
base de reglas elegida, pero no superó el baseline más sencillo.

### “¿Generaliza a otros años o fincas?”

No se evaluó esa generalización. La prueba es posterior en la misma temporada
Arnesano 2025. Para sostener generalización interanual o entre fincas se requerirían
datos de esas temporadas/fincas y una validación diseñada por grupos temporales o
geográficos, sin reutilizar la prueba para ajustar decisiones.

### “¿Qué representa un grado como 0,7?”

Grado de pertenencia al conjunto difuso correspondiente. No significa probabilidad
del 70 %.

### “¿Por qué se purgan cuatro filas?”

El target mira 24 horas desde la decisión. Las observaciones del 27 de junio
alcanzarían el inicio de TEST el 28 de junio a las 06:00. Se descartan completas
para evitar que sus etiquetas atraviesen esa frontera.

### “¿Qué pasa con el sector 3 en TEST?”

No tiene casos de riego positivo. Sus métricas no están definidas y aparecen vacías;
no se inventa un error cero.

## Cierre sugerido

> Como conclusión, construimos un pipeline reproducible de datos de sensores y
> eventos, definimos dos entradas difusas, un motor Mamdani de salida continua en
> litros nominales y un GA que optimiza nueve conclusiones lingüísticas usando
> únicamente TRAIN. Evaluamos cronológicamente en un periodo posterior de la misma
> temporada, reportamos comparación global y por sector y comprobamos el flujo con
> pruebas automatizadas. Los resultados son transparentes: el GA mejora la base
> Mamdani manual, pero no supera la mediana de TRAIN, y el alcance no permite
> afirmar generalización a otras temporadas o fincas.

Después de la última pregunta, ofrece mostrar los CSV de resultados o la tabla de
reglas si el profesor desea revisar una evidencia concreta.
