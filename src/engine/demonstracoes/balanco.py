"""
Módulo: engine/statements/balanco.py — Balanço / Demonstração da Situação Financeira (2024-2029)
Versão: v2 — Estrutura modular temática
Idioma: Português Europeu

OBJETIVO ACADÉMICO:
O Balanço apresenta a posição financeira de uma empresa numa data específica (fim de ano).
Segue a equação fundamental: ATIVO = PASSIVO + PATRIMÔNIO

ESTRUTURA DO BALANÇO:

┌─────────────────────────────────────────────────────────────────┐
│ ATIVO (Aplicação de Recursos)                                   │
├─────────────────────────────────────────────────────────────────┤
│ A. ATIVO CORRENTE (Curto Prazo: < 12 meses)                    │
│    1. Disponibilidades (Caixa, Bancos): dinheiro disponível    │
│    2. Contas a Receber (Clientes): crédito concedido          │
│    3. Inventários (Stock): mercadorias, matérias-primas        │
│    4. Outros ativos correntes (devedores diversos)             │
│                                                                 │
│ B. ATIVO NÃO CORRENTE (Longo Prazo: > 12 meses)               │
│    1. Imobilizado Corpóreo: máquinas, edifícios, equipamento   │
│    2. Imobilizado Incorpóreo: software, marcas, patentes       │
│    3. Investimentos Financeiros: ações em associadas          │
│    4. Créditos a Longo Prazo: empréstimos a clientes          │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ PASSIVO (Origem de Recursos - Obrigações)                       │
├─────────────────────────────────────────────────────────────────┤
│ A. PASSIVO CORRENTE (Curto Prazo: a pagar < 12 meses)         │
│    1. Contas a Pagar (Fornecedores): dívida a fornecedores    │
│    2. Outros Credores: salários a pagar, impostos a pagar      │
│    3. Empréstimos Bancários Curto Prazo: parcela 1 ano        │
│                                                                 │
│ B. PASSIVO NÃO CORRENTE (Longo Prazo: a pagar > 12 meses)    │
│    1. Empréstimos Bancários Longo Prazo: dívida futura        │
│    2. Outras Obrigações Financeiras: arrendamentos, etc.      │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ PATRIMÔNIO (Capital Próprio / Equity)                           │
├─────────────────────────────────────────────────────────────────┤
│    1. Capital Social: investimento inicial dos acionistas      │
│    2. Reservas: lucros retidos de anos anteriores              │
│    3. Resultado do Exercício: lucro/prejuízo do ano corrente   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

LÓGICA DE CÁLCULO:
  1. Inicia com saldos 2024 reais (inputs base.saldos)
  2. Calcula variações anuais de cada conta:
     - Caixa: Saldo Anterior ± Fluxo Operacional ± Invest. ± Financ.
     - Clientes: crescem com receita de vendas
     - Inventário: cresce com CMVMC
     - Fornecedores: crescem com compras (CMVMC)
     - Empréstimos: amortizam segundo plano de financiamento
     - Patrimônio: acumula resultados (lucro retido)
  3. Reconciliação: Ativo Total = Passivo + Patrimônio (sempre, por construção)

RECONCILIAÇÃO COM DEMONSTRAÇÃO DE RESULTADOS:
  - Lucro Retido = Resultado Líquido da DR
  - Variação de Clientes = origem/aplicação de caixa na DFC
  - Variação de Fornecedores = origem/aplicação de caixa na DFC
"""

from __future__ import annotations

import pandas as pd

from ..inputs import Assumptions, Base2024, Schedules, ALL_YEARS, YEARS
from ..operacional import vendas
from ..operacional import fse
from ..investimento import investimento
from ..financiamento import financiamento
from ..operacional import cmvmc
from ..operacional import clientes as conta_clientes
from ..modelo import eoep
from ..operacional import inventarios
from ..operacional import fornecedores


def _hub_nfm_cumulative(a: Assumptions) -> dict[int, float]:
    """NFM acumulada do hub por ano — WC operacional do hub não incluído no balanço Grestel.

    Representa capital de giro imobilizado no hub (stock de manutenção +
    crédito a clientes de serviços − crédito de fornecedores hub).
    Adicionado a outros_ac para que o plug da caixa reflita a saída de caixa
    capturada na DFC como var_nfm hub.
    """
    try:
        raw_hub = a.raw.get("hub_logistico", {})
        if not raw_hub.get("incluir_hub", False):
            return {}
        from ..projetos import hub_logistico as hub_mod
        nfm_map = hub_mod.hub_nfm(raw_hub)
        cumulative = 0.0
        result: dict[int, float] = {}
        for y in ALL_YEARS:
            cumulative += nfm_map.get(y, 0.0)
            result[y] = cumulative
        return result
    except Exception:
        return {}


def _hub_pt2030_diferido(a: Assumptions) -> dict[int, float]:
    """Subsídio PT2030 recebido mas ainda não reconhecido em DR — passivo diferido.

    NCRF 22 §26: subsídio recebido em caixa é diferido como passivo até ser
    reconhecido no DR proporcionalmente às depreciações dos ativos financiados.
    Sem este passivo, a caixa plug do balanço fica subavaliada em relação
    ao cash efetivamente recebido, causando divergência com a DFC.
    """
    try:
        raw_hub = a.raw.get("hub_logistico", {})
        if not raw_hub.get("incluir_hub", False):
            return {}
        from ..projetos import hub_logistico as hub_mod
        proj = raw_hub["projeto_hub"]
        pt = proj["financiamento"]["PT2030"]
        pt_montante = float(pt["montante"])
        pt_ano = int(pt["ano_recebimento"])
        reconhecimento = hub_mod.pt2030_reconhecimento(raw_hub)
        pt_received = 0.0
        cum_rec = 0.0
        result: dict[int, float] = {}
        for y in ALL_YEARS:
            if y == pt_ano:
                pt_received = pt_montante
            # Acumula reconhecimento apenas a partir do ano de recebimento.
            # Reconhecimentos anteriores ao recebimento (ex: 2026) fluem pelo RL → CP
            # e criam caixa "phantom" consistente com a DFC (sem ajuste não-monetário).
            # A partir do recebimento, o DFC subtrai o reconhecimento como ajuste
            # não-monetário; o passivo diferido aqui deve reflectir só o reconhecimento
            # pós-recebimento para que a reconciliação feche.
            if y >= pt_ano:
                cum_rec += reconhecimento.get(y, 0.0)
            result[y] = max(0.0, pt_received - cum_rec)
        return result
    except Exception:
        return {}


def _hub_inv_liberation(a: Assumptions) -> dict[int, float]:
    """Redução acumulada de inventário pelo Hub por ano (só quando hub ativo).

    A libertação de inventário do hub (ex: €1,5M em 2026) é um stock correction
    permanente: o saldo de inventários diminui a partir do ano de libertação.
    Retorna {ano: redução_acumulada} para todos os anos.
    """
    try:
        raw_hub = a.raw.get("hub_logistico", {})
        if not raw_hub.get("incluir_hub", False):
            return {}
        from ..projetos import hub_logistico as hub_mod
        dr_imp = hub_mod.hub_dr_impact(raw_hub)
        cumulative = 0.0
        result: dict[int, float] = {}
        for y in ALL_YEARS:
            cumulative += dr_imp.get(y, {}).get("inventario_libertado", 0.0)
            result[y] = cumulative
        return result
    except Exception:
        return {}


def build_balanco(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
    df_dr: pd.DataFrame,
    df_eoep_mensal: "pd.DataFrame | None" = None,
    df_prod: "pd.DataFrame | None" = None,
    df_merc: "pd.DataFrame | None" = None,
    df_total: "pd.DataFrame | None" = None,
) -> pd.DataFrame:
    """Constrói o Balanço 2024-2029 com treasury plug.

    Se df_eoep_mensal for fornecido, os saldos EOEP de 2025 são derivados
    do calendário mensal em vez do schedules.yaml.
    """
    if df_prod is None:
        df_prod = vendas.vendas_anuais(a, base, sched)
    if df_merc is None:
        df_merc = vendas.vendas_mercadorias_anuais(a, base)
    if df_total is None:
        df_total = vendas.resumo_anual(df_prod, df_merc)

    vn_2024_b = float(df_total[df_total.ano == 2024]["vn_total"].iloc[0])
    vn_2025_b = float(df_total[df_total.ano == 2025]["vn_total"].iloc[0])

    factor_2025 = vn_2025_b / vn_2024_b if vn_2024_b else 1.0

    df_fse = fse.fse_anual(a, base, factor_2025)
    df_inv = investimento.investimento_anual(a, base, sched)
    df_fin = financiamento.financiamento_anual(sched, a)
    df_cmvmc = cmvmc.cmvmc_anual(a, base, df_prod, df_merc)
    df_cli = conta_clientes.clientes_anual(a, base, df_total)
    df_inv_st = inventarios.inventarios_anual(a, base, df_cmvmc)
    df_forn = fornecedores.fornecedores_anual(base, df_cmvmc, df_fse, a)

    # Imparidades acumuladas — NCRF 27 §41: activos financeiros apresentados pelo
    # valor líquido (bruto − imparidade acumulada). O gasto anual passa pela DR;
    # aqui acumula-se para que o saldo de Clientes no Balanço seja líquido.
    imparidades_acum: dict[int, float] = {}
    _cumul_imp = 0.0
    for _y_imp in ALL_YEARS:
        _dr_row = df_dr[df_dr.ano == _y_imp]
        if not _dr_row.empty:
            _cumul_imp += abs(float(_dr_row["imparidades"].iloc[0]))
        imparidades_acum[_y_imp] = _cumul_imp

    cp = base.balanco["capital_proprio"]

    capital_social = cp["Capital_Social"]
    premios = cp["Premios_Emissao"]
    outros_ic = cp["Outros_IC_Proprio"]
    reservas = cp["Reservas_Legais"]
    ajust_af = cp["Ajust_AF"]
    outras_var = cp["Outras_Var_CP"]

    payout = a.distribuicao["payout_ratio"]
    reserva_legal = a.distribuicao.get("reserva_legal_pct", 0.0)
    inicio_div = a.distribuicao["ano_inicio_distribuicao"]

    rt = {
        2024: cp["Resultados_Transitados"],
    }

    for y in YEARS:
        rl_prev = float(df_dr[df_dr.ano == (y - 1)]["rl"].iloc[0])
        rl_cur = float(df_dr[df_dr.ano == y]["rl"].iloc[0])

        if y == 2025:
            rt[y] = rt[y - 1] + base.balanco["capital_proprio"]["RL_2024"]
        else:
            if rl_cur > 0 and y >= inicio_div:
                div = rl_prev * payout
                res = rl_prev * reserva_legal
            else:
                div = res = 0.0
            rt[y] = rt[y - 1] + rl_prev - div - res

    irc_dict = {
        y: -float(df_dr[df_dr.ano == y]["irc"].iloc[0])
        for y in ALL_YEARS
    }

    df_eoep = eoep.eoep_anual(a, base, sched, irc_dict, df_mensal=df_eoep_mensal)

    base_outros_ac = base.balanco["ativo_corrente"]["Outros_AC"]
    eoep_dev_24 = base.saldos["EOEP_devedor"]
    outros_ac_2024 = base_outros_ac - eoep_dev_24

    eoep_cred_24 = eoep._get_eoep_credor_2024(base)
    base_outros_pc_total = base.balanco["passivo"]["Outros_PC"]

    # Outros_PC operacional, excluindo EOEP credor porque EOEP é apresentado
    # separadamente no Balanço.
    outros_pc_24 = base_outros_pc_total - eoep_cred_24

    ab = sched.plurianual_AB
    g_73 = ab.get("AB73", 0.025)
    g_74 = ab.get("AB74", 0.02)

    out_ac_yr = {
        2024: outros_ac_2024,
    }

    outros_pc_yr = {
        2024: outros_pc_24,
    }

    for y in ALL_YEARS:
        if y == 2024:
            continue

        if y == 2025:
            # Mantém a base 2024 sem EOEP, evitando dupla contagem.
            out_ac_yr[y] = outros_ac_2024
            outros_pc_yr[y] = outros_pc_24
        else:
            out_ac = base_outros_ac

            for k in range(2026, y + 1):
                out_ac *= 1 + (g_73 if k == 2026 else g_74)

            eoep_d_y = float(df_eoep[df_eoep.ano == y]["eoep_devedor"].iloc[0])
            out_ac_yr[y] = out_ac - eoep_d_y

            outros_pc_yr[y] = outros_pc_yr[y - 1] * (1 + g_74)

    rows = []
    hub_inv_lib = _hub_inv_liberation(a)
    hub_nfm_cum = _hub_nfm_cumulative(a)
    hub_pt2030_dif = _hub_pt2030_diferido(a)

    # IDA dinâmico — NCRF 25 §24:
    #   Imposto Diferido Ativo (IDA): direito fiscal futuro que nasce quando a
    #   empresa reconhece um gasto contabilístico antes de o poder deduzir
    #   fiscalmente. Representa poupança de imposto a recuperar em anos seguintes.
    #   O modelo recalcula o IDA a cada ano ("dinâmico") em vez de usar um valor fixo.
    # Componente 1: diferença temporária de imparidades de clientes
    #   Provisionadas na DR mas não fiscalmente dedutíveis até realização
    #   → IDA_impairment_y = Σ(imp_k − imp_2024) × t para k = 2025..y
    # Componente 2: SIFIDE II carry-forward não absorvido
    #   Crédito gerado mas coleta insuficiente → transposto para anos seguintes
    #   → lido da coluna "sifide_carryforward" do df_dr (build_dr já o calcula)
    ida_2024 = float(base.balanco["ativo_nao_corrente"]["Impostos_Diferidos_Ativos"])
    taxa_irc_base = float(a.impostos.get("IRC_taxa_geral", 0.20))
    imp_2024 = abs(float(df_dr[df_dr.ano == 2024]["imparidades"].iloc[0]))
    cumul_imp_delta = 0.0

    ida_por_ano: dict[int, float] = {2024: ida_2024}
    for y_ida in [2025, 2026, 2027, 2028, 2029]:
        dr_row_ida = df_dr[df_dr.ano == y_ida]
        if dr_row_ida.empty:
            ida_por_ano[y_ida] = ida_por_ano[y_ida - 1]
            continue
        imp_y = abs(float(dr_row_ida["imparidades"].iloc[0]))
        cumul_imp_delta += max(0.0, imp_y - imp_2024)
        ida_imp_timing = cumul_imp_delta * taxa_irc_base

        sifide_cf_y = float(dr_row_ida.get("sifide_carryforward", 0.0).iloc[0])
        ida_por_ano[y_ida] = ida_2024 + ida_imp_timing + sifide_cf_y

    for y in ALL_YEARS:
        aft = float(df_inv[df_inv.ano == y]["aft_liquido_fim"].iloc[0])
        outros_anc = float(
            df_inv[df_inv.ano == y]["goodwill_intang_subs_af_total"].iloc[0]
        )
        goodwill_val = float(df_inv[df_inv.ano == y]["goodwill"].iloc[0])
        intangiveis_val = float(df_inv[df_inv.ano == y]["intangiveis_fim"].iloc[0])
        subsidiarias_val = float(df_inv[df_inv.ano == y]["subsidiarias_fim"].iloc[0])
        ativos_fin_jv_val = float(df_inv[df_inv.ano == y]["ativos_fin_jv"].iloc[0])
        outros_fixos_val = float(df_inv[df_inv.ano == y]["outros_fixos_af"].iloc[0])

        impostos_dif_a = ida_por_ano.get(y, ida_2024)

        total_anc = aft + outros_anc + impostos_dif_a

        inv_st = float(df_inv_st[df_inv_st.ano == y]["inventarios"].iloc[0])
        inv_st = max(0.0, inv_st - hub_inv_lib.get(y, 0.0))
        cli = float(df_cli[df_cli.ano == y]["saldo_clientes"].iloc[0])
        cli = max(0.0, cli - imparidades_acum.get(y, 0.0))  # valor líquido (NCRF 27 §41)
        eoep_d = float(df_eoep[df_eoep.ano == y]["eoep_devedor"].iloc[0])
        out_ac = out_ac_yr[y]

        rl_y = float(df_dr[df_dr.ano == y]["rl"].iloc[0])

        cp_total_pre_caixa = (
            capital_social
            + premios
            + outros_ic
            + reservas
            + ajust_af
            + rt[y]
            + outras_var
            + rl_y
        )

        emp_nc = float(df_fin[df_fin.ano == y]["emprestimos_NC"].iloc[0])
        emp_c = float(df_fin[df_fin.ano == y]["emprestimos_C"].iloc[0])

        imp_dif_p = base.balanco["passivo"]["Impostos_Diferidos_Passivos"]

        forn = float(df_forn[df_forn.ano == y]["fornecedores"].iloc[0])
        eoep_c = float(df_eoep[df_eoep.ano == y]["eoep_credor"].iloc[0])
        out_pc = outros_pc_yr[y]

        # NFM acumulada do hub: WC operacional do hub não rastreado nos itens
        # principais do balanço (inventarios/clientes Grestel). Adicionado a
        # ac_sem_caixa para que o plug da caixa reflita a saída real de caixa.
        hub_nfm_ac_y = hub_nfm_cum.get(y, 0.0)

        # Subsídio PT2030 diferido: montante recebido em caixa mas ainda não
        # reconhecido na DR. Adicionado ao passivo (NCRF 22) para que o plug
        # da caixa reflita o cash recebido na DFC (hub_pt2030_recebimento).
        hub_subsidio_dif_y = hub_pt2030_dif.get(y, 0.0)

        passivo_pre = emp_nc + emp_c + imp_dif_p + forn + eoep_c + out_pc + hub_subsidio_dif_y
        ac_sem_caixa = inv_st + cli + eoep_d + out_ac + hub_nfm_ac_y

        # surplus = recursos disponíveis após financiar todos os ativos fixos e
        # capital circulante operacional (clientes, inventários, EOEP, outros AC).
        # É o "dinheiro sobrante" antes de decidir onde o alocar.
        #   surplus > caixa_max  →  excesso depositado em aplicações financeiras CP
        #   caixa_min ≤ surplus ≤ caixa_max  →  fica todo em caixa
        #   surplus < caixa_min  →  caixa fica em caixa_min; o deficit é coberto por
        #                           uma linha de crédito de curto prazo (treasury plug).
        #
        # LIMITAÇÕES DO PLUG:
        #   • A linha_credito_cp é um plug contabilístico: garante que Ativo = Passivo+CP
        #     mas não verifica covenants bancários nem capacidade de obter o crédito.
        #   • Não são calculados juros sobre a linha — o custo financeiro real seria
        #     superior ao modelado. Para maior rigor, seria necessário retroalimentar
        #     os juros na DR e recalcular iterativamente.
        surplus = cp_total_pre_caixa + passivo_pre - total_anc - ac_sem_caixa

        # Limites de caixa anuais expressos como % do VN (motivo transação — Keynes/Baumol):
        # escalam com o crescimento, ao contrário de valores fixos.
        # Para 2024 estes valores não são usados (caixa vem do balanço histórico).
        vn_y = float(df_dr[df_dr.ano == y]["vn"].iloc[0])
        caixa_min = vn_y * float(a.caixa.get("minima_pct_vn", 0.013))
        caixa_max = vn_y * float(a.caixa.get("maxima_pct_vn", 0.086))

        if y == 2024:
            caixa = base.balanco["ativo_corrente"]["Caixa"]
            aplic_cp = 0.0
            linha_cp = 0.0
        else:
            caixa = min(caixa_max, max(caixa_min, surplus))
            aplic_cp = max(0.0, surplus - caixa_max)   # excesso → aplicações fin. CP
            linha_cp = max(0.0, caixa_min - surplus)   # deficit → linha crédito CP

        total_ac = aplic_cp + inv_st + cli + eoep_d + out_ac + hub_nfm_ac_y + caixa
        passivo_total = passivo_pre + linha_cp  # linha_cp = 0 quando surplus ≥ caixa_min
        cp_total = cp_total_pre_caixa
        total_passivo_cp = cp_total + passivo_total
        total_ativo = total_anc + total_ac

        rows.append(
            {
                "ano": y,
                "aft_liquido": aft,
                "goodwill_intang_subs_af": outros_anc,
                "goodwill": goodwill_val,
                "intangiveis": intangiveis_val,
                "subsidiarias": subsidiarias_val,
                "ativos_fin_justo_valor": ativos_fin_jv_val,
                "outros_ativos_fixos": outros_fixos_val,
                "impostos_dif_ativos": impostos_dif_a,
                "total_anc": total_anc,
                "aplicacoes_fin_cp": aplic_cp,
                "inventarios": inv_st,
                "clientes": cli,
                "eoep_devedor": eoep_d,
                "outros_ac": out_ac,
                "caixa": caixa,
                "total_ac": total_ac,
                "total_ativo": total_ativo,
                "capital_social": capital_social,
                "premios_emissao": premios,
                "outros_ic_proprio": outros_ic,
                "reservas_legais": reservas,
                "ajust_af": ajust_af,
                "resultados_transitados": rt[y],
                "outras_var_cp": outras_var,
                "rl": rl_y,
                "total_cp": cp_total,
                "emprestimos_nc": emp_nc,
                "emprestimos_c": emp_c,
                "imp_dif_passivos": imp_dif_p,
                "fornecedores": forn,
                "eoep_credor": eoep_c,
                "outros_pc": out_pc,
                "hub_subsidio_diferido": hub_subsidio_dif_y,
                "linha_credito_cp": linha_cp,
                "total_passivo": passivo_total,
                "hub_nfm": hub_nfm_ac_y,
                "total_cp_passivo": total_passivo_cp,
                "controlo": total_passivo_cp - total_ativo,
            }
        )

    return pd.DataFrame(rows)