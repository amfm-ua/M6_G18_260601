from __future__ import annotations

import pandas as pd

from ...inputs import Assumptions, Base2024, Schedules, MESES
from ...modelo.eoep import _get_eoep_credor_2024
from ...operacional.clientes import iva_efetivo_vendas
from .auxiliares import _financiamento_mensal, _capex_mensal, _interp, _hub_monthly_impact


# ──────────────────────────────────────────────────────────────────────────────
# Loop Integrado: DFC determina Caixa; Balanço fecha por construção
# ──────────────────────────────────────────────────────────────────────────────

def _build_integrated_monthly(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
    df_dr_m: pd.DataFrame,
    df_t_m: pd.DataFrame,
    anual_ref: dict | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Loop mensal integrado: DFC determina Caixa; Balanço fecha naturalmente.

    Args:
        anual_ref: valores do modelo anual 2025 (live) para ancoragem.
            Chaves usadas: inventarios, outros_pc, clientes, fornecedores,
            subs_2025, rend_equiv_2025, dividendos_2025.
            Se None, usa reference_balanco do schedules.yaml e sem ajustes.

    Retorna:
        tuple[pd.DataFrame, pd.DataFrame]: df_balanco, df_dfc.
    """
    # ── Parâmetros de caixa ───────────────────────────────────────────────────
    # Floor dinâmico: Floor[m] = MAX(floor_minimo_abs ; pct_floor × Pag_Totais[m+1])
    # Retrocede para mensal_minima (legado) quando ambos os parâmetros novos são 0.
    floor_minimo_abs = float(a.caixa.get("floor_minimo_abs", 250_000))
    pct_floor = float(a.caixa.get("pct_floor", 0.15))
    taxa_linha = float(a.caixa.get("taxa_juro_cc_anual", 0.065))
    tecto_linha = a.caixa.get("tecto_linha_credito", None)
    if tecto_linha is not None:
        tecto_linha = float(tecto_linha)
    # Teto mensal: % do VN anual projetado 2025 (consistente com o Balanço anual).
    _vn_anual = float(df_dr_m["vn"].sum()) if "vn" in df_dr_m.columns else 40_000_000.0
    caixa_max = _vn_anual * float(a.caixa.get("maxima_pct_vn", 0.086))
    iva_venda = iva_efetivo_vendas(a)
    iva_fse = a.impostos.get("IVA_FSE", 0.15)
    iva_cmvmc = float(a.impostos.get("IVA_CMVMC", 0.23)) if a is not None else 0.23

    # ── Novo financiamento core (não-hub) ─────────────────────────────────────
    # Lê parâmetros de globais.yaml § novo_financiamento_core.
    # Escolhe montante_com_projeto quando hub está activo, sem_projeto caso contrário.
    # O novo empréstimo entra como caixa (DFC) E como passivo NC (balanço),
    # garantindo controlo = 0 (dupla entrada contabilística completa).
    _raw_nf = a.raw.get("novo_financiamento_core", {})
    _mes_nf = str(_raw_nf.get("mes_desembolso", "Jan"))
    _hub_activo = bool(a.raw.get("hub_logistico", {}).get("incluir_hub", False))
    if _hub_activo:
        _montante_nf = float(_raw_nf.get("montante_com_projeto",
                                          _raw_nf.get("montante_sem_projeto", 1_130_000)))
    else:
        _montante_nf = float(_raw_nf.get("montante_sem_projeto", 1_130_000))
    # Índice do mês de desembolso (0=Jan … 11=Dez); fallback 0 se mês inválido.
    _mes_nf_idx = MESES.index(_mes_nf) if _mes_nf in MESES else 0

    fin_m = _financiamento_mensal(sched)
    cap_m = _capex_mensal(sched)
    dr_map = df_dr_m.set_index("mes").to_dict("index")
    t_map = df_t_m.set_index("mes").to_dict("index")

    # ── Pré-computar pagamentos totais por mês (para floor dinâmico) ──────────
    # Pagamentos_Totais[m] = Pag.Fornecedores + Pag.Pessoal + Total_Fiscal
    # Todos positivos (saídas de caixa) — ver tesouraria.py § sign convention.
    pag_totais: dict[str, float] = {}
    for _m in MESES:
        _t = t_map[_m]
        pag_totais[_m] = (
            float(_t["pagamentos_fornecedores"])
            + float(_t["pagamentos_pessoal"])
            + float(_t.get("total_saidas_fiscais", abs(float(_t.get("fluxo_fiscal", 0)))))
        )

    b = base.balanco
    ref = sched.reference_balanco

    # ── Constantes ─────────────────────────────────────────────────────────────
    # Subsidiárias: interpoladas linearmente 2024→2025 usando schedules.yaml.
    # Não requer modelo anual externo — valores pré-calculados no schedule.
    subs_ini = float(b["ativo_nao_corrente"]["Subsidiarias"])
    _inv_s        = sched.investimento
    _rend_eq_2025 = float(_inv_s.get("rend_equiv_patrimonial", {}).get(2025, 0.0))
    _div_2025     = float(_inv_s.get("dividendos_recebidos",   {}).get(2025, 0.0))
    subs_fin      = subs_ini + _rend_eq_2025 - _div_2025

    # DFC — ajustes pelo método indireto para rendimentos não-monetários:
    #   rend_equiv_m : incluído no RL mas não é caixa → subtrai de fluxo_op
    #   dividendos_m : caixa real recebido das subsidiárias → fluxo_inv
    rend_equiv_m = _rend_eq_2025 / 12.0
    dividendos_m = _div_2025 / 12.0

    anc_outros_nosubs = (
        b["ativo_nao_corrente"]["Goodwill"]
        + b["ativo_nao_corrente"]["Ativos_Fin_Justo_Valor"]
        + b["ativo_nao_corrente"]["Outros_Ativos_Fixos"]
    )

    impost_dif_a = b["ativo_nao_corrente"]["Impostos_Diferidos_Ativos"]
    impost_dif_p = b["passivo"]["Impostos_Diferidos_Passivos"]

    rt_opening = (
        b["capital_proprio"]["Resultados_Transitados"]
        + b["capital_proprio"]["RL_2024"]
    )

    cp_fixo = (
        b["capital_proprio"]["Capital_Social"]
        + b["capital_proprio"]["Premios_Emissao"]
        + b["capital_proprio"]["Outros_IC_Proprio"]
        + b["capital_proprio"]["Reservas_Legais"]
        + b["capital_proprio"]["Ajust_AF"]
        + b["capital_proprio"]["Outras_Var_CP"]
        + rt_opening
    )

    eoep_dev_ini = base.saldos["EOEP_devedor"]
    eoep_cred_ini = _get_eoep_credor_2024(base)

    outros_ac = b["ativo_corrente"]["Outros_AC"] - eoep_dev_ini

    # ── Refs para interpolação ─────────────────────────────────────────────────
    eoep_dev_fin = ref["eoep_devedor"][2025]
    eoep_cred_fin = ref["eoep_credor"][2025]

    outros_pc_ini = b["passivo"]["Outros_PC"] - eoep_cred_ini
    outros_pc_fin = (
        float(anual_ref["outros_pc"])
        if anual_ref and "outros_pc" in anual_ref
        else outros_pc_ini
    )

    inv_ini = b["ativo_corrente"]["Inventarios"]
    inv_fin = (
        float(anual_ref["inventarios"])
        if anual_ref and "inventarios" in anual_ref
        else ref["inventarios"][2025]
    )

    nc_ini   = sched.financiamento["emprestimos_NC"][2024]
    nc_fin_r = sched.financiamento["emprestimos_NC"][2025]  # core live, sem hub

    c_ini   = sched.financiamento["emprestimos_C"][2024]
    c_fin_r = sched.financiamento["emprestimos_C"][2025]    # core live, sem hub

    # ── Hub: impacto mensal (None se desativado) ───────────────────────────────
    hub_impact = _hub_monthly_impact(a)
    hub_nc = float(hub_impact["nc"]) if hub_impact else 0.0
    hub_c  = float(hub_impact["c"])  if hub_impact else 0.0

    # ── Estado inicial: abertura 31 Dez 2024 ───────────────────────────────────
    aft_core_prev = b["ativo_nao_corrente"]["AFT_liquido"]
    aft_hub_cum   = 0.0  # acumula CAPEX hub + juros capitalizados (NCRF 10)
    intang_prev = b["ativo_nao_corrente"]["Intangiveis"]
    cli_prev = b["ativo_corrente"]["Clientes"]
    forn_prev = b["passivo"]["Fornecedores"]
    inv_prev = inv_ini
    eoep_dev_prev = eoep_dev_ini
    eoep_cred_prev = eoep_cred_ini
    outros_pc_prev = outros_pc_ini
    aplic_prev = 0.0
    linha_prev = 0.0
    caixa_prev = b["ativo_corrente"]["Caixa"]
    rl_acum = 0.0

    bs_rows: list[dict] = []
    dfc_rows: list[dict] = []

    for i, m in enumerate(MESES):
        dr = dr_map[m]
        t = t_map[m]
        fin = fin_m[m]
        cap = cap_m[m]

        dep_m   = cap["dep_total"]
        juros_m = fin["juros"]
        amort_m = fin["amortizacao"]

        # ── Hub: fluxos do mês ────────────────────────────────────────────────
        hub_m            = hub_impact["meses"][m] if hub_impact else {}
        hub_capex_m      = float(hub_m.get("capex",       0.0))
        hub_jc_m         = float(hub_m.get("juros_cap",   0.0))
        hub_juros_pag_m  = float(hub_m.get("juros_pagos", 0.0))
        hub_desembolso_m = float(hub_m.get("desembolso",  0.0))

        # CAPEX total do mês (core Grestel + hub) — para DFC fluxo_investimento
        capex_m = cap["capex_aft"] + cap["capex_int"] + hub_capex_m

        # ── Floor dinâmico do mês ─────────────────────────────────────────────
        # Floor[m] = MAX(floor_minimo_abs ; pct_floor × Pag_Totais[m+1])
        # Dezembro: proxy = média(Out, Nov, Dez) — Jan do ano seguinte indisponível.
        if i < 11:
            _pag_next = pag_totais[MESES[i + 1]]
        else:
            _pag_next = (pag_totais["Out"] + pag_totais["Nov"] + pag_totais["Dez"]) / 3.0
        floor_m = max(floor_minimo_abs, pct_floor * _pag_next)

        # ── Novo financiamento core — encaixe único no mês configurado ────────
        novo_fin_m = _montante_nf if m == _mes_nf else 0.0

        # ── 1. Itens determinísticos do Balanço ───────────────────────────────
        # AFT core (Grestel) — evolução autónoma independente do hub
        aft_core_m = aft_core_prev + cap["capex_aft"] - cap["dep_aft"]
        aft_core_m = max(aft_core_m, 0.0)
        # AFT hub: acumula CAPEX (saída caixa) + juros capitalizados (NCRF 10)
        # Sem depreciação em 2025 — hub entra em exploração em 2026
        aft_hub_cum += hub_capex_m + hub_jc_m
        aft_m = aft_core_m + aft_hub_cum

        intang_m = intang_prev + cap["capex_int"] - cap["dep_int"]
        intang_m = max(intang_m, 0.0)

        subs_m = _interp(subs_ini, subs_fin, i)

        inv_m = _interp(inv_ini, inv_fin, i)

        cli_m = (
            cli_prev
            + dr["vn"] * (1 + iva_venda)
            - t["recebimentos_clientes"]
        )

        eoep_dev_m = _interp(eoep_dev_ini, eoep_dev_fin, i)

        forn_m = (
            forn_prev
            + dr["cmvmc"] * (1 + iva_cmvmc)
            + dr["fse"] * (1 + iva_fse)
            - t["pagamentos_fornecedores"]
        )

        # Ancoragem de Dezembro: clientes e fornecedores forçados ao valor anual.
        # A diferença metodológica (DFC-first PMR cash vs. PMR/365 ratio) flui
        # integralmente por var_nfm → var_caixa → caixa_m (DFC-first preservado).
        if anual_ref is not None and m == "Dez":
            cli_m  = float(anual_ref.get("clientes",     cli_m))
            forn_m = float(anual_ref.get("fornecedores", forn_m))

        eoep_cred_m = _interp(eoep_cred_ini, eoep_cred_fin, i)
        outros_pc_m = _interp(outros_pc_ini, outros_pc_fin, i)

        # NC/C: core Grestel (interpolação) + hub (constante, carência 2025-2027)
        #       + novo_fin_nc (constante a partir do mês de desembolso — dupla entrada)
        _novo_fin_nc = _montante_nf if i >= _mes_nf_idx else 0.0
        nc_m = _interp(nc_ini, nc_fin_r, i) + hub_nc + _novo_fin_nc
        c_m  = _interp(c_ini,  c_fin_r,  i) + hub_c

        rl_acum += dr["rl"]
        cp_m = cp_fixo + rl_acum

        # ── 2. ΔNFM ───────────────────────────────────────────────────────────
        d_cli = -(cli_m - cli_prev)
        d_inv = -(inv_m - inv_prev)
        d_eoep_dev = -(eoep_dev_m - eoep_dev_prev)
        d_forn = forn_m - forn_prev
        d_eoep_cred = eoep_cred_m - eoep_cred_prev
        d_outros_pc = outros_pc_m - outros_pc_prev

        var_nfm = (
            d_cli
            + d_inv
            + d_eoep_dev
            + d_forn
            + d_eoep_cred
            + d_outros_pc
        )

        # ── 3. Fluxos base ────────────────────────────────────────────────────
        # rend_equiv_patrimonial é não-monetário: incluso no RL (via outros_ebitda_m)
        # mas não gera caixa — subtrai do fluxo_op (NCRF 2 método indireto).
        # Dividendos recebidos são caixa real das subsidiárias → fluxo_investimento.
        fluxo_op = dr["rl"] + dep_m + juros_m - rend_equiv_m + var_nfm
        fluxo_inv_base = -capex_m + dividendos_m
        # Hub: desembolso bancário (entrada Jan) − juros totais pagos (saída mensal)
        # Os juros hub são sempre saída de caixa real (NCRF 2 §33b), mesmo
        # os capitalizados no AFT (NCRF 10) — distinção contabilística, não financeira.
        # novo_fin_m: encaixe de novo financiamento core (entrada única no mês configurado)
        fluxo_fin_base = -amort_m - juros_m + hub_desembolso_m - hub_juros_pag_m + novo_fin_m
        var_caixa_base = fluxo_op + fluxo_inv_base + fluxo_fin_base

        # ── 4. Posição líquida disponível no fecho do mês ─────────────────────
        posicao_liq = caixa_prev + aplic_prev - linha_prev + var_caixa_base

        # ── 5. Decisão de gestão de caixa ─────────────────────────────────────
        # floor_m é dinâmico: MAX(floor_minimo_abs ; pct_floor × Pag_Totais[m+1])
        # gap_m = drawdown necessário = MAX(0 ; floor_m − posicao_liq)
        if posicao_liq >= caixa_max:
            aplic_cp_m = posicao_liq - caixa_max
            linha_cp_m = 0.0
            caixa_m = caixa_max
        elif posicao_liq >= floor_m:
            aplic_cp_m = 0.0
            linha_cp_m = 0.0
            caixa_m = posicao_liq
        else:
            aplic_cp_m = 0.0
            linha_cp_m = floor_m - posicao_liq   # drawdown = gap pontual
            caixa_m = floor_m

        # Custo estimado da linha: drawdown × taxa_anual / 12
        juros_linha_m = linha_cp_m * (taxa_linha / 12.0)

        # ── 6. Ajustes DFC: Δ Aplicações e Δ Linha CP ─────────────────────────
        d_aplic = -(aplic_cp_m - aplic_prev)
        d_linha = linha_cp_m - linha_prev

        fluxo_inv = fluxo_inv_base + d_aplic
        fluxo_fin = fluxo_fin_base + d_linha
        var_caixa = fluxo_op + fluxo_inv + fluxo_fin

        # ── 7. Reconciliação ──────────────────────────────────────────────────
        reconciliacao = round((caixa_prev + var_caixa) - caixa_m, 2)

        # ── Totais do Balanço ─────────────────────────────────────────────────
        anc_outros_m = anc_outros_nosubs + subs_m + intang_m
        total_anc = aft_m + anc_outros_m + impost_dif_a
        total_ac = aplic_cp_m + inv_m + cli_m + eoep_dev_m + outros_ac + caixa_m
        total_ativo = total_anc + total_ac

        total_passivo = (
            nc_m
            + c_m
            + impost_dif_p
            + forn_m
            + eoep_cred_m
            + outros_pc_m
            + linha_cp_m
        )

        total_cp_passivo = cp_m + total_passivo
        controlo = round(total_cp_passivo - total_ativo, 2)

        bs_rows.append(
            {
                "mes": m,
                "aft_liquido": round(aft_m),
                "anc_outros": round(anc_outros_m),
                "impost_dif_ativos": round(impost_dif_a),
                "total_anc": round(total_anc),
                "aplicacoes_fin_cp": round(aplic_cp_m),
                "inventarios": round(inv_m),
                "clientes": round(cli_m),
                "eoep_devedor": round(eoep_dev_m),
                "outros_ac": round(outros_ac),
                "caixa": round(caixa_m),
                "total_ac": round(total_ac),
                "total_ativo": round(total_ativo),
                "cp_fixo": round(cp_fixo),
                "rl_acumulado": round(rl_acum),
                "total_cp": round(cp_m),
                "emprestimos_nc": round(nc_m),
                "impost_dif_passivos": round(impost_dif_p),
                "emprestimos_c": round(c_m),
                "fornecedores": round(forn_m),
                "eoep_credor": round(eoep_cred_m),
                "outros_pc": round(outros_pc_m),
                "linha_credito_cp": round(linha_cp_m),
                "total_passivo": round(total_passivo),
                "total_cp_passivo": round(total_cp_passivo),
                "controlo": controlo,
                # ── Linha rotativa: outputs analíticos ───────────────────────
                "floor_m": round(floor_m),
                "saldo_antes_linha": round(posicao_liq),
                "gap_mensal": round(max(0.0, floor_m - posicao_liq)),
                "juros_linha": round(juros_linha_m),
                "novo_financiamento_m": round(novo_fin_m),
                # ── Internos para reconciliação ───────────────────────────────
                "_capex_m": round(capex_m),
                "_dep_m": round(dep_m),
                "_amort_m": round(amort_m),
                "_juros_m": round(juros_m),
                "_aplic_delta": round(aplic_cp_m - aplic_prev),
            }
        )

        dfc_rows.append(
            {
                "mes": m,
                "rl": round(dr["rl"]),
                "dep_amort": round(dep_m),
                "juros_add_back": round(juros_m),
                "var_clientes": round(d_cli),
                "var_inventarios": round(d_inv),
                "var_eoep_dev": round(d_eoep_dev),
                "var_fornecedores": round(d_forn),
                "var_eoep_cred": round(d_eoep_cred),
                "var_outros_pc": round(d_outros_pc),
                "var_nfm_total": round(var_nfm),
                "fluxo_operacional": round(fluxo_op),
                "capex": round(-capex_m),
                "dividendos_recebidos": round(dividendos_m),
                "var_aplic_cp": round(d_aplic),
                "fluxo_investimento": round(fluxo_inv),
                "amortizacoes": round(-amort_m),
                "juros_pagos": round(-juros_m),
                "novo_financiamento": round(novo_fin_m),
                "var_linha_cp": round(d_linha),
                "fluxo_financiamento": round(fluxo_fin),
                "variacao_caixa": round(var_caixa),
                "caixa_abertura": round(caixa_prev),
                "caixa_fecho": round(caixa_m),
                "reconciliacao": reconciliacao,
            }
        )

        # ── Actualiza estado ───────────────────────────────────────────────────
        aft_core_prev = aft_core_m  # hub acumula em aft_hub_cum (fora deste campo)
        intang_prev = intang_m
        cli_prev = cli_m
        forn_prev = forn_m
        inv_prev = inv_m
        eoep_dev_prev = eoep_dev_m
        eoep_cred_prev = eoep_cred_m
        outros_pc_prev = outros_pc_m
        aplic_prev = aplic_cp_m
        linha_prev = linha_cp_m
        caixa_prev = caixa_m

    return pd.DataFrame(bs_rows), pd.DataFrame(dfc_rows)
