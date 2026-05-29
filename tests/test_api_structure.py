import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / 'src'))

from src.api.routes import get_scenarios_all
from src.engine.inputs.loader import CENARIOS


def test_api_scenarios_structure():
    result = get_scenarios_all(hub_on=False, ecogres_on=False)

    # A API deve devolver exactamente os cenários definidos no motor (fonte única
    # de verdade). Não duplicar a lista aqui — senão o teste parte sempre que se
    # adiciona/remove um cenário em _SCENARIO_OVERRIDES.
    assert set(result.keys()) == set(CENARIOS)
    assert "Base" in result  # sanidade mínima

    for data in result.values():
        for key in (
            "dr",
            "balanco",
            "dfc",
            "fse_detalhe_anual",
            "fse_detalhe_mensal_2025",
        ):
            assert "rows" in data[key]
        assert isinstance(data["kpis"], dict)

