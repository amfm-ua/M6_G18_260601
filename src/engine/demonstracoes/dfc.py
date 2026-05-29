"""
Módulo: engine/statements/dfc.py — Demonstração de Fluxos de Caixa (2024-2029)
Versão: v2 — Estrutura modular temática
Idioma: Português Europeu

OBJETIVO ACADÉMICO:
A Demonstração de Fluxos de Caixa (DFC) mostra como a caixa da empresa evoluiu,
dividindo as atividades em três categorias:

ESTRUTURA DA DFC:

┌─────────────────────────────────────────────────────────────────┐
│ FLUXOS DE CAIXA DO EXERCÍCIO                                    │
├─────────────────────────────────────────────────────────────────┤
│ A. ATIVIDADES OPERACIONAIS (Lucro → Caixa)                     │
│    Início: Resultado Líquido (da DR)                           │
│    Ajustamentos (não-caixa):                                   │
│      + Depreciação (redução de ativo, não caixa)              │
│      + Imparidades (provisão de crédito, não caixa)           │
│      - Variação de Clientes (↑ clientes = caixa negativa)     │
│      + Variação de Fornecedores (↑ fornecedores = caixa +)    │
│      - Variação de Inventário (↑ stock = caixa negativa)      │
│    Fluxo de Caixa Operacional (FCO)                           │
│                                                                 │
│ B. ATIVIDADES DE INVESTIMENTO (Ativo Fixo)                     │
│    - Aquisição de imobilizado (máquinas, edifícios)           │
│    + Venda de ativos/imobilizado (recuperação caixa)          │
│    Fluxo de Caixa de Investimento (FCI)                       │
│                                                                 │
│ C. ATIVIDADES DE FINANCIAMENTO (Estrutura Financeira)         │
│    + Novos empréstimos/capital                                │
│    - Reembolso de empréstimos (amortizações)                 │
│    - Pagamento de juros (carga financeira)                    │
│    Fluxo de Caixa de Financiamento (FCF)                      │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ VARIAÇÃO LÍQUIDA DE CAIXA = FCO + FCI + FCF                    │
│                                                                 │
│ Caixa Final = Caixa Inicial + Variação Líquida                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

MÉTODO INDIRETO vs MÉTODO DIRETO:
  Este modelo usa MÉTODO INDIRETO:
    1. Começa pelo Resultado Líquido (lucro contabilístico)
    2. Adiciona/subtrai ajustamentos (despesas não-caixa)
    3. Ajusta variações de contas correntes (clientes, fornecedores)
    4. Resultado: Fluxo de Caixa Operacional (mais realista que lucro)

LÓGICA CRÍTICA (Por que DR ≠ Fluxo de Caixa):
  Exemplo: Empresa com Lucro €100K mas Clientes em crescimento
    - DR: Lucro = €100K (receita reconhecida, ainda não cobrada)
    - Clientes aumentaram €30K (dinheiro ainda não recebido)
    - Caixa Real = €100K - €30K = €70K

  Motivo: Contabilidade vs Caixa:
    - Contabilidade (Acuidade): reconhece receita ao momento da venda
    - Caixa (Tesouraria): conta só o dinheiro efetivamente recebido

IMPORTÂNCIA PRÁTICA:
  - Uma empresa pode ser lucrativa (DR positiva) mas sem caixa (insolvente)
  - Fluxo de caixa é crítico para: pagamentos, investimentos, sobrevivência
  - Gestão de tesouraria foca no fluxo de caixa, não no lucro
"""

from __future__ import annotations

import pandas as pd

from ..inputs import Assumptions, Base2024, Schedules, ALL_YEARS
from ..operacional.clientes import iva_efetivo_vendas


def _load_hub_pt2030_rec(a: Assumptions) -> tuple[dict[int, float], int]:
    """Reconhecimento anual PT2030 do hub + ano de recebimento.

    A partir do ano de recebimento, o subsídio reconhecido em outros_rend
    (RL) é não-monetário — o cash real já está em fluxo_inv como hub_pt2030.
    Deduzir da op_pre_nfm evita dupla contagem (NCRF 2 §19).
    Anos anteriores ao recebimento: reconhecimento flui como operacional
    (tratamento simplificado, consistente com o balanço).
    """
    try:
        hub_raw = a.raw.get("hub_logistico", {})
        if not hub_raw.get("incluir_hub", False):
            return {}, 0
        from ..projetos import hub_logistico as hub_mod
        rec = hub_mod.pt2030_reconhecimento(hub_raw)
        proj = hub_raw["projeto_hub"]
        pt_ano = int(proj["financiamento"]["PT2030"]["ano_recebimento"])
        return rec, pt_ano
    except Exception:
        return {}, 0


def _load_hub_dfc(a: Assumptions) -> dict[int, dict] | None:
    """Carrega impactos do Hub na DFC, ou None se o Hub estiver desativado."""
    try:
        hub_raw = a.raw.get("hub_logistico", {})
        if not hub_raw.get("incluir_hub", False):
            return None

        from ..projetos import hub_logistico as hub_mod

        return hub_mod.hub_dfc_impact(hub_raw)
    except Exception:
        return None


def build_dfc(
    a: Assumptions,
    df_dr: pd.DataFrame,
    df_balanco: pd.DataFrame,
    sched: Schedules,
    base: Base2024,
) -> pd.DataFrame:
    """Constrói a Demonstração de Fluxos de Caixa pelo método indireto."""
    rows = []

    payout = a.distribuicao["payout_ratio"]
    inicio_div = a.distribuicao["ano_inicio_distribuicao"]

    hub_dfc = _load_hub_dfc(a)
    hub_pt2030_rec, hub_pt2030_ano = _load_hub_pt2030_rec(a)

    # IVA efectivo sobre vendas: só mercado interno PT; exportações isentas
    iva_vendas = iva_efetivo_vendas(a)
    # IVA sobre compras: matérias-primas (CMVMC) sujeitas a 23 % (taxa plena);
    # FSE (serviços, energia, rendas) sujeitos a taxa média ponderada 15 %.
    # Usar taxas distintas evita subestimar as saídas de caixa de IVA — art. 18.º CIVA.
    iva_compras_cmvmc = float(a.impostos.get("IVA_CMVMC", 0.23))
    iva_compras_fse   = float(a.impostos.get("IVA_FSE", 0.15))

    for y in ALL_YEARS:
        rl = float(df_dr[df_dr.ano == y]["rl"].iloc[0])
        dep = -float(df_dr[df_dr.ano == y]["depreciacoes"].iloc[0])
        imp = -float(df_dr[df_dr.ano == y]["imparidades"].iloc[0])
        juros = -float(df_dr[df_dr.ano == y]["juros"].iloc[0])
        rend_fin = float(df_dr[df_dr.ano == y]["rend_financeiros"].iloc[0])
        irc = -float(df_dr[df_dr.ano == y]["irc"].iloc[0])

        if y == 2024:
            d24 = base.raw["dfc_2024_real"]

            fluxo_op = d24["fluxo_operacional"]
            op_pre_nfm = rl + dep + imp + juros - rend_fin

            # Mantém a lógica original para derivar variação de NFM implícita em 2024.
            var_nfm = fluxo_op - op_pre_nfm - (-irc)

            fluxo_inv = d24["fluxo_investimento"]
            fluxo_fin = d24["fluxo_financiamento"]
            var_caixa = fluxo_op + fluxo_inv + fluxo_fin

            rows.append(
                {
                    "ano": 2024,
                    "rl": rl,
                    "dep_amort": dep,
                    "imparidades": imp,
                    "juros_pagos": juros,
                    "rend_fin": -rend_fin,
                    "op_pre_nfm": op_pre_nfm,
                    "var_nfm": var_nfm,
                    "irc_pago": -irc,
                    "recebimentos_clientes": d24.get("recebimentos_clientes", 0.0),
                    "pagamentos_fornecedores": d24.get("pagamentos_fornecedores", 0.0),
                    "pagamentos_pessoal": d24.get("pagamentos_pessoal", 0.0),
                    "fluxo_operacional": fluxo_op,
                    "capex_aft": d24["capex_aft"],
                    "pag_intang": 0.0,
                    "dividendos_recebidos": d24["dividendos_recebidos"],
                    "hub_capex": 0.0,
                    "hub_pt2030": 0.0,
                    "fluxo_investimento": fluxo_inv,
                    "rec_emprestimos": d24["rec_emprestimos"],
                    "pag_emprestimos": d24["pag_emprestimos"],
                    "juros_pagos_fin": -juros,
                    "hub_amortizacao": 0.0,
                    "var_linha_cp": 0.0,
                    "pag_dividendos": 0.0,
                    "fluxo_financiamento": fluxo_fin,
                    "variacao_caixa": var_caixa,
                }
            )

            continue

        row_y = df_balanco[df_balanco.ano == y].iloc[0]
        row_p = df_balanco[df_balanco.ano == (y - 1)].iloc[0]

        d_inv = row_p["inventarios"] - row_y["inventarios"]
        d_cli = row_p["clientes"] - row_y["clientes"]
        d_eoep_d = row_p["eoep_devedor"] - row_y["eoep_devedor"]
        d_out_ac = row_p["outros_ac"] - row_y["outros_ac"]

        d_forn = row_y["fornecedores"] - row_p["fornecedores"]
        d_eoep_c = row_y["eoep_credor"] - row_p["eoep_credor"]
        d_out_pc = row_y["outros_pc"] - row_p["outros_pc"]

        # ΔNFM do Hub: saída de caixa real para capital circulante operacional
        # (stock de manutenção + clientes serviços externos − fornecedores hub)
        # Incluída em var_nfm porque é variação de ativos correntes operacionais
        # — NCRF 2 §14: variações em ativos e passivos correntes operacionais
        # integram os fluxos das atividades operacionais (método indireto).
        # Valor positivo em hub_dfc = saída de caixa → subtrair de var_nfm.
        hub_nfm_y = (
            float(hub_dfc[y].get("nfm_delta", 0.0))
            if hub_dfc and y in hub_dfc
            else 0.0
        )

        # Rendimentos de equivalência patrimonial: rendimento não monetário
        # (método da equivalência patrimonial em investimento.py) — eliminar do FCO
        # e reclassificar para FCI, onde os dividendos efectivamente recebidos
        # já figuram como entradas de caixa.
        rend_equiv_y = float(
            sched.investimento.get("rend_equiv_patrimonial", {}).get(y, 0.0)
        )

        # Reconhecimento PT2030 do hub: não-monetário a partir do ano de recebimento.
        # O cash real (+2.7M) está em fluxo_inv; subtrair o reconhecimento aqui evita
        # dupla contagem. Antes do recebimento (ex: 2026), o reconhecimento é tratado
        # como monetário (consistente com o balanço — sem ajuste), o que simplifica
        # o modelo à custa de um ligeiro desfasamento de timing pré-recebimento.
        hub_pt2030_rec_y = (
            hub_pt2030_rec.get(y, 0.0)
            if hub_pt2030_ano > 0 and y >= hub_pt2030_ano
            else 0.0
        )

        # Variação de IDA (Impostos Diferidos Ativos — NCRF 25):
        # IDA é um ativo não-corrente; o seu aumento representa um benefício
        # fiscal diferido reconhecido fora do DR (SIFIDE carry-forward + timing
        # de imparidades). Não é caixa — subtrair de op_pre_nfm evita que o plug
        # do Balanço crie uma divergência na reconciliação DFC ↔ Balanço.
        d_ida = row_y["impostos_dif_ativos"] - row_p["impostos_dif_ativos"]

        # op_pre_nfm:
        #   + imp: imparidade é gasto NÃO-caixa (NCRF 2 §18 al. c) — adiciona-se de
        #     volta ao RL. Para esta adição ser correcta (e não duplicar), a variação
        #     de clientes em var_nfm tem de ser em base BRUTA (ver d_cli_bruto abaixo).
        #   - sem +juros/-juros: juros são reclassificados para FCF (ver fluxo_fin).
        #   - sem -irc: o timing do IRC já está capturado em d_eoep_c (EOEP credor
        #     inclui IRC pendente); adicioná-lo separadamente causaria dupla dedução.
        #   - -d_ida: variação de IDA é não-monetária; deduzir reconcilia DFC ↔ Balanço.
        op_pre_nfm = rl + dep + imp + juros - rend_fin - rend_equiv_y - hub_pt2030_rec_y - d_ida

        # Clientes no Balanço está LÍQUIDO de imparidades acumuladas (NCRF 27 §41),
        # logo d_cli (líquido) já embute o gasto anual de imparidade. Como esse gasto
        # já é adicionado em op_pre_nfm (+imp), usar d_cli líquido aqui contá-lo-ia
        # DUAS vezes — era a origem do antigo desfasamento DFC↔Balanço. Converte-se
        # para a base bruta (d_cli − imp), em que a imparidade aparece uma só vez.
        d_cli_bruto = d_cli - imp

        # Nota: hub_inventario (inventario_libertado) NÃO é adicionado aqui porque
        # build_balanco já aplica hub_inv_lib ao saldo de inventários, pelo que d_inv
        # captura a libertação. Somar hub_inventario causaria dupla contagem.
        var_nfm = (
            d_inv
            + d_cli_bruto
            + d_eoep_d
            + d_out_ac
            + d_forn
            + d_eoep_c
            + d_out_pc
            - hub_nfm_y   # ΔNFM hub: positivo = saída, subtrai de var_nfm
        )

        fluxo_op = op_pre_nfm + var_nfm

        inv_aft = sched.investimento["investimento_aft_dfc"][y]
        inv_int = sched.investimento["investimento_intang_dfc"][y]
        div_recebidos = sched.investimento["dividendos_dfc"][y]

        hub_capex_y = 0.0
        hub_pt2030_y = 0.0

        if hub_dfc and y in hub_dfc:
            hub_capex_y = hub_dfc[y]["capex_hub"]
            hub_pt2030_y = hub_dfc[y]["pt2030_recebimento"]

        # Variação em aplicações financeiras de curto prazo:
        # aumento → saída de caixa (investimento); redução → entrada de caixa.
        # Necessário para que var_caixa reconcilie com Δcaixa do Balanço.
        # Fórmula: d_aplic_cp = aplic_anterior − aplic_atual (sinal positivo = inflow)
        d_aplic_cp = row_p["aplicacoes_fin_cp"] - row_y["aplicacoes_fin_cp"]

        fluxo_inv = (
            -inv_aft
            - inv_int
            + div_recebidos
            + rend_fin
            + hub_capex_y
            + hub_pt2030_y
            + d_aplic_cp   # variação em aplicações fin. CP (↑investimento = saída)
        )

        amort_base = sched.financiamento["amortizacoes_capital"][y]

        hub_amort_y = 0.0
        if hub_dfc and y in hub_dfc:
            hub_amort_y = hub_dfc[y]["amortizacao_banco"]

        amort_total = amort_base + abs(hub_amort_y)

        d_emp_total = (
            row_y["emprestimos_nc"]
            + row_y["emprestimos_c"]
            - row_p["emprestimos_nc"]
            - row_p["emprestimos_c"]
        )

        rec_emp = d_emp_total + amort_total
        d_linha_cp = row_y["linha_credito_cp"] - row_p["linha_credito_cp"]

        rl_prev = float(df_dr[df_dr.ano == (y - 1)]["rl"].iloc[0])
        rl_cur = float(df_dr[df_dr.ano == y]["rl"].iloc[0])

        pag_div = (
            -rl_prev * payout
            if rl_cur > 0 and y >= inicio_div
            else 0.0
        )

        # Juros capitalizados (NCRF 10): não estão no DR (juros_expensed está),
        # mas são saídas de caixa reais — NCRF 2 §33b exige a divulgação dos
        # juros pagos no período, incluindo os incorporados no custo do ativo.
        # Adicionados ao fluxo_fin para reconciliar DFC ↔ pagamentos reais ao banco.
        hub_juros_cap_y = (
            float(hub_dfc[y].get("juros_capitalizados", 0.0))
            if hub_dfc and y in hub_dfc
            else 0.0
        )

        fluxo_fin = rec_emp - amort_total - juros + d_linha_cp + pag_div - hub_juros_cap_y
        var_caixa = fluxo_op + fluxo_inv + fluxo_fin

        caixa_ini = float(row_p["caixa"])

        # Método direto — componentes estimadas a partir do DR e variações do Balanço
        dr_row_y = df_dr[df_dr.ano == y].iloc[0]
        vn_y = float(dr_row_y["vn"])
        cmvmc_y = float(dr_row_y["cmvmc"])          # negativo (custo)
        fse_y = float(dr_row_y.get("fse", 0.0))     # negativo (custo)
        pessoal_y = float(dr_row_y["gastos_pessoal"])  # negativo (custo)

        # IVA sobre vendas ponderado por mercado (PT 23%, UE/USA/ROW 0%)
        rec_clientes = vn_y * (1 + iva_vendas) + d_cli
        # IVA sobre compras: CMVMC a 23 % (matérias-primas — taxa plena);
        # FSE a 15 % (média ponderada serviços/energia/rendas — CIVA art. 18.º)
        pag_forn = cmvmc_y * (1 + iva_compras_cmvmc) + fse_y * (1 + iva_compras_fse) + d_forn

        rows.append(
            {
                "ano": y,
                "rl": rl,
                "dep_amort": dep,
                "imparidades": imp,
                "juros_pagos": juros,
                "rend_fin": -rend_fin,
                "rend_equiv_patrimonial": -rend_equiv_y,
                "hub_pt2030_nao_monetario": -hub_pt2030_rec_y,
                "var_impostos_dif_ativos": -d_ida,
                "op_pre_nfm": op_pre_nfm,
                "var_nfm": var_nfm,
                "hub_nfm": -hub_nfm_y,
                "irc_pago": -irc,
                "recebimentos_clientes": rec_clientes,
                "pagamentos_fornecedores": pag_forn,
                "pagamentos_pessoal": pessoal_y,
                "fluxo_operacional": fluxo_op,
                "capex_aft": -inv_aft,
                "pag_intang": -inv_int,
                "dividendos_recebidos": div_recebidos,
                "hub_capex": hub_capex_y,
                "hub_pt2030": hub_pt2030_y,
                "var_aplic_fin_cp": d_aplic_cp,
                "fluxo_investimento": fluxo_inv,
                "rec_emprestimos": rec_emp,
                "pag_emprestimos": -amort_total,
                "juros_pagos_fin": -juros,
                "hub_amortizacao": hub_amort_y,
                "hub_juros_capitalizados": -hub_juros_cap_y,
                "var_linha_cp": d_linha_cp,
                "pag_dividendos": pag_div,
                "fluxo_financiamento": fluxo_fin,
                "variacao_caixa": var_caixa,
                "caixa_ini": caixa_ini,
                "caixa_fim": caixa_ini + var_caixa,
                "caixa_fim_balanco": float(row_y["caixa"]),
                "reconciliacao_ok": abs((caixa_ini + var_caixa) - float(row_y["caixa"])) < 1.0,
            }
        )

    return pd.DataFrame(rows)