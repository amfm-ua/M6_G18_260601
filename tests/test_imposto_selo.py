"""
Testes do Imposto do Selo sobre financiamento.

Ancoragem R&C 2024: juro incremental 42.978,56 € → selo 1.719,14 € = 4,00%
Taxa de juros (Verba 17.3.1): 4% — CONFIRMADO R&C 2024.
Verba 17.1 (utilização): estimativa, toggle separado, default OFF.
"""
from __future__ import annotations

import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

import copy
import pytest

from src.engine.inputs import load
from src.engine.financiamento.financiamento import financiamento_anual, imposto_selo_anual
from src.engine.demonstracoes.statements import build_statements
from src.engine.modelo.kpis import build_kpis


JUROS_INCREMENTAL_RC2024 = 42_978.56
SELO_ESPERADO_RC2024 = 1_719.14
TOLERANCIA_EUR = 1.0


@pytest.fixture(scope="module")
def base_setup():
    return load("Base")


@pytest.fixture(scope="module")
def df_fin(base_setup):
    a, base, sched = base_setup
    return financiamento_anual(sched, a)


# ============================================================
# 1. ANCORAGEM R&C 2024: 4% sobre juros
# ============================================================

def test_ancoragem_rc2024_taxa_4pct():
    """Replica o ponto de ancoragem dos R&C 2024: 4% sobre juro incremental."""
    taxa = 0.04
    calculado = taxa * JUROS_INCREMENTAL_RC2024
    assert abs(calculado - SELO_ESPERADO_RC2024) < TOLERANCIA_EUR, (
        f"Ancoragem falhou: {taxa} × {JUROS_INCREMENTAL_RC2024} = {calculado:.2f} "
        f"(esperado {SELO_ESPERADO_RC2024:.2f})"
    )


def test_selo_juros_2024(base_setup, df_fin):
    """selo_juros[2024] ≈ taxa_juros × juros_total[2024]."""
    a, _, _ = base_setup
    df_s = imposto_selo_anual(df_fin, a)
    row = df_s[df_s.ano == 2024].iloc[0]

    taxa = float(a.raw.get("imposto_selo", {}).get("taxa_juros", 0.04))
    juros_2024 = abs(float(df_fin[df_fin.ano == 2024]["juros_total"].iloc[0]))
    esperado = taxa * juros_2024

    assert abs(float(row["selo_juros"]) - esperado) < TOLERANCIA_EUR, (
        f"selo_juros 2024: {row['selo_juros']:.2f} vs esperado {esperado:.2f}"
    )


def test_selo_credito_default_zero(base_setup, df_fin):
    """Verba 17.1 está OFF por defeito → selo_credito = 0."""
    a, _, _ = base_setup
    df_s = imposto_selo_anual(df_fin, a)
    assert (df_s["selo_credito"] == 0.0).all(), \
        "aplicar_utilizacao=false → selo_credito deve ser 0 em todos os anos"


def test_selo_total_igual_soma(base_setup, df_fin):
    """selo_total = selo_juros + selo_credito."""
    a, _, _ = base_setup
    df_s = imposto_selo_anual(df_fin, a)
    for _, r in df_s.iterrows():
        assert abs(float(r["selo_total"]) - float(r["selo_juros"]) - float(r["selo_credito"])) < 1e-6


# ============================================================
# 2. TOGGLE aplicar_juros = false → selo_juros = 0
# ============================================================

def test_toggle_off_anula_selo(base_setup, df_fin):
    """Se aplicar_juros=false → selo_juros=0 e DR volta ao baseline."""
    a, base, sched = base_setup
    a2_raw = copy.deepcopy(a.raw)
    a2_raw.setdefault("imposto_selo", {})["aplicar_juros"] = False

    from src.engine.inputs.models import Assumptions
    a2 = Assumptions(raw=a2_raw)
    df_s2 = imposto_selo_anual(df_fin, a2)
    assert (df_s2["selo_juros"] == 0.0).all(), "Toggle OFF deve zerar selo_juros"
    assert (df_s2["selo_total"] == 0.0).all(), "Toggle OFF deve zerar selo_total (Verba 17.1 já é 0)"


def test_toggle_off_dr_coincide_sem_selo():
    """Com toggle OFF, os juros são menores (sem selo) → RAI maior."""
    a, base, sched = load("Base")

    # Baseline com toggle ON (padrão)
    dfs_on = build_statements(a, base, sched)

    # Com toggle OFF — copiar produtos_raw/mercadorias_raw para build_statements funcionar
    from src.engine.inputs.models import Assumptions
    a2_raw = copy.deepcopy(a.raw)
    a2_raw.setdefault("imposto_selo", {})["aplicar_juros"] = False
    a2 = Assumptions(
        raw=a2_raw,
        produtos_raw=a.produtos_raw,
        mercadorias_raw=a.mercadorias_raw,
    )
    dfs_off = build_statements(a2, base, sched)

    # Com toggle ON, os juros são maiores (incluem o selo) → RAI menor
    dr_on = dfs_on["dr"]
    dr_off = dfs_off["dr"]

    for y in [2025, 2026, 2027]:
        rai_on = float(dr_on[dr_on.ano == y]["rai"].iloc[0])
        rai_off = float(dr_off[dr_off.ano == y]["rai"].iloc[0])
        assert rai_on < rai_off, (
            f"Ano {y}: com selo, RAI={rai_on:.0f} devia ser < sem selo RAI={rai_off:.0f}"
        )


# ============================================================
# 3. RECONCILIAÇÃO — selo flui para DFC (controlo ≈ 0)
# ============================================================

def test_reconciliacao_com_selo(base_setup):
    """reconciliacao_ok=True em todos os anos com o selo ativo.

    2026 tem um gap conhecido pré-existente (ver DIVIDA_TECNICA.md),
    documentado nos testes de invariantes financeiras — excluído aqui.
    """
    ANOS_GAP_CONHECIDOS = {2026}
    a, base, sched = base_setup
    dfs = build_statements(a, base, sched)
    dfc = dfs["dfc"]
    falhas = [
        int(r["ano"]) for _, r in dfc.iterrows()
        if not bool(r["reconciliacao_ok"]) and int(r["ano"]) not in ANOS_GAP_CONHECIDOS
    ]
    assert not falhas, f"reconciliacao_ok=False nos anos (excl. gaps conhecidos): {falhas}"
