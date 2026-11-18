# Metodología

## Problemas de datos y cómo se resolvieron
| Problema | Regla | Detalle |
|---|---|---|
| Nulos y años faltantes | WB04, WB05 | Los nulos se eliminan (formato largo). Solo se interpolan huecos **interiores de 1 año**, con `is_interpolated = 1`, y se muestran con marcador hueco. Huecos mayores o en los extremos quedan vacíos. |
| Códigos de país distintos | CT03, `country_codes_map` | Banco Mundial: ISO2/ISO3; Comtrade: M49 numérico; BCE: nombre. Todo se resuelve a ISO3. |
| Agregados mezclados con países | `is_aggregate`, CT06 | LCN se marca como agregado y no entra en rankings de países. En Comtrade, Mundo (0) y áreas "n.e.s.", zonas francas y bunkers se marcan y quedan fuera del HHI de destinos. |
| USD corrientes vs constantes | — | Comercio en USD corrientes (FOB). Las comparaciones entre países usan participaciones, HHI e índices (sin unidades). El crecimiento del PIB es real (NY.GDP.MKTP.KD.ZG). |
| Mensual vs anual | OIL, `vw_oil_price_annual` | Brent mensual → promedio anual. La elasticidad solo usa años con 12 meses. |
| Revisiones de cifras | Watermark − 1/−2 + MERGE | Se vuelven a pedir los últimos años; MERGE actualiza solo si el valor cambió. |
| Doble conteo HS2 vs HS4 | `vw_export_basket` | La canasta usa total − Σ productos clave para "Resto"; el HHI usa solo capítulos HS2 (partición completa). |
| Desgloses de Comtrade | CT02 | Solo totales: `partner2_code = 0`, `mot_code = 0`, `customs_code = C00`. |

## Indicadores
Ver fórmulas en `docs/plan.md`. El HHI se reporta en escala 0–10 000 junto con su número equivalente (10 000/HHI),
que es más fácil de comunicar ("la canasta se comporta como si tuviera N productos del mismo tamaño").

## Econometría
- Elasticidad: MCO log-log anual (en SQL y en el notebook con errores robustos HC1).
- Proyección: SARIMAX(1,0,0) con tendencia sobre el logaritmo de exportaciones no petroleras (notebook); la app usa una
  versión ligera equivalente (tendencia log-lineal + AR(1)) para no instalar statsmodels en la nube.
- Correlación no es causalidad: los resultados son asociaciones descriptivas.

## Limitaciones
- Comtrade publica con rezago y algunos países reportan tarde; el último año puede faltar para algunos pares.
- El crudo ecuatoriano cotiza con descuento frente al Brent.
- Las exportaciones declaradas por el reportante pueden diferir de las importaciones espejo de los socios.
- No se evalúan políticas ni gobiernos; el análisis es descriptivo y neutral.
