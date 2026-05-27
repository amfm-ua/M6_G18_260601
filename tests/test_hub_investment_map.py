import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / 'src'))

from src.api.routes.hub import get_hub_investment_map


def test_investment_map_has_sintese():
    result = get_hub_investment_map()
    assert "sintese" in result


def test_investment_map_nfm_rows_have_acumulada_and_pct():
    result = get_hub_investment_map()
    nfm_rows = result["nfm"]
    assert nfm_rows, "nfm deve ter pelo menos uma linha"
    for row in nfm_rows:
        assert "delta_nfm" in row
        assert "nfm_acumulada" in row
        assert "nfm_pct_capex" in row


def test_investment_map_sintese_balanceado():
    """Total Investimento == Total Financiamento (check_diferenca == 0)."""
    result = get_hub_investment_map()
    s = result["sintese"]
    assert s["balanceado"], (
        f"Síntese não balanceada: diferença = {s['check_diferenca']}"
    )
    assert s["check_diferenca"] == 0.0


def test_investment_map_sintese_totais_coerentes():
    """CAPEX + NFM == Banco + PT2030 + Fundos Próprios."""
    result = get_hub_investment_map()
    s = result["sintese"]
    assert abs(s["total_investimento"] - (s["capex_base"] + s["nfm_acumulada"])) < 0.01
    assert abs(
        s["total_financiamento"]
        - (s["banco_hub_montante"] + s["pt2030_montante"] + s["fundos_proprios"])
    ) < 0.01


def test_investment_map_pcts_somam_100():
    """% Banco + % PT2030 + % Fundos Próprios == 100%."""
    result = get_hub_investment_map()
    s = result["sintese"]
    total_pct = s["banco_hub_pct"] + s["pt2030_pct"] + s["fundos_proprios_pct"]
    assert abs(total_pct - 1.0) < 1e-9, f"Percentagens não somam 100%: {total_pct}"


def test_investment_map_tem_fonte_nfm():
    """Síntese deve indicar explicitamente a fonte de financiamento da NFM."""
    result = get_hub_investment_map()
    s = result["sintese"]
    assert "fonte_nfm" in s
    assert isinstance(s["fonte_nfm"], str)
    assert len(s["fonte_nfm"]) > 0


def test_investment_map_tem_situacao_financiamento():
    """Síntese deve ter campo situacao_financiamento para diagnóstico."""
    result = get_hub_investment_map()
    s = result["sintese"]
    assert "situacao_financiamento" in s
    assert s["situacao_financiamento"] in ("equilibrado", "sobrefinanciado")


def test_investment_map_nfm_acumulada_monotonica():
    """NFM acumulada deve ser não decrescente (ΔNFM pode ser 0 mas não negativo em arranque)."""
    result = get_hub_investment_map()
    nfm_rows = result["nfm"]
    acumuladas = [row["nfm_acumulada"] for row in nfm_rows]
    for i in range(1, len(acumuladas)):
        assert acumuladas[i] >= acumuladas[i - 1] - 0.01, (
            f"NFM acumulada decresce entre anos: {acumuladas[i-1]} → {acumuladas[i]}"
        )
