# ADR 0006 · FastAPI como capa de servicio

- **Estado:** aceptado
- **Fecha:** 2026-11-17

## Contexto
Otros sistemas (una web, un bot, un Excel con Power Query) deberían poder consumir los KPIs sin acceso directo a la base.

## Decisión
API REST en `api/main.py` con FastAPI: `/indicators`, `/trade/basket`, `/diversification`, `/compare`, `/oil-sensitivity`, `/pipeline/last-run`. Lee solo vistas gold. Backend conmutable (`API_BACKEND=sql|parquet`) para pruebas sin SQL Server.

## Alternativas consideradas
Exponer la base (inseguro, acopla consumidores al modelo); Flask (más código para validación y documentación); Data API Builder (menos flexible para lógica).

## Consecuencias
Documentación OpenAPI automática en `/docs`, validación de parámetros y pruebas con `TestClient`.
