"""Configuración común de pytest."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(ROOT / "tests"))

import synthetic  # noqa: E402


@pytest.fixture(scope="session")
def synthetic_dir(tmp_path_factory):
    """Snapshot sintético en una carpeta temporal (nunca en app/data)."""
    return synthetic.write(tmp_path_factory.mktemp("snapshot"))


@pytest.fixture(scope="session")
def synthetic_data():
    return synthetic.build()
