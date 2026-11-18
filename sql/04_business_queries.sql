/* =====================================================================
   04_business_queries.sql — Consultas de negocio sobre la capa gold.
   Cada consulta responde una pregunta del plan (docs/plan.md).
   Ejecutar por bloques en SSMS / Azure Data Studio.
   ===================================================================== */
USE EcuadorMonitor;
GO

/* Q1. DEPENDENCIA — ¿Cuánto pesa el petróleo en las exportaciones de Ecuador cada año? */
SELECT [year], total_exports_usd, oil_exports_usd, CAST(oil_share * 100 AS DECIMAL(5,1)) AS oil_share_pct
FROM gold.vw_oil_dependency
WHERE iso3 = 'ECU'
ORDER BY [year];

/* Q2. DEPENDENCIA — Año de mayor y menor peso petrolero (con ventana, sin subconsultas repetidas) */
WITH r AS (
    SELECT [year], oil_share,
           ROW_NUMBER() OVER (ORDER BY oil_share DESC) AS rk_max,
           ROW_NUMBER() OVER (ORDER BY oil_share ASC)  AS rk_min
    FROM gold.vw_oil_dependency WHERE iso3 = 'ECU'
)
SELECT CASE WHEN rk_max = 1 THEN 'máximo' ELSE 'mínimo' END AS extremo, [year], CAST(oil_share * 100 AS DECIMAL(5,1)) AS oil_share_pct
FROM r WHERE rk_max = 1 OR rk_min = 1;

/* Q3. CANASTA — Top 3 productos clave de Ecuador por año (¿cuándo cambió el líder?) */
SELECT [year], product_group, value_usd, CAST(share * 100 AS DECIMAL(5,1)) AS share_pct, rank_in_year
FROM gold.vw_export_basket
WHERE iso3 = 'ECU' AND product_group <> 'other' AND rank_in_year <= 3
ORDER BY [year], rank_in_year;

/* Q4. CANASTA — Año en que cada producto clave superó por primera vez al petróleo */
WITH p AS (
    SELECT b.[year], b.product_group, b.value_usd, o.value_usd AS oil_usd
    FROM gold.vw_export_basket b
    JOIN gold.vw_export_basket o ON o.iso3 = b.iso3 AND o.[year] = b.[year] AND o.product_group = 'oil'
    WHERE b.iso3 = 'ECU' AND b.product_group NOT IN ('oil', 'other')
)
SELECT product_group, MIN([year]) AS first_year_above_oil
FROM p WHERE value_usd > oil_usd
GROUP BY product_group;

/* Q5. CRECIMIENTO — CAGR por producto clave entre el primer y el último año disponibles */
SELECT iso3, product_group, start_year, end_year, CAST(cagr * 100 AS DECIMAL(6,2)) AS cagr_pct
FROM gold.vw_product_cagr
WHERE product_group <> 'other'
ORDER BY iso3, cagr DESC;

/* Q6. CRECIMIENTO — Variación interanual (YoY) de exportaciones no petroleras con LAG */
SELECT iso3, [year], non_oil_exports_usd,
       CAST((non_oil_exports_usd / NULLIF(LAG(non_oil_exports_usd) OVER (PARTITION BY iso3 ORDER BY [year]), 0) - 1) * 100
            AS DECIMAL(6,1)) AS yoy_pct
FROM gold.vw_oil_dependency
ORDER BY iso3, [year];

/* Q7. DIVERSIFICACIÓN — HHI por producto y destino: primer vs último año de cada país */
WITH b AS (
    SELECT *, FIRST_VALUE([year]) OVER (PARTITION BY iso3 ORDER BY [year]) AS y0,
              LAST_VALUE([year]) OVER (PARTITION BY iso3 ORDER BY [year] ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS y1
    FROM gold.vw_diversification
)
SELECT iso3, [year], CAST(hhi_product AS INT) AS hhi_product, CAST(equiv_products AS DECIMAL(5,1)) AS equiv_products,
       CAST(hhi_destination AS INT) AS hhi_destination
FROM b WHERE [year] IN (y0, y1)
ORDER BY iso3, [year];

/* Q8. DIVERSIFICACIÓN — ¿Diversificación real o sustitución? Peso del primer producto vs HHI */
SELECT b.[year], b.product_group AS top_product, CAST(b.share * 100 AS DECIMAL(5,1)) AS top_share_pct,
       CAST(d.hhi_product AS INT) AS hhi_product
FROM gold.vw_export_basket b
JOIN gold.vw_diversification d ON d.iso3 = b.iso3 AND d.[year] = b.[year]
WHERE b.iso3 = 'ECU' AND b.rank_in_year = 1
ORDER BY b.[year];

/* Q9. VULNERABILIDAD — Exportaciones petroleras vs Brent en los años de choque */
SELECT o.[year], o.oil_exports_usd, CAST(p.avg_price_usd_bbl AS DECIMAL(6,2)) AS brent,
       CAST((o.oil_exports_usd / NULLIF(LAG(o.oil_exports_usd) OVER (ORDER BY o.[year]), 0) - 1) * 100 AS DECIMAL(6,1)) AS oil_exports_yoy_pct,
       CAST((p.avg_price_usd_bbl / NULLIF(LAG(p.avg_price_usd_bbl) OVER (ORDER BY o.[year]), 0) - 1) * 100 AS DECIMAL(6,1)) AS brent_yoy_pct,
       e.event_code
FROM gold.vw_oil_dependency o
JOIN gold.vw_oil_price_annual p ON p.[year] = o.[year] AND p.series = 'brent'
LEFT JOIN gold.vw_economic_events e ON o.[year] BETWEEN YEAR(e.start_date) AND YEAR(e.end_date)
WHERE o.iso3 = 'ECU'
ORDER BY o.[year];

/* Q10. VULNERABILIDAD — Elasticidad al Brent por país (cuanto mayor β, más sensible) */
SELECT iso3, target, n, CAST(elasticity_beta AS DECIMAL(5,2)) AS beta, CAST(r_squared AS DECIMAL(4,2)) AS r2
FROM gold.vw_oil_sensitivity
ORDER BY target, elasticity_beta DESC;

/* Q11. REGIÓN — Ranking regional de exportaciones (% del PIB) en el último año con datos para todos */
WITH y AS (
    SELECT MAX([year]) AS yr FROM (
        SELECT [year] FROM gold.vw_regional_compare WHERE indicator_code = 'NE.EXP.GNFS.ZS'
        GROUP BY [year] HAVING COUNT(DISTINCT iso3) = (SELECT COUNT(*) FROM gold.dim_country)) t
)
SELECT r.country_es, r.[year], CAST(r.[value] AS DECIMAL(6,1)) AS exports_pct_gdp,
       RANK() OVER (ORDER BY r.[value] DESC) AS ranking
FROM gold.vw_regional_compare r CROSS JOIN y
WHERE r.indicator_code = 'NE.EXP.GNFS.ZS' AND r.[year] = y.yr;

/* Q12. REGIÓN — Exportaciones no petroleras, índice 2000 = 100 (pivote por país) */
SELECT [year], [ECU], [PER], [COL], [CHL]
FROM (SELECT iso3, [year], CAST(non_oil_index_2000 AS DECIMAL(8,1)) AS idx FROM gold.vw_exports_index) s
PIVOT (MAX(idx) FOR iso3 IN ([ECU], [PER], [COL], [CHL])) pv
ORDER BY [year];

/* Q13. MACRO — Remesas e IED como % del PIB de Ecuador (fuentes de dólares además de exportaciones) */
SELECT g.[year],
       CAST(rm.[value] / g.[value] * 100 AS DECIMAL(5,2)) AS remittances_pct_gdp,
       CAST(fdi.[value] / g.[value] * 100 AS DECIMAL(5,2)) AS fdi_pct_gdp
FROM gold.vw_regional_compare g
LEFT JOIN gold.vw_regional_compare rm  ON rm.iso3 = g.iso3 AND rm.[year] = g.[year] AND rm.indicator_code = 'BX.TRF.PWKR.CD.DT'
LEFT JOIN gold.vw_regional_compare fdi ON fdi.iso3 = g.iso3 AND fdi.[year] = g.[year] AND fdi.indicator_code = 'BX.KLT.DINV.CD.WD'
WHERE g.iso3 = 'ECU' AND g.indicator_code = 'NY.GDP.MKTP.CD'
ORDER BY g.[year];

/* Q14. CALIDAD — Concordancia entre fuentes: Comtrade (HS 27) vs Banco Mundial (combustibles) */
SELECT [year], CAST(oil_share_comtrade * 100 AS DECIMAL(5,1)) AS comtrade_pct,
       CAST(fuel_share_worldbank * 100 AS DECIMAL(5,1)) AS worldbank_pct,
       CAST((oil_share_comtrade - fuel_share_worldbank) * 100 AS DECIMAL(5,1)) AS diff_pp,
       CAST(oil_share_bce * 100 AS DECIMAL(5,1)) AS bce_pct
FROM gold.vw_source_reconciliation
WHERE iso3 = 'ECU'
ORDER BY [year];

/* Q15. OPERACIÓN — Historial del pipeline y filas por capa */
SELECT TOP (10) run_id, batch_id, run_mode, status, duration_seconds, rows_bronze, rows_silver, rows_gold
FROM gold.vw_pipeline_runs ORDER BY run_id DESC;
SELECT layer, SUM(row_count) AS rows_in_layer FROM gold.vw_layer_counts GROUP BY layer;
GO
