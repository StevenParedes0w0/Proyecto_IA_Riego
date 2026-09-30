# Ejercicios manuales resueltos

Ejercicios conceptuales conectados al código en [`main.py`](../../riego_simple/main.py). Los ejemplos sintéticos están marcados; no son filas adicionales del dataset.

## 1. Humedad relativa al MADP

**Enunciado:** sector 3 registra humedad 55. **Desarrollo:** MADP=60; `55−60=−5`. **Resultado:** humedad relativa −5. **Interpretación:** lectura cinco puntos bajo referencia. **Código:** L26, L309–338.

## 2. Pertenencias en cuatro posiciones

**Enunciado:** `tres_grados(x,-20,0,20)` para x=−30,0,10,30. **Desarrollo:**

|x|Baja|Media|Alta|
|--:|--:|--:|--:|
|−30|1|0|0|
|0|0|1|0|
|10|0|0.5|0.5|
|30|0|0|1|

**Resultado:** en 10 hay pertenencia simultánea a Media y Alta. **Interpretación:** grados no probabilidades. **Código:** L162–169.

## 3. Activación de regla

**Enunciado:** antecedente humedad Media=.9 y días Reciente=.7. **Desarrollo:** AND=min(.9,.7)=.7. **Resultado:** R4 se activa a .7. **Interpretación:** limita el antecedente menos compatible. **Código:** L171–177.

## 4. Varias reglas activas

**Enunciado:** consulta sector 2, humedad42, días.8. **Desarrollo:** Hrel=2 → (0,.9,.1); días → (.7,.3,0). Aplicar min a cada pareja. **Resultado R1–R9:** `[0,0,0,.7,.3,0,.1,.1,0]`. **Código:** L171–177, L309–338.

## 5. Truncamiento

**Enunciado:** regla activa .7 concluye conjunto Media con pertenencias `[0,.4,1,.6,0]`. **Desarrollo:** min elemento a elemento. **Resultado:** `[0,.4,.7,.6,0]`. **Interpretación:** se recorta el consecuente al nivel de activación. **Código:** L204–211.

## 6. Agregación

**Enunciado:** dos reglas recortadas `[0,.4,.7,.6,0]` y `[.2,.5,.3,0,0]`. **Desarrollo:** máximo punto a punto. **Resultado:** `[.2,.5,.7,.6,0]`. **Código:** L207–211.

## 7. Centroide discreto pequeño

**Enunciado:** malla y grados `y=[0,10,20]`, `μ=[0,1,0]`. **Desarrollo:** `(0×0+10×1+20×0)/(0+1+0)=10`. **Resultado:** centroide 10 unidades. **Interpretación:** salida nítida ponderada por pertenencia. **Código:** L212–215.

## 8. Volumen nominal, sector 5

**Enunciado:** evento estándar dura 25 minutos en sector5. **Desarrollo:** `25×0.4=10`. **Resultado:** 10 L nominales. **Interpretación:** no es medición por contador. **Código:** L26–27, L45–60.

## 9. Solapamiento de ventana

**Enunciado:** ventana 06:00–06:00 siguiente; evento 05:50–06:20. **Desarrollo:** intersección 06:00–06:20 =20 min. Sector2: `20×1.1=22`. **Resultado:** 22 L nominales en esa ventana. **Código:** L45–60.

## 10. MAE

**Enunciado:** reales `[10,20,40]`, estimados `[12,15,50]`. **Desarrollo:** errores absolutos `[2,5,10]`; suma17/3. **Resultado:** MAE=5.667. **Código:** L220–222.

## 11. RMSE

**Enunciado:** mismos errores firmados `[-2,5,-10]`. **Desarrollo:** raíz de `(4+25+100)/3`. **Resultado:** `√43=6.557`. **Interpretación:** eleva el impacto de error grande. **Código:** L284–292.

## 12. MedAE

**Enunciado:** errores absolutos `[2,5,10]`. **Desarrollo:** mediana ordenada. **Resultado:** 5. **Código:** L284–292.

## 13. Fitness

**Enunciado:** cromosoma A MAE=9; B MAE=4. **Desarrollo:** A `1/10=.1`; B `1/5=.2`. **Resultado:** B tiene mayor fitness. **Interpretación:** ruleta favorece B pero puede elegir A. **Código:** L224–231.

## 14. Decodificar cromosoma GA

**Enunciado:** decodificar `120101121`. **Desarrollo/resultado:**

|Gen|Regla|Consecuente|
|--:|---|---|
|1|R1|Media|
|2|R2|Alta|
|3|R3|Baja|
|4|R4|Media|
|5|R5|Baja|
|6|R6|Media|
|7|R7|Media|
|8|R8|Alta|
|9|R9|Media|

**Código:** L32–34, L294–307.

## 15. Selección por ruleta

**Enunciado:** fitness `[1,2,1]`. **Desarrollo:** suma4; pesos `[.25,.5,.25]`. Un número aleatorio 0.6 cae en individuo 2 con acumulados `.25,.75,1`. **Resultado:** se selecciona el segundo. **Interpretación:** selección probabilística proporcional. **Código:** L264–265.

## 16. Cruce de un punto

**Enunciado sintético:** padres `012|210` y `222|001`, corte después del tercer gen. **Desarrollo:** prefijo1+sufijo2; prefijo2+sufijo1. **Resultado:** hijos `012001`, `222210`. **Código:** L266–267. En proyecto real son nueve genes.

## 17. Mutación ternaria

**Enunciado:** muta el gen con valor1. **Desarrollo:** suma aleatoria 1 o 2 módulo3: 1→2 o 0. **Resultado:** nunca queda en1. **Código:** L233–239.

## 18. Una generación simplificada

**Enunciado:** población de tres cromosomas obtiene MAE `[9,4,7]`. **Desarrollo:** fitness `[.1,.2,.125]`; el segundo tiene mayor peso; se seleccionan padres por ruleta, se cruza un punto, puede mutar cada gen con probabilidad .08 y el mejor se copia sin cambio. **Resultado:** siguiente población mantiene al individuo de MAE4 como élite. **Interpretación:** ejemplo didáctico, no reproducción exacta de la corrida aleatoria. **Código:** L224–279.

## 19. Cromosoma base y espacio

**Enunciado:** ¿cuántas combinaciones? **Desarrollo:** nueve posiciones, tres valores cada una: `3^9=19 683`. **Resultado:** espacio discreto ternario. **Código:** L32–34, L241–279.

## 20. Métricas reales

**Enunciado:** ordenar MAE TEST. **Desarrollo:** GA241.44, Base277.48, mediana188.98, media206.42. **Resultado:** menor es mediana TRAIN; GA mejora base por36.03, pero pierde por52.46 frente a mediana. **Interpretación:** declarar ambos hallazgos. **Datos:** `resultados/metricas.csv`.

## 21. Corte cronológico

**Enunciado:** total707, TRAIN473, purga4, TEST230. Verificación `473+4+230=707`. Positivos:142+56=198. **Resultado:** split coherente; ceros siguen presentes antes del filtro. **Código:** L128–157, L343–354.

## 22. Proporción sectorial

**Enunciado:** sector4 contiene40 de56 positivos TEST. **Desarrollo:** `40/56×100=71.428…%`. **Resultado:** 71.43%. **Interpretación:** composición desigual; no concluye causalidad. **Datos:** `resultados/metricas_por_sector.csv`.

## 23. Centroide de consulta

**Enunciado:** explique resultado GA para sector2, humedad42, días.8. **Desarrollo:** Hrel2; humedad `(0,.9,.1)`, días `(.7,.3,0)`; activaciones `[0,0,0,.7,.3,0,.1,.1,0]`. GA asigna R4 Media(.7), R5 Baja(.3), R7 Media(.1), R8 Alta(.1); las salidas por término agregan máximos. Se recortan conjuntos Baja/Media/Alta, se agregan sobre 501 puntos y se toma centroide. **Resultado verificado:** 266.37 L GA; Base137.99 L. **Código:** L194–215, L309–338; comando CLI en guion.

## 24. Semilla y reproducibilidad

**Enunciado:** ¿por qué mismo cromosoma? **Desarrollo:** generador `default_rng(42)` fija secuencia pseudoaleatoria para misma versión/entorno. **Resultado:** se reproduce `120101121` en ejecución verificada. **Código:** L39, L244. **Interpretación:** no garantiza mismo resultado si cambia implementación o datos.

## 25. ¿Qué significa mejora de 13%?

**Enunciado:** comparar MAE Base277.478 y GA241.445. **Desarrollo:** `(277.478−241.445)/277.478×100≈12.99%`. **Resultado:** cerca de13% de reducción frente a Base. No implica vencer baseline: mediana queda en188.984. **Datos:** `resultados/metricas.csv`.
