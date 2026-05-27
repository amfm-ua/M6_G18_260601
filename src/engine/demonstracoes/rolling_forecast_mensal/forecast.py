from __future__ import annotations

import copy
from typing import Optional, Dict, Any

import pandas as pd

from ...inputs import Assumptions, Base2024, Schedules
from ...financiamento import tesouraria as teso_mod
from .integrado import _build_integrated_monthly
from .mensais import build_nfm_mensal, build_tesouraria_completa, build_linha_summary
from .reconciliacao import build_reconciliacao_mensal_anual, _overlay_dez_mensal_no_anual


# ──────────────────────────────────────────────────────────────────────────────
# Ponto de Entrada
# ──────────────────────────────────────────────────────────────────────────────

def build_rolling_forecast(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
    ov: Optional[Dict[str, Any]] = None,
) -> dict:
    """Constrói todas as demonstrações mensais articuladas (M3) e propaga para M6/OE4.

    Fluxo Option B — M3 → M6 → OE4:
      1. Modelo mensal DFC-first — fonte de verdade para 2025
      2. Modelo anual DR + Balanço + DFC construídos independentemente
      3. Linha 2025 do Balanço anual substituída pelo fecho de Dezembro mensal
      4. DFC anual reconstruída com o Balanço híbrido — 2026-2029 usam o
         fecho mensal de 2025 como abertura, propagando M3 → M6 → OE4
    """
    from ..dr import build_dr as _build_dr_anual
    from ..balanco import build_balanco as _build_balanco_anual
    from ..dfc import build_dfc as _build_dfc_anual

    # ── 1. Modelo mensal DFC-first ────────────────────────────────────────────
    df_dr = teso_mod.build_dr_mensal(a, base, sched)
    df_t  = teso_mod.build_tesouraria(a, base, sched)
    df_bs, df_dfc = _build_integrated_monthly(a, base, sched, df_dr, df_t)

    df_nfm = build_nfm_mensal(df_bs, df_dr)
    df_tc  = build_tesouraria_completa(a, base, sched, df_bs=df_bs)
    _vn_anual = float(df_dr["vn"].sum()) if "vn" in df_dr.columns else 40_000_000.0
    linha_sum = build_linha_summary(df_bs, _vn_anual, a)

    # ── 2. Modelo anual independente (DR → Balanço → DFC) ────────────────────
    df_dr_anual     = _build_dr_anual(a, base, sched)
    df_bs_anual_raw = _build_balanco_anual(a, base, sched, df_dr_anual)

    # ── 3. Opção B: fecho Dez mensal ancora Balanço anual 2025 ───────────────
    df_bs_hibrido = _overlay_dez_mensal_no_anual(df_bs, df_bs_anual_raw)

    # ── 4. DFC anual reconstruída — 2026-2029 partem do fecho mensal 2025 ────
    df_dfc_anual = _build_dfc_anual(a, df_dr_anual, df_bs_hibrido, sched, base)

    stmt_m6 = {
        "dr":      df_dr_anual,
        "balanco": df_bs_hibrido,
        "dfc":     df_dfc_anual,
    }

    # ── 5. Reconciliação DR/DFC (Balanço Dez = anual 2025 por construção) ────
    reconciliacao = build_reconciliacao_mensal_anual(
        a, base, df_bs, df_dr, df_dfc, sched, stmt=stmt_m6
    )

    return {
        "dr_mensal":           df_dr,
        "balanco_mensal":      df_bs,
        "dfc_mensal":          df_dfc,
        "nfm_mensal":          df_nfm,
        "tesouraria_completa": df_tc,
        "reconciliacao_anual": reconciliacao,
        "stmt_m6":             stmt_m6,
        "linha_summary":       linha_sum,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Rolling Forecast Dual: sem projeto vs. com projeto
# ──────────────────────────────────────────────────────────────────────────────

def _build_comparacao_dual(rf_sem: dict, rf_com: dict) -> list[dict]:
    """Tabela comparativa sem/com projeto para as métricas da linha rotativa."""
    s = rf_sem.get("linha_summary", {})
    c = rf_com.get("linha_summary", {})

    def _d(key: str):
        vs, vc = s.get(key), c.get(key)
        if isinstance(vs, (int, float)) and isinstance(vc, (int, float)):
            return round(vc - vs, 1)
        return None

    return [
        {"metrica": "Pico da linha (€)",      "sem_projeto": s.get("pico_linha"),        "com_projeto": c.get("pico_linha"),        "delta": _d("pico_linha")},
        {"metrica": "Mês do pico",             "sem_projeto": s.get("mes_do_pico"),       "com_projeto": c.get("mes_do_pico"),       "delta": None},
        {"metrica": "Drawdown médio (€)",      "sem_projeto": s.get("drawdown_medio"),    "com_projeto": c.get("drawdown_medio"),    "delta": _d("drawdown_medio")},
        {"metrica": "Juros anuais linha (€)",  "sem_projeto": s.get("juros_anuais_linha"), "com_projeto": c.get("juros_anuais_linha"), "delta": _d("juros_anuais_linha")},
        {"metrica": "Saldo final 31-Dez (€)",  "sem_projeto": s.get("saldo_final_31dez"), "com_projeto": c.get("saldo_final_31dez"), "delta": _d("saldo_final_31dez")},
        {"metrica": "Nº meses com gap > 0",    "sem_projeto": s.get("n_meses_gap"),       "com_projeto": c.get("n_meses_gap"),       "delta": _d("n_meses_gap")},
        {"metrica": "Rácio pico/VN (%)",       "sem_projeto": s.get("racio_pico_vn_pct"), "com_projeto": c.get("racio_pico_vn_pct"), "delta": _d("racio_pico_vn_pct")},
    ]


def build_rolling_dual(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
) -> dict:
    """Corre rolling forecast em paralelo para sem projeto (hub_on=False) e com projeto
    (hub_on=True), devolvendo ambos os resultados e uma tabela comparativa.

    Args:
        a: pressupostos base (hub_on será sobreposto internamente).
        base: dados históricos 2024.
        sched: schedules computados.

    Returns:
        {
          "sem_projeto": dict (output de build_rolling_forecast),
          "com_projeto": dict (idem),
          "comparacao": list[dict] com tabela lado-a-lado,
          "alertas_sem": list,
          "alertas_com": list,
        }
    """
    a_sem = copy.deepcopy(a)
    a_sem.raw.setdefault("hub_logistico", {})["incluir_hub"] = False

    a_com = copy.deepcopy(a)
    a_com.raw.setdefault("hub_logistico", {})["incluir_hub"] = True

    rf_sem = build_rolling_forecast(a_sem, base, sched)
    rf_com = build_rolling_forecast(a_com, base, sched)

    return {
        "sem_projeto": rf_sem,
        "com_projeto": rf_com,
        "comparacao": _build_comparacao_dual(rf_sem, rf_com),
        "alertas_sem": rf_sem.get("linha_summary", {}).get("alertas", []),
        "alertas_com": rf_com.get("linha_summary", {}).get("alertas", []),
    }
