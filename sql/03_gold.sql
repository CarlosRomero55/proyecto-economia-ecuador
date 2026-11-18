/* =====================================================================
   03_gold.sql — Capa gold: esquema estrella (Kimball) + vistas de KPIs.
   Es lo único que consumen Power BI, la API y el snapshot de Streamlit.
   gold.usp_build_gold reconstruye dimensiones y hechos con MERGE.
   ===================================================================== */
USE EcuadorMonitor;
GO
/* ------------------------------------------------------------ Dimensiones */
IF OBJECT_ID(N'gold.dim_date', N'U') IS NULL
CREATE TABLE gold.dim_date (
    date_key     INT          NOT NULL CONSTRAINT pk_dim_date PRIMARY KEY,   -- AAAAMMDD (día 1 del mes)
    [date]       DATE         NOT NULL CONSTRAINT uq_dim_date UNIQUE,
    [year]       SMALLINT     NOT NULL,
    [quarter]    TINYINT      NOT NULL,
    [month]      TINYINT      NOT NULL,
    month_name_es NVARCHAR(15) NOT NULL,
    year_month   CHAR(7)      NOT NULL,
    is_year_start BIT         NOT NULL
);
GO
IF OBJECT_ID(N'gold.dim_country', N'U') IS NULL
CREATE TABLE gold.dim_country (
    country_key   INT IDENTITY(1,1) CONSTRAINT pk_dim_country PRIMARY KEY,
    iso3          CHAR(3)       NOT NULL CONSTRAINT uq_dim_country_iso3 UNIQUE,
    name_es       NVARCHAR(100) NOT NULL,
    name_en       NVARCHAR(100) NOT NULL,
    is_aggregate  BIT           NOT NULL,
    is_focus      BIT           NOT NULL
);
GO
IF OBJECT_ID(N'gold.dim_product', N'U') IS NULL
CREATE TABLE gold.dim_product (
    product_key    INT IDENTITY(1,1) CONSTRAINT pk_dim_product PRIMARY KEY,
    hs_code        NVARCHAR(10)  NOT NULL CONSTRAINT uq_dim_product_hs UNIQUE,
    hs_level       TINYINT       NOT NULL,
    product_group  NVARCHAR(20)  NOT NULL,
    name_es        NVARCHAR(400) NOT NULL,
    name_en        NVARCHAR(400) NOT NULL,
    is_key_product BIT           NOT NULL
);
GO
IF OBJECT_ID(N'gold.dim_indicator', N'U') IS NULL
CREATE TABLE gold.dim_indicator (
    indicator_key  INT IDENTITY(1,1) CONSTRAINT pk_dim_indicator PRIMARY KEY,
    indicator_code NVARCHAR(50)  NOT NULL CONSTRAINT uq_dim_indicator_code UNIQUE,
    name_es        NVARCHAR(200) NOT NULL,
    name_en        NVARCHAR(200) NOT NULL,
    unit           NVARCHAR(10)  NOT NULL
);
GO
/* ------------------------------------------------------------ Hechos */
IF OBJECT_ID(N'gold.fact_indicator', N'U') IS NULL
CREATE TABLE gold.fact_indicator (
    country_key     INT   NOT NULL CONSTRAINT fk_fi_country REFERENCES gold.dim_country(country_key),
    indicator_key   INT   NOT NULL CONSTRAINT fk_fi_indicator REFERENCES gold.dim_indicator(indicator_key),
    date_key        INT   NOT NULL CONSTRAINT fk_fi_date REFERENCES gold.dim_date(date_key),
    [value]         FLOAT NOT NULL,
    is_interpolated BIT   NOT NULL,
    CONSTRAINT pk_fact_indicator PRIMARY KEY (country_key, indicator_key, date_key)
);
GO
IF OBJECT_ID(N'gold.fact_trade', N'U') IS NULL
CREATE TABLE gold.fact_trade (
    country_key        INT           NOT NULL CONSTRAINT fk_ft_country REFERENCES gold.dim_country(country_key),
    product_key        INT           NOT NULL CONSTRAINT fk_ft_product REFERENCES gold.dim_product(product_key),
    date_key           INT           NOT NULL CONSTRAINT fk_ft_date REFERENCES gold.dim_date(date_key),
    partner_code       INT           NOT NULL,
    partner_iso3       NVARCHAR(10)  NOT NULL,
    partner_desc       NVARCHAR(200) NULL,
    value_usd          DECIMAL(20,2) NOT NULL,
    net_weight_kg      FLOAT         NULL,
    is_world           BIT           NOT NULL,
    is_special_partner BIT           NOT NULL,
    CONSTRAINT pk_fact_trade PRIMARY KEY (country_key, product_key, partner_code, date_key)
);
GO
IF OBJECT_ID(N'gold.fact_oil_price', N'U') IS NULL
CREATE TABLE gold.fact_oil_price (
    series        NVARCHAR(20)  NOT NULL,
    date_key      INT           NOT NULL CONSTRAINT fk_fop_date REFERENCES gold.dim_date(date_key),
    price_usd_bbl DECIMAL(10,4) NOT NULL,
    source_name   NVARCHAR(50)  NOT NULL,
    CONSTRAINT pk_fact_oil_price PRIMARY KEY (series, date_key)
);
GO
/* ------------------------------------------------------------ Construcción */
CREATE OR ALTER PROCEDURE gold.usp_build_gold
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRANSACTION;

    -- dim_date: un registro por mes, 2000-01 a 2040-12 (idempotente)
    ;WITH n AS (SELECT TOP (492) ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) - 1 AS i FROM sys.all_objects),
          d AS (SELECT DATEADD(MONTH, i, CAST('2000-01-01' AS DATE)) AS dt FROM n)
    INSERT INTO gold.dim_date (date_key, [date], [year], [quarter], [month], month_name_es, year_month, is_year_start)
    SELECT YEAR(dt) * 10000 + MONTH(dt) * 100 + 1, dt, YEAR(dt), DATEPART(QUARTER, dt), MONTH(dt),
           CHOOSE(MONTH(dt), N'enero', N'febrero', N'marzo', N'abril', N'mayo', N'junio', N'julio',
                  N'agosto', N'septiembre', N'octubre', N'noviembre', N'diciembre'),
           CONVERT(CHAR(7), dt, 126), CASE WHEN MONTH(dt) = 1 THEN 1 ELSE 0 END
    FROM d WHERE NOT EXISTS (SELECT 1 FROM gold.dim_date x WHERE x.[date] = d.dt);

    MERGE gold.dim_country AS t
    USING silver.countries AS s ON t.iso3 = s.iso3
    WHEN MATCHED THEN UPDATE SET name_es = s.name_es, name_en = s.name_en, is_aggregate = s.is_aggregate,
                                 is_focus = CASE WHEN s.iso3 = 'ECU' THEN 1 ELSE 0 END
    WHEN NOT MATCHED THEN INSERT (iso3, name_es, name_en, is_aggregate, is_focus)
         VALUES (s.iso3, s.name_es, s.name_en, s.is_aggregate, CASE WHEN s.iso3 = 'ECU' THEN 1 ELSE 0 END);

    MERGE gold.dim_product AS t
    USING silver.products_hs AS s ON t.hs_code = s.hs_code
    WHEN MATCHED THEN UPDATE SET hs_level = s.hs_level, product_group = s.product_group, name_es = s.name_es,
                                 name_en = s.name_en, is_key_product = s.is_key_product
    WHEN NOT MATCHED THEN INSERT (hs_code, hs_level, product_group, name_es, name_en, is_key_product)
         VALUES (s.hs_code, s.hs_level, s.product_group, s.name_es, s.name_en, s.is_key_product);

    MERGE gold.dim_indicator AS t
    USING silver.indicators AS s ON t.indicator_code = s.indicator_code
    WHEN MATCHED THEN UPDATE SET name_es = s.name_es, name_en = s.name_en, unit = s.unit
    WHEN NOT MATCHED THEN INSERT (indicator_code, name_es, name_en, unit) VALUES (s.indicator_code, s.name_es, s.name_en, s.unit);

    MERGE gold.fact_indicator AS t
    USING (SELECT c.country_key, i.indicator_key, v.[year] * 10000 + 101 AS date_key, v.[value], v.is_interpolated
           FROM silver.indicator_values v
           JOIN gold.dim_country c ON c.iso3 = v.country_iso3
           JOIN gold.dim_indicator i ON i.indicator_code = v.indicator_code) AS s
    ON t.country_key = s.country_key AND t.indicator_key = s.indicator_key AND t.date_key = s.date_key
    WHEN MATCHED AND (t.[value] <> s.[value] OR t.is_interpolated <> s.is_interpolated) THEN
         UPDATE SET [value] = s.[value], is_interpolated = s.is_interpolated
    WHEN NOT MATCHED THEN INSERT (country_key, indicator_key, date_key, [value], is_interpolated)
         VALUES (s.country_key, s.indicator_key, s.date_key, s.[value], s.is_interpolated);

    MERGE gold.fact_trade AS t
    USING (SELECT c.country_key, p.product_key, f.[year] * 10000 + 101 AS date_key, f.partner_code, f.partner_iso3,
                  f.partner_desc, f.value_usd, f.net_weight_kg, f.is_world, f.is_special_partner
           FROM silver.trade_flows f
           JOIN gold.dim_country c ON c.iso3 = f.reporter_iso3
           JOIN gold.dim_product p ON p.hs_code = f.hs_code) AS s
    ON t.country_key = s.country_key AND t.product_key = s.product_key AND t.partner_code = s.partner_code AND t.date_key = s.date_key
    WHEN MATCHED AND t.value_usd <> s.value_usd THEN
         UPDATE SET value_usd = s.value_usd, net_weight_kg = s.net_weight_kg, partner_desc = s.partner_desc
    WHEN NOT MATCHED THEN INSERT (country_key, product_key, date_key, partner_code, partner_iso3, partner_desc,
                                  value_usd, net_weight_kg, is_world, is_special_partner)
         VALUES (s.country_key, s.product_key, s.date_key, s.partner_code, s.partner_iso3, s.partner_desc,
                 s.value_usd, s.net_weight_kg, s.is_world, s.is_special_partner);

    MERGE gold.fact_oil_price AS t
    USING (SELECT series, YEAR(price_month) * 10000 + MONTH(price_month) * 100 + 1 AS date_key, price_usd_bbl, source_name
           FROM silver.commodity_prices) AS s
    ON t.series = s.series AND t.date_key = s.date_key
    WHEN MATCHED AND t.price_usd_bbl <> s.price_usd_bbl THEN UPDATE SET price_usd_bbl = s.price_usd_bbl, source_name = s.source_name
    WHEN NOT MATCHED THEN INSERT (series, date_key, price_usd_bbl, source_name) VALUES (s.series, s.date_key, s.price_usd_bbl, s.source_name);

    COMMIT TRANSACTION;
END
GO
/* ------------------------------------------------------------ Vistas de KPIs */

-- Canasta exportadora por país-año (destino = Mundo). 'other' = total − productos clave.
CREATE OR ALTER VIEW gold.vw_export_basket AS
WITH w AS (
    SELECT c.iso3, d.[year], p.hs_code, p.product_group, p.is_key_product, CAST(f.value_usd AS FLOAT) AS value_usd
    FROM gold.fact_trade f
    JOIN gold.dim_country c ON c.country_key = f.country_key
    JOIN gold.dim_product p ON p.product_key = f.product_key
    JOIN gold.dim_date d ON d.date_key = f.date_key
    WHERE f.is_world = 1
),
tot AS (SELECT iso3, [year], MAX(CASE WHEN hs_code = N'TOTAL' THEN value_usd END) AS total_usd,
               SUM(CASE WHEN is_key_product = 1 THEN value_usd ELSE 0 END) AS key_usd
        FROM w GROUP BY iso3, [year]),
basket AS (
    SELECT iso3, [year], product_group, value_usd FROM w WHERE is_key_product = 1
    UNION ALL
    SELECT iso3, [year], N'other', CASE WHEN total_usd - key_usd > 0 THEN total_usd - key_usd ELSE 0 END
    FROM tot WHERE total_usd IS NOT NULL
)
SELECT b.iso3, b.[year], b.product_group, b.value_usd,
       b.value_usd / NULLIF(SUM(b.value_usd) OVER (PARTITION BY b.iso3, b.[year]), 0) AS share,
       RANK() OVER (PARTITION BY b.iso3, b.[year] ORDER BY b.value_usd DESC) AS rank_in_year
FROM basket b;
GO

-- Dependencia del petróleo: participación petrolera vs no petrolera
CREATE OR ALTER VIEW gold.vw_oil_dependency AS
SELECT iso3, [year],
       SUM(value_usd) AS total_exports_usd,
       SUM(CASE WHEN product_group = N'oil' THEN value_usd ELSE 0 END) AS oil_exports_usd,
       SUM(CASE WHEN product_group <> N'oil' THEN value_usd ELSE 0 END) AS non_oil_exports_usd,
       SUM(CASE WHEN product_group = N'oil' THEN value_usd ELSE 0 END) / NULLIF(SUM(value_usd), 0) AS oil_share
FROM gold.vw_export_basket
GROUP BY iso3, [year];
GO

-- Diversificación: HHI por producto (capítulos HS2) y por destino (países socios)
CREATE OR ALTER VIEW gold.vw_diversification AS
WITH ch AS (
    SELECT c.iso3, d.[year], CAST(f.value_usd AS FLOAT) AS v
    FROM gold.fact_trade f
    JOIN gold.dim_country c ON c.country_key = f.country_key
    JOIN gold.dim_product p ON p.product_key = f.product_key
    JOIN gold.dim_date d ON d.date_key = f.date_key
    WHERE f.is_world = 1 AND p.hs_level = 2 AND f.value_usd > 0
),
chs AS (SELECT iso3, [year], v / SUM(v) OVER (PARTITION BY iso3, [year]) * 100 AS s FROM ch),
hp AS (SELECT iso3, [year], SUM(s * s) AS hhi_product, COUNT(*) AS n_chapters FROM chs GROUP BY iso3, [year]),
de AS (
    SELECT c.iso3, d.[year], CAST(f.value_usd AS FLOAT) AS v
    FROM gold.fact_trade f
    JOIN gold.dim_country c ON c.country_key = f.country_key
    JOIN gold.dim_product p ON p.product_key = f.product_key
    JOIN gold.dim_date d ON d.date_key = f.date_key
    WHERE f.is_world = 0 AND f.is_special_partner = 0 AND p.hs_code = N'TOTAL' AND f.value_usd > 0
),
des AS (SELECT iso3, [year], v / SUM(v) OVER (PARTITION BY iso3, [year]) * 100 AS s FROM de),
hd AS (SELECT iso3, [year], SUM(s * s) AS hhi_destination, COUNT(*) AS n_destinations FROM des GROUP BY iso3, [year])
SELECT COALESCE(hp.iso3, hd.iso3) AS iso3, COALESCE(hp.[year], hd.[year]) AS [year],
       hp.hhi_product, 10000.0 / NULLIF(hp.hhi_product, 0) AS equiv_products, hp.n_chapters,
       hd.hhi_destination, 10000.0 / NULLIF(hd.hhi_destination, 0) AS equiv_destinations, hd.n_destinations
FROM hp FULL OUTER JOIN hd ON hp.iso3 = hd.iso3 AND hp.[year] = hd.[year];
GO

-- CAGR por grupo de producto entre el primer y el último año con dato
CREATE OR ALTER VIEW gold.vw_product_cagr AS
WITH b AS (SELECT * FROM gold.vw_export_basket WHERE value_usd > 0),
lim AS (SELECT iso3, product_group, MIN([year]) AS y0, MAX([year]) AS y1 FROM b GROUP BY iso3, product_group)
SELECT l.iso3, l.product_group, l.y0 AS start_year, l.y1 AS end_year, b0.value_usd AS start_value, b1.value_usd AS end_value,
       CASE WHEN l.y1 > l.y0 THEN POWER(b1.value_usd / b0.value_usd, 1.0 / (l.y1 - l.y0)) - 1 END AS cagr
FROM lim l
JOIN b b0 ON b0.iso3 = l.iso3 AND b0.product_group = l.product_group AND b0.[year] = l.y0
JOIN b b1 ON b1.iso3 = l.iso3 AND b1.product_group = l.product_group AND b1.[year] = l.y1;
GO

-- Precio anual del crudo (promedio de meses disponibles)
CREATE OR ALTER VIEW gold.vw_oil_price_annual AS
SELECT f.series, d.[year], AVG(CAST(f.price_usd_bbl AS FLOAT)) AS avg_price_usd_bbl, COUNT(*) AS months_available
FROM gold.fact_oil_price f JOIN gold.dim_date d ON d.date_key = f.date_key
GROUP BY f.series, d.[year];
GO

-- Sensibilidad al Brent: elasticidad log-log (β = cov(ln P, ln X) / var(ln P)) y R²
CREATE OR ALTER VIEW gold.vw_oil_sensitivity AS
WITH x AS (
    SELECT o.iso3, N'oil_exports' AS target, LOG(o.oil_exports_usd) AS ly, LOG(p.avg_price_usd_bbl) AS lx
    FROM gold.vw_oil_dependency o JOIN gold.vw_oil_price_annual p ON p.[year] = o.[year] AND p.series = N'brent'
    WHERE o.oil_exports_usd > 0 AND p.months_available = 12
    UNION ALL
    SELECT o.iso3, N'total_exports', LOG(o.total_exports_usd), LOG(p.avg_price_usd_bbl)
    FROM gold.vw_oil_dependency o JOIN gold.vw_oil_price_annual p ON p.[year] = o.[year] AND p.series = N'brent'
    WHERE o.total_exports_usd > 0 AND p.months_available = 12
),
m AS (SELECT iso3, target, COUNT(*) AS n, AVG(lx) AS mx, AVG(ly) AS my, AVG(lx * ly) AS mxy,
             AVG(lx * lx) AS mxx, AVG(ly * ly) AS myy FROM x GROUP BY iso3, target)
SELECT iso3, target, n,
       (mxy - mx * my) / NULLIF(mxx - mx * mx, 0) AS elasticity_beta,
       POWER((mxy - mx * my) / NULLIF(SQRT((mxx - mx * mx) * (myy - my * my)), 0), 2) AS r_squared
FROM m WHERE n >= 5;
GO

-- Comparación regional: indicadores macro en formato largo listos para filtrar
CREATE OR ALTER VIEW gold.vw_regional_compare AS
SELECT c.iso3, c.name_es AS country_es, c.name_en AS country_en, c.is_aggregate, i.indicator_code,
       i.name_es AS indicator_es, i.name_en AS indicator_en, i.unit, d.[year], f.[value], f.is_interpolated
FROM gold.fact_indicator f
JOIN gold.dim_country c ON c.country_key = f.country_key
JOIN gold.dim_indicator i ON i.indicator_key = f.indicator_key
JOIN gold.dim_date d ON d.date_key = f.date_key;
GO

-- Exportaciones como índice (año 2000 = 100) para comparar países de distinto tamaño
CREATE OR ALTER VIEW gold.vw_exports_index AS
SELECT o.iso3, o.[year], o.total_exports_usd, o.non_oil_exports_usd,
       o.total_exports_usd / NULLIF(b.total_exports_usd, 0) * 100 AS total_index_2000,
       o.non_oil_exports_usd / NULLIF(b.non_oil_exports_usd, 0) * 100 AS non_oil_index_2000
FROM gold.vw_oil_dependency o
LEFT JOIN gold.vw_oil_dependency b ON b.iso3 = o.iso3 AND b.[year] = 2000;
GO

CREATE OR ALTER VIEW gold.vw_economic_events AS
SELECT event_code, start_date, end_date, name_es, name_en FROM silver.economic_events;
GO

-- Validación cruzada: participación petrolera Comtrade vs indicador del Banco Mundial vs BCE
CREATE OR ALTER VIEW gold.vw_source_reconciliation AS
SELECT o.iso3, o.[year], o.oil_share AS oil_share_comtrade,
       wb.[value] / 100.0 AS fuel_share_worldbank,
       bce.oil_exports_fob_usd / NULLIF(bce.oil_exports_fob_usd + bce.non_oil_exports_fob_usd, 0) AS oil_share_bce
FROM gold.vw_oil_dependency o
LEFT JOIN gold.vw_regional_compare wb ON wb.iso3 = o.iso3 AND wb.[year] = o.[year] AND wb.indicator_code = N'TX.VAL.FUEL.ZS.UN'
LEFT JOIN silver.bce_trade_balance bce ON o.iso3 = 'ECU' AND bce.[year] = o.[year];
GO

-- Operación del pipeline
CREATE OR ALTER VIEW gold.vw_pipeline_runs AS
SELECT run_id, batch_id, run_mode, started_at, finished_at, status, rows_bronze, rows_silver, rows_gold, [message],
       DATEDIFF(SECOND, started_at, finished_at) AS duration_seconds
FROM silver.etl_runs;
GO

CREATE OR ALTER VIEW gold.vw_layer_counts AS
SELECT s.name AS layer, t.name AS table_name, SUM(p.rows) AS row_count
FROM sys.tables t
JOIN sys.schemas s ON s.schema_id = t.schema_id
JOIN sys.partitions p ON p.object_id = t.object_id AND p.index_id IN (0, 1)
WHERE s.name IN (N'bronze', N'silver', N'gold') AND t.name NOT LIKE N'stg[_]%'
GROUP BY s.name, t.name;
GO

CREATE OR ALTER VIEW gold.vw_cleaning_rules AS
SELECT l.batch_id, l.rule_id, l.source_name, l.[description], l.rows_affected, l.logged_at
FROM silver.cleaning_log l;
GO
