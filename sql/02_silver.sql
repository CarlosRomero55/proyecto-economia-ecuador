/* =====================================================================
   02_silver.sql — Capa silver: modelo normalizado (3FN) con PK, FK, CHECK
   e índices. Datos limpios y armonizados. Todo idempotente.
   Flujo: Python limpia bronze → carga silver.stg_* → EXEC silver.usp_merge_*
   ===================================================================== */
USE EcuadorMonitor;
GO
/* ------------------------------------------------------------ Catálogos */
IF OBJECT_ID(N'silver.data_sources', N'U') IS NULL
CREATE TABLE silver.data_sources (
    source_name    NVARCHAR(50)  NOT NULL CONSTRAINT pk_data_sources PRIMARY KEY,
    provider       NVARCHAR(200) NOT NULL,
    url            NVARCHAR(400) NOT NULL,
    access_method  NVARCHAR(100) NOT NULL,
    notes          NVARCHAR(500) NULL
);
GO
IF OBJECT_ID(N'silver.countries', N'U') IS NULL
CREATE TABLE silver.countries (
    iso3          CHAR(3)       NOT NULL CONSTRAINT pk_countries PRIMARY KEY,
    name_es       NVARCHAR(100) NOT NULL,
    name_en       NVARCHAR(100) NOT NULL,
    is_aggregate  BIT           NOT NULL CONSTRAINT df_countries_agg DEFAULT (0)
);
GO
IF OBJECT_ID(N'silver.country_codes_map', N'U') IS NULL
CREATE TABLE silver.country_codes_map (
    iso3           CHAR(3)       NOT NULL CONSTRAINT pk_country_codes_map PRIMARY KEY
                   CONSTRAINT fk_ccm_country REFERENCES silver.countries(iso3),
    iso2           CHAR(2)       NOT NULL CONSTRAINT uq_ccm_iso2 UNIQUE,
    comtrade_code  INT           NULL,
    bce_name       NVARCHAR(100) NULL
);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'uq_ccm_comtrade')
    CREATE UNIQUE INDEX uq_ccm_comtrade ON silver.country_codes_map(comtrade_code) WHERE comtrade_code IS NOT NULL;
GO
IF OBJECT_ID(N'silver.indicators', N'U') IS NULL
CREATE TABLE silver.indicators (
    indicator_code NVARCHAR(50)  NOT NULL CONSTRAINT pk_indicators PRIMARY KEY,
    name_es        NVARCHAR(200) NOT NULL,
    name_en        NVARCHAR(200) NOT NULL,
    unit           NVARCHAR(10)  NOT NULL CONSTRAINT ck_indicators_unit CHECK (unit IN (N'USD', N'%')),
    source_name    NVARCHAR(50)  NOT NULL CONSTRAINT fk_indicators_source REFERENCES silver.data_sources(source_name)
);
GO
IF OBJECT_ID(N'silver.products_hs', N'U') IS NULL
CREATE TABLE silver.products_hs (
    hs_code        NVARCHAR(10)  NOT NULL CONSTRAINT pk_products_hs PRIMARY KEY,
    hs_level       TINYINT       NOT NULL CONSTRAINT ck_products_level CHECK (hs_level IN (0, 2, 4)),
    product_group  NVARCHAR(20)  NOT NULL,
    name_es        NVARCHAR(400) NOT NULL,
    name_en        NVARCHAR(400) NOT NULL,
    is_key_product BIT           NOT NULL CONSTRAINT df_products_key DEFAULT (0)
);
GO
IF OBJECT_ID(N'silver.economic_events', N'U') IS NULL
CREATE TABLE silver.economic_events (
    event_code  NVARCHAR(30)  NOT NULL CONSTRAINT pk_economic_events PRIMARY KEY,
    start_date  DATE          NOT NULL,
    end_date    DATE          NOT NULL,
    name_es     NVARCHAR(200) NOT NULL,
    name_en     NVARCHAR(200) NOT NULL,
    CONSTRAINT ck_events_dates CHECK (end_date >= start_date)
);
GO
/* ------------------------------------------------------------ Hechos limpios */
IF OBJECT_ID(N'silver.indicator_values', N'U') IS NULL
CREATE TABLE silver.indicator_values (   -- formato largo (ADR 0004)
    country_iso3    CHAR(3)       NOT NULL CONSTRAINT fk_iv_country REFERENCES silver.countries(iso3),
    indicator_code  NVARCHAR(50)  NOT NULL CONSTRAINT fk_iv_indicator REFERENCES silver.indicators(indicator_code),
    [year]          SMALLINT      NOT NULL CONSTRAINT ck_iv_year CHECK ([year] BETWEEN 2000 AND 2100),
    [value]         FLOAT         NOT NULL,
    is_interpolated BIT           NOT NULL CONSTRAINT df_iv_interp DEFAULT (0),
    obs_status      NVARCHAR(50)  NULL,
    source_name     NVARCHAR(50)  NOT NULL CONSTRAINT fk_iv_source REFERENCES silver.data_sources(source_name),
    batch_id        NVARCHAR(40)  NOT NULL,
    updated_at      DATETIME2(0)  NOT NULL CONSTRAINT df_iv_updated DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT pk_indicator_values PRIMARY KEY (country_iso3, indicator_code, [year])
);
GO
IF OBJECT_ID(N'silver.trade_flows', N'U') IS NULL
CREATE TABLE silver.trade_flows (
    reporter_iso3      CHAR(3)        NOT NULL CONSTRAINT fk_tf_country REFERENCES silver.countries(iso3),
    partner_code       INT            NOT NULL,     -- M49; 0 = Mundo
    partner_iso3       NVARCHAR(10)   NOT NULL,
    partner_desc       NVARCHAR(200)  NULL,
    [year]             SMALLINT       NOT NULL CONSTRAINT ck_tf_year CHECK ([year] BETWEEN 2000 AND 2100),
    hs_code            NVARCHAR(10)   NOT NULL CONSTRAINT fk_tf_product REFERENCES silver.products_hs(hs_code),
    value_usd          DECIMAL(20,2)  NOT NULL CONSTRAINT ck_tf_value CHECK (value_usd >= 0),
    net_weight_kg      FLOAT          NULL,
    is_world           BIT            NOT NULL,
    is_special_partner BIT            NOT NULL,
    source_name        NVARCHAR(50)   NOT NULL CONSTRAINT fk_tf_source REFERENCES silver.data_sources(source_name),
    batch_id           NVARCHAR(40)   NOT NULL,
    updated_at         DATETIME2(0)   NOT NULL CONSTRAINT df_tf_updated DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT pk_trade_flows PRIMARY KEY (reporter_iso3, partner_code, [year], hs_code)
);
GO
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'ix_tf_world_year')
    CREATE INDEX ix_tf_world_year ON silver.trade_flows(is_world, [year]) INCLUDE (reporter_iso3, hs_code, value_usd);
GO
IF OBJECT_ID(N'silver.commodity_prices', N'U') IS NULL
CREATE TABLE silver.commodity_prices (
    series         NVARCHAR(20)  NOT NULL CONSTRAINT ck_cp_series CHECK (series IN (N'brent', N'wti')),
    price_month    DATE          NOT NULL CONSTRAINT ck_cp_month CHECK (DAY(price_month) = 1),
    price_usd_bbl  DECIMAL(10,4) NOT NULL CONSTRAINT ck_cp_price CHECK (price_usd_bbl > 0),
    source_name    NVARCHAR(50)  NOT NULL CONSTRAINT fk_cp_source REFERENCES silver.data_sources(source_name),
    batch_id       NVARCHAR(40)  NOT NULL,
    updated_at     DATETIME2(0)  NOT NULL CONSTRAINT df_cp_updated DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT pk_commodity_prices PRIMARY KEY (series, price_month)
);
GO
IF OBJECT_ID(N'silver.bce_trade_balance', N'U') IS NULL
CREATE TABLE silver.bce_trade_balance (
    [year]                   SMALLINT      NOT NULL CONSTRAINT pk_bce_trade_balance PRIMARY KEY,
    oil_exports_fob_usd      DECIMAL(20,2) NOT NULL CONSTRAINT ck_bce_oil CHECK (oil_exports_fob_usd >= 0),
    non_oil_exports_fob_usd  DECIMAL(20,2) NOT NULL CONSTRAINT ck_bce_nonoil CHECK (non_oil_exports_fob_usd >= 0),
    source_file              NVARCHAR(260) NULL,
    batch_id                 NVARCHAR(40)  NOT NULL,
    updated_at               DATETIME2(0)  NOT NULL CONSTRAINT df_bce_updated DEFAULT (SYSUTCDATETIME())
);
GO
/* ------------------------------------------------------------ Operación del pipeline */
IF OBJECT_ID(N'silver.etl_runs', N'U') IS NULL
CREATE TABLE silver.etl_runs (
    run_id       INT IDENTITY(1,1) CONSTRAINT pk_etl_runs PRIMARY KEY,
    batch_id     NVARCHAR(40)  NOT NULL CONSTRAINT uq_etl_runs_batch UNIQUE,
    run_mode     NVARCHAR(20)  NOT NULL CONSTRAINT ck_etl_runs_mode CHECK (run_mode IN (N'full', N'incremental')),
    started_at   DATETIME2(0)  NOT NULL,
    finished_at  DATETIME2(0)  NULL,
    status       NVARCHAR(20)  NOT NULL CONSTRAINT ck_etl_runs_status CHECK (status IN (N'running', N'success', N'failed')),
    rows_bronze  INT           NULL,
    rows_silver  INT           NULL,
    rows_gold    INT           NULL,
    [message]    NVARCHAR(2000) NULL
);
GO
IF OBJECT_ID(N'silver.etl_watermarks', N'U') IS NULL
CREATE TABLE silver.etl_watermarks (
    source_name     NVARCHAR(50)  NOT NULL,
    scope_key       NVARCHAR(50)  NOT NULL,   -- p. ej. ISO3 del reportante en Comtrade
    watermark_value NVARCHAR(50)  NOT NULL,   -- último año/mes cargado
    updated_at      DATETIME2(0)  NOT NULL CONSTRAINT df_wm_updated DEFAULT (SYSUTCDATETIME()),
    CONSTRAINT pk_etl_watermarks PRIMARY KEY (source_name, scope_key)
);
GO
IF OBJECT_ID(N'silver.cleaning_log', N'U') IS NULL
CREATE TABLE silver.cleaning_log (
    log_id         BIGINT IDENTITY(1,1) CONSTRAINT pk_cleaning_log PRIMARY KEY,
    batch_id       NVARCHAR(40)  NOT NULL,
    rule_id        NVARCHAR(10)  NOT NULL,
    source_name    NVARCHAR(50)  NOT NULL,
    [description]  NVARCHAR(300) NOT NULL,
    rows_affected  INT           NOT NULL,
    logged_at      DATETIME2(0)  NOT NULL CONSTRAINT df_cl_logged DEFAULT (SYSUTCDATETIME())
);
GO
/* ------------------------------------------------------------ Staging (sin restricciones) */
IF OBJECT_ID(N'silver.stg_indicator_values', N'U') IS NULL
CREATE TABLE silver.stg_indicator_values (
    country_iso3 NVARCHAR(10), indicator_code NVARCHAR(50), [year] INT, [value] FLOAT,
    is_interpolated INT, obs_status NVARCHAR(50), source_name NVARCHAR(50), batch_id NVARCHAR(40)
);
IF OBJECT_ID(N'silver.stg_trade_flows', N'U') IS NULL
CREATE TABLE silver.stg_trade_flows (
    reporter_iso3 NVARCHAR(10), partner_code INT, partner_iso3 NVARCHAR(10), partner_desc NVARCHAR(200),
    [year] INT, hs_code NVARCHAR(10), hs_level INT, value_usd FLOAT, net_weight_kg FLOAT,
    is_world INT, is_special_partner INT, source_name NVARCHAR(50), batch_id NVARCHAR(40), cmd_desc NVARCHAR(400)
);
IF OBJECT_ID(N'silver.stg_commodity_prices', N'U') IS NULL
CREATE TABLE silver.stg_commodity_prices (
    series NVARCHAR(20), price_month DATE, price_usd_bbl FLOAT, source_name NVARCHAR(50), batch_id NVARCHAR(40)
);
IF OBJECT_ID(N'silver.stg_bce_trade_balance', N'U') IS NULL
CREATE TABLE silver.stg_bce_trade_balance (
    [year] INT, oil_exports_fob_usd FLOAT, non_oil_exports_fob_usd FLOAT, source_file NVARCHAR(260), batch_id NVARCHAR(40)
);
GO
/* ------------------------------------------------------------ Datos de referencia (MERGE idempotente) */
MERGE silver.data_sources AS t
USING (VALUES
    (N'world_bank_wdi', N'Banco Mundial — World Development Indicators', N'https://api.worldbank.org/v2', N'API REST v2 (sin llave)', NULL),
    (N'un_comtrade',    N'Naciones Unidas — UN Comtrade',               N'https://comtradeplus.un.org', N'API con llave gratuita (comtradeapicall)', N'Exportaciones FOB declaradas por el reportante'),
    (N'wb_pink_sheet',  N'Banco Mundial — Commodity Price Data (Pink Sheet)', N'https://www.worldbank.org/en/research/commodity-markets', N'Excel mensual', N'Fuente principal del Brent/WTI'),
    (N'fred',           N'Federal Reserve Bank of St. Louis — FRED',    N'https://fred.stlouisfed.org', N'API con llave gratuita', N'Respaldo del precio del crudo'),
    (N'bce_manual',     N'Banco Central del Ecuador',                   N'https://www.bce.fin.ec', N'Descarga manual (CSV)', N'Solo validación cruzada')
) AS s (source_name, provider, url, access_method, notes)
ON t.source_name = s.source_name
WHEN MATCHED THEN UPDATE SET provider = s.provider, url = s.url, access_method = s.access_method, notes = s.notes
WHEN NOT MATCHED THEN INSERT (source_name, provider, url, access_method, notes)
     VALUES (s.source_name, s.provider, s.url, s.access_method, s.notes);
GO
MERGE silver.countries AS t
USING (VALUES
    ('ECU', N'Ecuador', N'Ecuador', 0), ('PER', N'Perú', N'Peru', 0), ('COL', N'Colombia', N'Colombia', 0),
    ('CHL', N'Chile', N'Chile', 0), ('LCN', N'América Latina y el Caribe', N'Latin America & Caribbean', 1)
) AS s (iso3, name_es, name_en, is_aggregate)
ON t.iso3 = s.iso3
WHEN MATCHED THEN UPDATE SET name_es = s.name_es, name_en = s.name_en, is_aggregate = s.is_aggregate
WHEN NOT MATCHED THEN INSERT (iso3, name_es, name_en, is_aggregate) VALUES (s.iso3, s.name_es, s.name_en, s.is_aggregate);
GO
MERGE silver.country_codes_map AS t
USING (VALUES ('ECU','EC',218,N'Ecuador'), ('PER','PE',604,NULL), ('COL','CO',170,NULL),
              ('CHL','CL',152,NULL), ('LCN','ZJ',NULL,NULL)) AS s (iso3, iso2, comtrade_code, bce_name)
ON t.iso3 = s.iso3
WHEN MATCHED THEN UPDATE SET iso2 = s.iso2, comtrade_code = s.comtrade_code, bce_name = s.bce_name
WHEN NOT MATCHED THEN INSERT (iso3, iso2, comtrade_code, bce_name) VALUES (s.iso3, s.iso2, s.comtrade_code, s.bce_name);
GO
MERGE silver.indicators AS t
USING (VALUES
    (N'NY.GDP.MKTP.CD',    N'PIB (USD corrientes)', N'GDP (current US$)', N'USD'),
    (N'NY.GDP.MKTP.KD.ZG', N'Crecimiento del PIB (% anual)', N'GDP growth (annual %)', N'%'),
    (N'NY.GDP.PCAP.CD',    N'PIB per cápita (USD corrientes)', N'GDP per capita (current US$)', N'USD'),
    (N'FP.CPI.TOTL.ZG',    N'Inflación, precios al consumidor (% anual)', N'Inflation, consumer prices (annual %)', N'%'),
    (N'NE.EXP.GNFS.ZS',    N'Exportaciones de bienes y servicios (% del PIB)', N'Exports of goods and services (% of GDP)', N'%'),
    (N'BX.TRF.PWKR.CD.DT', N'Remesas recibidas (USD corrientes)', N'Personal remittances, received (current US$)', N'USD'),
    (N'BX.KLT.DINV.CD.WD', N'IED, entradas netas (USD corrientes)', N'FDI, net inflows (BoP, current US$)', N'USD'),
    (N'SL.UEM.TOTL.ZS',    N'Desempleo (% de la fuerza laboral)', N'Unemployment (% of labor force)', N'%'),
    (N'TX.VAL.FUEL.ZS.UN', N'Combustibles (% de exportaciones de mercancías)', N'Fuel exports (% of merchandise exports)', N'%')
) AS s (indicator_code, name_es, name_en, unit)
ON t.indicator_code = s.indicator_code
WHEN MATCHED THEN UPDATE SET name_es = s.name_es, name_en = s.name_en, unit = s.unit
WHEN NOT MATCHED THEN INSERT (indicator_code, name_es, name_en, unit, source_name)
     VALUES (s.indicator_code, s.name_es, s.name_en, s.unit, N'world_bank_wdi');
GO
MERGE silver.products_hs AS t
USING (VALUES
    (N'TOTAL', 0, N'total',   N'Total exportaciones', N'Total exports', 0),
    (N'27',    2, N'oil',     N'Petróleo y combustibles', N'Oil & fuels', 1),
    (N'26',    2, N'mining',  N'Minerales metalíferos', N'Metal ores', 1),
    (N'0306',  4, N'shrimp',  N'Camarón y crustáceos', N'Shrimp & crustaceans', 1),
    (N'0803',  4, N'banana',  N'Banano', N'Bananas', 1),
    (N'1801',  4, N'cocoa',   N'Cacao en grano', N'Cocoa beans', 1),
    (N'0603',  4, N'flowers', N'Flores', N'Cut flowers', 1),
    (N'1604',  4, N'tuna',    N'Conservas de pescado (atún)', N'Prepared fish (tuna)', 1)
) AS s (hs_code, hs_level, product_group, name_es, name_en, is_key_product)
ON t.hs_code = s.hs_code
WHEN MATCHED THEN UPDATE SET hs_level = s.hs_level, product_group = s.product_group, name_es = s.name_es,
     name_en = s.name_en, is_key_product = s.is_key_product
WHEN NOT MATCHED THEN INSERT (hs_code, hs_level, product_group, name_es, name_en, is_key_product)
     VALUES (s.hs_code, s.hs_level, s.product_group, s.name_es, s.name_en, s.is_key_product);
GO
MERGE silver.economic_events AS t
USING (VALUES
    (N'global_crisis', '2008-07-01', '2009-06-30', N'Crisis financiera global y caída del crudo', N'Global financial crisis and oil price drop'),
    (N'oil_collapse',  '2014-07-01', '2016-02-29', N'Caída prolongada del precio del petróleo', N'Prolonged oil price collapse'),
    (N'covid',         '2020-03-01', '2020-12-31', N'Pandemia de COVID-19 y desplome del crudo', N'COVID-19 pandemic and oil price crash')
) AS s (event_code, start_date, end_date, name_es, name_en)
ON t.event_code = s.event_code
WHEN MATCHED THEN UPDATE SET start_date = s.start_date, end_date = s.end_date, name_es = s.name_es, name_en = s.name_en
WHEN NOT MATCHED THEN INSERT (event_code, start_date, end_date, name_es, name_en)
     VALUES (s.event_code, s.start_date, s.end_date, s.name_es, s.name_en);
GO
/* ------------------------------------------------------------ Procedimientos de upsert */
CREATE OR ALTER PROCEDURE silver.usp_merge_indicator_values
AS
BEGIN
    SET NOCOUNT ON;
    MERGE silver.indicator_values AS t
    USING (SELECT s.* FROM silver.stg_indicator_values s
           JOIN silver.countries c ON c.iso3 = s.country_iso3
           JOIN silver.indicators i ON i.indicator_code = s.indicator_code) AS s
    ON t.country_iso3 = s.country_iso3 AND t.indicator_code = s.indicator_code AND t.[year] = s.[year]
    -- Solo se actualiza si el valor cambió (revisiones del Banco Mundial)
    WHEN MATCHED AND (t.[value] <> s.[value] OR t.is_interpolated <> s.is_interpolated) THEN
        UPDATE SET [value] = s.[value], is_interpolated = s.is_interpolated, obs_status = s.obs_status,
                   batch_id = s.batch_id, updated_at = SYSUTCDATETIME()
    WHEN NOT MATCHED THEN
        INSERT (country_iso3, indicator_code, [year], [value], is_interpolated, obs_status, source_name, batch_id)
        VALUES (s.country_iso3, s.indicator_code, s.[year], s.[value], s.is_interpolated, s.obs_status, s.source_name, s.batch_id);
END
GO
CREATE OR ALTER PROCEDURE silver.usp_merge_trade_flows
AS
BEGIN
    SET NOCOUNT ON;
    -- 1) Capítulos HS2 nuevos (no clave) se agregan al catálogo como 'other'
    MERGE silver.products_hs AS t
    USING (SELECT hs_code, MAX(hs_level) AS hs_level, MAX(cmd_desc) AS cmd_desc
           FROM silver.stg_trade_flows GROUP BY hs_code) AS s
    ON t.hs_code = s.hs_code
    WHEN NOT MATCHED THEN
        INSERT (hs_code, hs_level, product_group, name_es, name_en, is_key_product)
        VALUES (s.hs_code, s.hs_level, N'other', COALESCE(LEFT(s.cmd_desc, 400), s.hs_code),
                COALESCE(LEFT(s.cmd_desc, 400), s.hs_code), 0);
    -- 2) Upsert de flujos
    MERGE silver.trade_flows AS t
    USING (SELECT s.* FROM silver.stg_trade_flows s JOIN silver.countries c ON c.iso3 = s.reporter_iso3) AS s
    ON t.reporter_iso3 = s.reporter_iso3 AND t.partner_code = s.partner_code AND t.[year] = s.[year] AND t.hs_code = s.hs_code
    WHEN MATCHED AND t.value_usd <> CAST(s.value_usd AS DECIMAL(20,2)) THEN
        UPDATE SET value_usd = CAST(s.value_usd AS DECIMAL(20,2)), net_weight_kg = s.net_weight_kg,
                   partner_desc = s.partner_desc, batch_id = s.batch_id, updated_at = SYSUTCDATETIME()
    WHEN NOT MATCHED THEN
        INSERT (reporter_iso3, partner_code, partner_iso3, partner_desc, [year], hs_code, value_usd, net_weight_kg,
                is_world, is_special_partner, source_name, batch_id)
        VALUES (s.reporter_iso3, s.partner_code, s.partner_iso3, s.partner_desc, s.[year], s.hs_code,
                CAST(s.value_usd AS DECIMAL(20,2)), s.net_weight_kg, s.is_world, s.is_special_partner, s.source_name, s.batch_id);
END
GO
CREATE OR ALTER PROCEDURE silver.usp_merge_commodity_prices
AS
BEGIN
    SET NOCOUNT ON;
    MERGE silver.commodity_prices AS t
    USING silver.stg_commodity_prices AS s
    ON t.series = s.series AND t.price_month = s.price_month
    WHEN MATCHED AND t.price_usd_bbl <> CAST(s.price_usd_bbl AS DECIMAL(10,4)) THEN
        UPDATE SET price_usd_bbl = CAST(s.price_usd_bbl AS DECIMAL(10,4)), source_name = s.source_name,
                   batch_id = s.batch_id, updated_at = SYSUTCDATETIME()
    WHEN NOT MATCHED THEN
        INSERT (series, price_month, price_usd_bbl, source_name, batch_id)
        VALUES (s.series, s.price_month, CAST(s.price_usd_bbl AS DECIMAL(10,4)), s.source_name, s.batch_id);
END
GO
CREATE OR ALTER PROCEDURE silver.usp_merge_bce_trade_balance
AS
BEGIN
    SET NOCOUNT ON;
    MERGE silver.bce_trade_balance AS t
    USING silver.stg_bce_trade_balance AS s
    ON t.[year] = s.[year]
    WHEN MATCHED THEN
        UPDATE SET oil_exports_fob_usd = s.oil_exports_fob_usd, non_oil_exports_fob_usd = s.non_oil_exports_fob_usd,
                   source_file = s.source_file, batch_id = s.batch_id, updated_at = SYSUTCDATETIME()
    WHEN NOT MATCHED THEN
        INSERT ([year], oil_exports_fob_usd, non_oil_exports_fob_usd, source_file, batch_id)
        VALUES (s.[year], s.oil_exports_fob_usd, s.non_oil_exports_fob_usd, s.source_file, s.batch_id);
END
GO
CREATE OR ALTER PROCEDURE silver.usp_set_watermark
    @source_name NVARCHAR(50), @scope_key NVARCHAR(50), @watermark_value NVARCHAR(50)
AS
BEGIN
    SET NOCOUNT ON;
    MERGE silver.etl_watermarks AS t
    USING (SELECT @source_name AS source_name, @scope_key AS scope_key, @watermark_value AS watermark_value) AS s
    ON t.source_name = s.source_name AND t.scope_key = s.scope_key
    WHEN MATCHED THEN UPDATE SET watermark_value = s.watermark_value, updated_at = SYSUTCDATETIME()
    WHEN NOT MATCHED THEN INSERT (source_name, scope_key, watermark_value) VALUES (s.source_name, s.scope_key, s.watermark_value);
END
GO
