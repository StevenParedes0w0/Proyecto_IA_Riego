# Proyecto del parcial: estimación condicional de volumen nominal de riego

La entrega sencilla y ejecutable está en [riego_simple](riego_simple/README.md). El programa principal es `riego_simple/main.py`; no necesita ejecutar el pipeline histórico ni los experimentos del proyecto anterior.

El informe académico de esta versión se encuentra en [Informe-Riego-Simple](Informe-Riego-Simple/Informe_Final_Sistema_Inteligente_Riego.pdf). Utiliza exclusivamente Arnesano 2025 con un holdout cronológico dentro de la misma temporada.

El paquete técnico compacto actualizado es [riego_simple_volumen_nominal_2026-09-29.zip](riego_simple_volumen_nominal_2026-09-29.zip).

```bash
python -m pip install -r riego_simple/requirements.txt
python riego_simple/main.py
python -m pytest -q
```

El algoritmo genético busca los consecuentes Baja/Media/Alta de nueve reglas difusas. Con información disponible a las 06:00, Mamdani defuzzifica una cantidad continua en litros, **condicionada a que se observe un riego estándar en las siguientes 24 horas**. El volumen objetivo se reconstruye con duración del evento y caudal nominal; no es una medición directa ni una decisión sobre iniciar el riego. La salida permite consultar casos manuales y guarda reglas, historial, predicciones y métricas.

Se retiraron las carpetas del pipeline anterior. Se conserva `datasets/arnesano_2025/` como fuente de datos; dentro de `riego_simple/` están el programa, el CSV preparado, las pruebas y sus resultados. Para estudiar o entregar este parcial, siga solamente `riego_simple/`, el informe y `docs/estudio_defensa/`.
