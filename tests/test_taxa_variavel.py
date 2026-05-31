"""
Testes T5a: Risco de taxa variável (choque Euribor).
Testes T5b: Headroom de dívida face ao teto estratégico de gearing.
"""
from __future__ import annotations

import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

import copy
import pytest

from src.engine.inputs import load
from src.engine.inputs.models import Assumptions
from src.engine.financiamento.financiamento import financiamento_anual
from src.engine.demonstracoes.statements import build_statements
from src.engine.modelo.kpis import build_kpis
from src.engine.modelo.covenants import headroom_divida


@pytest.fixture(scope="module")
def base_setup():
    return load("Base")


# ============================================================
# T5a — Choque Euribor
# ============================================================

def test_choque_zero_nao_altera_juros(base_setup):
    """euribor_choque_bps=0 → juros_choque_euribor=0 em todos os anos."""
    a, base, sched = base_setup
    df = financiamento_anual(sched, a)
    assert (df["juros_choque_euribor"] == 0.0).all(), \
        "Com choque=0, juros_choque_euribor deve ser 0 em todos os anos"


def test_choque_200bps_aumenta_juros(base_setup):
    """Choque +200bps aumenta juros_total proporcionalmente ao saldo de dívida variável."""
    a, base, sched = base_setup

    # Baseline sem choque
    df0 = financiamento_anual(sched, a)

    # Com choque +200bps
    a_raw = copy.deepcopy(a.raw)
    a_raw.setdefault("risco_taxa", {})["euribor_choque_bps"] = 200
    a_raw["risco_taxa"]["aplica_a_taxa_variavel"] = True
    a_raw["risco_taxa"]["pct_divida_variavel"] = 1.0
    a2 = Assumptions(raw=a_raw, produtos_raw=a.produtos_raw, mercadorias_raw=a.mercadorias_raw)
    df200 = financiamento_anual(sched, a2)

    # Para anos com saldo > 0, os juros devem aumentar
    for y in [2025, 2026, 2027]:
        j0 = float(df0[df0.ano == y]["juros_total"].iloc[0])
        j200 = float(df200[df200.ano == y]["juros_total"].iloc[0])
        cap = float(df0[df0.ano == y]["capital_divida_total_fim"].iloc[0])
        choque_esperado = cap * 0.02  # 200bps = 2%

        assert j200 > j0, f"Ano {y}: juros com choque ({j200:.0f}) devem ser > sem choque ({j0:.0f})"
        assert abs((j200 - j0) - choque_esperado) < 1.0, (
            f"Ano {y}: incremento de juros {j200-j0:.2f} != esperado {choque_esperado:.2f}"
        )


def test_choque_reduz_rai_e_dscr(base_setup):
    """Choque +200bps reduz RAI e DSCR em 2025-2029."""
    a, base, sched = base_setup

    dfs0 = build_statements(a, base, sched)
    kpis0 = build_kpis(dfs0["dr"], dfs0["balanco"], dfs0["dfc"], a)

    a_raw = copy.deepcopy(a.raw)
    a_raw.setdefault("risco_taxa", {})["euribor_choque_bps"] = 200
    a2 = Assumptions(raw=a_raw, produtos_raw=a.produtos_raw, mercadorias_raw=a.mercadorias_raw)
    dfs200 = build_statements(a2, base, sched)
    kpis200 = build_kpis(dfs200["dr"], dfs200["balanco"], dfs200["dfc"], a2)

    for y in [2025, 2026, 2027]:
        rai0 = float(dfs0["dr"][dfs0["dr"].ano == y]["rai"].iloc[0])
        rai200 = float(dfs200["dr"][dfs200["dr"].ano == y]["rai"].iloc[0])
        assert rai200 < rai0, (
            f"Ano {y}: com choque 200bps, RAI={rai200:.0f} devia ser < {rai0:.0f}"
        )

        dscr0 = float(kpis0[kpis0.ano == y]["dscr"].iloc[0])
        dscr200 = float(kpis200[kpis200.ano == y]["dscr"].iloc[0])
        assert dscr200 <= dscr0, (
            f"Ano {y}: com choque 200bps, DSCR={dscr200:.3f} devia ser ≤ {dscr0:.3f}"
        )


def test_toggle_off_anula_choque(base_setup):
    """aplica_a_taxa_variavel=False → choque não tem efeito mesmo com bps != 0."""
    a, base, sched = base_setup
    df0 = financiamento_anual(sched, a)

    a_raw = copy.deepcopy(a.raw)
    a_raw.setdefault("risco_taxa", {})["euribor_choque_bps"] = 500
    a_raw["risco_taxa"]["aplica_a_taxa_variavel"] = False
    a2 = Assumptions(raw=a_raw, produtos_raw=a.produtos_raw, mercadorias_raw=a.mercadorias_raw)
    df_off = financiamento_anual(sched, a2)

    assert (df_off["juros_choque_euribor"] == 0.0).all(), \
        "Toggle OFF: choque deve ser 0 mesmo com 500bps"


# ============================================================
# T5b — Headroom de dívida
# ============================================================

def test_headroom_estrutura(base_setup):
    """headroom_divida devolve DataFrame com colunas corretas."""
    a, base, sched = base_setup
    dfs = build_statements(a, base, sched)
    kpis = build_kpis(dfs["dr"], dfs["balanco"], dfs["dfc"], a)
    hd = headroom_divida(kpis, a)

    for col in ("ano", "gearing", "divida_max_para_teto", "headroom_eur"):
        assert col in hd.columns, f"Coluna '{col}' em falta no headroom"
    assert len(hd) == len(kpis)


def test_headroom_positivo_com_gearing_baixo(base_setup):
    """headroom_eur > 0 quando gearing < gearing_max (65%)."""
    a, base, sched = base_setup
    dfs = build_statements(a, base, sched)
    kpis = build_kpis(dfs["dr"], dfs["balanco"], dfs["dfc"], a)
    hd = headroom_divida(kpis, a)
    cov_cfg = a.raw.get("covenants", {})
    gmax = float(cov_cfg.get("gearing_max", 0.65))
    for _, r in hd.iterrows():
        if float(r["gearing"]) < gmax:
            assert float(r["headroom_eur"]) > 0, (
                f"Ano {r['ano']}: gearing={r['gearing']:.2%} < {gmax:.0%} "
                f"mas headroom={r['headroom_eur']:.0f} não é > 0"
            )
