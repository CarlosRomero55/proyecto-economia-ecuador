# Modelo de Power BI — EcuadorMonitor (gold)

Modelo estrella sobre `EcuadorMonitor.gold`. Se entrega como especificación lista para copiar (en lugar de un
`.pbip`/TMDL generado a ciegas, que podría no abrir): ver ADR 0007. Guarda el archivo como **Power BI Project
(.pbip)** desde Power BI Desktop (*Archivo → Guardar como → .pbip*) para que el modelo quede versionado en Git.

## 1. Conexión

*Inicio → Obtener datos → SQL Server*

| Campo | Valor |
|---|---|
| Servidor | `localhost` (o `localhost\SQLEXPRESS`) |
| Base de datos | `EcuadorMonitor` |
| Modo | **Import** (los datos son anuales/mensuales y pequeños) |
| Autenticación | Windows (usuario actual) |

Selecciona solo objetos del esquema **gold**:

| Tabla / vista | Tipo en el modelo | Notas |
|---|---|---|
| `gold.dim_date` | Dimensión | Marcar como **tabla de fechas** (columna `date`) |
| `gold.dim_country` | Dimensión | |
| `gold.dim_product` | Dimensión | Ordenar `name_es` por `hs_code` |
| `gold.dim_indicator` | Dimensión | |
| `gold.fact_trade` | Hecho | Grano: país × producto × socio × año |
| `gold.fact_indicator` | Hecho | Grano: país × indicador × año |
| `gold.fact_oil_price` | Hecho | Grano: serie × mes |
| `gold.vw_diversification` | Tabla auxiliar | HHI ya calculado en SQL |
| `gold.vw_oil_sensitivity` | Tabla auxiliar | Elasticidades |
| `gold.vw_economic_events` | Tabla auxiliar | Hitos para anotaciones |
| `gold.vw_pipeline_runs` | Tabla auxiliar | Última actualización |

## 2. Relaciones (todas 1:* y dirección de filtro simple)

| Desde (1) | Hacia (*) | Columna |
|---|---|---|
| `dim_date[date_key]` | `fact_trade[date_key]` | date_key |
| `dim_date[date_key]` | `fact_indicator[date_key]` | date_key |
| `dim_date[date_key]` | `fact_oil_price[date_key]` | date_key |
| `dim_country[country_key]` | `fact_trade[country_key]` | country_key |
| `dim_country[country_key]` | `fact_indicator[country_key]` | country_key |
| `dim_product[product_key]` | `fact_trade[product_key]` | product_key |
| `dim_indicator[indicator_key]` | `fact_indicator[indicator_key]` | indicator_key |
| `dim_country[iso3]` | `vw_diversification[iso3]` | iso3 |

Oculta las columnas `*_key` en la vista de informe.

## 3. Medidas DAX (tabla de medidas `_Medidas`)

```dax
-- Exportaciones al Mundo (evita sumar los desgloses por destino)
Exportaciones USD =
CALCULATE ( SUM ( fact_trade[value_usd] ), fact_trade[is_world] = TRUE (), dim_product[hs_code] = "TOTAL" )

Exportaciones petroleras USD =
CALCULATE ( SUM ( fact_trade[value_usd] ), fact_trade[is_world] = TRUE (), dim_product[hs_code] = "27" )

Exportaciones no petroleras USD = [Exportaciones USD] - [Exportaciones petroleras USD]

Peso petróleo % = DIVIDE ( [Exportaciones petroleras USD], [Exportaciones USD] )

-- Valor de un producto clave (usar con dim_product[product_group] en el eje/leyenda)
Valor producto USD =
CALCULATE ( SUM ( fact_trade[value_usd] ), fact_trade[is_world] = TRUE (), dim_product[is_key_product] = TRUE () )

Participación % =
DIVIDE ( [Valor producto USD], CALCULATE ( [Exportaciones USD], REMOVEFILTERS ( dim_product ) ) )

-- Variación interanual
Exportaciones año anterior =
CALCULATE ( [Exportaciones USD], DATEADD ( dim_date[date], -1, YEAR ) )

YoY % = DIVIDE ( [Exportaciones USD] - [Exportaciones año anterior], [Exportaciones año anterior] )

-- CAGR entre el primer y el último año visibles en el contexto
CAGR % =
VAR _y0 = CALCULATE ( MIN ( dim_date[year] ), fact_trade[is_world] = TRUE () )
VAR _y1 = CALCULATE ( MAX ( dim_date[year] ), fact_trade[is_world] = TRUE () )
VAR _v0 = CALCULATE ( [Valor producto USD], dim_date[year] = _y0 )
VAR _v1 = CALCULATE ( [Valor producto USD], dim_date[year] = _y1 )
RETURN IF ( _y1 > _y0 && _v0 > 0, ( _v1 / _v0 ) ^ ( 1 / ( _y1 - _y0 ) ) - 1 )

-- HHI por producto calculado en DAX (capítulos HS2) — debe coincidir con vw_diversification
HHI producto =
VAR _tot = CALCULATE ( SUM ( fact_trade[value_usd] ), fact_trade[is_world] = TRUE (), dim_product[hs_level] = 2 )
RETURN
SUMX (
    CALCULATETABLE ( VALUES ( dim_product[hs_code] ), dim_product[hs_level] = 2 ),
    VAR _v = CALCULATE ( SUM ( fact_trade[value_usd] ), fact_trade[is_world] = TRUE () )
    RETURN ( DIVIDE ( _v, _tot ) * 100 ) ^ 2
)

Productos equivalentes = DIVIDE ( 10000, [HHI producto] )

-- Ranking de productos clave dentro del año
Ranking producto =
IF ( HASONEVALUE ( dim_product[product_group] ),
     RANKX ( CALCULATETABLE ( VALUES ( dim_product[product_group] ), dim_product[is_key_product] = TRUE (), REMOVEFILTERS ( dim_product ) ),
             [Valor producto USD], , DESC, DENSE ) )

Brent promedio = CALCULATE ( AVERAGE ( fact_oil_price[price_usd_bbl] ), fact_oil_price[series] = "brent" )

Valor indicador = AVERAGE ( fact_indicator[value] )

Última actualización =
VAR _f = CALCULATE ( MAX ( vw_pipeline_runs[finished_at] ), vw_pipeline_runs[status] = "success" )
RETURN "Datos actualizados: " & FORMAT ( _f, "dd/mm/yyyy hh:nn" )

-- Título dinámico que dice la conclusión
Título peso petróleo =
VAR _y = MAX ( dim_date[year] )
RETURN "El petróleo representó " & FORMAT ( [Peso petróleo %], "0.0%" ) & " de las exportaciones en " & _y
```

Formatos: `* USD` → moneda, sin decimales, unidades "Miles de millones"; `* %` → porcentaje, 1 decimal;
`HHI producto` → número entero.

## 4. Validación del modelo

1. Tarjeta `[HHI producto]` filtrada a Ecuador y un año = columna `hhi_product` de `vw_diversification` (±0,01).
2. `[Peso petróleo %]` = `oil_share` de `gold.vw_oil_dependency` para el mismo año.
3. `[Exportaciones USD]` sin filtro de país ni año no tiene sentido de negocio: usa siempre un segmentador de país.
