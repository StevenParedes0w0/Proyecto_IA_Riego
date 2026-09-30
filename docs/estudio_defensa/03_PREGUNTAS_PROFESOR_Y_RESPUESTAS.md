# Banco de preguntas y respuestas para defensa

Las ubicaciones corresponden a [`main.py`](../../riego_simple/main.py). “Respuesta corta” está pensada para contestar primero; luego se amplía si el profesor pregunta más.

## Básicas (25)

1. **Pregunta:** ¿Qué resuelve? **Corta:** Estima litros nominales, condicionado a observar riego posterior. **Completa:** Usa entradas a las 06:00 para estimar el target nominal de eventos estándar en 24 h. **Código:** L45–60, L343–451. **Evitar:** Afirmar que decide el riego.
2. **Pregunta:** ¿Qué datos usa? **Corta:** Sensores y eventos Arnesano 2025. **Completa:** Cinco sectores de una finca, datos procesados locales y eventos de actuadores. **Código:** L20–21, L62–123. **Evitar:** Generalizar a otros años.
3. **Pregunta:** ¿Cuáles son las entradas? **Corta:** Humedad relativa al MADP y días sin riego. **Completa:** Ambas se calculan con información disponible antes de 06:00. **Código:** L26, L62–123. **Evitar:** Agregar clima como entrada actual.
4. **Pregunta:** ¿Cuál es la salida? **Corta:** Litros nominales estimados. **Completa:** Centroide directo de conjuntos de salida definidos por TRAIN. **Código:** L179–215. **Evitar:** Llamarlos litros medidos.
5. **Pregunta:** ¿Qué es un conjunto difuso? **Corta:** Un término con grados de pertenencia graduales. **Completa:** Asocia a cada valor un grado de compatibilidad en [0,1]. **Código:** L162–177. **Evitar:** Decir “clase difusa”.
6. **Pregunta:** ¿Qué es grado de pertenencia? **Corta:** Nivel de compatibilidad con un término. **Completa:** Se calcula mediante función; no es una probabilidad. **Código:** L162–177. **Evitar:** Interpretarlo como porcentaje de ocurrencia.
7. **Pregunta:** ¿Qué significa fuzzificar? **Corta:** Convertir valores numéricos en grados. **Completa:** Se calculan tres grados por entrada y nueve activaciones. **Código:** L171–177. **Evitar:** Confundirlo con normalizar.
8. **Pregunta:** ¿Qué es defuzzificar? **Corta:** Obtener un valor numérico de salida. **Completa:** Se calcula el centroide de la salida agregada en litros. **Código:** L194–215. **Evitar:** Decir que se elige una clase.
9. **Pregunta:** ¿Cuántas reglas hay? **Corta:** Nueve. **Completa:** Tres conjuntos de humedad por tres de días. **Código:** L28–34, L294–307. **Evitar:** Contar etiquetas de salida como reglas.
10. **Pregunta:** ¿Qué significa MADP? **Corta:** Umbral de agotamiento permisible usado como referencia. **Completa:** La entrada es humedad del suelo menos el valor por sector. **Código:** L26, L62–123. **Evitar:** Confundirlo con caudal.
11. **Pregunta:** ¿Qué es el target? **Corta:** Volumen nominal reconstruido por duración y caudal. **Completa:** Suma el solapamiento de eventos estándar con la ventana futura. **Código:** L45–60. **Evitar:** Afirmar medición por contador.
12. **Pregunta:** ¿Se incluye fertirrigación? **Corta:** No. **Completa:** Solo se suman eventos de tipo `standard_irrigation`. **Código:** L45–60. **Evitar:** Mezclar categorías.
13. **Pregunta:** ¿Qué hace la base manual? **Corta:** Da una referencia de consecuentes fija. **Completa:** Se compara usando el mismo motor que GA. **Código:** L32–34, L194–215. **Evitar:** Decir que es otro algoritmo de aprendizaje.
14. **Pregunta:** ¿Qué optimiza el GA? **Corta:** Nueve consecuentes. **Completa:** Cada gen elige salida Baja, Media o Alta para una regla. **Código:** L32–39, L241–279. **Evitar:** Decir que optimiza sensores.
15. **Pregunta:** ¿Cuántos genes? **Corta:** Nueve. **Completa:** Uno por regla; cada gen es ternario. **Código:** L194–198, L241–279. **Evitar:** Llamarlo cromosoma binario.
16. **Pregunta:** ¿Qué es MAE? **Corta:** Error absoluto medio. **Completa:** Promedia magnitudes de diferencias entre litros objetivo y estimados. **Código:** L220–231. **Evitar:** Confundir error con fitness.
17. **Pregunta:** ¿Qué es RMSE? **Corta:** Raíz del error cuadrático medio. **Completa:** Penaliza relativamente más errores grandes. **Código:** L284–292. **Evitar:** Interpretarlo como máximo error.
18. **Pregunta:** ¿Qué es MedAE? **Corta:** Mediana del error absoluto. **Completa:** Resume error típico robusto a valores extremos. **Código:** L284–292. **Evitar:** Decir que es la media.
19. **Pregunta:** ¿Qué es TRAIN? **Corta:** Periodo cronológico inicial usado por GA. **Completa:** Solo sus positivos aportan al ajuste de consecuentes y cuantiles. **Código:** L128–157, L343–365. **Evitar:** Afirmar que es una muestra aleatoria.
20. **Pregunta:** ¿Qué es TEST? **Corta:** Periodo posterior reservado para evaluación. **Completa:** El GA no recibe sus objetivos durante ajuste. **Código:** L343–400. **Evitar:** Usarlo para cambiar reglas.
21. **Pregunta:** ¿Qué es purgar? **Corta:** Excluir el día de frontera. **Completa:** Evita que target de 24 h del 27 llegue al periodo de prueba. **Código:** L128–157. **Evitar:** Llamar esos casos errores.
22. **Pregunta:** ¿El sistema decide Regar/NoRegar? **Corta:** No. **Completa:** Produce litros condicionales a que haya ocurrido un riego. **Código:** L309–338, L421–450. **Evitar:** Presentarlo como controlador.
23. **Pregunta:** ¿Qué es una regla Mamdani? **Corta:** Relación SI–Y–ENTONCES entre conjuntos. **Completa:** Antecedentes activan un conjunto difuso de salida. **Código:** L194–215. **Evitar:** Decir que el GA crea reglas desde cero.
24. **Pregunta:** ¿Qué reproduce la semilla? **Corta:** La secuencia pseudoaleatoria del GA. **Completa:** Facilita reproducir la búsqueda con el mismo entorno. **Código:** L39, L244. **Evitar:** Afirmar que garantiza generalización.
25. **Pregunta:** ¿Qué archivos entrega? **Corta:** Cinco CSV de reglas, historial, predicciones y métricas. **Completa:** Se guardan en `riego_simple/resultados/`. **Código:** L397–410. **Evitar:** Confundir archivos con datos fuente.

## Intermedias (30)

26. **Pregunta:** ¿Por qué lógica difusa? **Corta:** Permite representar términos graduales y reglas legibles. **Completa:** En lugar de cortes rígidos, una observación puede activar varios conjuntos. **Código:** L162–215. **Evitar:** Decir que es automáticamente más precisa.
27. **Pregunta:** ¿Por qué tres términos por entrada? **Corta:** Es una decisión sencilla que produce nueve combinaciones. **Completa:** Baja/Media/Alta y Reciente/Intermedio/Lejano forman la matriz de reglas. **Código:** L28–34, L171–177. **Evitar:** Atribuirlo al profesor sin fuente.
28. **Pregunta:** ¿Por qué AND=min? **Corta:** Es el operador de conjunción elegido. **Completa:** La regla queda limitada por su antecedente menos compatible. **Código:** L171–177. **Evitar:** Afirmar que es el único operador posible.
29. **Pregunta:** ¿Cómo se calcula la implicación? **Corta:** Con mínimo. **Completa:** Trunca el conjunto de salida al nivel de activación. **Código:** L204–211. **Evitar:** Confundir implicación con producto.
30. **Pregunta:** ¿Cómo se agregan reglas? **Corta:** Con máximo punto a punto. **Completa:** Une las salidas truncadas de los tres términos. **Código:** L207–211. **Evitar:** Sumarlas sin límite.
31. **Pregunta:** ¿Por qué centroide? **Corta:** Da un valor continuo representativo del área agregada. **Completa:** Se calcula suma ponderada por grado dividida por área discreta. **Código:** L207–215. **Evitar:** Presentarlo como promedio de reglas activadas.
32. **Pregunta:** ¿Cómo se forma Baja/Media/Alta de humedad? **Corta:** Con rampas y un término triangular residual. **Completa:** `tres_grados` usa puntos -20,0,20. **Código:** L162–177. **Evitar:** Llamarlas campanas gaussianas.
33. **Pregunta:** ¿Qué significa humedad relativa 2? **Corta:** La lectura excede MADP por dos puntos. **Completa:** En sector 2, 42−40=2. **Código:** L26, L309–338. **Evitar:** Decir 2% de probabilidad.
34. **Pregunta:** ¿Cómo calcula días? **Corta:** Diferencia desde el fin del último evento estándar. **Completa:** Acota el valor a 30 días; sin antecedente asigna 30. **Código:** L85–102. **Evitar:** Medir desde inicio del evento.
35. **Pregunta:** ¿Por qué litros nominales? **Corta:** Se calculan con duración y caudal nominal declarado. **Completa:** No hay una medición independiente de volumen real. **Código:** L45–60. **Evitar:** Afirmar lectura de contador.
36. **Pregunta:** ¿Cómo cuenta varios eventos? **Corta:** Suma cada solapamiento por el mismo caudal del sector. **Completa:** Cada evento estándar se recorta a la ventana y luego se acumula. **Código:** L45–60. **Evitar:** Contar fertirrigación.
37. **Pregunta:** ¿Qué pasa si la válvula está abierta a las 06? **Corta:** Se omite esa observación. **Completa:** No se trata como nueva decisión independiente. **Código:** L90–92. **Evitar:** Afirmar que se predice durante un riego en curso.
38. **Pregunta:** ¿Cómo evita usar el futuro en humedad? **Corta:** Desplaza el inicio de celda diez minutos. **Completa:** Solo la última celda completada antes de la decisión puede usarse. **Código:** L75–86. **Evitar:** Usar serie interpolada con futuro.
39. **Pregunta:** ¿Por qué mantener ceros antes del split? **Corta:** Para definir el corte sobre cronología completa. **Completa:** El filtrado positivo ocurre después de TRAIN/TEST. **Código:** L128–157, L348–352. **Evitar:** Separar solo eventos positivos.
40. **Pregunta:** ¿Por qué un split temporal? **Corta:** Simula evaluar un periodo posterior. **Completa:** Evita mezclar cronología futura con pasada. **Código:** L128–157. **Evitar:** Afirmar validación externa.
41. **Pregunta:** ¿Por qué purgar un día? **Corta:** La etiqueta mira 24 horas adelante. **Completa:** Se omite 27 junio para que target no cruce corte 28 junio. **Código:** L150–157. **Evitar:** Purgar por resultados malos.
42. **Pregunta:** ¿Qué aprende el GA de TRAIN? **Corta:** Qué consecuente asignar a cada regla. **Completa:** Compara predicciones Mamdani contra litros nominales mediante MAE. **Código:** L224–279. **Evitar:** Decir que cambia las pertenencias.
43. **Pregunta:** ¿Por qué 19 683? **Corta:** Tres opciones elevadas a nueve genes. **Completa:** Cada una de las nueve reglas puede concluir tres términos. **Código:** L32–34. **Evitar:** Usar 2^9.
44. **Pregunta:** ¿Cómo funciona ruleta? **Corta:** Selecciona proporcional al fitness normalizado. **Completa:** Individuos con mejor fitness tienen mayor probabilidad de ser padre. **Código:** L264–265. **Evitar:** Decir que siempre escoge el mejor.
45. **Pregunta:** ¿Cómo funciona cruce? **Corta:** Corta entre genes y combina prefijo/sufijo. **Completa:** El punto está entre 1 y 8 para mantener nueve genes. **Código:** L266–267. **Evitar:** Cambiar orden de reglas.
46. **Pregunta:** ¿Cómo muta? **Corta:** Probabilidad .08 por gen. **Completa:** Un gen mutado se reemplaza por uno de los otros dos términos. **Código:** L233–239. **Evitar:** Suponer cambio binario 0↔1.
47. **Pregunta:** ¿Qué hace elitismo? **Corta:** Copia el mejor individuo a la siguiente población. **Completa:** Lo conserva sin mutación para no perder su aptitud histórica. **Código:** L262–263. **Evitar:** Decir que toda población se conserva.
48. **Pregunta:** ¿Cuántas evaluaciones hay? **Corta:** Generaciones 0 a 50. **Completa:** El bucle calcula 51 estados; crea nuevas poblaciones hasta 50. **Código:** L251–260, L261–277. **Evitar:** Decir 50 filas de historial.
49. **Pregunta:** ¿Por qué el fitness es inverso al MAE? **Corta:** Para que error menor dé puntuación mayor. **Completa:** `1/(1+MAE)` da pesos positivos para ruleta. **Código:** L224–231. **Evitar:** Maximizar directamente MAE.
50. **Pregunta:** ¿Por qué añadir 1? **Corta:** Evita división por cero y mantiene denominador positivo. **Completa:** Con error cero el fitness sería 1. **Código:** L229–231. **Evitar:** Interpretarlo como normalización probabilística.
51. **Pregunta:** ¿Qué significa Q25 de salida? **Corta:** Cuartil inferior de litros positivos TRAIN. **Completa:** Ancla conjuntos difusos de salida sin utilizar TEST. **Código:** L179–189. **Evitar:** Tratarlo como límite agronómico.
52. **Pregunta:** ¿Qué es el universo 0–746.90? **Corta:** Malla de posibles salidas evaluadas. **Completa:** 501 puntos hasta máximo positivo TRAIN. **Código:** L179–189. **Evitar:** Decir que es rango garantizado en TEST.
53. **Pregunta:** ¿Qué aporta comparar mediana? **Corta:** Baseline simple de predicción constante. **Completa:** Permite saber si reglas complejas mejoran una referencia básica. **Código:** L372–378. **Evitar:** Omitir porque gana.
54. **Pregunta:** ¿Cómo interpretar MAE? **Corta:** En TEST, GA se equivoca en promedio 241.44 L absolutos. **Completa:** Comparte unidad con el target y refleja gran error. **Código:** `resultados/metricas.csv`. **Evitar:** Presentarlo como error porcentual.
55. **Pregunta:** ¿Cómo interpretar RMSE mayor que MAE? **Corta:** Hay errores grandes que elevan los cuadrados. **Completa:** La diferencia sugiere dispersión de errores, sin identificar causa. **Código:** L284–292. **Evitar:** Inferir causalidad.

## Difíciles (20)

56. **Pregunta:** ¿Por qué GA no supera la mediana? **Corta:** Las reglas y entradas no capturan bien escala y distribución TEST. **Completa:** TEST desplaza volumen y composición por sector; los resultados solo sugieren limitación, no una causa única. **Código:** L343–400; reporte §8–9. **Evitar:** Ocultar baseline.
57. **Pregunta:** ¿Fracasó el proyecto? **Corta:** No como implementación; sí muestra rendimiento limitado. **Completa:** Se construyó y probó el método, pero no se demuestra superioridad predictiva. **Código:** resultados CSV. **Evitar:** Confundir objetivo académico con éxito predictivo.
58. **Pregunta:** ¿Qué es leakage aquí? **Corta:** Información de prueba influyendo en decisiones de ajuste. **Completa:** Se protege haciendo split primero y derivando cuantiles/GA solo de TRAIN. **Código:** L343–365. **Evitar:** Afirmar ausencia de toda limitación de fuente.
59. **Pregunta:** ¿El TEST participa al crear conjuntos? **Corta:** No. **Completa:** `preparar_salida` recibe `reales_train` únicamente. **Código:** L179–189, L355–365. **Evitar:** Usar estadísticas globales.
60. **Pregunta:** ¿El cromosoma final se eligió mirando TEST? **Corta:** No, por fitness TRAIN. **Completa:** TEST se infiere una vez para métricas luego de GA. **Código:** L343–378. **Evitar:** Ajustarlo después de ver tabla.
61. **Pregunta:** ¿La purga elimina fuga de sensores? **Corta:** Protege el horizonte de etiqueta en la frontera. **Completa:** No resuelve toda incertidumbre o circularidad de la fuente. **Código:** L150–157. **Evitar:** Prometer ausencia total de leakage.
62. **Pregunta:** ¿Por qué medir solo positivos? **Corta:** El objetivo definido es cantidad condicionada a evento. **Completa:** Los ceros sirven para cronología, pero cantidad positiva es el problema modelado. **Código:** L348–354. **Evitar:** Afirmar que predice ocurrencia.
63. **Pregunta:** ¿Cómo sería un sistema operacional? **Corta:** Requeriría un componente externo que determine que habrá riego. **Completa:** Este modelo estima cantidad solo bajo esa condición; no acciona válvula. **Código:** L421–450. **Evitar:** Llamarlo controlador terminado.
64. **Pregunta:** ¿Puede interpretarse volumen como recomendación? **Corta:** No. **Completa:** Es estimación retrospectiva asociada a eventos y caudal nominal, sin validación agronómica. **Código:** L45–60. **Evitar:** Recomendar dosis óptima.
65. **Pregunta:** ¿Qué sesgo introduce humedad filtrando eventos fuente? **Corta:** Puede haber dependencia entre predictor y etiqueta. **Completa:** Algunos eventos inferidos por dataset usaron humedad como plausibilidad; se declara posible circularidad parcial. **Código:** reporte §2. **Evitar:** Afirmar magnitud cuantificada.
66. **Pregunta:** ¿Por qué sector 4 domina TEST? **Corta:** 40 de 56 casos positivos pertenecen al sector 4. **Completa:** Es composición observada, no prueba que sector cause el error. **Código:** `metricas_por_sector.csv`. **Evitar:** Atribuir causalidad.
67. **Pregunta:** ¿Qué implica cero casos en sector 3? **Corta:** No se puede calcular error condicional TEST para ese sector. **Completa:** La tabla deja métricas vacías, no cero. **Código:** L383–395. **Evitar:** Declarar rendimiento perfecto.
68. **Pregunta:** ¿Por qué sector 5 es distinto? **Corta:** Usa caudal nominal .4 L/min y MADP 70. **Completa:** El caudal modifica el target; MADP afecta una entrada. **Código:** L26–27. **Evitar:** Confundir MADP con el umbral 50.
69. **Pregunta:** ¿Podrían añadir sector como entrada? **Corta:** Sí, sería una extensión. **Completa:** Requeriría rediseñar representación, reglas y evaluación; no forma parte de esta versión. **Código:** L171–177. **Evitar:** Afirmar que ya se usa.
70. **Pregunta:** ¿Por qué no añadir más variables? **Corta:** Se priorizó una versión pequeña y defendible. **Completa:** Más variables pueden mejorar representación, pero requieren disponibilidad sin fuga y validación adicional. **Código:** L171–177. **Evitar:** Decir que dos entradas bastan universalmente.
71. **Pregunta:** ¿Es validación entre temporadas? **Corta:** No. **Completa:** Es holdout posterior dentro de 2025. **Código:** `FECHA_CORTE` L25 y reporte. **Evitar:** Afirmar validación interanual.
72. **Pregunta:** ¿El GA garantiza óptimo global? **Corta:** No. **Completa:** Es búsqueda estocástica con población/generaciones fijadas; no demuestra óptimo global. **Código:** L241–279. **Evitar:** Afirmar certeza matemática.
73. **Pregunta:** ¿Por qué comparar con base manual? **Corta:** Mide si optimizar consecuentes mejora la tabla fija. **Completa:** Ambas usan misma estructura Mamdani; cambia asignación de consecuentes. **Código:** L32–34, L367–370. **Evitar:** Atribuir mejora al motor cambiado.
74. **Pregunta:** ¿El fitness es precisión? **Corta:** No, es transformación del MAE TRAIN. **Completa:** No está entre 0–1 como probabilidad ni es exactitud porcentual. **Código:** L224–231. **Evitar:** Llamarlo accuracy.
75. **Pregunta:** ¿Qué limitación tienen referencias constantes? **Corta:** Ignoran diferencias por sector y entradas. **Completa:** Son baselines sencillos; aun así superarles sería necesario para justificar complejidad predictiva. **Código:** L372–378. **Evitar:** Descartarlos como injustos sin análisis.

## Preguntas trampa (5)

76. **Pregunta:** “Entonces 0.7 significa 70% de probabilidad, ¿verdad?” **Corta:** No, es grado de pertenencia. **Completa:** Indica compatibilidad con un conjunto, no frecuencia ni probabilidad calibrada. **Código:** L162–177. **Evitar:** Decir sí.
77. **Pregunta:** “¿Cuáles son las clases difusas?” **Corta:** Hablamos de conjuntos o términos lingüísticos. **Completa:** Para humedad: Baja, Media, Alta; para días: Reciente, Intermedio, Lejano. **Código:** L28–30. **Evitar:** “clase difusa”.
78. **Pregunta:** “¿Cuánto entrenaron Mamdani?” **Corta:** Mamdani no se ajusta aquí; el GA optimiza consecuentes. **Completa:** La estructura, conjuntos y operadores se definen; las nueve conclusiones son buscadas con TRAIN. **Código:** L179–279. **Evitar:** “entrenamos Mamdani”.
79. **Pregunta:** “¿Mamdani predice si riego o no riego?” **Corta:** No, devuelve litros condicionales. **Completa:** El modelo de cantidad se evalúa solo si el target futuro es positivo. **Código:** L343–378. **Evitar:** Afirmar clasificación binaria.
80. **Pregunta:** “¿Estos litros son mediciones reales?” **Corta:** No, son volumen nominal reconstruido. **Completa:** Duración solapada por caudal nominal publicado. **Código:** L45–60. **Evitar:** Llamarlos litros reales medidos.

## Frases que protegen la defensa

- “El alcance es condicional y retrospectivo: estimamos cantidades nominales observadas, no decidimos la necesidad de riego.”
- “La partición evalúa un periodo posterior de la misma temporada y no demuestra generalización externa.”
- “El GA mejora la base manual, aunque la mediana TRAIN obtiene menor error; mostramos ambas cosas.”
- “El grado de pertenencia no es probabilidad.”
- “El target se reconstruye con duración y caudal nominal, no con un contador.”
