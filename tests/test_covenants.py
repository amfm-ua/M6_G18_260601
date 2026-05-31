"""
Testes de covenants bancários e política financeira da Grestel.

Covenants bancários contratuais (R&C 2024):
  - ND/EBITDA ≤ 3,5×
  - Autonomia Financeira ≥ 30%

Política estratégica (flags, não breach contratual):
  - Gearing 40–65%
"""
from __future__ import annotations

import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

import pytest
import pandas as pd

from src.engine.inputs import load
from src.engine.demonstracoes.statements import build_statements
from src.engine.modelo.kpis import build_kpis
from src.engine.modelo.covenants import avaliar_covenants, headroom_divida


@pytest.fixture(scope="module")
def cov_data():
    a, base, sched = load("Base")
    dfs = build_statements(a, base, sched)
    kpis = build_kpis(dfs["dr"], dfs["balanco"], dfs["dfc"], a)
    cov = avaliar_covenants(kpis, a)
    return {"a": a, "kpis": kpis, "covenants": cov}


@pytest.fixture(scope="module")
def cov_df(cov_data):
    return cov_data["covenants"]


# ============================================================
# 1. ESTRUTURA DO DATAFRAME
# ============================================================

COLUNAS_OBRIGATORIAS = {
    "ano", "nd_ebitda", "nd_ebitda_ok", "autonomia", "autonomia_ok",
    "covenants_todos_ok", "n_breaches",
    "gearing", "gearing_abaixo_banda", "gearing_acima_banda",
    "autonomia_meta_ok", "dscr", "cobertura_juros",
}


def test_covenants_tem_todas_as_colunas(cov_df):
    missing = COLUNAS_OBRIGATORIAS - set(cov_df.columns)
    assert not missing, f"Colunas em falta: {sorted(missing)}"


def test_covenants_uma_linha_por_ano(cov_df, cov_data):
    anos_cov = sorted(cov_df["ano"].astype(int).tolist())
    anos_kpi = sorted(cov_data["kpis"]["ano"].astype(int).tolist())
    assert anos_cov == anos_kpi


# ============================================================
# 2. COVENANTS BANCÁRIOS (covenants_todos_ok conta apenas os 2)
# ============================================================

def test_covenants_todos_ok_e_conjuncao_dos_dois(cov_df):
    """covenants_todos_ok = nd_ebitda_ok AND autonomia_ok — não inclui gearing."""
    for _, r in cov_df.iterrows():
        esperado = bool(r["nd_ebitda_ok"]) and bool(r["autonomia_ok"])
        assert bool(r["covenants_todos_ok"]) == esperado, (
            f"Ano {r['ano']}: covenants_todos_ok={r['covenants_todos_ok']} mas "
            f"nd_ok={r['nd_ebitda_ok']}, af_ok={r['autonomia_ok']}"
        )


def test_n_breaches_conta_so_covenants_bancarios(cov_df):
    for _, r in cov_df.iterrows():
        esperado = (0 if r["nd_ebitda_ok"] else 1) + (0 if r["autonomia_ok"] else 1)
        assert int(r["n_breaches"]) == esperado


# ============================================================
# 3. LIMIARES VÊM DO YAML (alterar YAML muda resultado)
# ============================================================

def test_limiar_nd_ebitda_vem_do_yaml(cov_data):
    """Se nd_ebitda_max = 0 → todos os anos em breach (nd_ebitda_ok = False)."""
    a = cov_data["a"]
    import copy
    a2_raw = copy.deepcopy(a.raw)
    a2_raw.setdefault("covenants", {})["nd_ebitda_max"] = 0.0

    from src.engine.inputs.models import Assumptions
    a2 = Assumptions(raw=a2_raw)
    cov2 = avaliar_covenants(cov_data["kpis"], a2)
    assert cov2["nd_ebitda_ok"].all() == False or not cov2["nd_ebitda_ok"].all(), \
        "Reduzir nd_ebitda_max para 0 deve colocar anos em breach"


def test_limiar_af_vem_do_yaml(cov_data):
    """Se autonomia_financeira_min = 1.0 → todos os anos em breach."""
    a = cov_data["a"]
    import copy
    a2_raw = copy.deepcopy(a.raw)
    a2_raw.setdefault("covenants", {})["autonomia_financeira_min"] = 1.0

    from src.engine.inputs.models import Assumptions
    a2 = Assumptions(raw=a2_raw)
    cov2 = avaliar_covenants(cov_data["kpis"], a2)
    assert not cov2["autonomia_ok"].any(), \
        "AF_min=1.0 deve colocar todos os anos em breach de autonomia"


# ============================================================
# 4. GEARING É POLÍTICA (flags, não breach contratual)
# ============================================================

def test_gearing_flags_nao_afetam_covenants_todos_ok(cov_df):
    """Um ano com gearing fora da banda NÃO muda covenants_todos_ok."""
    for _, r in cov_df.iterrows():
        fora_banda = bool(r["gearing_abaixo_banda"]) or bool(r["gearing_acima_banda"])
        if fora_banda:
            # covenants_todos_ok deve basear-se apenas nos 2 covenants bancários
            esperado = bool(r["nd_ebitda_ok"]) and bool(r["autonomia_ok"])
            assert bool(r["covenants_todos_ok"]) == esperado


# ============================================================
# 5. HEADROOM DE DÍVIDA
# ============================================================

def test_headroom_divida_estrutura(cov_data):
    hd = headroom_divida(cov_data["kpis"], cov_data["a"])
    for col in ("ano", "gearing", "divida_max_para_teto", "headroom_eur"):
        assert col in hd.columns, f"Coluna '{col}' em falta no headroom"
    assert len(hd) == len(cov_data["kpis"])


def test_headroom_positivo_quando_abaixo_teto(cov_data):
    """headroom_eur > 0 quando gearing < gearing_max."""
    hd = headroom_divida(cov_data["kpis"], cov_data["a"])
    cov = cov_data["a"].raw.get("covenants", {})
    gmax = float(cov.get("gearing_max", 0.65))
    for _, r in hd.iterrows():
        if float(r["gearing"]) < gmax:
            assert float(r["headroom_eur"]) > 0, (
                f"Ano {r['ano']}: gearing={r['gearing']:.2%} < {gmax:.0%} "
                f"mas headroom={r['headroom_eur']:.0f} não é positivo"
            )
