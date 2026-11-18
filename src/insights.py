"""Genera docs/insights.md a partir del snapshot (los mismos hallazgos que la app)."""
from __future__ import annotations

import json
import sys

import pandas as pd

from src import config

sys.path.insert(0, str(config.ROOT_DIR / "app"))
import analytics  # noqa: E402  (módulo compartido con la app)

log = config.get_logger("insights")


def names(lang: str) -> dict[str, str]:
    i = 1 if lang == "es" else 2
    out = {v[0]: v[i] for v in config.KEY_PRODUCTS.values()}
    out[config.OTHER_GROUP[0]] = config.OTHER_GROUP[i]
    out.update({iso: v[1] if lang == "es" else v[2] for iso, v in config.COUNTRIES.items()})
    return out


def load_snapshot(data_dir=config.APP_DATA_DIR) -> dict[str, pd.DataFrame]:
    return {p.stem: pd.read_parquet(p) for p in data_dir.glob("*.parquet")}


def render(data: dict[str, pd.DataFrame], meta: dict | None = None) -> str:
    meta = meta or {}
    lines = ["# Hallazgos principales", "",
             "Generado automáticamente por `src/insights.py` desde el snapshot gold "
             f"(exportado {meta.get('exported_at_utc', 'n/d')}). Cada cifra sale de la base; nada se escribe a mano.",
             "Formato: **dato → interpretación → implicación**. Lenguaje neutral, sin evaluación de políticas.", ""]
    for n, f in enumerate(analytics.findings(data, "es", names("es")), 1):
        lines += [f"## {n}. {f['title']}", "", f"- **Dato:** {f['data']}", f"- **Interpretación:** {f['interpretation']}",
                  f"- **Implicación:** {f['implication']}", ""]
    lines += ["---", "", "Fuentes: Banco Mundial (WDI y Pink Sheet), UN Comtrade. Ver README para códigos y fechas de extracción.", ""]
    return "\n".join(lines)


def write_all() -> None:
    data = load_snapshot()
    meta_path = config.APP_DATA_DIR / "metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    (config.DOCS_DIR / "insights.md").write_text(render(data, meta), encoding="utf-8")
    update_portfolio(data)
    log.info("docs/insights.md y portfolio.json actualizados")


def update_portfolio(data: dict[str, pd.DataFrame]) -> None:
    """Completa kpis y findings de portfolio.json con los valores calculados."""
    path = config.ROOT_DIR / "portfolio.json"
    pf = json.loads(path.read_text(encoding="utf-8"))
    k = analytics.kpis(data)
    pf["kpis"] = [
        {"name": f"Peso del petróleo en exportaciones ({k['first_year']} → {k['last_year']})",
         "value": f"{analytics._fmt_pct(k['oil_share_first'], 'es')} → {analytics._fmt_pct(k['oil_share_last'], 'es')}"},
        {"name": f"HHI por producto ({k['last_year']})", "value": analytics._fmt_num(k["hhi_product_last"], "es")},
        {"name": "Elasticidad exportaciones petroleras vs Brent", "value": analytics._fmt_num(k["oil_elasticity"], "es", 2)},
    ]
    pf["findings"] = [f["data"] for f in analytics.findings(data, "es", names("es"))]
    path.write_text(json.dumps(pf, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    write_all()
