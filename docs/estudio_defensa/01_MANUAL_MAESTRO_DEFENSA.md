# Manual maestro de defensa

## 1. ¿Cuál es el problema?

En palabras sencillas: cuando ya se sabe que después de una observación ocurrió riego, el programa estima el volumen nominal total que se asocia a ese riego. No decide abrir una válvula ni cuándo regar.

Técnicamente, para cada sector y día se usan datos disponibles a las 06:00 y se estima la suma nominal asociada a los riegos estándar que solapan las 24 horas siguientes. Es una regresión difusa condicional: el modelo solo se evalúa sobre filas cuyo volumen reconstruido es positivo.

- Problema agronómico amplio: decidir el momento y la cantidad de riego considerando suelo, cultivo, clima, agua y restricciones.
- Problema computacional de este proyecto: dada una fila histórica y condicionada a que ocurra riego estándar, estimar sus litros nominales reconstruidos.
- Fuera de alcance: decidir Regar/NoRegar, recomendar dosis óptima, medir caudal real o demostrar ahorro/rendimiento.

## 2. ¿Por qué este problema?

Una cantidad continua en litros permite ilustrar una salida Mamdani que se defuzzifica directamente, en vez de convertirla en una decisión binaria. El algoritmo genético busca qué término lingüístico de salida asignar a cada regla. [PROYECTO] La hora 06:00, horizonte de 24 h, variables, reglas y GA son decisiones de implementación; no se atribuyen al profesor sin evidencia directa. [PROFESOR] Se emplea la terminología grado de pertenencia, conjunto difuso y salida defuzzificada.

## 3. Datos

La fuente efectiva es el dataset Arnesano 2025, Mendeley Data V1, DOI `10.17632/c837v6p8ph.1`, una finca con cinco sectores. Se combinan las series de sensores de humedad y eventos de actuadores. El target incluye solo `standard_irrigation`; se excluye fertirrigación. El CSV de eventos cuenta 432 eventos estándar y 357 de fertirrigación según el reporte. Caudales nominales: sectores 1–4, 1.1 L/min; sector 5, 0.4 L/min. MADP por sector: 40, 40, 60, 80 y 70.

La reconstrucción de eventos y caudal nominal no equivale a medición por contador. La fuente tiene una finca y temporada; algunos eventos inferidos fueron filtrados por plausibilidad de humedad, posible circularidad parcial con una entrada. El sector 5 tiene MADP 70, mientras que 50 es otro umbral descrito por la fuente para reconstrucción de ciertos inicios.

## 4. Una observación

```text
Para cada sector y fecha
       ↓
06:00: última celda de sensor ya terminada (promedio 10 min, antigüedad ≤8 h)
       ↓
descartar humedad inválida o válvula abierta
       ↓
humedad relativa al MADP + días desde fin del último riego estándar
       ↓
target: eventos estándar solapados con [06:00, 06:00 + 24 h)
```

Una fila representa un sector-día. La marca `ts` inicia una celda de diez minutos; el código suma esos diez minutos antes de seleccionar mediciones, evitando usar una celda que aún no terminó a las 06:00.

## 5. Target nominal

Para sector `s` y ventana `W=[inicio,inicio+24h)`, el código calcula para cada evento estándar el intervalo de intersección. Si el solapamiento dura `t_i` minutos y el caudal nominal es `q_s`, entonces:

`V = Σ_i t_i q_s`.

Ejemplo: sector 2 tiene caudal 1.1 L/min. Dos eventos solapan la ventana 30 y 20 minutos: `30×1.1 + 20×1.1 = 55 L nominales`. Si un evento comienza antes de las 06:00 o acaba después de las 06:00 del día siguiente, solo se cuenta el tramo dentro de la ventana. Fertirrigación no se suma. No debe llamarse a este resultado litros medidos.

## 6. Humedad relativa al MADP

`H_rel = H_suelo - MADP_s`. Un valor negativo significa que la lectura está por debajo del MADP de referencia; cero coincide con él; positivo está por encima. Es una diferencia en la escala de humedad del sensor, no una probabilidad. En sector 5 se resta 70; el umbral 50 es distinto y no sustituye al MADP del modelo.

## 7. Días desde último riego

Se busca el final del último evento estándar de ese sector que no sea posterior a la decisión. Se calcula diferencia en días y se limita a 30; si no existe historial anterior, se asignan 30. Puede representar recencia de un riego, pero por sí sola no describe clima, cultivo ni necesidad hídrica.

## 8. Lógica difusa desde cero

- Variable lingüística: magnitud descrita por términos (por ejemplo humedad relativa con Baja, Media y Alta).
- Universo: valores numéricos posibles de la variable.
- Conjunto difuso: asigna a cada valor un grado entre 0 y 1.
- Grado de pertenencia: compatibilidad gradual con un término, no probabilidad y los grados de varios términos no son alternativas probabilísticas.
- Fuzzificación: transforma entradas numéricas en esos grados.
- Regla: relación SI antecedente Y antecedente ENTONCES consecuente.
- AND: mínimo de los grados de los antecedentes.
- Implicación: mínimo entre activación y conjunto de salida (truncamiento).
- Agregación: máximo entre salidas truncadas.
- Centroide: `Σ(y μ(y))/Σμ(y)`; produce un valor continuo.

[CONCEPTO] Es el esquema Mamdani clásico. En este proyecto, Base y GA usan el mismo motor; solo difieren los consecuentes.

## 9. Funciones de pertenencia del proyecto

`tres_grados(x,b,c,a)` implementa:

```text
μ_Baja  = clip((c-x)/(c-b), 0, 1)
μ_Alta  = clip((x-c)/(a-c), 0, 1)
μ_Media = 1 - μ_Baja - μ_Alta
```

Humedad relativa usa `b=-20,c=0,a=20`. Días usa `b=0.5,c=1.5,a=4.5`. La salida usa los cuantiles positivos de TRAIN: Q25=119.30, Q50=233.75, Q75=363.825 L; universo 0–746.90 L en 501 puntos.

Consulta reproducida: sector 2, humedad 42, días 0.8. MADP=40, así que `H_rel=2`. Humedad: Baja 0, Media 0.9, Alta 0.1. Para días: Reciente 0.7, Intermedio 0.3, Lejano 0. El resultado se confirma en la salida real de la CLI.

## 10. Nueve reglas

| Regla | Humedad | Días | Base | GA final |
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

Ejemplo: “SI humedad relativa es Media Y días es Reciente ENTONCES volumen es Media” es R4 final. “SI humedad es Baja Y días es Lejano ENTONCES…” es Alta en Base y Baja en GA. Base `122012001`; GA `120101121`, con 0=Baja, 1=Media, 2=Alta.

## 11. Inferencia completa para consulta

Entradas producen H=(0,0.9,0.1), D=(0.7,0.3,0). Con AND=min, las activaciones R1–R9 son `[0,0,0,0.7,0.3,0,0.1,0.1,0]`. Para cromosoma GA `120101121`, R4 y R7 asignan Media (máximo 0.7); R5 asigna Baja (0.3); R8 asigna Alta (0.1). Se truncan los tres conjuntos de salida con esos niveles y luego se unen con máximo punto a punto. El centroide discreto se calcula sobre 501 valores entre 0 y 746.90 L. La ejecución concreta da 266.37 L GA y 137.99 L Base. Para reproducir cada decimal se usan los cuantiles TRAIN y la malla real; la CLI imprime los datos de entrada y reglas activadas.

## 12. Papel del algoritmo genético

```text
cromosoma de 9 genes
        ↓ define consecuentes
motor Mamdani común sobre TRAIN
        ↓ predicciones
MAE en litros → fitness
        ↓ selección, cruce, mutación y elitismo
mejor cromosoma
```

No reemplaza Mamdani ni cambia funciones de pertenencia, entradas u operadores. Optimiza solo las nueve conclusiones.

## 13. Cromosoma

Son nueve genes, cada uno en `{0,1,2}`; por tanto hay `3^9=19 683` asignaciones. Orden: humedad Baja/Media/Alta y, dentro de cada una, días Reciente/Intermedio/Lejano.

| Gen | Regla | Base | GA |
|---:|---|---|---|
|1|R1|1 Media|1 Media|
|2|R2|2 Alta|2 Alta|
|3|R3|2 Alta|0 Baja|
|4|R4|0 Baja|1 Media|
|5|R5|1 Media|0 Baja|
|6|R6|2 Alta|1 Media|
|7|R7|0 Baja|1 Media|
|8|R8|0 Baja|2 Alta|
|9|R9|1 Media|1 Media|

## 14. Operadores genéticos

La población inicial contiene 30 cromosomas ternarios generados con semilla 42. Se evalúa cada individuo en TRAIN; selección por ruleta usa pesos proporcionales al fitness. El cruce elige un punto entre genes 1 y 8 y concatena prefijo de padre 1 y sufijo de padre 2. Cada gen muta independientemente con probabilidad 0.08; si muta, cambia a uno de los otros dos valores. El mejor se copia sin cambio (elitismo). Se evalúan generaciones 0 a 50; al terminar se devuelve el mejor histórico. La semilla permite reproducibilidad en este entorno.

Ejemplo didáctico de cruce: `012|210` y `222|001` producen hijos `012001` y `222210` para cromosomas de seis genes; en el sistema real el corte puede estar tras cualquiera de los primeros ocho genes. Ejemplo de mutación: gen 1 muta de 0 a 2, nunca permanece en 0.

## 15. Fitness

`MAE=(1/n)Σ|y-y_hat|`; `fitness=1/(1+MAE)`. Si en un ejercicio pequeño el MAE es 9 L, fitness es 0.1; si otro tiene MAE 4 L, fitness es 0.2 y tiene mayor probabilidad proporcional de ser elegido. Para el mejor GA, MAE TRAIN=145.112091 L y fitness aproximado `1/146.112091 = 0.00684406`.

## 16. División temporal y fuga

No se mezclan fechas aleatoriamente: eso podría poner días próximos de la misma temporada en ambos conjuntos y no simular futuro. Corte fijo: 28 junio 2025. De 707 filas: 473 TRAIN, cuatro filas del 27 junio purgadas y 230 TEST. La etiqueta abarca las siguientes 24 h; purgar el día anterior impide que su etiqueta atraviese la frontera. Solo después del split se filtran positivos: 142 TRAIN y 56 TEST. Cuantiles de salida, cromosoma, MAE/fitness y referencias constantes se calculan con TRAIN. TEST solo recibe inferencia y métricas finales. Es evaluación posterior dentro de la misma temporada, no interanual.

## 17. Resultados

| Modelo | MAE L | RMSE L | MedAE L |
|---|---:|---:|---:|
| Mamdani Base |277.48|301.86|301.69|
| Mamdani + GA |241.44|258.69|254.57|
| Mediana TRAIN |188.98|197.86|207.35|
| Media TRAIN |206.42|215.01|230.91|

MAE es error absoluto promedio; RMSE penaliza más errores grandes; MedAE es mediana del error absoluto. GA reduce MAE de Base en 36.03 L (~13%), pero queda 52.46 L peor que la referencia mediana. Esto se informa porque una comparación honesta incluye un baseline sencillo y porque la prueba indica límites predictivos; no se seleccionó el corte para favorecerlo.

## 18. Cambio TRAIN–TEST y sectores

La mediana de volúmenes positivos baja de 233.75 L a 31.90 L. En TEST, sector 4 aporta 40/56 casos (71.43%); sector 3 no tiene casos. Sectores 1 y 2 tienen solo cuatro y dos casos, respectivamente. Sector 5 tiene caudal nominal 0.4 L/min, diferente a los demás. Es evidencia de distinta distribución/composición, no prueba por sí misma de una causa. Una única superficie de reglas no incluye sector ni caudal como entrada.

## 19. Limitaciones

El target depende de duración reconstruida y caudal declarado, no de contador. La condición “ocurrió riego” se conoce retrospectivamente; en uso real se necesitaría que otro proceso/operador ya haya decidido regar. Solo hay una finca y temporada, y la evaluación cubre una parte posterior de esa temporada. La composición por sectores cambia mucho y un sector queda sin positivos de prueba. Las entradas no incluyen clima, cultivo o caudal; el conjunto de nueve reglas es común a todos los sectores. Algunos eventos inferidos se filtraron por humedad, lo que puede introducir dependencia entre predictor y target. Finalmente, una referencia de mediana supera al GA: el proyecto demuestra implementación reproducible de Mamdani+GA, no superioridad ni validez agronómica.

## 20. Qué demuestra

**Respuesta de 30 segundos:** “Construimos en español un sistema Mamdani de dos entradas para estimar, condicionado a que se haya observado un riego estándar, su volumen nominal reconstruido en las 24 horas posteriores a las 06:00. Un GA ternario optimiza los consecuentes de nueve reglas usando solo el periodo inicial de Arnesano 2025. En la prueba cronológica posterior el GA mejora la base Mamdani, pero no la mediana de TRAIN; por eso presentamos el resultado como demostración técnica, no como recomendador agronómico.”

**Respuesta de 2 minutos:** “Cada fila representa un sector y un día. A las 06:00 usamos una medición ya terminada, la expresamos relativa al MADP del sector y calculamos días desde el último riego estándar finalizado. El target suma duración solapada por caudal nominal para eventos estándar de la ventana siguiente de 24 horas; fertirrigación se excluye. No son litros medidos. La humedad y los días tienen tres términos cada uno, que generan nueve reglas. Mamdani activa reglas con mínimo, trunca las salidas con mínimo, las agrega con máximo y obtiene litros mediante centroide. El cromosoma tiene nueve genes ternarios que eligen Baja, Media o Alta como consecuente. El GA usa ruleta, cruce de un punto, mutación y elitismo para minimizar MAE de TRAIN mediante fitness inverso. Se congeló el corte del 28 de junio; una purga protege la etiqueta de 24 horas y el TEST posterior no interviene en ajuste. El GA obtiene MAE 241.44 L frente a 277.48 de la base, pero la mediana TRAIN consigue 188.98. Además, TEST está desplazado y dominado por sector 4. Por eso el sistema estima una cantidad nominal condicional y no decide riego, optimiza dosis ni demuestra generalización externa.”

## Fuentes de trazabilidad

Código: [`riego_simple/main.py`](../../riego_simple/main.py); resultados: [`riego_simple/resultados/`](../../riego_simple/resultados/); explicación operativa: [`riego_simple/README.md`](../../riego_simple/README.md); reporte: [`docs/reports/REPORTE_RIEGO_SIMPLE_2026-09-28.md`](../reports/REPORTE_RIEGO_SIMPLE_2026-09-28.md).
