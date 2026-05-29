import sys
from pathlib import Path

import pytest

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


# VAL e TIR canónicos publicados no relatório M6 (Cap. 10 / Anexo).
# Trava de regressão: se falharem após uma alteração ao motor, ou o número do
# relatório está desatualizado, ou houve regressão — confirmar antes de mexer
# nas tolerâncias.
VAL_TIR_CANONICOS = {
    "Base":     (2_493_769.74, 0.174928),
    "Upside":   (3_710_054.43, 0.244336),
    "Downside":     (26_600.51, 0.082230),
    "Stress":  (-1_860_363.07, 0.001783),
}


@pytest.mark.parametrize(
    "cenario,val_esp,tir_esp",
    [(c, v, t) for c, (v, t) in VAL_TIR_CANONICOS.items()],
)
def test_hub_viabilidade_val_tir_canonicos(cenario, val_esp, tir_esp):
    r = get_hub_viability(cenario=cenario, irc_taxa=None, wacc=None)
    assert r["val"] == pytest.approx(val_esp, abs=1.0)
    assert r["tir"] == pytest.approx(tir_esp, abs=1e-4)


def test_hub_viabilidade_base_metricas_canonicas():
    """Métricas-síntese do cenário Base publicadas no relatório (IR e payback)."""
    base = get_hub_viability(cenario="Base", irc_taxa=None, wacc=None)

    assert base["indice_rendibilidade"] == pytest.approx(1.4156, abs=1e-3)  # 1,42
    assert base["payback_atualizado"] == pytest.approx(7.3665, abs=1e-2)    # 7,37 anos
