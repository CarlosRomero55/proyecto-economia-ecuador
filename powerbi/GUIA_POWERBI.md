# Guía de Power BI — página por página

El informe replica las 6 páginas de la app de Streamlit, pero conectado directo a SQL Server (lo que piden
bancos y empresas locales). Tiempo estimado: 2–3 horas. Antes, carga el modelo siguiendo `model.md`.

**Reglas de diseño (las mismas de la app):**
- El **título dice la conclusión**, no el nombre del gráfico ("El camarón superó al petróleo en 20XX", no "Exportaciones por producto").
  Usa medidas de título dinámico (ejemplo: `Título peso petróleo` en `model.md`).
- **Nunca doble eje.** Dos medidas con escalas distintas van en dos visuales alineados.
- Colores por entidad, siempre los mismos: importa `theme.json` (*Vista → Temas → Buscar temas*). Petróleo azul,
  camarón naranja, banano aqua, cacao amarillo, minería magenta, flores verde, atún violeta, resto gris.
- Segmentadores en una fila arriba; pie de página con fuentes y la medida `Última actualización`.

## Página 1 · Resumen
| Visual | Configuración |
|---|---|
| 4 tarjetas | `Exportaciones USD`, `Peso petróleo %`, `HHI producto`, `vw_oil_sensitivity[elasticity_beta]` (filtro target = oil_exports) |
| Segmentador | `dim_date[year]` (selección única, por defecto último año) |
| Cuadro de texto | Pregunta gancho y hallazgo principal (copiar de `docs/insights.md`) |
| Tarjeta pequeña | `Última actualización` |

Filtro de página: `dim_country[iso3] = ECU`.

## Página 2 · Canasta exportadora
| Visual | Configuración |
|---|---|
| Gráfico de áreas apiladas | Eje X `dim_date[year]`, valores `Valor producto USD`, leyenda `dim_product[product_group]` |
| Barras horizontales | Eje `dim_product[name_es]`, valor `Valor producto USD`, etiquetas `Participación %`, ordenar desc |
| Segmentadores | País (`dim_country[name_es]`), Año (para el ranking; editar interacciones para que no filtre el área) |
| Tabla | Producto, `Valor producto USD`, `Participación %`, `Ranking producto`, `CAGR %` |

## Página 3 · Dependencia del petróleo
| Visual | Configuración |
|---|---|
| Líneas (arriba) | `Exportaciones petroleras USD` por año, Ecuador |
| Líneas (abajo, mismo ancho) | `Brent promedio` por año |
| Líneas | `Peso petróleo %` por año con leyenda país (ECU, PER, COL, CHL) |
| Bandas de eventos | Línea constante/sombreado manual o anotaciones de texto en 2008–09, 2014–16 y 2020 (tabla `vw_economic_events`) |
| Tarjeta | Elasticidad y R² de `vw_oil_sensitivity` |

## Página 4 · Ecuador vs la región
| Visual | Configuración |
|---|---|
| Segmentadores | Indicador (`dim_indicator[name_es]`, selección única) y país (multi) |
| Líneas | `Valor indicador` por año, leyenda país; LCN con línea punteada (formato por serie) |
| Líneas | `vw_diversification[hhi_product]` por año y país |
| Barras | Último año: `Valor indicador` por país, ordenado desc (título: "Ecuador ocupa el puesto X") |

## Página 5 · Proyección y metodología
| Visual | Configuración |
|---|---|
| Líneas con pronóstico | `Exportaciones no petroleras USD` por año, Ecuador → panel *Análisis → Previsión* (5 años, IC 80 %) |
| Cuadro de texto | Supuestos y limitaciones (copiar de la página 5 de la app / `docs/methodology.md`) |

Nota: el pronóstico nativo de Power BI usa suavizado exponencial; la app usa tendencia + AR(1). Explica la diferencia si te preguntan.

## Página 6 · Calidad y pipeline
| Visual | Configuración |
|---|---|
| Imagen | Diagrama de arquitectura (exportar el Mermaid del README como PNG) |
| Tabla | `vw_pipeline_runs`: run_id, batch_id, status, duration_seconds, filas por capa |
| Tabla | `gold.vw_cleaning_rules` (importar la vista) del último lote |
| Barras | `gold.vw_layer_counts` sumado por `layer` |

## Publicación
- Guarda como **.pbip** dentro de `powerbi/` y haz commit (el `.gitignore` ya excluye `.pbix` y la caché).
- Para mostrarlo en LinkedIn/portafolio: exporta a PDF o graba un GIF corto; "Publicar en la web" expone los datos
  públicamente (aquí son datos públicos, así que es aceptable si lo deseas).
