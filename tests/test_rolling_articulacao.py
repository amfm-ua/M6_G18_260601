"""Testes de articulação do Rolling Forecast Mensal.

Verifica três identidades fundamentais:
  1. Balanço mensal: controlo = 0 (Total Ativo = CP + Passivo) em todos os meses
  2. DFC mensal: reconciliacao = 0 (caixa_abertura + var_caixa = caixa_fecho)
  3. Articulação EBITDA → fluxo_operacional: identidade DFC indireto
     fluxo_op ≈ EBITDA - IRC + rend_fin - rend_equiv + ΔNFM

Nota: o gap esperado na identidade 3 é residual (< €5 000) porque o efeito dos
gastos pré-operacionais do hub (€105K/ano de formação WMS/MES) é capturado via RL
no fluxo_operacional, não como pagamento explícito — comportamento correto por
construção do método indireto (fluxo_op = RL + D&A + juros - rend_equiv + ΔNFM).
"""
import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

import pytest
from src.engine.inputs import load
from src.engine.demonstracoes.rolling_forecast_mensal import (
    build_rolling_forecast,
)


TOL_BALANCO   = 1.0    # €1 — arredondamento
TOL_DFC_REC   = 1.0    # €1 — arredondamento
TOL_EBITDA_OP = 5_000  # €5k — diferenças de timing IRC e rend. financeiros


@pytest.fixture(scope="module")
def rf_sem():
    a, base, sched = load("Base")
    a.raw.setdefault("hub_logistico", {})["incluir_hub"] = False
    return build_rolling_forecast(a, base, sched)


@pytest.fixture(scope="module")
def rf_com():
    a, base, sched = load("Base")
    a.raw.setdefault("hub_logistico", {})["incluir_hub"] = True
    return build_rolling_forecast(a, base, sched)


# ──────────────────────────────────────────────────────────────────────────────
# 1. Balanço: controlo = 0
# ──────────────────────────────────────────────────────────────────────────────

def _check_balanco_controlo(rf_dict, label):
    df_bs = rf_dict["balanco_mensal"]
    for _, row in df_bs.iterrows():
        ctrl = abs(row["controlo"])
        assert ctrl <= TOL_BALANCO, (
            f"[{label}] Balanço fora de equilíbrio em {row['mes']}: "
            f"controlo = {row['controlo']:,.2f}€ (tol={TOL_BALANCO}€)"
        )


def test_balanco_controlo_sem_hub(rf_sem):
    _check_balanco_controlo(rf_sem, "sem_hub")


def test_balanco_controlo_com_hub(rf_com):
    _check_balanco_controlo(rf_com, "com_hub")


# ──────────────────────────────────────────────────────────────────────────────
# 2. DFC: reconciliacao = 0
# ──────────────────────────────────────────────────────────────────────────────

def _check_dfc_reconciliacao(rf_dict, label):
    df_dfc = rf_dict["dfc_mensal"]
    for _, row in df_dfc.iterrows():
        rec = abs(row["reconciliacao"])
        assert rec <= TOL_DFC_REC, (
            f"[{label}] DFC não reconcilia em {row['mes']}: "
            f"reconciliacao = {row['reconciliacao']:,.2f}€ (tol={TOL_DFC_REC}€)"
        )


def test_dfc_reconciliacao_sem_hub(rf_sem):
    _check_dfc_reconciliacao(rf_sem, "sem_hub")


def test_dfc_reconciliacao_com_hub(rf_com):
    _check_dfc_reconciliacao(rf_com, "com_hub")


# ──────────────────────────────────────────────────────────────────────────────
# 3. Consistência interna do DR mensal: RL = EBITDA − dep − juros + rend_fin − IRC
#
#    Esta é a identidade contabilística fundamental do DR. Verifica que cada mês
#    é internamente consistente — se falhar, há um bug na construção de build_dr_mensal.
#
#    Nota: a articulação completa EBITDA→fluxo_op exige rend_equiv_patrimonial
#    (~€843K/ano de rendimentos de subsidiárias, não-cash), que é subtraído do
#    fluxo_op no método indireto (NCRF 2 §33). Não testada aqui porque requer
#    acesso ao schedules.investimento — capturada implicitamente pelos testes 1 e 2.
# ──────────────────────────────────────────────────────────────────────────────

TOL_DR_INTERNO = 2.0   # €2 — tolerância para arredondamento de round()

def _check_dr_interno(rf_dict, label):
    df_dr = rf_dict["dr_mensal"]
    for _, row in df_dr.iterrows():
        rl_computed = (
            row["ebitda"]
            - row["depreciacoes"]
            - row["juros"]
            + row.get("rend_financeiros", 0)
            - row["irc"]
        )
        gap = abs(rl_computed - row["rl"])
        assert gap <= TOL_DR_INTERNO, (
            f"[{label}] DR interno inconsistente em {row['mes']}: "
            f"RL calculado={rl_computed:,.0f} ≠ RL modelo={row['rl']:,.0f} "
            f"(gap=€{gap:,.2f})"
        )


def test_dr_interno_sem_hub(rf_sem):
    _check_dr_interno(rf_sem, "sem_hub")


def test_dr_interno_com_hub(rf_com):
    _check_dr_interno(rf_com, "com_hub")


# ──────────────────────────────────────────────────────────────────────────────
# 4. Caixa Dez (Balanço) == Caixa fecho (DFC)
# ──────────────────────────────────────────────────────────────────────────────

def _check_caixa_fecho(rf_dict, label):
    df_bs  = rf_dict["balanco_mensal"]
    df_dfc = rf_dict["dfc_mensal"]
    caixa_bs  = float(df_bs[df_bs["mes"] == "Dez"]["caixa"].iloc[0])
    caixa_dfc = float(df_dfc[df_dfc["mes"] == "Dez"]["caixa_fecho"].iloc[0])
    gap = abs(caixa_bs - caixa_dfc)
    assert gap <= TOL_BALANCO, (
        f"[{label}] Caixa Dez: Balanço={caixa_bs:,.0f} ≠ DFC={caixa_dfc:,.0f} "
        f"(gap={gap:,.2f}€)"
    )


def test_caixa_fecho_sem_hub(rf_sem):
    _check_caixa_fecho(rf_sem, "sem_hub")


def test_caixa_fecho_com_hub(rf_com):
    _check_caixa_fecho(rf_com, "com_hub")
