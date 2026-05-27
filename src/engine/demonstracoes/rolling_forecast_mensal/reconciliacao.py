from __future__ import annotations

import pandas as pd

from ...inputs import Assumptions, Base2024, Schedules


# ──────────────────────────────────────────────────────────────────────────────
# Reconciliação Mensal-Anual
# ──────────────────────────────────────────────────────────────────────────────

def build_reconciliacao_mensal_anual(
    a: "Assumptions",
    base: "Base2024",
    df_bs: pd.DataFrame,
    df_dr_m: pd.DataFrame,
    df_dfc_m: pd.DataFrame,
    sched: Schedules,
    stmt: dict | None = None,
) -> dict:
    """Compara o fecho de Dezembro do loop mensal com o modelo anual 2025 (live).

    A referência anual é o modelo anual calculado on-the-fly (via build_statements
    se stmt não for passado), garantindo que compara sempre contra o modelo atual.

    Desvio = mensal − anual. Zero significa articulação perfeita.

    Args:
        stmt: resultado de build_statements() pré-calculado (evita double call).
              Se None, calcula internamente.

    Returns:
        dict com três secções:
          balanco_dezembro  — itens do Balanço em Dez vs Balanço anual 2025
          dr_soma_vs_anual  — soma dos 12 meses do DR vs DR anual 2025
          dfc_consolidado   — fluxos acumulados e reconciliação de Caixa
    """
    if stmt is None:
        from ..statements import build_statements
        stmt = build_statements(a, base, sched)

    df_bs_anual = stmt["balanco"]
    df_dr_anual = stmt["dr"]

    anual_b = df_bs_anual[df_bs_anual["ano"] == 2025].iloc[0]
    anual_dr = df_dr_anual[df_dr_anual["ano"] == 2025].iloc[0]

    dez = df_bs[df_bs["mes"] == "Dez"].iloc[0]

    def _it(mensal_val: float, ref_val: float) -> dict:
        return {
            "mensal": round(mensal_val),
            "ref_anual": round(ref_val),
            "desvio": round(mensal_val - ref_val),
        }

    # ── Balanço: fecho de Dezembro vs Balanço anual 2025 ─────────────────────
    balanco = {
        "aft_liquido":      _it(dez["aft_liquido"],      float(anual_b["aft_liquido"])),
        "inventarios":      _it(dez["inventarios"],      float(anual_b["inventarios"])),
        "clientes":         _it(dez["clientes"],         float(anual_b["clientes"])),
        "eoep_devedor":     _it(dez["eoep_devedor"],     float(anual_b["eoep_devedor"])),
        "caixa":            _it(dez["caixa"],            float(anual_b["caixa"])),
        "total_ac":         _it(dez["total_ac"],         float(anual_b["total_ac"])),
        "total_anc":        _it(dez["total_anc"],        float(anual_b["total_anc"])),
        "total_ativo":      _it(dez["total_ativo"],      float(anual_b["total_ativo"])),
        "total_cp":         _it(dez["total_cp"],         float(anual_b["total_cp"])),
        "emprestimos_nc":   _it(dez["emprestimos_nc"],   float(anual_b["emprestimos_nc"])),
        "emprestimos_c":    _it(dez["emprestimos_c"],    float(anual_b["emprestimos_c"])),
        "fornecedores":     _it(dez["fornecedores"],     float(anual_b["fornecedores"])),
        "eoep_credor":      _it(dez["eoep_credor"],      float(anual_b["eoep_credor"])),
        "outros_pc":        _it(dez["outros_pc"],        float(anual_b["outros_pc"])),
        "linha_credito_cp": _it(dez["linha_credito_cp"], float(anual_b["linha_credito_cp"])),
        "total_passivo":    _it(dez["total_passivo"],    float(anual_b["total_passivo"])),
    }

    # ── DR: soma 12 meses vs DR anual 2025 ────────────────────────────────────
    # No DR anual, custos são negativos; no DR mensal, custos são positivos.
    # Negamos os custos do DR anual para comparar na mesma escala.
    dr_soma = df_dr_m[["vn", "cmvmc", "fse", "gastos_pessoal", "ebitda",
                        "depreciacoes", "ebit", "juros", "rl"]].sum()
    dr = {
        "vn":             _it(dr_soma["vn"],             float(anual_dr["vn"])),
        "cmvmc":          _it(dr_soma["cmvmc"],          -float(anual_dr["cmvmc"])),
        "fse":            _it(dr_soma["fse"],            -float(anual_dr["fse"])),
        "gastos_pessoal": _it(dr_soma["gastos_pessoal"], -float(anual_dr["gastos_pessoal"])),
        "ebitda":         _it(dr_soma["ebitda"],         float(anual_dr["ebitda"])),
        "depreciacoes":   _it(dr_soma["depreciacoes"],   -float(anual_dr["depreciacoes"])),
        "ebit":           _it(dr_soma["ebit"],           float(anual_dr["ebit"])),
        "juros":          _it(dr_soma["juros"],          -float(anual_dr["juros"])),
        "rl":             _it(dr_soma["rl"],             float(anual_dr["rl"])),
    }

    # ── DFC: fluxos acumulados e reconciliação de Caixa ───────────────────────
    dfc_soma = df_dfc_m[
        ["fluxo_operacional", "fluxo_investimento", "fluxo_financiamento", "variacao_caixa"]
    ].sum()

    caixa_ini = int(df_dfc_m["caixa_abertura"].iloc[0])
    caixa_fim = int(df_dfc_m["caixa_fecho"].iloc[-1])

    dfc = {
        "fluxo_operacional":    round(dfc_soma["fluxo_operacional"]),
        "fluxo_investimento":   round(dfc_soma["fluxo_investimento"]),
        "fluxo_financiamento":  round(dfc_soma["fluxo_financiamento"]),
        "variacao_caixa_total": round(dfc_soma["variacao_caixa"]),
        "caixa_abertura_jan":   caixa_ini,
        "caixa_fecho_dez":      caixa_fim,
        "ref_caixa_dez_anual":  round(float(anual_b["caixa"])),
        "desvio_caixa":         caixa_fim - round(float(anual_b["caixa"])),
    }

    return {
        "balanco_dezembro": balanco,
        "dr_soma_vs_anual": dr,
        "dfc_consolidado": dfc,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Opção B — overlay mensal Dezembro → Balanço anual 2025
# ──────────────────────────────────────────────────────────────────────────────

def _overlay_dez_mensal_no_anual(
    df_bs_mensal: pd.DataFrame,
    df_balanco_anual: pd.DataFrame,
) -> pd.DataFrame:
    """Substitui a linha 2025 do Balanço anual pelos valores de Dezembro do mensal.

    Implementa Option B: M3 DFC-first é a fonte de verdade para 2025.
    As linhas 2026-2029 ficam inalteradas mas o DFC anual passará a usar os
    valores mensais como fecho de 2025 (abertura de 2026), propagando M3→M6→OE4.

    Colunas com breakdown detalhado de CP e ANC (goodwill, reservas, etc.)
    mantêm-se do modelo anual — só os totais e os itens NFM/caixa são
    substituídos pelo mensal.
    """
    dez = df_bs_mensal[df_bs_mensal["mes"] == "Dez"].iloc[0]

    # Colunas NFM + caixa + financiamento + totais — computadas pelo DFC-first
    _OVERLAY = [
        "aft_liquido", "total_anc",
        "aplicacoes_fin_cp", "inventarios", "clientes",
        "eoep_devedor", "outros_ac", "caixa",
        "total_ac", "total_ativo",
        "total_cp",
        "emprestimos_nc", "emprestimos_c",
        "fornecedores", "eoep_credor", "outros_pc",
        "linha_credito_cp", "total_passivo", "total_cp_passivo",
    ]

    df = df_balanco_anual.copy()
    mask = df["ano"] == 2025
    for col in _OVERLAY:
        if col in dez.index and col in df.columns:
            df.loc[mask, col] = float(dez[col])

    df.loc[mask, "controlo"] = (
        df.loc[mask, "total_cp_passivo"] - df.loc[mask, "total_ativo"]
    )
    return df
