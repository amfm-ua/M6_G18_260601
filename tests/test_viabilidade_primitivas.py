"""Testes unitários das primitivas de avaliação do Hub.

Travam a semântica de desconto de `_npv`, `_irr` e `_npv_variable_wacc`.
Estas funções não tinham cobertura direta — foi essa lacuna que permitiu que o
relatório de um bug afirmasse um impacto inexistente sobre `_npv_variable_wacc`.
Os valores esperados são derivados analiticamente (independentes da implementação).
"""
import pytest

from src.engine.projetos.hub_logistico.viabilidade import (
    _npv,
    _irr,
    _npv_variable_wacc,
)


# ----------------------------------------------------------------------------
# _npv — convenção fim-de-período (NPV Excel: CF[0] descontado em t=1)
# ----------------------------------------------------------------------------

def test_npv_valor_conhecido():
    # 100/1,1 + 100/1,1² + 100/1,1³ = 248,6852 (calculado à parte / Excel)
    assert _npv([100, 100, 100], 0.10) == pytest.approx(248.6852, abs=1e-3)


def test_npv_taxa_zero_e_soma():
    assert _npv([10, 20, 30], 0.0) == pytest.approx(60.0)


# ----------------------------------------------------------------------------
# _irr — bissecção sobre _npv (mesma convenção start=1)
# ----------------------------------------------------------------------------

def test_irr_raiz_exata():
    # -110/1,1 + 121/1,1² = -100 + 100 = 0  ⇒  TIR = 10%
    assert _irr([-110, 121]) == pytest.approx(0.10, abs=1e-4)


def test_irr_sem_mudanca_de_sinal_devolve_none():
    # Sem fluxo negativo não há raiz ⇒ None (não levanta exceção)
    assert _irr([100, 100, 100]) is None


# ----------------------------------------------------------------------------
# _npv_variable_wacc — desconto com taxa variável por período
# ----------------------------------------------------------------------------

def test_variable_wacc_equivale_a_npv_com_taxa_constante():
    """Com WACC constante e o placeholder t=0 (WACC 0), tem de coincidir
    exatamente com _npv — é assim que o call-site real o usa."""
    cfs = [500, -200, 300, 1000]
    r = 0.0646
    assert _npv_variable_wacc([0.0] + cfs, [0.0] + [r] * len(cfs)) == pytest.approx(
        _npv(cfs, r), abs=1e-9
    )


def test_variable_wacc_composicao_correta():
    # 100/1,1 + 100/(1,1×1,2) = 90,9091 + 75,7576 = 166,6667
    assert _npv_variable_wacc([100, 100], [0.10, 0.20]) == pytest.approx(
        166.6667, abs=1e-3
    )


def test_variable_wacc_placeholder_zero_e_no_op():
    """Pré-pender (cf=0, wacc=0) não altera o resultado — multiplicar o fator
    acumulado por (1+0) é neutro. Protege o BUG 1 de reintroduzir o off-by-one."""
    cfs = [500, 300, 1000]
    ws = [0.06, 0.07, 0.08]
    assert _npv_variable_wacc([0.0] + cfs, [0.0] + ws) == pytest.approx(
        _npv_variable_wacc(cfs, ws), abs=1e-9
    )
