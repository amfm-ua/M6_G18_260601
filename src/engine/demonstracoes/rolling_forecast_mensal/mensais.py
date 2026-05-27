from __future__ import annotations

import pandas as pd

from ...inputs import Assumptions, Base2024, Schedules, MESES
from ...financiamento import tesouraria as teso_mod
from .auxiliares import _financiamento_mensal, _capex_mensal, _hub_monthly_impact
from .integrado import _build_integrated_monthly


# ──────────────────────────────────────────────────────────────────────────────
# Balanço Mensal
# ──────────────────────────────────────────────────────────────────────────────

def build_balanco_mensal(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
    _df_dr_m: pd.DataFrame | None = None,
    _df_t_m: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Balanço mensal 2025, com Caixa derivada dos fluxos DFC."""
    if _df_dr_m is None:
        _df_dr_m = teso_mod.build_dr_mensal(a, base, sched)

    if _df_t_m is None:
        _df_t_m = teso_mod.build_tesouraria(a, base, sched)

    df_bs, _ = _build_integrated_monthly(a, base, sched, _df_dr_m, _df_t_m)
    return df_bs


# ──────────────────────────────────────────────────────────────────────────────
# DFC Mensal
# ──────────────────────────────────────────────────────────────────────────────

def build_dfc_mensal(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
    df_bs: pd.DataFrame | None = None,
    df_dr_m: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """DFC mensal 2025 pelo método indireto, reconciliada com o Balanço."""
    if df_dr_m is None:
        df_dr_m = teso_mod.build_dr_mensal(a, base, sched)

    df_t_m = teso_mod.build_tesouraria(a, base, sched)

    _, df_dfc = _build_integrated_monthly(a, base, sched, df_dr_m, df_t_m)
    return df_dfc


# ──────────────────────────────────────────────────────────────────────────────
# NFM Mensal
# ──────────────────────────────────────────────────────────────────────────────

def build_nfm_mensal(
    df_bs: pd.DataFrame,
    df_dr_m: pd.DataFrame,
) -> pd.DataFrame:
    """NFM e Ciclo de Conversão de Caixa mensais, derivados do Balanço."""
    bs_map = df_bs.set_index("mes").to_dict("index")
    dr_map = df_dr_m.set_index("mes").to_dict("index")

    rows: list[dict] = []

    for m in MESES:
        bs = bs_map[m]
        dr = dr_map[m]

        vn_m = max(dr["vn"], 1)
        cmvmc_m = max(dr["cmvmc"], 1)
        fse_m = max(dr["fse"], 1)

        ac_cicl = bs["inventarios"] + bs["clientes"] + bs.get("eoep_devedor", 0.0) + bs.get("outros_ac", 0.0)
        pc_cicl = bs["fornecedores"] + bs["eoep_credor"] + bs.get("outros_pc", 0.0)
        nfm_m = ac_cicl - pc_cicl

        pmr_eff = bs["clientes"] / vn_m * 30
        dmi_eff = bs["inventarios"] / cmvmc_m * 30
        pmp_eff = bs["fornecedores"] / (cmvmc_m + fse_m) * 30
        ccc_eff = pmr_eff + dmi_eff - pmp_eff

        rows.append(
            {
                "mes": m,
                "ativo_ciclico": round(ac_cicl),
                "inventarios": round(bs["inventarios"]),
                "clientes": round(bs["clientes"]),
                "eoep_devedor": round(bs.get("eoep_devedor", 0.0)),
                "outros_ac": round(bs.get("outros_ac", 0.0)),
                "passivo_ciclico": round(pc_cicl),
                "fornecedores": round(bs["fornecedores"]),
                "eoep_credor": round(bs["eoep_credor"]),
                "outros_pc": round(bs.get("outros_pc", 0.0)),
                "nfm": round(nfm_m),
                "pmr_eff": round(pmr_eff, 1),
                "dmi_eff": round(dmi_eff, 1),
                "pmp_eff": round(pmp_eff, 1),
                "ccc_eff": round(ccc_eff, 1),
            }
        )

    df = pd.DataFrame(rows)
    df["delta_nfm"] = df["nfm"].diff().fillna(0).round().astype(int)

    return df


# ──────────────────────────────────────────────────────────────────────────────
# Tesouraria Completa
# ──────────────────────────────────────────────────────────────────────────────

def build_tesouraria_completa(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
    df_bs: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Tesouraria mensal completa: operacional + serviço dívida + CAPEX."""
    if df_bs is None:
        df_bs = build_balanco_mensal(a, base, sched)

    df_teso = teso_mod.build_tesouraria(a, base, sched)
    fin_m = _financiamento_mensal(sched)
    cap_m = _capex_mensal(sched)
    hub_impact = _hub_monthly_impact(a)

    t_map = df_teso.set_index("mes").to_dict("index")
    bs_map = df_bs.set_index("mes").to_dict("index")

    caixa_prev = base.balanco["ativo_corrente"]["Caixa"]

    rows: list[dict] = []

    for m in MESES:
        t = t_map[m]
        bs = bs_map[m]
        fin = fin_m[m]
        cap = cap_m[m]

        rec = t["recebimentos_clientes"]
        pag_forn = t["pagamentos_fornecedores"]
        pag_pess = t["pagamentos_pessoal"]
        fluxo_fisc = t["fluxo_fiscal"]
        fluxo_op_b = t["fluxo_operacional_bruto"]
        fluxo_op_l = t["fluxo_liquido"]

        hub_m            = hub_impact["meses"][m] if hub_impact else {}
        hub_capex_m      = float(hub_m.get("capex",       0.0))
        hub_juros_pag_m  = float(hub_m.get("juros_pagos", 0.0))
        hub_desembolso_m = float(hub_m.get("desembolso",  0.0))

        capex_pag = cap["capex_aft"] + cap["capex_int"] + hub_capex_m
        amort_pag = fin["amortizacao"]
        juros_pag = fin["juros"]
        novo_fin_m = float(bs.get("novo_financiamento_m", 0))

        fluxo_fin = -(amort_pag + juros_pag) + hub_desembolso_m - hub_juros_pag_m + novo_fin_m

        var_total = fluxo_op_l - capex_pag + fluxo_fin
        caixa_bruta = caixa_prev + var_total

        linha_cp = bs["linha_credito_cp"]

        rows.append(
            {
                "mes": m,
                "recebimentos_clientes": round(rec),
                "pagamentos_fornecedores": round(pag_forn),
                "pagamentos_pessoal": round(pag_pess),
                "fluxo_operacional_bruto": round(fluxo_op_b),
                "iva_pago_estado": round(t["iva_pagamento_estado"]),
                "ss_pagamento": round(t["ss_pagamento"]),
                "irc_ppc": round(t["irc_ppc"]),
                "fluxo_fiscal": round(fluxo_fisc),
                "fluxo_operacional_liquido": round(fluxo_op_l),
                "capex_pagamento": round(-capex_pag),
                "amortizacoes": round(-amort_pag),
                "juros_pagos": round(-juros_pag),
                "novo_financiamento": round(bs.get("novo_financiamento_m", 0)),
                "fluxo_financiamento": round(fluxo_fin),
                "variacao_caixa_total": round(var_total),
                "caixa_abertura": round(caixa_prev),
                "caixa_antes_credito": round(caixa_bruta),
                # ── Linha rotativa ────────────────────────────────────────────
                "floor_m": round(bs.get("floor_m", 0)),
                "saldo_antes_linha": round(bs.get("saldo_antes_linha", caixa_bruta)),
                "gap_mensal": round(bs.get("gap_mensal", 0)),
                "linha_credito_utilizada": round(linha_cp),
                "juros_linha": round(bs.get("juros_linha", 0)),
                "caixa_fecho": round(bs["caixa"]),
            }
        )

        caixa_prev = bs["caixa"]

    return pd.DataFrame(rows)


# ──────────────────────────────────────────────────────────────────────────────
# Resumo da Linha de Crédito Rotativo
# ──────────────────────────────────────────────────────────────────────────────

def build_linha_summary(
    df_bs: pd.DataFrame,
    vn_anual: float,
    a: Assumptions,
) -> dict:
    """Resumo analítico da linha rotativa com alertas e indicador de saúde.

    Inputs:
        df_bs     — balanço mensal com colunas linha_credito_cp, floor_m,
                    gap_mensal, juros_linha, caixa, mes.
        vn_anual  — VN anual 2025 (para rácio pico/VN).
        a         — pressupostos (lê tecto_linha_credito).

    Returns dict com métricas de resumo e lista de alertas.
    """
    tecto = a.caixa.get("tecto_linha_credito", None)
    if tecto is not None:
        tecto = float(tecto)

    pico_linha = float(df_bs["linha_credito_cp"].max())
    idx_pico = int(df_bs["linha_credito_cp"].idxmax())
    mes_do_pico = df_bs.loc[idx_pico, "mes"]
    drawdown_medio = float(df_bs["linha_credito_cp"].mean())
    juros_anuais = float(df_bs["juros_linha"].sum()) if "juros_linha" in df_bs.columns else 0.0
    saldo_final = float(df_bs.loc[df_bs["mes"] == "Dez", "caixa"].iloc[0])
    n_meses_gap = int((df_bs["linha_credito_cp"] > 0).sum())
    dez_drawdown = float(df_bs.loc[df_bs["mes"] == "Dez", "linha_credito_cp"].iloc[0])

    # Rácio saúde: pico_linha / VN — benchmark <20% saudável, 20–35% atenção, >35% crítico
    racio_saude = pico_linha / vn_anual if vn_anual > 0 else 0.0
    if racio_saude < 0.20:
        semaforo = "saudavel"
    elif racio_saude < 0.35:
        semaforo = "atencao"
    else:
        semaforo = "critico"

    alertas: list[dict] = []

    # ⚠️ Bug: saldo_final < floor em algum mês
    if "floor_m" in df_bs.columns:
        for _, row in df_bs.iterrows():
            if row["caixa"] < row["floor_m"] - 1:
                alertas.append({
                    "tipo": "erro",
                    "codigo": "SALDO_ABAIXO_FLOOR",
                    "mes": row["mes"],
                    "mensagem": (
                        f"Bug: saldo_final ({row['caixa']:,.0f}€) < floor"
                        f" ({row['floor_m']:,.0f}€) em {row['mes']}"
                    ),
                })

    # ⚠️ Pico acima do tecto
    if tecto is not None and pico_linha > tecto:
        alertas.append({
            "tipo": "aviso",
            "codigo": "PICO_ACIMA_TECTO",
            "mensagem": (
                f"Pico da linha ({pico_linha:,.0f}€) excede o teto definido ({tecto:,.0f}€)"
            ),
        })

    # ⚠️ Empresa termina o ano em dívida
    if dez_drawdown > 0:
        alertas.append({
            "tipo": "aviso",
            "codigo": "DIVIDA_FIM_ANO",
            "mensagem": (
                f"Empresa termina o ano com {dez_drawdown:,.0f}€ em dívida na linha rotativa"
            ),
        })

    return {
        "pico_linha": round(pico_linha),
        "mes_do_pico": mes_do_pico,
        "drawdown_medio": round(drawdown_medio),
        "juros_anuais_linha": round(juros_anuais),
        "saldo_final_31dez": round(saldo_final),
        "n_meses_gap": n_meses_gap,
        "racio_pico_vn_pct": round(racio_saude * 100, 1),
        "semaforo_saude": semaforo,
        "alertas": alertas,
    }
