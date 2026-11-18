# ADR 0002 · 3FN en silver y esquema estrella en gold

- **Estado:** aceptado
- **Fecha:** 2026-11-17

## Contexto
Silver debe garantizar integridad; gold debe ser fácil y rápido de consumir para Power BI, la API y la app.

## Decisión
Silver normalizado (catálogos `countries`, `indicators`, `products_hs`, `data_sources` + hechos limpios con PK/FK/CHECK). Gold en estrella Kimball: `dim_date`, `dim_country`, `dim_product`, `dim_indicator` y hechos `fact_trade`, `fact_indicator`, `fact_oil_price`, más vistas de KPIs.

## Alternativas consideradas
Todo en 3FN (consultas BI complejas); todo desnormalizado (duplicación y errores de integridad); Data Vault (excesivo para 4 fuentes).

## Consecuencias
Las reglas de integridad viven en silver y los consumidores solo ven gold. Las vistas de KPIs concentran la lógica de negocio en SQL, una sola vez.
