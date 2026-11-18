"""El snapshot que se versiona debe ser liviano y traer metadatos."""
import json

from src import config, export_snapshot


def test_metadata(tmp_path):
    meta = export_snapshot.write_metadata(tmp_path, {"export_basket": 10})
    disk = json.loads((tmp_path / "metadata.json").read_text(encoding="utf-8"))
    assert disk["rows_per_table"] == {"export_basket": 10} and meta["sources"]


def test_app_data_versionado_pesa_menos_de_5mb():
    for p in config.APP_DATA_DIR.glob("*.parquet"):
        assert p.stat().st_size < export_snapshot.MAX_MB * 1_048_576, p.name


def test_snapshot_cubre_lo_que_usa_la_app():
    import common
    assert set(common.REQUIRED) <= set(export_snapshot.SNAPSHOT_QUERIES)
