"""
Módulo: engine/demonstracoes/extensao_maturidade.py
Extensão das demonstrações financeiras consolidadas para a fase de maturidade
(anos 6-10 do projeto: 2030-2034).
Idioma: Português Europeu

CONTEXTO ACADÉMICO
------------------
O motor "detalhado" (DR + Balanço + DFC linha-a-linha) cobre 2024-2029. A avaliação
de um projeto de investimento real (Hub Logístico) exige, porém, uma janela de 10
anos (2025-2034) para:
  • captar o momento do payback (~7 anos), impossível de mostrar numa janela de 5;
  • não truncar metade da vida útil (anos 6-10 contêm a maturação do VN do hub,
    o CAPEX de substituição e o valor residual dos activos).

ABORDAGEM (B — "append" isolado, sem mexer no motor 2024-2029)
--------------------------------------------------------------
Em vez de empurrar `ANO_FIM` (que obrigaria a recriar todas as tabelas
pré-computadas até 2034 e recalibrar reconciliações), faz-se um *roll-forward* de
estado estacionário a partir da última linha detalhada (2029):

  • Receitas e custos crescem a uma taxa constante `g` próxima da inflação (~2%).
  • Fundo de maneio (inventários, clientes, EOEP, fornecedores, ...) cresce a `g`
    → estabiliza como % fixa das vendas (rácio constante).
  • CAPEX = Amortizações → activo fixo líquido (AFT) constante; depreciação
    mantida ao nível de 2029.
  • Dívida mantida ao nível de 2029 (manter alavancagem) → juros constantes.
  • Payout mantido (mesmo `payout_ratio` e `reserva_legal_pct` do motor).
  • IRC à taxa efectiva de 2029 (SIFIDE/RFAI já consumidos até 2029).

GARANTIA DE FECHO DO BALANÇO
----------------------------
O Balanço fecha por construção via o mesmo *treasury plug* do motor
(`balanco.py`): a caixa/aplicações/linha de crédito absorvem o residual, pelo que
`controlo ≈ 0` em qualquer ano de extensão. A DFC (método indirecto) replica a
lógica de `dfc.py` — incluindo o crédito da reserva legal em reservas_legais e a
variação de clientes em base bruta — pelo que `reconciliacao_ok` é True em todos
os anos de extensão (2030-2034), tal como no motor 2024-2029 após a correção.

NOTA — going concern vs. liquidação do projeto
----------------------------------------------
Esta extensão consolidada é em *going concern* (a Grestel continua para além de
2034). O valor de **liquidação** (venda residual de terrenos/armazéns líquida de
mais-valias + recuperação de fundo de maneio) aplica-se **apenas ao VAL standalone
do Hub**, não ao valor terminal consolidado — ver
`docs/horizonte_10anos_extensao_motor.md`.
"""

from __future__ import annotations

import pandas as pd

from ..inputs import Assumptions, Base2024, Schedules
from ..operacional.clientes import iva_efetivo_vendas
from .dfc import dynamic_payout

# Inflação anual usada no estado estacionário (parametrizável).
G_MATURIDADE_DEFAULT = 0.02

# Colunas da DR mantidas constantes ao nível de 2029 (não escalam com g).
_DR_HOLD = {
    "depreciacoes",      # CAPEX = amortizações → AFT constante
    "juros",             # dívida constante (manter alavancagem)
    "imparidades",       # provisão estável → IDA constante (coerência DFC)
    "juros_linha_cp",
    "sifide_carryforward",
    "hub_gastos_preop",
}

# Colunas da DR recalculadas a partir das restantes (não escalam nem se copiam).
_DR_RECALC = {"ano", "ebitda", "ebit", "rai", "irc", "rl"}

# Componentes do EBITDA (somatório verificado contra o motor).
_DR_EBITDA_COMPONENTES = [
    "vn", "var_inventarios", "var_producao", "outros_rend",
    "cmvmc", "fse", "gastos_pessoal", "imparidades", "outros_gastos",
]

# Linhas do Balanço que crescem com o fundo de maneio (escalam com g).
_BAL_GROW = {
    "inventarios", "clientes", "eoep_devedor", "outros_ac",
    "fornecedores", "eoep_credor", "outros_pc",
}

# Linhas do Balanço mantidas constantes ao nível de 2029.
_BAL_HOLD_ANC = {
    "aft_liquido", "goodwill_intang_subs_af", "goodwill", "intangiveis",
    "subsidiarias", "ativos_fin_justo_valor", "outros_ativos_fixos",
    "impostos_dif_ativos",
}
_BAL_HOLD_PASSIVO = {
    "emprestimos_nc", "emprestimos_c", "imp_dif_passivos",
    "hub_subsidio_diferido", "hub_nfm",
}
# reservas_legais NÃO está aqui: cresce com a apropriação anual da reserva legal
# (ver rollforward no loop), tal como em balanco.py — necessário para a DFC reconciliar.
_BAL_EQUITY_CONST = {
    "capital_social", "premios_emissao", "outros_ic_proprio",
    "ajust_af", "outras_var_cp",
}


def estender_maturidade(
    dfs: dict[str, pd.DataFrame],
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
    g: float = G_MATURIDADE_DEFAULT,
    ano_fim_ext: int = 2034,
    ano_base_ext: int = 2029,
) -> dict[str, pd.DataFrame]:
    """Anexa as linhas 2030-2034 a dr/balanco/dfc por roll-forward de maturidade.

    Recebe o dicionário já construído por `build_statements` e devolve um novo
    dicionário com as mesmas chaves, mas com as três demonstrações estendidas
    até `ano_fim_ext`. Não altera os anos 2024-2029.
    """
    df_dr = dfs["dr"].copy()
    df_bal = dfs["balanco"].copy()
    df_dfc = dfs["dfc"].copy()

    dr_b = df_dr[df_dr.ano == ano_base_ext].iloc[0]
    bal_b = df_bal[df_bal.ano == ano_base_ext].iloc[0]

    # Taxa efectiva de IRC do último ano detalhado (SIFIDE/RFAI já consumidos).
    rai_b = float(dr_b["rai"])
    irc_b = float(dr_b["irc"])  # armazenado negativo
    taxa_irc_efetiva = (-irc_b / rai_b) if rai_b != 0 else 0.0

    payout = float(a.distribuicao["payout_ratio"])
    reserva_legal = float(a.distribuicao.get("reserva_legal_pct", 0.0))
    inicio_div = int(a.distribuicao["ano_inicio_distribuicao"])
    caixa_min_pct = float(a.caixa.get("minima_pct_vn", 0.013))
    caixa_max_pct = float(a.caixa.get("maxima_pct_vn", 0.086))
    pol_payout = a.raw.get("payout_policy", {})

    iva_vendas = iva_efetivo_vendas(a)
    iva_cmvmc = float(a.impostos.get("IVA_CMVMC", 0.23))
    iva_fse = float(a.impostos.get("IVA_FSE", 0.15))

    anos_ext = list(range(ano_base_ext + 1, ano_fim_ext + 1))

    dr_rows: list[dict] = []
    bal_rows: list[dict] = []
    dfc_rows: list[dict] = []

    # rt acumulado e linha do balanço anterior (arranca em 2029).
    rt_prev = float(bal_b["resultados_transitados"])
    reservas_leg_prev = float(bal_b["reservas_legais"])
    bal_prev = bal_b
    rl_prev = float(dr_b["rl"])
    aplic_prev = float(bal_b["aplicacoes_fin_cp"])

    # Teto da reserva legal (CSC art. 295.º): a dotação cessa aos 20% do capital
    # social — mesma regra de balanco.py, aplicada ao saldo acumulado.
    teto_reserva_legal = 0.20 * float(bal_b["capital_social"])

    for y in anos_ext:
        scale = (1.0 + g) ** (y - ano_base_ext)

        # ── Payout dinámico para ano y ───────────────────────────────────────
        # Endividamento do ano anterior (bal_prev) como rácio sobre ativo total.
        endiv_pct = 100.0 * (
            float(bal_prev["emprestimos_nc"]) + float(bal_prev["emprestimos_c"])
        ) / max(1.0, float(bal_prev["total_ativo"]))
        payout_y = dynamic_payout(
            y=y, rl_prev=rl_prev,
            endividamento_pct=endiv_pct,
            aplic_fin_cp=aplic_prev,
            pol=pol_payout,
            inicio_div=inicio_div,
        )

        # ---------- DR ----------
        dr_row: dict = {"ano": float(y)}
        for col in df_dr.columns:
            if col in _DR_RECALC:
                continue
            val = float(dr_b[col])
            if col in _DR_HOLD:
                dr_row[col] = val
            else:
                dr_row[col] = val * scale

        ebitda = sum(dr_row[c] for c in _DR_EBITDA_COMPONENTES)
        ebit = ebitda + dr_row["depreciacoes"]          # depreciacoes negativa
        rai = ebit + dr_row["juros"] + dr_row["rend_financeiros"]  # juros negativa
        irc = -taxa_irc_efetiva * rai
        rl = rai + irc
        dr_row["ebitda"] = ebitda
        dr_row["ebit"] = ebit
        dr_row["rai"] = rai
        dr_row["irc"] = irc
        dr_row["rl"] = rl
        dr_rows.append(dr_row)

        # ---------- Balanço ----------
        # Equity rollforward (igual a balanco.py): a reserva legal (res) sai dos
        # resultados transitados e é creditada em reservas_legais (transferência
        # interna ao capital próprio, CSC art. 295.º) — sem isto a DFC não reconcilia.
        if rl > 0 and y >= inicio_div:
            div = rl_prev * payout_y
            res = rl_prev * reserva_legal
            res = max(0.0, min(res, teto_reserva_legal - reservas_leg_prev))
        else:
            div = res = 0.0
        rt_y = rt_prev + rl_prev - div - res
        reservas_leg_y = reservas_leg_prev + res

        bal_row: dict = {"ano": float(y)}
        for col in _BAL_HOLD_ANC | _BAL_HOLD_PASSIVO | _BAL_EQUITY_CONST:
            bal_row[col] = float(bal_b[col])
        for col in _BAL_GROW:
            bal_row[col] = float(bal_b[col]) * scale
        bal_row["reservas_legais"] = reservas_leg_y
        bal_row["resultados_transitados"] = rt_y
        bal_row["rl"] = rl

        total_anc = (
            bal_row["aft_liquido"]
            + bal_row["goodwill_intang_subs_af"]
            + bal_row["impostos_dif_ativos"]
        )
        cp_total_pre_caixa = (
            bal_row["capital_social"]
            + bal_row["premios_emissao"]
            + bal_row["outros_ic_proprio"]
            + bal_row["reservas_legais"]
            + bal_row["ajust_af"]
            + rt_y
            + bal_row["outras_var_cp"]
            + rl
        )
        passivo_pre = (
            bal_row["emprestimos_nc"]
            + bal_row["emprestimos_c"]
            + bal_row["imp_dif_passivos"]
            + bal_row["fornecedores"]
            + bal_row["eoep_credor"]
            + bal_row["outros_pc"]
            + bal_row["hub_subsidio_diferido"]
        )
        ac_sem_caixa = (
            bal_row["inventarios"]
            + bal_row["clientes"]
            + bal_row["eoep_devedor"]
            + bal_row["outros_ac"]
            + bal_row["hub_nfm"]
        )

        surplus = cp_total_pre_caixa + passivo_pre - total_anc - ac_sem_caixa
        vn_y = dr_row["vn"]
        caixa_min = vn_y * caixa_min_pct
        caixa_max = vn_y * caixa_max_pct
        caixa = min(caixa_max, max(caixa_min, surplus))
        aplic_cp = max(0.0, surplus - caixa_max)
        linha_cp = max(0.0, caixa_min - surplus)

        total_ac = (
            aplic_cp
            + bal_row["inventarios"]
            + bal_row["clientes"]
            + bal_row["eoep_devedor"]
            + bal_row["outros_ac"]
            + bal_row["hub_nfm"]
            + caixa
        )
        total_passivo = passivo_pre + linha_cp
        total_cp = cp_total_pre_caixa
        total_cp_passivo = total_cp + total_passivo
        total_ativo = total_anc + total_ac

        bal_row["aplicacoes_fin_cp"] = aplic_cp
        bal_row["caixa"] = caixa
        bal_row["linha_credito_cp"] = linha_cp
        bal_row["total_anc"] = total_anc
        bal_row["total_ac"] = total_ac
        bal_row["total_ativo"] = total_ativo
        bal_row["total_cp"] = total_cp
        bal_row["total_passivo"] = total_passivo
        bal_row["total_cp_passivo"] = total_cp_passivo
        bal_row["controlo"] = total_cp_passivo - total_ativo
        bal_rows.append(bal_row)

        # ---------- DFC (método indirecto, estado estacionário) ----------
        dep = -dr_row["depreciacoes"]
        imp = -dr_row["imparidades"]
        juros = -dr_row["juros"]
        rend_fin = dr_row["rend_financeiros"]
        irc_pago_pos = -irc  # irc negativo → positivo

        d_inv = float(bal_prev["inventarios"]) - bal_row["inventarios"]
        d_cli = float(bal_prev["clientes"]) - bal_row["clientes"]
        d_eoep_d = float(bal_prev["eoep_devedor"]) - bal_row["eoep_devedor"]
        d_out_ac = float(bal_prev["outros_ac"]) - bal_row["outros_ac"]
        d_forn = bal_row["fornecedores"] - float(bal_prev["fornecedores"])
        d_eoep_c = bal_row["eoep_credor"] - float(bal_prev["eoep_credor"])
        d_out_pc = bal_row["outros_pc"] - float(bal_prev["outros_pc"])
        d_ida = bal_row["impostos_dif_ativos"] - float(bal_prev["impostos_dif_ativos"])

        # Maturidade: sem efeitos hub/equity-method residuais a partir de 2030.
        # Imparidade: +imp é add-back não-caixa; como o balanço de maturidade não
        # acumula a imparidade no saldo de clientes (clientes = nível 2029 escalado),
        # converte-se a variação de clientes à base bruta (d_cli − imp) para a
        # imparidade contar uma só vez — mesmo tratamento de dfc.py.
        op_pre_nfm = rl + dep + imp + juros - rend_fin - d_ida
        d_cli_bruto = d_cli - imp
        var_nfm = d_inv + d_cli_bruto + d_eoep_d + d_out_ac + d_forn + d_eoep_c + d_out_pc
        fluxo_op = op_pre_nfm + var_nfm

        # CAPEX = depreciação (substituição); sem intangíveis/dividendos/hub novos.
        inv_aft = dep
        inv_int = 0.0
        div_recebidos = 0.0
        d_aplic_cp = float(bal_prev["aplicacoes_fin_cp"]) - bal_row["aplicacoes_fin_cp"]
        fluxo_inv = -inv_aft - inv_int + div_recebidos + rend_fin + d_aplic_cp

        # Dívida constante → amortizações/novos empréstimos nulos.
        amort_total = 0.0
        d_emp_total = (
            bal_row["emprestimos_nc"] + bal_row["emprestimos_c"]
            - float(bal_prev["emprestimos_nc"]) - float(bal_prev["emprestimos_c"])
        )
        rec_emp = d_emp_total + amort_total
        d_linha_cp = bal_row["linha_credito_cp"] - float(bal_prev["linha_credito_cp"])
        pag_div = -div if (rl > 0 and y >= inicio_div) else 0.0
        fluxo_fin = rec_emp - amort_total - juros + d_linha_cp + pag_div

        var_caixa = fluxo_op + fluxo_inv + fluxo_fin
        caixa_ini = float(bal_prev["caixa"])

        vn_dfc = dr_row["vn"]
        cmvmc_dfc = dr_row["cmvmc"]
        fse_dfc = dr_row["fse"]
        pessoal_dfc = dr_row["gastos_pessoal"]
        rec_clientes = vn_dfc * (1 + iva_vendas) + d_cli
        pag_forn = cmvmc_dfc * (1 + iva_cmvmc) + fse_dfc * (1 + iva_fse) + d_forn

        dfc_rows.append({
            "ano": y,
            "rl": rl,
            "dep_amort": dep,
            "imparidades": imp,
            "juros_pagos": juros,
            "rend_fin": -rend_fin,
            "rend_equiv_patrimonial": 0.0,
            "hub_pt2030_nao_monetario": 0.0,
            "var_impostos_dif_ativos": -d_ida,
            "op_pre_nfm": op_pre_nfm,
            "var_nfm": var_nfm,
            "hub_nfm": 0.0,
            "irc_pago": -irc_pago_pos,
            "recebimentos_clientes": rec_clientes,
            "pagamentos_fornecedores": pag_forn,
            "pagamentos_pessoal": pessoal_dfc,
            "fluxo_operacional": fluxo_op,
            "capex_aft": -inv_aft,
            "pag_intang": -inv_int,
            "dividendos_recebidos": div_recebidos,
            "hub_capex": 0.0,
            "hub_pt2030": 0.0,
            "var_aplic_fin_cp": d_aplic_cp,
            "fluxo_investimento": fluxo_inv,
            "rec_emprestimos": rec_emp,
            "pag_emprestimos": -amort_total,
            "juros_pagos_fin": -juros,
            "hub_amortizacao": 0.0,
            "hub_juros_capitalizados": 0.0,
            "var_linha_cp": d_linha_cp,
            "pag_dividendos": pag_div,
            "payout_ratio": payout_y,
            "fluxo_financiamento": fluxo_fin,
            "variacao_caixa": var_caixa,
            "caixa_ini": caixa_ini,
            "caixa_fim": caixa_ini + var_caixa,
            "caixa_fim_balanco": caixa,
            "reconciliacao_ok": abs((caixa_ini + var_caixa) - caixa) < 1.0,
        })

        # Avança o estado.
        rt_prev = rt_y
        reservas_leg_prev = reservas_leg_y
        rl_prev = rl
        aplic_prev = bal_row["aplicacoes_fin_cp"]
        bal_prev = pd.Series(bal_row)

    # Truncar os anos de extensão que build_* já gerou (ALL_YEARS inclui 2030-2034),
    # para que estender_maturidade substitua em vez de duplicar esses anos.
    df_dr_ext = pd.concat([df_dr[df_dr.ano <= ano_base_ext], pd.DataFrame(dr_rows)], ignore_index=True)
    df_bal_ext = pd.concat([df_bal[df_bal.ano <= ano_base_ext], pd.DataFrame(bal_rows)], ignore_index=True)
    df_dfc_ext = pd.concat([df_dfc[df_dfc.ano <= ano_base_ext], pd.DataFrame(dfc_rows)], ignore_index=True)

    out = dict(dfs)
    out["dr"] = df_dr_ext
    out["balanco"] = df_bal_ext
    out["dfc"] = df_dfc_ext
    return out


__all__ = ["estender_maturidade", "G_MATURIDADE_DEFAULT"]
