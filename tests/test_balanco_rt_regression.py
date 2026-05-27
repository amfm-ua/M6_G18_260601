import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / 'src'))

import pytest
from src.engine.inputs import load
from src.engine.modelo.model import run_model


@pytest.fixture(scope="module")
def model_outputs():
    return run_model("Base", hub_on=False, ecogres_on=False)


def test_rt_formula_aplica_payout_e_reserva_legal(model_outputs):
    """RT[y] = RT[y-1] + RL[y-1] * (1 - payout - reserva_legal) para anos >= ano_inicio_distribuicao.

    Verifica a fórmula matematicamente contra os próprios valores do DR,
    independente dos valores absolutos (que variam com os pressupostos).
    """
    a, base, sched = load("Base")
    payout = a.distribuicao["payout_ratio"]
    reserva = a.distribuicao.get("reserva_legal_pct", 0.0)
    inicio_div = a.distribuicao["ano_inicio_distribuicao"]

    dr = model_outputs["dr"]
    balanco = model_outputs["balanco"]

    for ano in (2026, 2027, 2028, 2029):
        rl_prev = float(dr[dr.ano == (ano - 1)]["rl"].iloc[0])
        rl_cur = float(dr[dr.ano == ano]["rl"].iloc[0])
        rt_prev = float(balanco[balanco.ano == (ano - 1)]["resultados_transitados"].iloc[0])
        rt_cur = float(balanco[balanco.ano == ano]["resultados_transitados"].iloc[0])

        if rl_cur > 0 and ano >= inicio_div:
            expected = rt_prev + rl_prev - rl_prev * payout - rl_prev * reserva
        else:
            expected = rt_prev + rl_prev

        assert abs(rt_cur - expected) < 0.01, (
            f"RT {ano}: esperado {expected:,.2f} €, obtido {rt_cur:,.2f} €"
        )


def test_reserva_legal_deduzida_dos_rt(model_outputs):
    """RT deve ser inferior ao que seria com payout_ratio apenas (sem reserva_legal).

    Regressão directa: sem a dedução de reserva_legal_pct os RT seriam sistematicamente
    superiores em ~5% do RL de cada ano anterior.
    """
    a, base, sched = load("Base")
    payout = a.distribuicao["payout_ratio"]
    reserva = a.distribuicao.get("reserva_legal_pct", 0.0)

    if reserva == 0.0:
        pytest.skip("reserva_legal_pct é zero — teste de regressão não aplicável")

    dr = model_outputs["dr"]
    balanco = model_outputs["balanco"]
    inicio_div = a.distribuicao["ano_inicio_distribuicao"]

    rt_2029_actual = float(balanco[balanco.ano == 2029]["resultados_transitados"].iloc[0])

    # Simula o que o RT 2029 seria SEM reserva_legal (só payout)
    rt = float(balanco[balanco.ano == 2025]["resultados_transitados"].iloc[0])
    for ano in (2026, 2027, 2028, 2029):
        rl_prev = float(dr[dr.ano == (ano - 1)]["rl"].iloc[0])
        rl_cur = float(dr[dr.ano == ano]["rl"].iloc[0])
        if rl_cur > 0 and ano >= inicio_div:
            rt = rt + rl_prev - rl_prev * payout  # sem reserva
        else:
            rt = rt + rl_prev

    rt_2029_sem_reserva = rt
    assert rt_2029_actual < rt_2029_sem_reserva, (
        f"RT 2029 com reserva ({rt_2029_actual:,.0f} €) não é inferior "
        f"ao calculado só com payout ({rt_2029_sem_reserva:,.0f} €) — "
        "reserva_legal_pct não está a ser deduzida"
    )


def test_rt_2025_sem_deducoes(model_outputs):
    """Em 2025 não se aplicam dividendos nem reserva legal (exercício parcial, capital afecto ao hub)."""
    base_data = load("Base")[1]
    balanco = model_outputs["balanco"]

    rl_2024 = base_data.balanco["capital_proprio"]["RL_2024"]
    rt_2024 = base_data.balanco["capital_proprio"]["Resultados_Transitados"]
    rt_2025 = float(balanco[balanco.ano == 2025]["resultados_transitados"].iloc[0])

    assert abs(rt_2025 - (rt_2024 + rl_2024)) < 0.01, (
        f"RT 2025: esperado {rt_2024 + rl_2024:,.2f} € (sem deduções), "
        f"obtido {rt_2025:,.2f} €"
    )
