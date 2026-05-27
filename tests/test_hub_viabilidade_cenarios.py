import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

from src.api.routes.hub import get_hub_viabilidade_cenarios, get_hub_viability


def test_hub_viabilidade_cenarios_ordem_val():
    result = get_hub_viabilidade_cenarios(irc_taxa=None, wacc=None)

    assert result["Upside"]["val"] > result["Base"]["val"]
    assert result["Base"]["val"] > result["Downside"]["val"]
    assert result["Downside"]["val"] > result["Stress"]["val"]


def test_hub_viabilidade_cenarios_ordem_ir():
    result = get_hub_viabilidade_cenarios(irc_taxa=None, wacc=None)

    assert result["Upside"]["indice_rendibilidade"] > result["Base"]["indice_rendibilidade"]
    assert result["Base"]["indice_rendibilidade"] > result["Downside"]["indice_rendibilidade"]
    assert result["Downside"]["indice_rendibilidade"] > result["Stress"]["indice_rendibilidade"]


def test_hub_viability_respeita_cenario():
    base = get_hub_viability(cenario="Base", irc_taxa=None, wacc=None)
    upside = get_hub_viability(cenario="Upside", irc_taxa=None, wacc=None)
    downside = get_hub_viability(cenario="Downside", irc_taxa=None, wacc=None)

    assert upside["val"] > base["val"] > downside["val"]
    assert upside["tir"] > base["tir"] > downside["tir"]
