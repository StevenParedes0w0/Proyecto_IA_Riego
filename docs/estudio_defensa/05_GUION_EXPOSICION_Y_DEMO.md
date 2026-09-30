# Guion de exposición y demostración

Duración sugerida: 12–14 minutos. Mantén la distinción entre estimar volumen nominal condicionado y decidir si regar.

## Guion por tiempo

### 0:00–1:00 | Problema

**Decir:** “Estimamos el volumen nominal asociado a riegos estándar observados en las 24 horas después de las 06:00, dadas dos entradas. El modelo no decide iniciar el riego.”

**Mostrar:** objetivo y diagrama general. **Evitar:** hablar de dosis óptima. **Transición:** “Para construir la observación usamos Arnesano 2025.”

### 1:00–2:00 | Dataset

**Decir:** fuente Mendeley V1, una finca, cinco sectores; sensores y eventos. Usamos standard irrigation, excluimos fertirrigation. **Mostrar:** `README.md` o reporte. **Evitar:** decir que son litros medidos. **Transición:** “Veamos una fila y su etiqueta.”

### 2:00–3:00 | Observación y target

**Decir:** una fila sector-día a 06:00; lectura completada, humedad relativa al MADP y días desde riego finalizado. Target suma duración solapada×caudal nominal en ventana `[06:00,06:00+24h)`. **Mostrar:** fórmula y ejemplo 30+20 minutos×1.1=55 L. **Evitar:** incluir evento fuera de ventana. **Transición:** “Las entradas numéricas se expresan con conjuntos difusos.”

### 3:00–4:00 | Pertenencias

**Decir:** tres términos por variable; grado es compatibilidad, no probabilidad. **Mostrar:** `tres_grados`, consulta Hrel2 produce (0,.9,.1), días.8 produce (.7,.3,0). **Evitar:** hablar de clases. **Transición:** “Las combinaciones forman nueve reglas.”

### 4:00–5:15 | Reglas y Mamdani

**Decir:** 3×3=9. AND=min, implicación=min, agregación=max, centroide devuelve litros. **Mostrar:** matriz Base/GA. **Evitar:** decir que Mamdani se entrena. **Transición:** “El GA solo busca los consecuentes.”

### 5:15–6:45 | Cromosoma y GA

**Decir:** nueve genes ternarios, 3^9 posibilidades; población30, ruleta, cruce un punto, mutación .08, elitismo, 50 generaciones, semilla42. Fitness `1/(1+MAE_TRAIN)`. **Mostrar:** cromosoma `120101121`. **Evitar:** prometer óptimo global. **Transición:** “Para evaluar reservamos fechas posteriores.”

### 6:45–7:45 | Protocolo temporal

**Decir:** 707 filas: 473 TRAIN, 4 purga, 230 TEST; luego positivos 142/56. Corte fijo 28 junio. **Mostrar:** línea de tiempo. **Evitar:** split aleatorio o validación entre años. **Transición:** “Revisemos resultados sin ocultar baselines.”

### 7:45–9:15 | Resultados

**Decir:** GA MAE241.44; Base277.48; mediana TRAIN188.98; media206.42. Mejora la base, pierde frente a mediana. **Mostrar:** `metricas.csv`. Explicar MAE, RMSE, MedAE. **Evitar:** decir que GA es el mejor método.

### 9:15–10:15 | Shift y sectores

**Decir:** mediana positiva TRAIN233.75, TEST31.90; sector4 40/56; sector3 sin positivos; s5 caudal .4. Esto es una diferencia observada, no una causa demostrada. **Mostrar:** métricas por sector. **Transición:** “Por ello el alcance es acotado.”

### 10:15–11:15 | Límites y conclusión

**Decir:** una finca, temporada, target nominal, evaluación intra-temporada, salida condicional, baseline superior. Demuestra una implementación reproducible, no recomendador validado. **Mostrar:** conclusión del reporte.

### 11:15–12:30 | Demo terminal

Ejecutar desde raíz:

```bash
python riego_simple/main.py
python riego_simple/main.py --sector 2 --humedad 42 --dias 0.8
```

Mirar conteos 707/473/4/230, cromosoma `120101121`, métricas, errores por sector; en consulta: MADP40, humedad relativa2, grados, reglas R4/R5/R7/R8, Base137.99 L y GA266.37 L. Cerrar: “cantidad condicional; no inicia el riego”.

## Plan B si interrumpe a los 3 minutos

En tres minutos alcanza con: (1) alcance exacto y condicional, (2) fuente y observación 06:00, (3) fórmula de target nominal y exclusión fertirrigación, (4) dos entradas y nueve reglas, (5) mención de GA para consecuentes y prueba temporal, (6) resultado honesto: mejora Base, no mediana. No sacrifiques la aclaración de que no decide riego.

## Si pide abrir el código

1. `main.py:L45–60`: intersección y target.
2. `L62–123`: construcción de filas y entradas.
3. `L128–157`: corte y purga.
4. `L162–189`: funciones y salida solo TRAIN.
5. `L194–215`: inferencia Mamdani/centroide.
6. `L220–279`: MAE, fitness y GA.
7. `L343–459`: pipeline, métricas, resultados y consulta.

## Respuestas de transición

- “Primero explico de dónde sale el valor objetivo; después, cómo se estima.”
- “La lógica difusa no es un clasificador de clases: combina grados y produce una cantidad.”
- “El GA no sustituye el motor, solo propone sus consecuentes.”
- “La prueba posterior es limitada y por eso también muestro la referencia constante.”
