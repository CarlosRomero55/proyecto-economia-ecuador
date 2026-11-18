/* =====================================================================
   01_bronze.sql — Capa bronze: datos crudos tal como llegan de cada fuente.
   Regla: solo INSERT (append). Nunca se actualiza ni se borra.
   Cada fila lleva linaje: source_name, extracted_at (UTC) y batch_id.
   ===================================================================== */
USE EcuadorMonitor;
GO
IF OBJECT_ID(N'bronze.wb_indicator_raw', N'U') IS NULL
CREATE TABLE bronze.wb_indicator_raw (
    bronze_id       BIGINT IDENTITY(1,1) CONSTRAINT pk_wb_indicator_raw PRIMARY KEY,
    indicator_code  NVARCHAR(50)  NULL,
    indicator_name  NVARCHAR(300) NULL,
    country_iso2    NVARCHAR(10)  NULL,
    country_iso3    NVARCHAR(10)  NULL,
    country_name    NVARCHAR(200) NULL,
    [year]          NVARCHAR(10)  NULL,   -- texto, tal como lo entrega la API
    [value]         FLOAT         NULL,
    obs_status      NVARCHAR(50)  NULL,
    source_name     NVARCHAR(50)  NOT NULL,
    extracted_at    DATETIME2(0)  NOT NULL,
    batch_id        NVARCHAR(40)  NOT NULL
);
GO
IF OBJECT_ID(N'bronze.comtrade_raw', N'U') IS NULL
CREATE TABLE bronze.comtrade_raw (
    bronze_id       BIGINT IDENTITY(1,1) CONSTRAINT pk_comtrade_raw PRIMARY KEY,
    ref_year        INT            NULL,
    reporter_code   INT            NULL,
    reporter_iso    NVARCHAR(10)   NULL,
    flow_code       NVARCHAR(5)    NULL,
    partner_code    INT            NULL,
    partner_iso     NVARCHAR(10)   NULL,
    partner_desc    NVARCHAR(200)  NULL,
    partner2_code   INT            NULL,
    mot_code        INT            NULL,
    customs_code    NVARCHAR(10)   NULL,
    cmd_code        NVARCHAR(20)   NULL,
    cmd_desc        NVARCHAR(400)  NULL,
    aggr_level      INT            NULL,
    primary_value   FLOAT          NULL,
    fob_value       FLOAT          NULL,
    net_wgt         FLOAT          NULL,
    is_aggregate    NVARCHAR(10)   NULL,
    query_name      NVARCHAR(40)   NULL,
    source_name     NVARCHAR(50)   NOT NULL,
    extracted_at    DATETIME2(0)   NOT NULL,
    batch_id        NVARCHAR(40)   NOT NULL
);
GO
IF OBJECT_ID(N'bronze.oil_price_raw', N'U') IS NULL
CREATE TABLE bronze.oil_price_raw (
    bronze_id       BIGINT IDENTITY(1,1) CONSTRAINT pk_oil_price_raw PRIMARY KEY,
    [period]        NVARCHAR(10)  NULL,   -- AAAA-MM
    series          NVARCHAR(20)  NULL,   -- brent | wti
    value_raw       NVARCHAR(50)  NULL,   -- texto: puede venir '.', '…'
    source_name     NVARCHAR(50)  NOT NULL,
    extracted_at    DATETIME2(0)  NOT NULL,
    batch_id        NVARCHAR(40)  NOT NULL
);
GO
IF OBJECT_ID(N'bronze.bce_trade_raw', N'U') IS NULL
CREATE TABLE bronze.bce_trade_raw (
    bronze_id                BIGINT IDENTITY(1,1) CONSTRAINT pk_bce_trade_raw PRIMARY KEY,
    [year]                   INT           NULL,
    oil_exports_fob_usd      FLOAT         NULL,
    non_oil_exports_fob_usd  FLOAT         NULL,
    source_file              NVARCHAR(260) NULL,
    source_name              NVARCHAR(50)  NOT NULL,
    extracted_at             DATETIME2(0)  NOT NULL,
    batch_id                 NVARCHAR(40)  NOT NULL
);
GO
-- Índices por lote: el pipeline lee siempre "el último batch" de cada fuente
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'ix_wb_raw_batch')
    CREATE INDEX ix_wb_raw_batch ON bronze.wb_indicator_raw(batch_id);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'ix_comtrade_raw_batch')
    CREATE INDEX ix_comtrade_raw_batch ON bronze.comtrade_raw(batch_id);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'ix_oil_raw_batch')
    CREATE INDEX ix_oil_raw_batch ON bronze.oil_price_raw(batch_id);
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'ix_bce_raw_batch')
    CREATE INDEX ix_bce_raw_batch ON bronze.bce_trade_raw(batch_id);
GO
