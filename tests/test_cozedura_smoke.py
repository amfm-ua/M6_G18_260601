"""Smoke test do cenário "Cozedura de Baixa Temperatura" (toggle, fora de âmbito M6).

Garante que o toggle continua funcional e isolado: ON expõe o business case com
valores coerentes; OFF não contamina os outputs do caso base.
"""
import pytest

from src.engine.modelo.model import run_model


def test_cozedura_on_expoe_appraisal_coerente():
    dfs = run_model(cenario="Base", cozedura_on=True)

    assert "cozedura_resumo" in dfs
    assert "cozedura_appraisal" in dfs

    r = dfs["cozedura_resumo"]
    # Investimento determinístico do YAML: 200k bruto; 135k líquido (SIFIDE 32,5%).
    assert r["investimento_bruto"] == pytest.approx(200_000, abs=1.0)
    assert r["investimento_liquido"] == pytest.approx(135_000, abs=1.0)
    # Business case positivo e internamente coerente.
    assert r["val"] > 0
    assert r["ganho_ebitda_pleno"] > 0
    assert 0 < r["payback_anos"] < 10
    assert r["payback_regime_anos"] > 0


def test_cozedura_off_nao_expoe_appraisal():
    dfs = run_model(cenario="Base", cozedura_on=False)

    assert "cozedura_resumo" not in dfs
    assert "cozedura_appraisal" not in dfs
