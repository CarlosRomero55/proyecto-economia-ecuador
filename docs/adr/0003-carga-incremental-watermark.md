# ADR 0003 · Carga incremental con watermark

- **Estado:** aceptado
- **Fecha:** 2026-11-17

## Contexto
Comtrade limita la cuota diaria (~500 llamadas en el plan gratuito) y el Banco Mundial revisa cifras recientes. Recargar todo cada vez es lento y gasta cuota.

## Decisión
`silver.etl_watermarks` guarda el último período cargado por fuente y alcance (p. ej. `un_comtrade`/`ECU` = 2024). En modo `--incremental`: Banco Mundial desde watermark − 2 años; Comtrade desde watermark − 1 por reportante; precios del crudo completos (son pocos datos). Silver y gold usan MERGE, así que reprocesar años solapados no duplica filas.

## Alternativas consideradas
Recarga total siempre (simple pero desperdicia cuota); CDC (las fuentes no lo ofrecen); solo años nuevos (perdería revisiones).

## Consecuencias
Ejecuciones diarias baratas y que captan revisiones. Las respuestas de Comtrade se guardan en `data/raw/comtrade`, así que si se agota la cuota a mitad de camino, la siguiente ejecución continúa sin repetir llamadas.
