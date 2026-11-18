# Guía de estudio — para explicar el proyecto en una entrevista

Cada componente tiene la misma estructura: **qué es · por qué se usó · alternativas · cómo funciona · cómo
verificarlo · 3 preguntas de entrevista con respuesta modelo.** Al final hay una tabla comparativa de arquitecturas.

---

## 1. Extracción desde APIs (Banco Mundial, Comtrade, Pink Sheet/FRED)
- **Qué es:** módulos `src/extract_*.py` que descargan datos públicos y los dejan en bronze con linaje.
- **Por qué:** datos oficiales y reproducibles; nada se copia a mano.
- **Alternativas:** descargar CSV manualmente (no reproducible); librerías envoltorio como `wbgapi` (otra dependencia, menos control de paginación).
- **Cómo funciona:** `http_utils.get` hace GET con reintentos y backoff exponencial ante 429/5xx, y guarda cada respuesta en `data/raw` (caché). El Banco Mundial pagina con `page`/`pages`; Comtrade se llama por país-año con pausas por la cuota; el Pink Sheet se lee buscando dinámicamente las columnas `CRUDE_BRENT`/`CRUDE_WTI`.
- **Cómo verificarlo:** `pytest tests/test_extract_parsers.py`; revisar `logs/pipeline.log`; `SELECT batch_id, COUNT(*) FROM bronze.wb_indicator_raw GROUP BY batch_id`.
- **Preguntas:**
  1. *¿Qué pasa si la API falla a mitad de la carga?* → Reintenta con espera creciente; si no se recupera, el lote queda `failed` en `etl_runs`. Lo descargado está en caché, así que el reintento no repite llamadas.
  2. *¿Por qué guardas el JSON crudo?* → Auditoría y reproceso: puedo reconstruir bronze sin gastar cuota, y si cambio una regla de limpieza no vuelvo a llamar a la API.
  3. *¿Cómo manejas las llaves?* → En `.env` (ignorado por git), leídas con `python-dotenv`; nunca se registran en logs ni se suben al repo. `.env.example` documenta qué variables existen.

## 2. Arquitectura Medallion (bronze / silver / gold)
- **Qué es:** tres capas de calidad creciente en la misma base SQL Server.
- **Por qué:** separar "lo que llegó" de "lo que es correcto" y de "lo que usa el negocio".
- **Alternativas:** base única; Inmon (data warehouse corporativo normalizado); Lakehouse.
- **Cómo funciona:** bronze es solo-append con `batch_id`; silver aplica tipos, claves y reglas; gold expone estrella + vistas.
- **Cómo verificarlo:** `SELECT * FROM gold.vw_layer_counts`; página *Calidad* de la app.
- **Preguntas:**
  1. *¿Por qué no limpiar directo al cargar?* → Si una regla estaba mal, sin bronze tendría que volver a descargar todo; con bronze reproceso en minutos.
  2. *¿Quién puede leer cada capa?* → Consumidores (Power BI, API, app) solo gold; ingeniería, bronze y silver. En producción se haría con roles por esquema.
  3. *¿Bronze no crece sin control?* → Sí crece por lote; se puede particionar por fecha o aplicar retención (p. ej. 12 lotes), porque silver ya tiene la versión vigente.

## 3. Silver en 3FN con MERGE
- **Qué es:** modelo normalizado con PK, FK, CHECK; los datos limpios entran por tablas `stg_*` y procedimientos `usp_merge_*`.
- **Por qué:** integridad (no puede existir un flujo de un país inexistente) e idempotencia.
- **Alternativas:** `TRUNCATE + INSERT` (pierde historia de `updated_at`, ventana sin datos); `DELETE + INSERT` por año.
- **Cómo funciona:** `MERGE ... WHEN MATCHED AND valor distinto THEN UPDATE ... WHEN NOT MATCHED THEN INSERT`.
- **Cómo verificarlo:** correr el pipeline dos veces y comparar conteos (`docs/automatizacion.md`).
- **Preguntas:**
  1. *¿Qué es idempotencia?* → Ejecutar N veces produce el mismo estado que ejecutar una vez. Aquí: MERGE por clave natural.
  2. *¿Riesgos de MERGE en SQL Server?* → Condiciones de carrera bajo concurrencia alta (se mitiga con `HOLDLOCK` o con una sola ejecución a la vez) y error si el origen trae claves duplicadas; por eso se deduplica antes (regla CT07/WB03).
  3. *¿Por qué una tabla de staging?* → Para cargar rápido con `fast_executemany` y que el MERGE sea una sola operación de conjunto en el servidor.

## 4. Gold en esquema estrella (Kimball)
- **Qué es:** dimensiones (`dim_date`, `dim_country`, `dim_product`, `dim_indicator`) y hechos (`fact_trade`, `fact_indicator`, `fact_oil_price`).
- **Por qué:** es el modelo que Power BI optimiza (VertiPaq) y que cualquier analista entiende.
- **Alternativas:** tabla plana única (rápida pero redundante); copo de nieve (más uniones).
- **Cómo funciona:** `gold.usp_build_gold` hace MERGE de dimensiones y luego de hechos con llaves sustitutas.
- **Cómo verificarlo:** relaciones 1:* en Power BI sin advertencias; validación "hechos sin dimensión" = 0.
- **Preguntas:**
  1. *¿Qué es el grano de una tabla de hechos?* → Lo que representa una fila: en `fact_trade`, país × producto × socio × año.
  2. *¿Por qué llaves sustitutas?* → Desacoplan gold de códigos externos que pueden cambiar y permiten SCD tipo 2 si hiciera falta.
  3. *¿Dónde pusiste la lógica de KPIs?* → En vistas SQL (una sola definición), y las medidas DAX replican solo lo necesario para filtrar interactivamente; se reconcilian.

## 5. Carga incremental con watermarks
- **Qué es:** `silver.etl_watermarks` guarda el último período cargado por fuente y alcance.
- **Por qué:** cuota de Comtrade y tiempo de ejecución.
- **Alternativas:** recarga total; CDC; fechas de modificación de la fuente (no disponibles).
- **Cómo funciona:** incremental pide desde watermark − 1 (Comtrade) o − 2 (Banco Mundial) para captar revisiones.
- **Cómo verificarlo:** `SELECT * FROM silver.etl_watermarks`; comparar duración en `vw_pipeline_runs` entre full e incremental.
- **Preguntas:**
  1. *¿Por qué no pedir solo años nuevos?* → Las fuentes revisan años recientes; sin solapamiento me quedaría con cifras viejas.
  2. *¿Qué pasa si la ejecución falla después de avanzar el watermark?* → El watermark se actualiza después de cargar silver con el máximo período realmente presente, no el solicitado.
  3. *¿Diferencia entre watermark y CDC?* → El watermark es una marca de "hasta dónde llegué" calculada por mí; CDC captura cada cambio en el origen (requiere soporte de la fuente).

## 6. Limpieza y armonización
- **Qué es:** `src/clean.py` y `src/harmonize.py`, reglas identificadas (WB01…, CT01…, OIL01…) con filas afectadas.
- **Por qué:** cada fuente usa códigos, tipos y desgloses distintos.
- **Alternativas:** limpiar en SQL (posible, pero menos fácil de probar unitariamente).
- **Cómo funciona:** funciones puras DataFrame → DataFrame; `CleaningLog` registra cada regla en `silver.cleaning_log`.
- **Cómo verificarlo:** `pytest tests/test_clean.py`; `docs/data_quality_report.md`.
- **Preguntas:**
  1. *¿Interpolaste datos?* → Solo huecos interiores de 1 año, marcados con `is_interpolated` y mostrados con marcador hueco; nunca extremos ni huecos largos.
  2. *¿Cómo evitaste el doble conteo?* → El HHI usa solo capítulos HS2 (partición completa) y la canasta calcula "Resto" = total − productos clave.
  3. *¿Qué hiciste con "Áreas n.e.s." de Comtrade?* → Se marcan como socios especiales y se excluyen del HHI de destinos, pero se conservan en la base.

## 7. Calidad de datos y pruebas
- **Qué es:** pytest con pruebas unitarias (fórmulas, reglas, parsers), de integración (API, app) y de base (`test_quality_db.py`).
- **Por qué:** un número equivocado en un dashboard destruye la confianza.
- **Alternativas:** Great Expectations, dbt tests, Soda.
- **Cómo funciona:** `validate.CHECKS` define consultas que cuentan violaciones; las críticas detienen el pipeline.
- **Cómo verificarlo:** `pytest -q`; antes de cada commit.
- **Preguntas:**
  1. *¿Qué validas?* → Unicidad, FK, rangos, suma de participaciones = 1, cobertura de años, TOTAL vs Σ capítulos y reconciliación Python vs SQL.
  2. *¿Por qué reconciliar Python vs SQL?* → Dos implementaciones independientes del HHI que coinciden dan confianza en ambas.
  3. *¿Cómo pruebas la app sin base?* → Con un snapshot sintético generado en las pruebas (nunca en `app/data`) y `streamlit.testing.v1.AppTest`.

## 8. Indicadores: HHI, CAGR, elasticidad
- **Qué es:** las métricas que responden la pregunta gancho.
- **Por qué:** el % petrolero solo dice cuánto pesa el crudo; el HHI dice si la canasta se diversificó o solo cambió de líder.
- **Alternativas:** índice de Theil, Gini de exportaciones, número de productos con ventaja comparativa revelada (VCR).
- **Cómo funciona:** HHI = Σ(participación·100)²; CAGR = (final/inicial)^(1/n) − 1; β = cov(ln P, ln X)/var(ln P).
- **Cómo verificarlo:** `tests/test_indicators.py` con casos conocidos (monopolio = 10 000; 4 iguales = 2 500).
- **Preguntas:**
  1. *¿Cómo explicas el HHI a un gerente?* → "La canasta se comporta como si tuviera N productos del mismo tamaño" (N = 10 000/HHI).
  2. *¿Una caída del % petrolero prueba diversificación?* → No: puede ser efecto precio o sustitución por otro producto dominante; por eso se mira el HHI.
  3. *¿Qué significa una elasticidad de 1,2?* → Si el Brent sube 10 %, las exportaciones petroleras tienden a subir ~12 % ese año; es asociación, no causalidad.

## 9. Econometría y proyección
- **Qué es:** `notebooks/02_econometrics.ipynb` (MCO con errores robustos, diagnóstico de residuos, SARIMAX).
- **Por qué:** cuantificar sensibilidad y dar un rango de escenarios, no un número mágico.
- **Alternativas:** Prophet, suavizado exponencial (lo usa Power BI), modelos con variables exógenas (VAR, ARIMAX con Brent).
- **Cómo funciona:** logaritmos para interpretar elasticidades; intervalo de 80 %.
- **Cómo verificarlo:** Durbin-Watson, QQ-plot; comparar SARIMAX con la versión ligera de la app.
- **Preguntas:**
  1. *¿Por qué logaritmos?* → Estabilizan la varianza y el coeficiente se lee como elasticidad.
  2. *¿Limitaciones con ~25 datos anuales?* → Poca potencia, intervalos amplios, riesgo de sobreajuste: modelos simples.
  3. *¿Por qué no Prophet?* → Está pensado para series con estacionalidad y muchos puntos; con datos anuales cortos no aporta y agrega dependencias pesadas.

## 10. API con FastAPI
- **Qué es:** `api/main.py`, seis endpoints sobre gold.
- **Por qué:** desacoplar consumidores de la base.
- **Alternativas:** Flask, Django REST, Data API Builder.
- **Cómo funciona:** pandas + vistas gold; backend `sql` o `parquet`; OpenAPI en `/docs`.
- **Cómo verificarlo:** `uvicorn api.main:app` y abrir `/docs`; `pytest tests/test_api.py`.
- **Preguntas:**
  1. *¿Cómo evitas inyección SQL?* → Solo se leen vistas fijas; los filtros se aplican con parámetros validados (ISO3 de 3 letras) y nunca se concatena texto del usuario en SQL.
  2. *¿Cómo la llevarías a producción?* → Contenedor, autenticación (API key/OAuth), caché, paginación y monitoreo.
  3. *¿Por qué no consultar SQL desde la app pública?* → La nube no alcanza el servidor local y exponer la base es un riesgo.

## 11. Snapshot Parquet + Streamlit
- **Qué es:** export de vistas gold a Parquet versionado; app multipágina bilingüe en Streamlit Cloud.
- **Por qué:** demo pública gratuita que un reclutador abre en el celular.
- **Alternativas:** Dash, Power BI Publish to web, Evidence.dev.
- **Cómo funciona:** `src/export_snapshot.py` → `app/data`; `st.cache_data` lee los Parquet; `app/requirements.txt` liviano.
- **Cómo verificarlo:** `streamlit run app/streamlit_app.py`; `pytest tests/test_app.py`.
- **Preguntas:**
  1. *¿Por qué Parquet y no CSV?* → Columnar, comprimido (zstd), con tipos; más rápido y liviano.
  2. *¿Cómo se actualiza la demo?* → Pipeline → commit del snapshot → Streamlit redespliega.
  3. *¿Cómo garantizas que la app y los insights digan lo mismo?* → Ambos usan `app/analytics.py` sobre el mismo snapshot.

## 12. Power BI y DAX
- **Qué es:** informe conectado a gold, medidas documentadas en `powerbi/model.md`, guardado como PBIP.
- **Por qué:** es la herramienta más pedida en Ecuador para BI.
- **Alternativas:** Tableau, Looker Studio, Qlik.
- **Cómo funciona:** modo Import, estrella, medidas con `CALCULATE`, `DATEADD`, `RANKX`, `SUMX`.
- **Cómo verificarlo:** reconciliar `[HHI producto]` y `[Peso petróleo %]` con las vistas SQL.
- **Preguntas:**
  1. *¿Diferencia entre columna calculada y medida?* → La columna se calcula al refrescar y ocupa memoria por fila; la medida se evalúa en el contexto de filtro de cada visual.
  2. *¿Qué hace CALCULATE?* → Evalúa una expresión modificando el contexto de filtro; es la función central de DAX.
  3. *¿Import o DirectQuery?* → Import: datos pequeños y anuales, máximo rendimiento; DirectQuery solo si hiciera falta tiempo real.

## 13. Orquestación y automatización
- **Qué es:** `src/pipeline.py` (`--full`/`--incremental`), `run_scheduled.bat` y tarea programada de Windows.
- **Por qué:** que el proyecto se actualice solo y deje rastro (`etl_runs`).
- **Alternativas:** Airflow, Prefect, Dagster, Azure Data Factory, SQL Server Agent.
- **Cómo funciona:** pasos secuenciales con registro de estado, validaciones críticas que detienen la ejecución y código de salida ≠ 0 si falla.
- **Cómo verificarlo:** `schtasks /Run ...` y revisar `logs/` y `vw_pipeline_runs`.
- **Preguntas:**
  1. *¿Cuándo usarías Airflow?* → Con muchas dependencias entre tareas, reintentos por tarea, backfills y equipos; aquí sería sobreingeniería.
  2. *¿Cómo te enteras de una falla?* → `etl_runs.status = 'failed'` con mensaje; se podría agregar un correo o un webhook de Teams.
  3. *¿Qué harías para correrlo en la nube?* → Contenedor en Azure Container Apps Jobs o un pipeline de Fabric, con Azure SQL.

## 14. Git, Conventional Commits y ADRs
- **Qué es:** historial pequeño y descriptivo; decisiones registradas en `docs/adr/`.
- **Por qué:** un reclutador técnico lee el historial y los ADR para entender cómo piensas.
- **Alternativas:** un único commit (no muestra proceso); wiki externa.
- **Cómo funciona:** `tipo(alcance): descripción` en presente; pruebas en verde antes de cada commit; ramas por fase.
- **Cómo verificarlo:** `git log --oneline`.
- **Preguntas:**
  1. *¿Qué es un ADR?* → Un documento corto: contexto, decisión, alternativas y consecuencias.
  2. *¿Por qué ramas y no todo en main?* → Revisión por pull request, historia limpia y posibilidad de revertir una fase.
  3. *¿Qué no subes al repo?* → `.env`, datos crudos, logs y binarios (`.pbix`).

---

## Tabla comparativa de arquitecturas

| Enfoque | Qué es | Ventajas | Desventajas | ¿Por qué no (o sí) aquí? |
|---|---|---|---|---|
| **Este proyecto** (Medallion en SQL Server + estrella) | Capas bronze/silver/gold en una base relacional | Linaje, reproceso, integridad, Power BI nativo, barato | Escala vertical; ETL en Python local | Ajusta al volumen (miles de filas) y al mercado local |
| **Base única** | Cargar y consultar todo en las mismas tablas | Simple, rápido de empezar | Sin linaje; errores se propagan; reproceso implica re-descargar | Demasiado frágil para mostrar en un portafolio |
| **Inmon** | DW corporativo normalizado (3FN) y data marts derivados | Integración empresarial, una versión de la verdad | Lento de construir, consultas BI complejas | Silver sigue esta idea; gold añade Kimball para consumo |
| **Kimball** | Data marts dimensionales (estrella) por proceso de negocio | Rápido para BI, fácil de entender | Integración entre marts requiere dimensiones conformadas | Usado en gold |
| **Lakehouse** (Fabric, Databricks) | Archivos Delta/Parquet en un lago con capas Medallion y motor SQL/Spark | Escala horizontal, datos semi-estructurados, ML | Costo, curva de aprendizaje | **Migración:** bronze → tablas Delta con los JSON crudos; silver/gold → notebooks Spark o dataflows con la misma lógica; vistas → SQL endpoint; Power BI en Direct Lake. Los scripts ya separan capas, así que el cambio es de motor, no de diseño |
| **Lambda** | Capa batch + capa de velocidad (streaming) + capa de servicio | Datos en tiempo real y precisión histórica | Dos bases de código | Los datos son anuales/mensuales: no hay tiempo real |
| **Kappa** | Todo como streaming (reprocesar = re-leer el log) | Un solo código | Requiere Kafka/Event Hubs | Mismo motivo: sin eventos en tiempo real |
| **ETL** | Transformar antes de cargar al destino | Destino limpio, menos cómputo en el DW | Menos flexible para re-transformar | Se usa en la limpieza (Python) |
| **ELT** | Cargar crudo y transformar dentro del motor (dbt, SQL) | Aprovecha el motor, reproceso fácil | Necesita motor potente | Se usa entre silver y gold (SQL); el diseño es híbrido |
| **Power BI** | BI empresarial de Microsoft | Estándar local, DAX, seguridad por filas | Licencias para compartir, Windows para Desktop | Para entrevistas en banca y empresas locales |
| **Streamlit** | Apps de datos en Python | Gratis, público, control total, muestra código | Menos funciones de autoservicio | Demo pública para reclutadores |
| **Tableau** | BI visual de Salesforce | Visualización muy flexible | Costo, menos presente en Ecuador | No se usó; los conceptos (medidas, dimensiones) se transfieren |
