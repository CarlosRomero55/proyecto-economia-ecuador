"""Genera notebooks/01_eda.ipynb y 02_econometrics.ipynb (fuente única y versionable).

Las conclusiones se imprimen desde los datos (f-strings), así no hay cifras escritas a mano.
Ejecutar después del pipeline:
    jupyter nbconvert --to notebook --execute --inplace notebooks/01_eda.ipynb notebooks/02_econometrics.ipynb
"""
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell

SETUP = '''import os, sys, json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
DATA = Path(os.getenv("APP_DATA_DIR", ROOT / "app" / "data"))   # snapshot gold exportado por el pipeline
data = {p.stem: pd.read_parquet(p) for p in DATA.glob("*.parquet")}
meta = json.loads((DATA / "metadata.json").read_text(encoding="utf-8")) if (DATA / "metadata.json").exists() else {}
print("Snapshot exportado:", meta.get("exported_at_utc"), "| tablas:", len(data))

COLORS = {"ECU": "#2a78d6", "PER": "#eb6834", "COL": "#1baf7a", "CHL": "#eda100", "LCN": "#8a8984"}
PCOLORS = {"oil": "#2a78d6", "shrimp": "#eb6834", "banana": "#1baf7a", "cocoa": "#eda100", "mining": "#e87ba4",
           "flowers": "#008300", "tuna": "#6250d6", "other": "#a3a29c"}
plt.rcParams.update({"figure.figsize": (10, 4.5), "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": 0.3, "font.size": 11})
def shade_events(ax):
    for e in data["economic_events"].itertuples():
        ax.axvspan(pd.Timestamp(e.start_date).year - 0.5, pd.Timestamp(e.end_date).year + 0.5, color="grey", alpha=0.12)
dep, basket, div = data["oil_dependency"], data["export_basket"], data["diversification"]
ecu = dep[dep.iso3 == "ECU"].sort_values("year")
y0, y1 = int(ecu.year.min()), int(ecu.year.max())'''

eda = nbf.v4.new_notebook()
eda.cells = [
    md("# 01 · Análisis exploratorio — Ecuador Trade & Economy Monitor\n\n"
       "**Pregunta gancho:** en los últimos 20 años, ¿Ecuador diversificó de verdad su canasta exportadora o solo cambió "
       "el petróleo por el camarón? ¿Cómo se compara con Perú, Colombia y Chile?\n\n"
       "Fuente de datos: snapshot de la capa **gold** (`app/data/*.parquet`), generado por `src/pipeline.py`. "
       "Cada gráfico termina con una conclusión calculada desde los datos."),
    code(SETUP),
    md("## 1. Exportaciones totales de Ecuador"),
    code('''fig, ax = plt.subplots()
ax.plot(ecu.year, ecu.total_exports_usd / 1e9, marker="o", color=COLORS["ECU"]); shade_events(ax)
ax.set_title("Exportaciones totales de Ecuador (USD mil millones, corrientes)"); plt.show()
g = (ecu.total_exports_usd.iloc[-1] / ecu.total_exports_usd.iloc[0]) ** (1 / (y1 - y0)) - 1
print(f"Conclusión: las exportaciones pasaron de {ecu.total_exports_usd.iloc[0]/1e9:.1f} a {ecu.total_exports_usd.iloc[-1]/1e9:.1f} mil millones "
      f"entre {y0} y {y1} (CAGR {g:.1%}); las zonas grises marcan 2008–09, 2014–16 y 2020.")'''),
    md("## 2. Composición de la canasta (área apilada)"),
    code('''pv = basket[basket.iso3 == "ECU"].pivot_table(index="year", columns="product_group", values="value_usd") / 1e9
pv = pv[[c for c in PCOLORS if c in pv]]
fig, ax = plt.subplots(); ax.stackplot(pv.index, pv.T.values, labels=pv.columns, colors=[PCOLORS[c] for c in pv.columns], edgecolor="white", linewidth=0.5)
ax.legend(ncol=4, fontsize=9, loc="upper left"); ax.set_title("Canasta exportadora de Ecuador (USD mil millones)"); plt.show()
top = pv.drop(columns="other").iloc[-1].idxmax()
print(f"Conclusión: en {y1} el mayor producto clave fue '{top}' ({pv[top].iloc[-1]:.1f} mil millones).")'''),
    md("## 3. Peso del petróleo en Ecuador y sus pares"),
    code('''fig, ax = plt.subplots()
for iso in ["ECU", "PER", "COL", "CHL"]:
    d = dep[dep.iso3 == iso].sort_values("year"); ax.plot(d.year, d.oil_share * 100, label=iso, color=COLORS[iso], lw=3 if iso == "ECU" else 1.8)
shade_events(ax); ax.legend(); ax.set_title("Petróleo y combustibles (HS 27) como % de exportaciones"); plt.show()
print(f"Conclusión: en Ecuador el peso petrolero fue {ecu.oil_share.iloc[0]:.1%} en {y0} y {ecu.oil_share.iloc[-1]:.1%} en {y1}; "
      f"máximo {ecu.oil_share.max():.1%} en {int(ecu.loc[ecu.oil_share.idxmax(), 'year'])}.")'''),
    md("## 4. Exportaciones petroleras vs Brent (dos paneles, sin doble eje)"),
    code('''br = data["oil_price_annual"].query("series == 'brent'").sort_values("year")
fig, (a1, a2) = plt.subplots(2, 1, sharex=True, figsize=(10, 6))
a1.plot(ecu.year, ecu.oil_exports_usd / 1e9, marker="o", color=COLORS["ECU"]); a1.set_title("Exportaciones petroleras de Ecuador (USD mil millones)")
a2.plot(br.year, br.avg_price_usd_bbl, marker="o", color="#52514e"); a2.set_title("Brent, promedio anual (USD/bbl)")
shade_events(a1); shade_events(a2); plt.tight_layout(); plt.show()
m = ecu.merge(br, on="year"); r = np.corrcoef(np.log(m.oil_exports_usd), np.log(m.avg_price_usd_bbl))[0, 1]
print(f"Conclusión: correlación de logaritmos = {r:.2f} ({len(m)} años). Una asociación, aunque sea fuerte, no implica causalidad.")'''),
    md("## 5. Concentración por producto (HHI)"),
    code('''fig, ax = plt.subplots()
for iso in ["ECU", "PER", "COL", "CHL"]:
    d = div[div.iso3 == iso].sort_values("year"); ax.plot(d.year, d.hhi_product, label=iso, color=COLORS[iso], lw=3 if iso == "ECU" else 1.8)
ax.legend(); ax.set_title("HHI por producto (capítulos HS2; menor = más diversificado)"); plt.show()
de = div[div.iso3 == "ECU"].set_index("year")
print(f"Conclusión: HHI de Ecuador {de.hhi_product.iloc[0]:.0f} → {de.hhi_product.iloc[-1]:.0f} "
      f"(equivale a {de.equiv_products.iloc[0]:.1f} → {de.equiv_products.iloc[-1]:.1f} capítulos de igual tamaño).")'''),
    md("## 6. Concentración por destino"),
    code('''fig, ax = plt.subplots()
for iso in ["ECU", "PER", "COL", "CHL"]:
    d = div[div.iso3 == iso].sort_values("year"); ax.plot(d.year, d.equiv_destinations, label=iso, color=COLORS[iso], lw=3 if iso == "ECU" else 1.8)
ax.legend(); ax.set_title("Número equivalente de destinos (10 000 / HHI de destinos)"); plt.show()
print(f"Conclusión: Ecuador exporta como si tuviera {de.equiv_destinations.iloc[-1]:.1f} destinos de igual tamaño en {int(de.index[-1])}.")'''),
    md("## 7. Crecimiento por producto (CAGR)"),
    code('''cg = data["product_cagr"].query("iso3 == 'ECU' and product_group != 'other'").sort_values("cagr")
fig, ax = plt.subplots(); ax.barh(cg.product_group, cg.cagr * 100, color=[PCOLORS[g] for g in cg.product_group], edgecolor="white")
ax.set_title("CAGR por producto clave, Ecuador (%)"); plt.show()
print(f"Conclusión: el más dinámico fue '{cg.iloc[-1].product_group}' ({cg.iloc[-1].cagr:.1%} anual); el menos, '{cg.iloc[0].product_group}' ({cg.iloc[0].cagr:.1%}).")'''),
    md("## 8. Índice de exportaciones no petroleras (2000 = 100)"),
    code('''ix = data["exports_index"]; fig, ax = plt.subplots()
for iso in ["ECU", "PER", "COL", "CHL"]:
    d = ix[ix.iso3 == iso].sort_values("year"); ax.plot(d.year, d.non_oil_index_2000, label=iso, color=COLORS[iso], lw=3 if iso == "ECU" else 1.8)
ax.axhline(100, color="#c3c2b7"); ax.legend(); ax.set_title("Exportaciones no petroleras, índice 2000 = 100"); plt.show()
last = ix[ix.year == ix.dropna(subset=["non_oil_index_2000"]).year.max()].set_index("iso3").non_oil_index_2000.sort_values(ascending=False)
print("Conclusión: índice en el último año común →", ", ".join(f"{k} {v:.0f}" for k, v in last.items()))'''),
    md("## 9. Indicadores macro: crecimiento e inflación"),
    code('''rc = data["regional_compare"]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4))
for code, ax, ttl in [("NY.GDP.MKTP.KD.ZG", a1, "Crecimiento del PIB (%)"), ("FP.CPI.TOTL.ZG", a2, "Inflación (%)")]:
    for iso in ["ECU", "PER", "COL", "CHL", "LCN"]:
        d = rc[(rc.iso3 == iso) & (rc.indicator_code == code)].sort_values("year")
        ax.plot(d.year, d.value, label=iso, color=COLORS[iso], lw=2.5 if iso == "ECU" else 1.5, ls=":" if iso == "LCN" else "-")
    ax.set_title(ttl); shade_events(ax)
a1.legend(fontsize=9); plt.tight_layout(); plt.show()
g = rc[(rc.iso3 == "ECU") & (rc.indicator_code == "NY.GDP.MKTP.KD.ZG")]
print(f"Conclusión: crecimiento real promedio de Ecuador {g.value.mean():.1f} % anual en {g.year.min()}–{g.year.max()}; peor año {int(g.loc[g.value.idxmin(), 'year'])}.")'''),
    md("## 10. Fuentes de dólares: remesas e IED (% del PIB)"),
    code('''piv = rc[rc.iso3 == "ECU"].pivot_table(index="year", columns="indicator_code", values="value")
fig, ax = plt.subplots()
for c, lab, col in [("BX.TRF.PWKR.CD.DT", "Remesas", "#2a78d6"), ("BX.KLT.DINV.CD.WD", "IED neta", "#eb6834")]:
    ax.plot(piv.index, piv[c] / piv["NY.GDP.MKTP.CD"] * 100, label=lab, color=col, marker="o")
ax.legend(); ax.set_title("Ecuador: remesas e IED como % del PIB"); plt.show()
rem = (piv["BX.TRF.PWKR.CD.DT"] / piv["NY.GDP.MKTP.CD"] * 100).dropna()
print(f"Conclusión: las remesas equivalieron a {rem.iloc[-1]:.1f} % del PIB en {int(rem.index[-1])} (promedio {rem.mean():.1f} %).")'''),
]

eco = nbf.v4.new_notebook()
eco.cells = [
    md("# 02 · Econometría — correlaciones, regresión vs Brent y proyección\n\n"
       "> **Correlación no es causalidad.** Los modelos describen asociaciones anuales; no aíslan efectos de "
       "volumen, diferenciales de precio del crudo ecuatoriano, tipo de cambio de los socios ni política."),
    code(SETUP + "\nimport statsmodels.api as sm\nfrom statsmodels.tsa.statespace.sarimax import SARIMAX"),
    md("## 1. Matriz de correlaciones (variaciones anuales en logaritmos)"),
    code('''br = data["oil_price_annual"].query("series == 'brent'")[["year", "avg_price_usd_bbl"]]
rc = data["regional_compare"].query("iso3 == 'ECU'").pivot_table(index="year", columns="indicator_code", values="value")
df = ecu.set_index("year")[["oil_exports_usd", "non_oil_exports_usd", "total_exports_usd"]].join(br.set_index("year")).join(rc[["NY.GDP.MKTP.CD"]])
dl = np.log(df).diff().dropna()
corr = dl.corr().round(2); display(corr)
print(f"Conclusión: Δln(Brent) se correlaciona {corr.loc['avg_price_usd_bbl','oil_exports_usd']:.2f} con Δln(exportaciones petroleras) "
      f"y {corr.loc['avg_price_usd_bbl','non_oil_exports_usd']:.2f} con Δln(no petroleras).")'''),
    md("## 2. Regresión log-log: exportaciones petroleras vs Brent\n\n"
       "$\\ln(X_t) = \\alpha + \\beta\\,\\ln(\\text{Brent}_t) + \\varepsilon_t$ — β es la elasticidad. "
       "Errores estándar robustos (HC1)."),
    code('''m = df.dropna(subset=["oil_exports_usd", "avg_price_usd_bbl"])
X = sm.add_constant(np.log(m["avg_price_usd_bbl"])); y = np.log(m["oil_exports_usd"])
ols = sm.OLS(y, X).fit(cov_type="HC1"); print(ols.summary().tables[1])
b, lo, hi = ols.params.iloc[1], *ols.conf_int().iloc[1]
print(f"Conclusión: β = {b:.2f} (IC 95 % {lo:.2f} a {hi:.2f}), R² = {ols.rsquared:.2f}. "
      f"Un Brent 10 % más alto se asocia con ~{b*10:.1f} % más exportaciones petroleras ese año.")
sens = data["oil_sensitivity"].query("iso3 == 'ECU' and target == 'oil_exports'")
print("Chequeo vs vista SQL gold.vw_oil_sensitivity (años con 12 meses de precio):", sens[["elasticity_beta", "r_squared"]].round(3).to_dict("records"))'''),
    md("## 3. Diagnóstico de residuos"),
    code('''fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4))
a1.plot(m.index, ols.resid, marker="o"); a1.axhline(0, color="grey"); a1.set_title("Residuos en el tiempo")
sm.qqplot(ols.resid, line="s", ax=a2); a2.set_title("QQ-plot"); plt.tight_layout(); plt.show()
from statsmodels.stats.stattools import durbin_watson
print(f"Conclusión: Durbin-Watson = {durbin_watson(ols.resid):.2f} (≈2 sin autocorrelación; <1,5 sugiere autocorrelación positiva).")'''),
    md("## 4. Proyección de exportaciones no petroleras (SARIMAX con tendencia)\n\n"
       "Modelo: ln(no petroleras) con tendencia lineal y AR(1). Pocos puntos anuales → intervalos amplios."),
    code('''s = np.log(ecu.set_index("year")["non_oil_exports_usd"])
s.index = pd.PeriodIndex(s.index, freq="Y")
mod = SARIMAX(s, order=(1, 0, 0), trend="ct").fit(disp=False)
H = 5; fc = mod.get_forecast(H); ci = fc.conf_int(alpha=0.2)
yrs = [p.year for p in fc.predicted_mean.index]
fig, ax = plt.subplots()
ax.plot([p.year for p in s.index], np.exp(s) / 1e9, marker="o", label="Observado", color=COLORS["ECU"])
ax.plot(yrs, np.exp(fc.predicted_mean) / 1e9, ls="--", marker="o", color=COLORS["ECU"], label="Proyección")
ax.fill_between(yrs, np.exp(ci.iloc[:, 0]) / 1e9, np.exp(ci.iloc[:, 1]) / 1e9, alpha=0.15, color=COLORS["ECU"], label="IC 80 %")
ax.legend(); ax.set_title("Exportaciones no petroleras de Ecuador (USD mil millones)"); plt.show()
print(f"Conclusión: para {yrs[-1]} el modelo proyecta {np.exp(fc.predicted_mean.iloc[-1])/1e9:.1f} mil millones "
      f"(IC 80 %: {np.exp(ci.iloc[-1,0])/1e9:.1f}–{np.exp(ci.iloc[-1,1])/1e9:.1f}). AIC = {mod.aic:.1f}.")'''),
    md("## 5. Comparación con la versión ligera de la app\n\nLa app usa una tendencia log-lineal + AR(1) en numpy "
       "(sin statsmodels en la nube). Ambas deberían dar órdenes de magnitud similares."),
    code('''sys.path.insert(0, str(ROOT / "app")); import analytics
light = analytics.forecast_trend_ar1(ecu.year, ecu.non_oil_exports_usd, H)
light["sarimax_mean"] = np.exp(fc.predicted_mean.values)
display((light.set_index("year") / 1e9).round(2))'''),
    md("## Limitaciones\n\n- ~25 observaciones anuales: poca potencia estadística.\n- USD corrientes: mezclan precio y volumen.\n"
       "- Comtrade revisa los últimos años; el pipeline incremental vuelve a pedirlos.\n- No se modelan choques climáticos, "
       "sanitarios ni cambios regulatorios."),
]

for nb, name in [(eda, "01_eda.ipynb"), (eco, "02_econometrics.ipynb")]:
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    nbf.write(nb, ROOT / "notebooks" / name)
print("notebooks generados")
