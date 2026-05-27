from __future__ import annotations

from ...inputs import Assumptions, Schedules, MESES


# ──────────────────────────────────────────────────────────────────────────────
# Auxiliares internos
# ──────────────────────────────────────────────────────────────────────────────

def _financiamento_mensal(sched: Schedules) -> dict[str, dict]:
    """Distribui serviço da dívida bancária 2025 por mês, uniforme ÷12.

    Amortização = variação anual em Empréstimos NC+C.
    As responsabilidades de locação financeira estão em Outros PC e a sua
    amortização é capturada via ΔOutros_PC no ajuste de NFM da DFC, evitando
    dupla contagem e mantendo a reconciliação DFC-Balanço ≈ 0.
    """
    nc_ini = sched.financiamento["emprestimos_NC"][2024]
    nc_fin = sched.financiamento["emprestimos_NC"][2025]
    c_ini = sched.financiamento["emprestimos_C"][2024]
    c_fin = sched.financiamento["emprestimos_C"][2025]

    amort_banco = (nc_ini + c_ini - nc_fin - c_fin) / 12.0
    juros_a = sched.financiamento["juros_total"][2025]

    d = {
        "amortizacao": amort_banco,
        "juros": juros_a / 12.0,
    }

    return {m: d for m in MESES}


def _capex_mensal(sched: Schedules) -> dict[str, dict]:
    """Distribui CAPEX e depreciação 2025 por mês, uniforme ÷12."""
    inv = sched.investimento

    dep_total_a = inv["total_dep_amort_dr"][2025]
    dep_aft_a = inv["depreciacao_aft_anual"][2025]

    d = {
        "capex_aft": inv["novo_investimento_aft"][2025] / 12.0,
        "capex_int": inv["novo_investimento_intang"][2025] / 12.0,
        "dep_aft": dep_aft_a / 12.0,
        "dep_int": (dep_total_a - dep_aft_a) / 12.0,
        "dep_total": dep_total_a / 12.0,
    }

    return {m: d for m in MESES}


def _interp(ini: float, fin: float, m_idx: int) -> float:
    """Valor no fim do mês m_idx, onde 0=Jan e 11=Dez, por interpolação linear."""
    return ini + (m_idx + 1) / 12.0 * (fin - ini)


# ──────────────────────────────────────────────────────────────────────────────
# Hub Logístico: impacto mensal no Balanço e DFC
# ──────────────────────────────────────────────────────────────────────────────

def _hub_monthly_impact(a: Assumptions) -> dict | None:
    """Impacto mensal do Hub Logístico no Balanço e DFC de 2025.

    Retorna dict com:
      meses: {mes: {capex, juros_cap, juros_pagos, desembolso}}
      nc:    saldo NC hub constante (carência 2025-2027 → sem amortização)
      c:     saldo C hub constante em 2025
    None se hub desativado ou dados ausentes.

    Metodologia:
      • CAPEX mensal: perfil do cronograma_mensal do YAML → fluxo_investimento
      • Juros 2025 capitalizados (NCRF 10): aumentam custo do AFT, NÃO DR;
        são SEMPRE saída de caixa real (NCRF 2 §33b) → fluxo_financiamento
      • Desembolso bancário: Janeiro 2025 (única entrada) → fluxo_financiamento
      • NC/C constantes em 2025 (sem amortização durante a carência)
    """
    raw_hub = a.raw.get("hub_logistico", {})
    if not raw_hub.get("incluir_hub", False):
        return None

    try:
        from ...projetos import hub_logistico as hub_mod

        df_fin = hub_mod.hub_financing(raw_hub)
        jc_map = hub_mod._juros_capitalizados_map(raw_hub)

        fin_2025 = df_fin[df_fin.ano == 2025].iloc[0]
        hub_nc         = float(fin_2025["emprestimos_nc"])
        hub_c          = float(fin_2025["emprestimos_c"])
        hub_desembolso = float(fin_2025["desembolso"])
        hub_juros_anual = float(fin_2025["juros"])  # total cash outflow

        juros_m = hub_juros_anual / 12.0
        jc_m    = jc_map.get(2025, 0.0) / 12.0  # capitalizado → aumenta AFT

        # CAPEX mensal do cronograma (lowercase → MESES capitalizados)
        cron_proj = raw_hub.get("projeto_hub", {}).get("cronograma_mensal", {})
        cron_2025 = cron_proj.get("2025", cron_proj.get(2025, {}))
        _lower = {m.lower(): m for m in MESES}
        capex_por_mes: dict[str, float] = {m: 0.0 for m in MESES}
        for k, v in cron_2025.items():
            mes = _lower.get(str(k).lower())
            if mes:
                capex_por_mes[mes] = float(v)

        # Normalizar para que o total mensal coincida com o CAPEX anual.
        # cronograma_mensal define o perfil de obra mas o total deve fechar
        # com o cronograma anual usado no Balanco/DFC anual (articulacao M3-M6).
        df_cap_hub = hub_mod.hub_capex(raw_hub)
        _cap_2025_row = df_cap_hub[df_cap_hub.ano == 2025]
        capex_anual_2025 = float(_cap_2025_row["capex"].iloc[0]) if not _cap_2025_row.empty else 0.0
        _total_mes = sum(capex_por_mes.values())
        if _total_mes > 0 and abs(_total_mes - capex_anual_2025) > 1.0:
            _fct = capex_anual_2025 / _total_mes
            capex_por_mes = {m: v * _fct for m, v in capex_por_mes.items()}

        meses_data = {
            m: {
                "capex":       capex_por_mes[m],
                "juros_cap":   jc_m,
                "juros_pagos": juros_m,
                "desembolso":  hub_desembolso if i == 0 else 0.0,
            }
            for i, m in enumerate(MESES)
        }
        return {"meses": meses_data, "nc": hub_nc, "c": hub_c}

    except Exception:
        return None
