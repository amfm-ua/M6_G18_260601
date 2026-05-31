"""
Módulo: engine/modelo/covenants.py — Validação de Covenants e Política Financeira
Idioma: Português Europeu

Distingue entre:
  - Covenants bancários contratuais (vinculativos): ND/EBITDA ≤ 3,5× e AF ≥ 30%
  - Política/estratégia de gestão (flags, não breach): gearing 40–65%
  - Métricas informativas (reportadas, não avaliadas): DSCR, cobertura de juros
"""

from __future__ import annotations

import pandas as pd


def avaliar_covenants(df_kpis: pd.DataFrame, a) -> pd.DataFrame:
    """Por ano: valor de cada métrica, limiar e estado de cumprimento.

    Colunas de saída:
      ano,
      nd_ebitda, nd_ebitda_ok,             # covenant bancário (ND/EBITDA ≤ 3,5×)
      autonomia, autonomia_ok,              # covenant bancário (AF ≥ 30%)
      covenants_todos_ok, n_breaches,       # só os 2 covenants bancários acima
      gearing, gearing_abaixo_banda,        # política estratégica (flag)
      gearing_acima_banda,                  # política estratégica (flag)
      autonomia_meta_ok,                    # buffer interno 35% (soft)
      dscr, cobertura_juros                 # informativas
    """
    cov = (a.raw.get("covenants") or {}) if a is not None else {}

    nd_max = float(cov.get("nd_ebitda_max", 3.5))
    af_min = float(cov.get("autonomia_financeira_min", 0.30))
    gearing_min = float(cov.get("gearing_min", 0.40))
    gearing_max = float(cov.get("gearing_max", 0.65))
    af_meta = float(cov.get("autonomia_financeira_meta", 0.35))

    rows = []
    for _, kpi in df_kpis.sort_values("ano").iterrows():
        nd = float(kpi.get("nd_ebitda", 0.0))
        af = float(kpi.get("autonomia_financeira", 0.0))
        gear = float(kpi.get("gearing", 0.0))
        dscr = float(kpi.get("dscr", 0.0))
        cob_juros = float(kpi.get("cobertura_juros", 0.0))

        # Covenants bancários vinculativos
        nd_ok = nd <= nd_max
        af_ok = af >= af_min
        todos_ok = nd_ok and af_ok
        n_breaches = (0 if nd_ok else 1) + (0 if af_ok else 1)

        # Flags estratégicas (não breach contratual)
        gear_abaixo = gear < gearing_min
        gear_acima = gear > gearing_max
        af_meta_ok = af >= af_meta

        rows.append({
            "ano": int(kpi["ano"]),
            "nd_ebitda": nd,
            "nd_ebitda_ok": nd_ok,
            "autonomia": af,
            "autonomia_ok": af_ok,
            "covenants_todos_ok": todos_ok,
            "n_breaches": n_breaches,
            "gearing": gear,
            "gearing_abaixo_banda": gear_abaixo,
            "gearing_acima_banda": gear_acima,
            "autonomia_meta_ok": af_meta_ok,
            "dscr": dscr,
            "cobertura_juros": cob_juros,
        })

    return pd.DataFrame(rows)


def headroom_divida(df_kpis: pd.DataFrame, a) -> pd.DataFrame:
    """Headroom de dívida face ao teto estratégico de gearing.

    Colunas:
      ano, gearing, divida_max_para_teto, headroom_eur

    divida_max_para_teto = gearing_max × (DL + CP) — em caixa ou dívida, depende do sinal.
    headroom_eur = divida_max - divida_liquida_atual (positivo = espaço para mais dívida).

    Nota: não implementa sizing endógeno automático (risco de circularidade).
    O sizing dinâmico ao alvo requer solver iterativo — trabalho futuro.
    """
    cov = (a.raw.get("covenants") or {}) if a is not None else {}
    gearing_max = float(cov.get("gearing_max", 0.65))

    rows = []
    for _, kpi in df_kpis.sort_values("ano").iterrows():
        dl = float(kpi.get("divida_liquida", 0.0))
        cp_val = float(kpi.get("cp", 0.0))
        gear = float(kpi.get("gearing", 0.0))
        capital_total = dl + cp_val
        divida_max = gearing_max * capital_total if capital_total > 0 else 0.0
        headroom = divida_max - dl

        rows.append({
            "ano": int(kpi["ano"]),
            "gearing": gear,
            "divida_max_para_teto": divida_max,
            "headroom_eur": headroom,
        })

    return pd.DataFrame(rows)
