"""docs/insights.md y portfolio.json se generan desde el snapshot (aquí, el sintético)."""
import json

from src import insights


def test_render_seis_hallazgos(synthetic_data):
    md = insights.render(synthetic_data, {"exported_at_utc": "X"})
    assert md.count("## ") == 6 and "**Dato:**" in md


def test_update_portfolio(synthetic_data, tmp_path, monkeypatch):
    pf = tmp_path / "portfolio.json"
    pf.write_text(json.dumps({"kpis": [], "findings": []}), encoding="utf-8")
    monkeypatch.setattr(insights.config, "ROOT_DIR", tmp_path)
    insights.update_portfolio(synthetic_data)
    out = json.loads(pf.read_text(encoding="utf-8"))
    assert len(out["kpis"]) == 3 and len(out["findings"]) == 6
