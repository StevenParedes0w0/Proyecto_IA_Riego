# Chuleta de repaso rápido

## Objetivo

Estimar litros **nominales** asociados a riego estándar en `[06:00,06:00+24h)`, condicionado a que haya ocurrido riego. No decide Regar/NoRegar ni recomienda dosis agronómica.

## Datos y variables

- Arnesano 2025, Mendeley V1, una finca, cinco sectores.
- Una fila por sector y día; información disponible a las 06:00.
- Entradas: humedad relativa `humedad_suelo−MADP_sector`; días desde último riego estándar terminado (máx.30).
- MADP: 40,40,60,80,70. Caudales nominales: 1.1 L/min sectores1–4; 0.4 en sector5.
- Solo `standard_irrigation`; fertirrigación excluida. Target = minutos solapados×caudal sumado.
- Volumen reconstruido, no lectura real de contador.

## Lógica difusa

`μB=clip((c−x)/(c−b),0,1)`; `μA=clip((x−c)/(a−c),0,1)`; `μM=1−μB−μA`.

- Humedad puntos `−20,0,20`; días `.5,1.5,4.5`.
- 3×3 = 9 reglas.
- AND=min; implicación=min; agregación=max; centroide `Σ(yμ)/Σμ`.
- Grado de pertenencia no es probabilidad; conjunto difuso no es clase.
- Salida en 501 puntos 0–746.90 L; TRAIN Q25=119.30, Q50=233.75, Q75=363.825.

## Reglas y GA

- Genes: 9 valores de `{0,1,2}`; 0=Baja, 1=Media, 2=Alta; `3^9=19 683`.
- Base `122012001`; GA final `120101121`.
- GA cambia solo los consecuentes, no la estructura Mamdani.
- Población30, 50 generaciones, semilla42, ruleta, cruce de un punto, mutación .08 por gen, elitismo.
- `MAE=promedio(|real−estimado|)`; `fitness=1/(1+MAE_TRAIN)`.
- Mejor TRAIN MAE=145.112091 L.

## Evaluación y resultados

- Corte 28-06-2025: 707 filas = 473 TRAIN + 4 purga + 230 TEST.
- Positivos tras split: 142 TRAIN, 56 TEST. Holdout posterior de la misma temporada.
- TEST MAE: Base277.48; GA241.44; mediana TRAIN188.98; media TRAIN206.42 L.
- GA mejora Base ~13%, pero mediana es mejor. RMSE pondera errores grandes; MedAE es mediana del error absoluto.
- Mediana de target positivo TRAIN233.75, TEST31.90 L.
- Sector4: 40/56 casos; sector3: cero; sector5 caudal diferente.
- No es validación entre años ni fincas; no se demuestra generalización.

## Cinco frases que no debo decir y reemplazo correcto

| No decir | Decir |
|---|---|
| “Es 70% de probabilidad” | “Es grado de pertenencia 0.7” |
| “Son clases difusas” | “Son conjuntos/términos lingüísticos” |
| “Entrenamos Mamdani” | “El GA optimiza consecuentes de reglas Mamdani” |
| “Predice si regar” | “Estima volumen condicional si se observa riego” |
| “Litros reales/dosis óptima” | “Volumen nominal reconstruido, no recomendación” |

## 15 preguntas rápidas

1. **¿Qué estima?** Litros nominales condicionales a evento.
2. **¿A qué hora?** Observación diaria a las 06:00.
3. **¿Qué ventana?** Las 24 horas siguientes, con inicio incluido y fin exclusivo.
4. **¿Qué es MADP?** Referencia sectorial restada a humedad.
5. **¿Cuántas entradas?** Dos: humedad relativa y días sin riego.
6. **¿Cuántas reglas?** Nueve.
7. **¿Qué es un gen?** Consecuente de una regla.
8. **¿Qué hace Mamdani?** Fuzzifica, infiere, agrega y defuzzifica litros.
9. **¿Qué ajusta el GA?** Solo nueve consecuentes.
10. **¿Qué fitness usa?** `1/(1+MAE_TRAIN)`.
11. **¿Qué es purga?** Cuatro filas del día previo al corte por horizonte 24h.
12. **¿Cuántos positivos?** 142 TRAIN y 56 TEST.
13. **¿GA vence Base?** Sí, en MAE TEST: 241.44 frente a 277.48.
14. **¿GA vence mediana?** No; mediana logra 188.98.
15. **¿Qué demuestra?** Implementación reproducible y límites claros, no recomendación agronómica validada.
