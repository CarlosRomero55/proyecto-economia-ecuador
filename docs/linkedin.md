# Publicación para LinkedIn

> Reemplaza los `[corchetes]` con las cifras de `docs/insights.md` (generadas desde los datos) antes de publicar.

## Español
¿Ecuador diversificó de verdad sus exportaciones… o solo cambió el petróleo por el camarón? 🦐🛢️

Construí **Ecuador Trade & Economy Monitor**, un proyecto de datos de punta a punta con fuentes públicas
(Banco Mundial, UN Comtrade y el Pink Sheet del Banco Mundial), de 2000 a la fecha:

🔹 El petróleo pasó de [X %] a [Y %] de las exportaciones.
🔹 El índice de concentración (HHI) pasó de [A] a [B]: la canasta se comporta como si tuviera [N] productos del mismo tamaño.
🔹 Elasticidad de las exportaciones petroleras al Brent: [β] (asociación, no causalidad).

Cómo está hecho:
⚙️ Pipeline en Python (APIs con reintentos, caché y carga incremental con watermarks)
🗄️ SQL Server con arquitectura Medallion (bronze → silver 3FN → gold en estrella) y MERGE idempotente
✅ Pruebas de calidad con pytest y reconciliación Python vs SQL
🌐 API con FastAPI, app pública en Streamlit (ES/EN) y dashboard en Power BI
📝 Decisiones documentadas como ADRs

👉 App: [enlace]  · Código: [enlace al repo]

¿Qué otra pregunta sobre la economía ecuatoriana te gustaría ver respondida con datos?

#DataAnalytics #DataEngineering #SQLServer #PowerBI #Python #Streamlit #Ecuador #ComercioExterior

## English
Did Ecuador truly diversify its exports… or did it just swap oil for shrimp? 🦐🛢️

I built **Ecuador Trade & Economy Monitor**, an end-to-end data project on public sources (World Bank, UN Comtrade,
World Bank Pink Sheet), 2000 to date:

🔹 Oil went from [X%] to [Y%] of exports.
🔹 The concentration index (HHI) went from [A] to [B]: the basket behaves as if it had [N] equally sized products.
🔹 Elasticity of oil exports to Brent: [β] (association, not causation).

How it's built:
⚙️ Python pipeline (APIs with retries, caching and watermark-based incremental loads)
🗄️ SQL Server Medallion architecture (bronze → 3NF silver → star-schema gold) with idempotent MERGE
✅ Data-quality tests with pytest and Python-vs-SQL reconciliation
🌐 FastAPI service, public bilingual Streamlit app and a Power BI dashboard
📝 Decisions documented as ADRs

👉 App: [link] · Code: [repo link]

#DataAnalytics #DataEngineering #SQLServer #PowerBI #Python #Streamlit #LatAm
