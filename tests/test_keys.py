import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / 'src'))

from src.engine.operacional.fse import FSE_DETALHE_KEYS, fse_rubricas_ordered
from src.engine.inputs import load


def test_fse_keys_exist_in_base_data():
    _, b, _ = load("Base")
    base_vals = getattr(b, "fse_detalhe", {}) or {}

    assert FSE_DETALHE_KEYS
    assert fse_rubricas_ordered()
    # Hub_FSE_ajuste is computed at DR level, not a 2024 base measurement
    yaml_keys = {k for k in FSE_DETALHE_KEYS.keys() if not k.startswith("Hub_")}
    assert all(rub in base_vals for rub in yaml_keys)

