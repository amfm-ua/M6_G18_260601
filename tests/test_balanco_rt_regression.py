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
    """RT[y] = RT[y-1] + RL[y-1] - payout - dotação_reserva (com teto CSC art. 295.º).

    A dotação da reserva legal está limitada a 20% do capital social: a apropriação
    de cada ano é min(RL_prev * reserva_legal_pct, teto - reserva_acumulada). Verifica
    a fórmula contra os próprios valores do DR/Balanço, replicando o mesmo teto.
    """
    a, base, sched = load("Base")
    payout = a.distribuicao["payout_ratio"]
    reserva = a.distribuicao.get("reserva_legal_pct", 0.0)
    inicio_div = a.distribuicao["ano_inicio_distribuicao"]

    dr = model_outputs["dr"]
    balanco = model_outputs["balanco"]

    capital_social = float(balanco[balanco.ano == 2025]["capital_social"].iloc[0])
    teto = 0.20 * capital_social

    for ano in (2026, 2027, 2028, 2029):
        rl_prev = float(dr[dr.ano == (ano - 1)]["rl"].iloc[0])
        rl_cur = float(dr[dr.ano == ano]["rl"].iloc[0])
        rt_prev = float(balanco[balanco.ano == (ano - 1)]["resultados_transitados"].iloc[0])
        rt_cur = float(balanco[balanco.ano == ano]["resultados_transitados"].iloc[0])
        reserva_leg_prev = float(balanco[balanco.ano == (ano - 1)]["reservas_legais"].iloc[0])

        if rl_cur > 0 and ano >= inicio_div:
            dotacao = max(0.0, min(rl_prev * reserva, teto - reserva_leg_prev))
            expected = rt_prev + rl_prev - rl_prev * payout - dotacao
        else:
            expected = rt_prev + rl_prev

        assert abs(rt_cur - expected) < 0.01, (
            f"RT {ano}: esperado {expected:,.2f} €, obtido {rt_cur:,.2f} €"
        )


def test_reserva_legal_respeita_teto_csc_295(model_outputs):
    """A reserva legal não cresce acima do teto de 20% do capital social (CSC art. 295.º).

    A Grestel já entra no horizonte com reserva legal acima de 20% do capital social
    (~27%), pelo que a dotação obrigatória cessa: reservas_legais mantém-se constante
    e RT deixa de ser penalizado por nova dotação. Regressão directa do teto — sem ele
    a reserva crescia ~5% do RL por ano, indefinidamente.
    """
    a, base, sched = load("Base")
    reserva = a.distribuicao.get("reserva_legal_pct", 0.0)

    if reserva == 0.0:
        pytest.skip("reserva_legal_pct é zero — teste de regressão não aplicável")

    balanco = model_outputs["balanco"]
    capital_social = float(balanco[balanco.ano == 2025]["capital_social"].iloc[0])
    teto = 0.20 * capital_social

    reserva_2025 = float(balanco[balanco.ano == 2025]["reservas_legais"].iloc[0])

    # Pré-condição do cenário: já acima do teto legal → dotação deve cessar.
    assert reserva_2025 > teto, (
        f"Pré-condição falhou: reserva 2025 ({reserva_2025:,.0f} €) não excede "
        f"o teto ({teto:,.0f} €) — rever este teste se o capital social mudou"
    )

    for ano in (2026, 2027, 2028, 2029):
        reserva_ano = float(balanco[balanco.ano == ano]["reservas_legais"].iloc[0])
        assert abs(reserva_ano - reserva_2025) < 0.01, (
            f"Reserva legal {ano} ({reserva_ano:,.0f} €) cresceu face a 2025 "
            f"({reserva_2025:,.0f} €) apesar de já exceder 20% do capital social"
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
