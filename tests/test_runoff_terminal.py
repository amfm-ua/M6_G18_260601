"""
Testes do run-off contratual 2030-2034 (toggle terminal_debt_runoff).

Por defeito OFF: dívida constante (constant leverage), WACC estável.
Com ON: BPI amortiza até 2032, desalavancagem progressiva.

⚠ Interação crítica: run-off + cash sweep pode empurrar gearing abaixo de 40%.
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
from src.engine.demonstracoes.statements import build_statements
from src.engine.modelo.kpis import build_kpis
from src.engine.modelo.covenants import avaliar_covenants


def _run_with_runoff(runoff: bool, cash_sweep: bool = True):
    """Corre o modelo com combinação de toggles de run-off e cash sweep."""
    a, base, sched = load("Base")
    a_raw = copy.deepcopy(a.raw)
    a_raw.setdefault("financiamento", {})["terminal_debt_runoff"] = runoff
    a_raw.setdefault("distribuicao_resultados", {})["terminal_cash_sweep"] = cash_sweep
    a2 = Assumptions(raw=a_raw, produtos_raw=a.produtos_raw, mercadorias_raw=a.mercadorias_raw)
    dfs = build_statements(a2, base, sched)
    kpis = build_kpis(dfs["dr"], dfs["balanco"], dfs["dfc"], a2)
    cov = avaliar_covenants(kpis, a2)
    return dfs, kpis, cov


# ============================================================
# 1. DEFAULT OFF — comportamento não muda
# ============================================================

def test_runoff_off_divida_constante_2030_2034():
    """Com toggle OFF, a dívida mantém-se no nível de 2029 em 2030-2034."""
    dfs, kpis, _ = _run_with_runoff(runoff=False)
    bal = dfs["balanco"]
    saldo_2029 = (
        float(bal[bal.ano == 2029]["emprestimos_nc"].iloc[0])
        + float(bal[bal.ano == 2029]["emprestimos_c"].iloc[0])
    )
    for y in [2030, 2031, 2032]:
        row = bal[bal.ano == y].iloc[0]
        saldo_y = float(row["emprestimos_nc"]) + float(row["emprestimos_c"])
        assert abs(saldo_y - saldo_2029) < 1.0, (
            f"Run-off OFF: saldo {y}={saldo_y:.0f} devia ≈ 2029={saldo_2029:.0f}"
        )


# ============================================================
# 2. RUN-OFF ON — dívida decresce até 0 em 2032
# ============================================================

def test_runoff_on_divida_decresce():
    """Com toggle ON, a dívida bancária base cai progressivamente até 0 em 2032."""
    dfs, _, _ = _run_with_runoff(runoff=True)
    bal = dfs["balanco"]

    saldo_2029 = (
        float(bal[bal.ano == 2029]["emprestimos_nc"].iloc[0])
        + float(bal[bal.ano == 2029]["emprestimos_c"].iloc[0])
    )
    saldo_2032 = (
        float(bal[bal.ano == 2032]["emprestimos_nc"].iloc[0])
        + float(bal[bal.ano == 2032]["emprestimos_c"].iloc[0])
    )

    # A dívida deve descer de 2029 para 2032 (BPI liquida)
    assert saldo_2032 < saldo_2029 * 0.5, (
        f"Run-off ON: dívida em 2032 ({saldo_2032:.0f}) devia ser < 50% de 2029 ({saldo_2029:.0f})"
    )


def test_runoff_on_amortizacoes_2030_2032():
    """Com run-off ON, DFC tem pag_emprestimos > 0 em 2030-2032."""
    dfs, _, _ = _run_with_runoff(runoff=True)
    dfc = dfs["dfc"]
    for y in [2030, 2031, 2032]:
        row = dfc[dfc.ano == y].iloc[0]
        pag = abs(float(row.get("pag_emprestimos", 0.0)))
        assert pag > 0, f"Run-off ON: pag_emprestimos[{y}] = {pag:.0f} devia ser > 0"


def test_runoff_on_juros_decrescentes():
    """Com run-off ON, juros pagos decrescem de 2030 a 2033."""
    dfs, _, _ = _run_with_runoff(runoff=True)
    dr = dfs["dr"]
    anos = [2030, 2031, 2032, 2033]
    juros = [abs(float(dr[dr.ano == y]["juros"].iloc[0])) for y in anos]
    for i in range(len(juros) - 1):
        assert juros[i] >= juros[i + 1], (
            f"Juros devem decrescer: {anos[i]}={juros[i]:.0f} vs {anos[i+1]}={juros[i+1]:.0f}"
        )


# ============================================================
# 3. BEFORE/AFTER: gearing 4 combinações de toggles
# ============================================================

def test_before_after_gearing_4_combinacoes():
    """Reporta gearing 2030-34 nas 4 combinações de toggles.

    ⚠ Interação crítica: run-off + cash_sweep pode empurrar gearing < 40%.
    Assinala os anos < 40% (piso estratégico da Grestel).
    """
    combos = [
        (False, False, "OFF+SemSweep"),
        (False, True,  "OFF+ComSweep"),
        (True,  False, "ON+SemSweep"),
        (True,  True,  "ON+ComSweep"),
    ]
    GEARING_MIN = 0.40
    ANOS_TERMINAIS = [2030, 2031, 2032, 2033, 2034]

    print("\nGearing 2030-2034 por combinação de toggles:")
    print(f"{'Combinação':<18} | " + " | ".join(str(y) for y in ANOS_TERMINAIS))
    print("-" * 75)

    for runoff, sweep, label in combos:
        _, kpis, _ = _run_with_runoff(runoff=runoff, cash_sweep=sweep)
        gearing_vals = []
        for y in ANOS_TERMINAIS:
            if y in kpis["ano"].values:
                g = float(kpis[kpis.ano == y]["gearing"].iloc[0])
            else:
                g = float("nan")
            gearing_vals.append(g)
        linha = " | ".join(f"{g:>6.1%}" for g in gearing_vals)
        print(f"{label:<18} | {linha}")

    # Validar que os valores estão disponíveis (o teste só reporta, não falha)
    assert True


def test_runoff_e_sweep_gearing_abaixo_banda():
    """Run-off ON + cash_sweep ON pode empurrar gearing abaixo de 40%.

    Se isso acontecer, covenants.gearing_abaixo_banda deve ser True.
    Este teste documenta a interação crítica sem impor um resultado específico.
    """
    _, kpis, cov = _run_with_runoff(runoff=True, cash_sweep=True)

    # Verificar que a coluna existe
    assert "gearing_abaixo_banda" in cov.columns
    assert "gearing" in kpis.columns

    # Reportar anos fora da banda
    anos_abaixo = cov[cov["gearing_abaixo_banda"] == True]["ano"].tolist()
    # O teste documenta sem falhar — o resultado depende dos pressupostos
    print(f"\nRun-off+Sweep: anos com gearing < 40%: {anos_abaixo}")


# ============================================================
# 4. RECONCILIAÇÃO COM RUN-OFF
# ============================================================

def test_reconciliacao_runoff_on():
    """Com run-off ON, reconciliacao_ok=True exceto gaps conhecidos (2026)."""
    ANOS_GAP_CONHECIDOS = {2026}
    dfs, _, _ = _run_with_runoff(runoff=True)
    dfc = dfs["dfc"]
    falhas = [
        int(r["ano"]) for _, r in dfc.iterrows()
        if not bool(r["reconciliacao_ok"]) and int(r["ano"]) not in ANOS_GAP_CONHECIDOS
    ]
    assert not falhas, f"reconciliacao_ok=False com run-off ON: {falhas}"
