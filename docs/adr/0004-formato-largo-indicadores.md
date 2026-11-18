# ADR 0004 · Formato largo para indicadores

- **Estado:** aceptado
- **Fecha:** 2026-11-17

## Contexto
Hay 9 indicadores del Banco Mundial y es probable agregar más.

## Decisión
`silver.indicator_values(country_iso3, indicator_code, year, value)` en formato largo, con el catálogo `silver.indicators` (nombre ES/EN, unidad).

## Alternativas consideradas
Formato ancho (una columna por indicador): cada indicador nuevo exige un ALTER TABLE y muchas columnas nulas.

## Consecuencias
Agregar un indicador es agregar una fila al catálogo y el código en `config.py`; Power BI y la app filtran por `indicator_code`. Para análisis en ancho se pivotea en la consulta.
