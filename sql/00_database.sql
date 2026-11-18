/* =====================================================================
   00_database.sql — Crea la base EcuadorMonitor y los esquemas Medallion.
   Idempotente: se puede ejecutar varias veces sin borrar nada.
   Ejecutar con: sqlcmd -S localhost -E -C -i sql/00_database.sql
   ===================================================================== */
IF DB_ID(N'EcuadorMonitor') IS NULL
BEGIN
    CREATE DATABASE EcuadorMonitor;
END
GO
USE EcuadorMonitor;
GO
IF SCHEMA_ID(N'bronze') IS NULL EXEC (N'CREATE SCHEMA bronze AUTHORIZATION dbo;');
GO
IF SCHEMA_ID(N'silver') IS NULL EXEC (N'CREATE SCHEMA silver AUTHORIZATION dbo;');
GO
IF SCHEMA_ID(N'gold') IS NULL EXEC (N'CREATE SCHEMA gold AUTHORIZATION dbo;');
GO
