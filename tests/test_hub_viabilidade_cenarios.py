import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

from src.api.routes.hub import get_hub_viabilidade_cenarios, get_hub_viability
from src.engine.modelo.model import run_model


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
#
# Atualizados para o PLANO DE FINANCIAMENTO LEGAL (grande empresa): subsídio
# PT2030 a fundo perdido = 0 (sem acesso de grande empresa a SI PME; teto de
# auxílio regional 30 % satisfeito só pelo RFAI), RFAI 22,5 % (escalão Centro),
# dívida recomposta (BEI+Garantia Mútua+comercial), WACC 6,37 %. A partir da
# refatoração do Hub, a poupança de pessoal é derivada da elasticidade sobre VN
# orgânico (share 40 %) e as quebras escalam com CMVMC_prod, evitando dupla contagem
# com a DR consolidada.
VAL_TIR_CANONICOS = {
    "Base":     (1_342_474.04,  0.117170),
    "Upside":   (3_146_363.12,  0.199388),
    "Downside": (-1_337_074.68, 0.023670),
    "Stress":   (-3_030_702.06, -0.043297),
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

    assert base["indice_rendibilidade"] == pytest.approx(1.2237, abs=1e-3)  # 1,22
    assert base["payback_atualizado"] == pytest.approx(9.2098, abs=1e-2)    # 9,21 anos


def test_hub_pessoal_derivado_nao_duplica_alpha_consolidado():
    """A poupança de pessoal do hub deve entrar uma vez: via série derivada."""
    sem = run_model(
        cenario="Base",
        hub_on=False,
        ecogres_on=True,
        horizonte_maturidade=False,
    )["dr"].set_index("ano")
    com = run_model(
        cenario="Base",
        hub_on=True,
        ecogres_on=True,
        horizonte_maturidade=False,
    )["dr"].set_index("ano")

    for ano in [2026, 2027, 2028, 2029]:
        gastos_sem = -float(sem.loc[ano, "gastos_pessoal"])
        gastos_com = -float(com.loc[ano, "gastos_pessoal"])
        saving_dr = gastos_sem - gastos_com
        saving_hub = float(com.loc[ano, "hub_pessoal_reducao"])

        assert saving_dr == pytest.approx(saving_hub, abs=1.0)
