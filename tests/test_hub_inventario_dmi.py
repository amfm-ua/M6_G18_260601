"""Regressão: libertação de inventário modelada via dias de DMI (não escalar fixo).

Antes destas alterações, o driver de inventário era um escalar (`libertacao_inventario`)
sombreado por `libertacao_cronograma` → o VAL era totalmente insensível a ele (driver
morto, swing 0 no tornado, correlação ~0 no Monte Carlo). Estes testes garantem que o
driver físico (dias de DMI × CMVMC_prod) está vivo e move o VAL.
"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

from src.engine.projetos.hub_logistico import load, viabilidade_hub
from src.engine.projetos.hub_logistico.impacto import hub_inventario_release
from src.engine.projetos.hub_logistico.viabilidade import sensibilidade_hub, tornado_hub
from src.engine.projetos.monte_carlo_hub import monte_carlo_hub


def test_release_estrutura_clearing_mais_step_down():
    """2026 = clearing + step-down estrutural; anos seguintes = recorrente positivo."""
    hub = load()
    rel = hub_inventario_release(hub)

    # 2025 (pré-arranque) não liberta
    assert rel[2025]["total"] == 0.0
    # 2026 concentra clearing (€950 k) + step-down estrutural (20 d × CMVMC_prod/365)
    assert rel[2026]["total"] > 1_500_000
    assert rel[2026]["clearing"] > 0 and rel[2026]["estrutural"] > 0
    # Recorrente positivo mas muito menor (cresce só com ΔCMVMC_prod); só estrutural
    assert rel[2027]["clearing"] == 0.0
    assert 0 < rel[2027]["estrutural"] < 200_000


def test_dmi_reducao_dias_move_val():
    """Anti-driver-morto: variar os dias de DMI tem de mover o VAL."""
    hub = load()
    vals = [
        float(sensibilidade_hub("dmi_reducao_dias", [d], hub)["val"].iloc[0])
        for d in (0, 20, 40)
    ]
    # Mais dias de redução → mais libertação → maior VAL (monótono crescente)
    assert vals[0] < vals[1] < vals[2]
    # E o efeito é material (não residual)
    assert vals[2] - vals[0] > 500_000


def test_tornado_dmi_tem_swing():
    """A linha de DMI do tornado deixa de ter swing nulo."""
    df = tornado_hub(load())
    linha = df[df["driver"] == "dmi_reducao_dias"]
    assert not linha.empty
    assert float(linha["impacto_total"].iloc[0]) > 100_000


def test_monte_carlo_drivers_dmi_correlacionam():
    """No MC, os drivers de DMI deixam de ter correlação ~0 com o VAL."""
    r = monte_carlo_hub(n_simulations=1500, seed=42)
    corr = r["correlacoes_val"]
    assert "dmi_clearing_dias" in corr
    # O clearing (maior parcela) tem de correlacionar positivamente e de forma não-trivial
    assert corr["dmi_clearing_dias"] > 0.05
