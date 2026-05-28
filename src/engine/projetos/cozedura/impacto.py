"""Cozedura de Baixa Temperatura — impacto nas demonstrações e business case.

Modelo de "duas pernas" (mais investimento), faseado pela curva de adoção:

  Perna 1 — Poupança de energia (FSE):
      redução_y = ramp_y × 18% × (Gás×100% + Eletricidade×50%)
    Captura a menor PROCURA de energia ao cozer a 1140 ºC em vez de 1200 ºC.

  Perna 2 — Pasta reformulada (CMVMC):
      incremento_y = ramp_y × cmvmc_incremento_pct × CMVMC_y
    Custo da volastonite (mineral técnico) + moagem mais fina (d50 ~3 µm).

  Investimento (appraisal de viabilidade):
      one-off de I&D/ensaios em 2027, com crédito SIFIDE II, descontado ao WACC
      para VAL e payback. Tratado como projeto autónomo (não consolidado na DR),
      à semelhança de hub_fcf() para o Hub Logístico.

O efeito líquido recorrente (Perna 1 − Perna 2) é injetado na DR consolidada
(dr/build.py), propagando para EBITDA → EBIT → FCFF → avaliação.
"""
from __future__ import annotations

import pandas as pd

from ...inputs import YEARS, ALL_YEARS


def cozedura_ativo(a) -> dict | None:
    """Devolve os pressupostos da cozedura se o toggle estiver ativo, senão None."""
    try:
        coz = a.raw.get("cozedura_baixa_temp", {})
        if not coz or not coz.get("incluir", False):
            return None
        return coz
    except Exception:
        return None


def _ramp(coz: dict, y: int) -> float:
    return float((coz.get("ramp_up") or {}).get(y, 0.0))


def cozedura_fse_reducao(
    coz: dict,
    fse_det_by_year: dict[int, dict[str, float]],
) -> dict[int, float]:
    """Redução anual de FSE de energia (valor positivo = poupança).

    Args:
        coz: Pressupostos do cenário (já validado como ativo).
        fse_det_by_year: Detalhe de FSE por rubrica e ano (já reconciliado),
            chaveado pelos yaml_key ("Gas_Natural", "Eletricidade").
    """
    p = float(coz.get("poupanca_energia_pct", 0.18))
    g_pct = float(coz.get("base_gas_pct", 1.0))
    e_pct = float(coz.get("base_eletricidade_pct", 0.5))

    out: dict[int, float] = {}
    for y in ALL_YEARS:
        ramp = _ramp(coz, y)
        det = fse_det_by_year.get(y, {})
        gas = float(det.get("Gas_Natural", 0.0))
        elec = float(det.get("Eletricidade", 0.0))
        base_elegivel = gas * g_pct + elec * e_pct
        out[y] = ramp * p * base_elegivel
    return out


def cozedura_cmvmc_incremento(
    coz: dict,
    cmvmc_by_year: dict[int, float],
) -> dict[int, float]:
    """Incremento anual de CMVMC pela pasta reformulada (valor positivo = custo)."""
    pct = float(coz.get("cmvmc_incremento_pct", 0.0))
    out: dict[int, float] = {}
    for y in ALL_YEARS:
        ramp = _ramp(coz, y)
        out[y] = ramp * pct * float(cmvmc_by_year.get(y, 0.0))
    return out


def cozedura_gas_eficiencia_anual(coz: dict, base_efic) -> dict[int, float]:
    """Eficiência de gás/peça por ano = base (programa H2) + extra da cozedura.

    base_efic pode ser escalar (aplica-se a todos os anos) ou dict {ano: taxa}.
    """
    extra = coz.get("eficiencia_gas_extra", {}) or {}
    out: dict[int, float] = {}
    for y in YEARS:
        if isinstance(base_efic, dict):
            b = float(base_efic.get(y, 0.0) or 0.0)
        else:
            b = float(base_efic or 0.0)
        out[y] = b + float(extra.get(y, 0.0))
    return out


def cozedura_appraisal(
    coz: dict,
    fse_reducao: dict[int, float],
    cmvmc_inc: dict[int, float],
    irc_taxa: float,
) -> pd.DataFrame:
    """Business case do projeto: FCF anual, descontado ao WACC.

    FCF_projeto = ganho_EBITDA × (1 − t) − investimento + crédito_SIFIDE

    O crédito SIFIDE é deduzido à coleta (valor integral, não × t).
    """
    inv = float(coz.get("investimento", 0.0))
    ano_inv = int(coz.get("ano_investimento", 2027))
    sifide_pct = float(coz.get("sifide_taxa_credito", 0.325))
    wacc = float(coz.get("wacc_appraisal", 0.073))
    sifide_credito = inv * sifide_pct

    rows = []
    for y in YEARS:
        poup = float(fse_reducao.get(y, 0.0))
        custo = float(cmvmc_inc.get(y, 0.0))
        ganho_ebitda = poup - custo
        invest = inv if y == ano_inv else 0.0
        sifide = sifide_credito if y == ano_inv else 0.0
        fcf = ganho_ebitda * (1.0 - irc_taxa) - invest + sifide
        n = y - ano_inv  # desconto a partir do ano de investimento
        fator = (1.0 + wacc) ** (-n) if n >= 0 else 1.0
        rows.append({
            "ano": y,
            "poupanca_energia": poup,
            "custo_pasta_cmvmc": -custo,
            "ganho_ebitda": ganho_ebitda,
            "investimento": -invest,
            "sifide_credito": sifide,
            "fcf_projeto": fcf,
            "fcf_descontado": fcf * fator,
        })
    return pd.DataFrame(rows)


def cozedura_resumo(df_appraisal: pd.DataFrame, coz: dict) -> dict:
    """Métricas-síntese do business case: VAL, investimento líquido, payback."""
    inv = float(coz.get("investimento", 0.0))
    sifide_pct = float(coz.get("sifide_taxa_credito", 0.325))
    inv_liquido = inv * (1.0 - sifide_pct)

    ano_inv = int(coz.get("ano_investimento", 2027))
    val = float(df_appraisal["fcf_descontado"].sum())

    # Payback faseado: nº de anos a partir do investimento até o cash-flow
    # acumulado do projeto ficar ≥ 0 (anos pré-investimento são ignorados).
    cum = 0.0
    prev_cum = 0.0
    payback_anos = None
    for _, r in df_appraisal.iterrows():
        y = int(r["ano"])
        if y < ano_inv:
            continue
        prev_cum = cum
        cum += float(r["fcf_projeto"])
        if cum >= 0 and payback_anos is None:
            fluxo = float(r["fcf_projeto"])
            frac = (-prev_cum / fluxo) if fluxo > 0 else 0.0
            payback_anos = (y - ano_inv) + frac

    # Ganho recorrente em regime de cruzeiro (último ano, adoção plena).
    ganho_pleno = float(df_appraisal.iloc[-1]["ganho_ebitda"])
    # Cash-flow recorrente após impostos no último ano (sem investimento).
    fcf_pleno = float(df_appraisal.iloc[-1]["fcf_projeto"])
    payback_regime = (inv_liquido / fcf_pleno) if fcf_pleno > 0 else None

    return {
        "investimento_bruto": inv,
        "investimento_liquido": inv_liquido,
        "val": val,
        "payback_anos": payback_anos,
        "payback_regime_anos": payback_regime,
        "ganho_ebitda_pleno": ganho_pleno,
    }
