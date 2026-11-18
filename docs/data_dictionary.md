# Diccionario de datos

## bronze (crudo, solo-append)
| Tabla | Grano | Columnas clave |
|---|---|---|
| `wb_indicator_raw` | registro de la API WDI | indicator_code, country_iso2, country_iso3, year (texto), value, obs_status |
| `comtrade_raw` | registro de la API Comtrade | ref_year, reporter_code (M49), partner_code, partner2_code, mot_code, customs_code, cmd_code, primary_value, query_name |
| `oil_price_raw` | serie × mes | period (AAAA-MM), series (brent/wti), value_raw (texto) |
| `bce_trade_raw` | año | oil_exports_fob_usd, non_oil_exports_fob_usd, source_file |

Todas incluyen `source_name`, `extracted_at` (UTC) y `batch_id`.

## silver
| Tabla | Clave | Descripción |
|---|---|---|
| `data_sources` | source_name | Proveedor, URL y método de acceso |
| `countries` | iso3 | ECU, PER, COL, CHL y el agregado LCN (`is_aggregate = 1`) |
| `country_codes_map` | iso3 | ISO3 ↔ ISO2 (Banco Mundial) ↔ M49 (Comtrade) ↔ nombre BCE |
| `indicators` | indicator_code | Nombre ES/EN y unidad (USD o %) |
| `indicator_values` | país, indicador, año | Formato largo. `is_interpolated = 1` solo en huecos interiores de 1 año |
| `products_hs` | hs_code | `TOTAL` (nivel 0), capítulos HS2, partidas HS4 clave. `product_group` agrupa para la canasta |
| `trade_flows` | reportante, socio, año, hs_code | Exportaciones FOB en USD corrientes. `partner_code = 0` = Mundo; `is_special_partner` = áreas no país |
| `commodity_prices` | serie, mes | Brent y WTI en USD/bbl |
| `bce_trade_balance` | año | Validación opcional |
| `economic_events` | event_code | Hitos 2008–09, 2014–16, 2020 |
| `etl_runs` | run_id | Una fila por ejecución: modo, estado, duración, filas por capa |
| `etl_watermarks` | fuente, alcance | Último período cargado |
| `cleaning_log` | log_id | Regla aplicada y filas afectadas por lote |

## gold
| Objeto | Descripción |
|---|---|
| `dim_date` | Mensual 2000–2040; los hechos anuales usan el 1 de enero (`date_key = AAAA0101`) |
| `dim_country`, `dim_product`, `dim_indicator` | Dimensiones con llave sustituta |
| `fact_trade` | Exportaciones por país × producto × socio × año |
| `fact_indicator` | Indicadores macro por país × indicador × año |
| `fact_oil_price` | Precio mensual por serie |
| `vw_export_basket` | Canasta por grupo de producto (suma = total; `other` = total − clave) con participación y ranking |
| `vw_oil_dependency` | Exportaciones totales, petroleras, no petroleras y peso del petróleo |
| `vw_diversification` | HHI por producto y destino, número equivalente |
| `vw_product_cagr` | CAGR por grupo entre primer y último año |
| `vw_oil_price_annual` | Promedio anual y meses disponibles |
| `vw_oil_sensitivity` | Elasticidad log-log y R² vs Brent |
| `vw_regional_compare` | Indicadores macro con nombres ES/EN |
| `vw_exports_index` | Índices 2000 = 100 |
| `vw_source_reconciliation` | Peso petrolero: Comtrade vs Banco Mundial vs BCE |
| `vw_pipeline_runs`, `vw_layer_counts`, `vw_cleaning_rules`, `vw_economic_events` | Operación y contexto |

## Códigos de fuente
| Fuente | Códigos |
|---|---|
| Banco Mundial WDI | NY.GDP.MKTP.CD, NY.GDP.MKTP.KD.ZG, NY.GDP.PCAP.CD, FP.CPI.TOTL.ZG, NE.EXP.GNFS.ZS, BX.TRF.PWKR.CD.DT, BX.KLT.DINV.CD.WD, SL.UEM.TOTL.ZS, TX.VAL.FUEL.ZS.UN |
| UN Comtrade | Reportantes 218 (ECU), 604 (PER), 170 (COL), 152 (CHL); flujo X; HS: TOTAL, AG2, 0306, 0803, 1801, 0603, 1604 (26 y 27 vienen en AG2) |
| Pink Sheet / FRED | CRUDE_BRENT, CRUDE_WTI / DCOILBRENTEU, DCOILWTICO |
