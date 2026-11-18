# ADR 0009 · BCE como validación manual

- **Estado:** aceptado
- **Fecha:** 2026-11-17

## Contexto
El Banco Central del Ecuador publica la balanza comercial petrolera/no petrolera en boletines y Excel cuyas URL y estructura cambian; no hay API estable.

## Decisión
No se automatiza la descarga. `src/extract_bce.py` lee `data/raw/bce/bce_trade_balance.csv` si Carlos lo guarda a mano (columnas documentadas). La vista `gold.vw_source_reconciliation` compara la participación petrolera de Comtrade, Banco Mundial (TX.VAL.FUEL.ZS.UN) y BCE. Sin el archivo, el pipeline sigue y el reporte de calidad lo indica.

## Alternativas consideradas
Web scraping del sitio del BCE (frágil: se rompe con cada rediseño).

## Consecuencias
La validación cruzada principal (Comtrade vs Banco Mundial) es automática; la del BCE es opcional y documentada.
