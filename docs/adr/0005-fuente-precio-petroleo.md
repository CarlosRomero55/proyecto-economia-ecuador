# ADR 0005 · Fuente del precio del petróleo

- **Estado:** aceptado
- **Fecha:** 2026-11-17

## Contexto
Se necesita Brent (referencia del crudo ecuatoriano) y WTI mensual desde 2000, con una fuente pública y estable.

## Decisión
Fuente principal: **Banco Mundial — Commodity Price Data (Pink Sheet)**, archivo `CMO-Historical-Data-Monthly.xlsx`, hoja *Monthly Prices*, series `CRUDE_BRENT` y `CRUDE_WTI`. Respaldo automático: **FRED** (`DCOILBRENTEU`, `DCOILWTICO`, promedio mensual), si falla la descarga del Excel. Si existen ambos para un mes, gana el Pink Sheet (regla OIL03). La URL del Excel cambia de carpeta cada año: es configurable con `PINK_SHEET_URL` en `.env`.

## Alternativas consideradas
Solo FRED (requiere llave); EIA (API con llave y otra estructura); precio del crudo Oriente/Napo (no hay serie pública estable y larga).

## Consecuencias
Misma institución que los indicadores macro (coherencia). Limitación: el crudo ecuatoriano se vende con descuento respecto al Brent; la elasticidad mide la asociación con el marcador internacional.
