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
#
# ATUALIZADO para enablement play + 3PL como receita recorrente + perpetuidade:
# vn_incremental 2026-2034 recorrente (não finito 2029), receita_servicos_externos
# dict 2026-2034 (3PL explícito), cmvmc_servicos_pct=0.40 (margem 60%).
# Terminal value: VLC + NFM + perpetuidade 3PL (Gordon Growth).
# WACC 6,37 %, todos os cenários.
VAL_TIR_CANONICOS = {
    "Base":     (2_031_233.1,  0.139901),
    "Upside":   (3_868_078.0,  0.220060),
    "Downside": (-796_361.6,   0.048832),
    "Stress":   (-2_370_176.5, -0.004738),
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
    """Métricas-síntese do cenário Base para enablement play.

    Com 3PL recorrente e perpetuidade: IR=1.339, payback=8.80.
    """
    base = get_hub_viability(cenario="Base", irc_taxa=None, wacc=None)

    assert base["indice_rendibilidade"] == pytest.approx(1.3385, abs=1e-3)
    assert base["payback_atualizado"] == pytest.approx(8.800, abs=1e-2)


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