"""Hub Logístico M6 — impacto nas demonstrações financeiras da Grestel.

Reúne o reconhecimento do subsídio PT2030 (NCRF 22), as Necessidades de
Fundo de Maneio do hub, o crédito fiscal RFAI (CFI art. 22.º-23.º) e o
impacto anual no DR, na DFC e no FCF livre unlevered (FCFF) usado na
análise de viabilidade.
"""
from __future__ import annotations

import pandas as pd

from ...inputs import YEARS
from .base import _dep_por_ano
from .capex import hub_capex
from .financiamento import hub_financing


def pt2030_reconhecimento(hub: dict) -> dict[int, float]:
    """Subsídio PT2030 reconhecido no DR como outros rendimentos (NCRF 22).

    Usa dep_pools (excluindo dep_jc sobre juros capitalizados) como rácio
    de reconhecimento — resulta em Python EBITDA = Excel EBITDA (749 271 em 2026).
    A base tributável [3a] usa dep_total separadamente em hub_rfai/hub_fcf.
    """
    proj = hub["projeto_hub"]
    pt = proj["financiamento"]["PT2030"]

    montante = float(pt["montante"])
    capex_base = float(proj["capex"]["base"])

    if capex_base <= 0:
        return {y: 0.0 for y in YEARS}

    return {
        y: montante * _dep_por_ano(proj, y) / capex_base
        for y in YEARS
    }


def hub_nfm(hub: dict) -> dict[int, float]:
    """
    Variação anual das Necessidades de Fundo de Maneio do Hub (ΔNFM).

    Definição e lógica académica:
    ┌──────────────────────────────────────────────────────────────────┐
    │  NFM = Stock Operacional + Crédito a Clientes                   │
    │        − Crédito de Fornecedores                                │
    │                                                                  │
    │  ΔNFM > 0 → aumento da NFM → saída de caixa (investimento WC)  │
    │  ΔNFM < 0 → redução da NFM → entrada de caixa (desinvestimento) │
    └──────────────────────────────────────────────────────────────────┘

    A ΔNFM reduz o FCF livre do projeto porque representa capital «preso»
    no ciclo operacional que não está disponível para distribuição ou
    reinvestimento — Brealey, Myers & Allen, 13.ª ed., §11.2:
    «A project that requires an investment in working capital generates
    a cash outflow in its early years.»

    Componentes modelados por fase:

    FASE 1 — Arranque operacional (ano_inicio, tipicamente 2026):
      1. Stock de manutenção (peças de substituição VLMs + AMRs + WMS)
         Valorizado ao custo de aquisição ou VRL, o mais baixo (NCRF 18 §9).
         Estimado em ~3 % do CAPEX de equipamento (benchmark VDMA 2022).
         Saída única no ano de arranque → não volta a crescer organicamente.
      2. Consumíveis de arranque (embalagens, etiquetas, materiais packing)
         Necessários para comissionamento e testes de carga do sistema.
      3. Crédito de fornecedores (contratos manutenção contratada)
         Mensurado ao custo amortizado (NCRF 27 §11).
         Crédito recebido no arranque → reduz a NFM inicial (ΔNFM_forn < 0).
         PSP × compras anuais de manutenção.
         Nos anos seguintes: estável → ΔNFM de fornecedores ≈ 0.

    FASE 2 — Serviços logísticos a terceiros (a partir de 2028):
      4. Crédito a clientes externos (produtores cerâmicos Aveiro/Coimbra)
         Reconhecimento do rédito à medida que o serviço é prestado (NCRF 20 §20).
         Mensurado ao custo amortizado (NCRF 27 §11).
         ΔNFM_clientes = PMR/360 × Δ(receita de serviços) por ano.
         PMR B2B logística nacional: 45 dias (mediana APLOG 2023).

    Retorna: {ano: ΔNFM} com valor positivo = saída de caixa.
    """
    proj = hub["projeto_hub"]
    nfm_cfg = proj.get("necessidades_fundo_maneio", {})

    if not nfm_cfg:
        return {y: 0.0 for y in YEARS}

    ano_inicio = int(nfm_cfg.get("ano_inicio", 2026))

    # Fase 1: stock de manutenção + consumíveis de arranque
    stock_manut = float(nfm_cfg.get("stock_manutencao_inicial", 0.0))
    consumiveis = float(nfm_cfg.get("consumiveis_arranque", 0.0))
    nfm_stock_arranque = stock_manut + consumiveis

    # Crédito de fornecedores — reduz NFM inicial (sinal negativo na ΔNFM)
    psp = float(nfm_cfg.get("psp_fornecedores_dias", 30))
    compras_anuais = float(nfm_cfg.get("compras_manutencao_anuais", 0.0))
    credito_forn_inicial = (psp / 360) * compras_anuais

    # Fase 2: clientes externos (crédito a receber por serviços logísticos)
    pmr = float(nfm_cfg.get("pmr_clientes_externos_dias", 45))
    receita_base = float(nfm_cfg.get("receita_servicos_externos_2028", 0.0))
    cresc_serv = float(nfm_cfg.get("crescimento_servicos_anuais", 0.0))
    ano_fase2 = 2028

    result: dict[int, float] = {}
    receita_prev = 0.0

    for y in YEARS:
        if y < ano_inicio:
            result[y] = 0.0
            continue

        delta_nfm = 0.0

        if y == ano_inicio:
            # Investimento inicial: stock + consumíveis − crédito inicial de fornecedores
            # O crédito de fornecedores no arranque reduz a saída de caixa líquida
            delta_nfm = nfm_stock_arranque - credito_forn_inicial

        # Fase 2: variação anual do crédito a clientes externos
        # Só o INCREMENTO de receita gera ΔNFM (não o nível absoluto)
        if y >= ano_fase2:
            n = y - ano_fase2
            receita_y = receita_base * (1 + cresc_serv) ** n
            delta_cli = (pmr / 360) * (receita_y - receita_prev)
            delta_nfm += delta_cli
            receita_prev = receita_y

        result[y] = delta_nfm

    return result


def hub_rfai(hub: dict, irc_taxa: float | None = None) -> dict[int, float]:
    """
    Crédito fiscal RFAI anual aplicado ao IRC do hub — CFI art. 22.º-23.º.

    ┌──────────────────────────────────────────────────────────────────────────┐
    │  NATUREZA DO BENEFÍCIO: CRÉDITO FISCAL vs. DEDUÇÃO FISCAL               │
    │                                                                          │
    │  A distinção é fundamental para a correcta modelação do FCFF:           │
    │                                                                          │
    │  Dedução fiscal (e.g. SIFIDE): reduz a matéria colectável               │
    │    → poupança = dedução × t     (apenas a fracção da taxa)              │
    │                                                                          │
    │  Crédito fiscal (RFAI): deduzido directamente à colecta de IRC          │
    │    → poupança = crédito × 1     (valor integral, não multiplicado por t)│
    │                                                                          │
    │  O RFAI é por isso categorialmente mais valioso do que uma dedução      │
    │  de montante equivalente — erro frequente em modelos financeiros.       │
    └──────────────────────────────────────────────────────────────────────────┘

    Fórmula:
      crédito_total = taxa_rfai × CAPEX_elegível
      aplicado_ano  = min(crédito_restante, limite_irc_pct × IRC_bruto_ano)

    ┌──────────────────────────────────────────────────────────────────────────┐
    │  TRATAMENTO NO FCFF (abordagem WACC)                                    │
    │                                                                          │
    │  O crédito RFAI reduz o IRC efectivamente pago. No FCFF:                │
    │    IRC_pago = EBIT × t − rfai_credito_ano                               │
    │    NOPAT_efectivo = EBIT − IRC_pago = EBIT(1 − t) + rfai_credito_ano   │
    │                                                                          │
    │  Equivalência com a abordagem APV (Adjusted Present Value):             │
    │  No APV (Myers, 1974), benefícios fiscais específicos seriam            │
    │  descontados separadamente à taxa de risco do crédito (≈ rf). A        │
    │  abordagem WACC usada aqui desconta o rfai_credito ao WACC, o que      │
    │  é conservador (WACC > rf) — subestima ligeiramente o VAL do RFAI.     │
    │  Aceitável porque o RFAI é determinístico (crédito gerado = constante) │
    │  e o diferencial WACC − rf é pequeno no horizonte considerado.          │
    │                                                                          │
    │  Ref: Myers, S.C. (1974). "Interactions of Corporate Financing and      │
    │  Investment Decisions — Implications for Capital Budgeting". Journal    │
    │  of Finance, 29(1). §III — Side Effects of Financing.                   │
    │  Damodaran, "Investment Valuation", 3.ª ed., §10.5 — Tax Benefits.     │
    └──────────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────────────────────────────────────────────────────────┐
    │  MECÂNICA DO CARRY-FORWARD — TIMING E VALOR TEMPORAL                   │
    │                                                                          │
    │  O crédito é gerado no momento do CAPEX (2025-2026) mas só pode ser    │
    │  utilizado quando existe IRC liquidado a deduzir — gerando um desfasam │
    │  temporal (timing mismatch). O carry-forward legal (10 anos — art.     │
    │  23.º §6 CFI) permite absorver o crédito remanescente em exercícios    │
    │  futuros, mas a cada ano de diferimento perde valor temporal (PV        │
    │  decresce ao factor 1/(1+WACC)^n).                                      │
    │                                                                          │
    │  Implicação: uma absorção mais rápida (e.g. via IRC total da Grestel   │
    │  em vez do IRC incremental do hub) tem valor presente superior.         │
    │  Este modelo apresenta o cenário conservador — limite sobre IRC hub.    │
    └──────────────────────────────────────────────────────────────────────────┘

    Nota sobre cumulação de benefícios (CFI art. 23.º §9):
      O RFAI não é cumulável com o SIFIDE sobre o mesmo investimento.
      A elegibilidade ao PT2030 (subsídio não reembolsável) não impede
      o RFAI — são regimes distintos com bases de incidência independentes,
      salvo sobreposição sobre o mesmo CAPEX (a verificar na instrução do
      processo junto do IAPMEI — art. 22.º §5 CFI).

    Retorna: {ano: crédito_rfai_aplicado} para YEARS = [2025..2029].
    """
    proj = hub["projeto_hub"]
    rfai_cfg = proj.get("rfai", {})

    if not rfai_cfg.get("aplicar", False):
        return {y: 0.0 for y in YEARS}

    taxa = float(rfai_cfg.get("taxa", 0.10))
    capex_elegivel = float(rfai_cfg.get("capex_elegivel", 0.0))
    limite_pct = float(rfai_cfg.get("limite_irc_pct", 0.50))

    if irc_taxa is None:
        irc_taxa = float(proj["viabilidade"]["irc_taxa"])

    # dep_total per year (pools + dep_jc) — usado para PT2030 [3a] Excel
    df_cap = hub_capex(hub)
    dep_total_map = df_cap.set_index("ano")["depreciacao"]
    capex_base = float(proj["capex"]["base"])
    pt2030_montante = float(proj["financiamento"]["PT2030"]["montante"])

    dr_imp = hub_dr_impact(hub)

    # Crédito total gerado: determinístico, calculado uma única vez no momento
    # do reconhecimento do investimento elegível (independente do IRC futuro).
    credito_restante = taxa * capex_elegivel
    result: dict[int, float] = {}

    for y in YEARS:
        if credito_restante <= 0:
            result[y] = 0.0
            continue

        ebit_y = float(dr_imp[y].get("ebit_impact", 0.0))
        dep_total_y = float(dep_total_map.get(y, 0.0))
        # Excel [3a]: PT2030 accrual usando dep_total (não dep_pools) — base tributável
        pt2030_3a_y = round(pt2030_montante * dep_total_y / capex_base, 0) if capex_base > 0 else 0.0
        # Excel [3b]: EBIT tributável = EBIT + PT2030_accrual_dep_total
        ebit_trib = ebit_y + pt2030_3a_y

        # Sem IRC liquidado (EBIT_trib ≤ 0) não há colecta à qual deduzir o crédito.
        # O crédito não se perde — transita para o exercício seguinte dentro
        # do prazo de carry-forward (art. 23.º §6 CFI).
        if ebit_trib <= 0:
            result[y] = 0.0
            continue

        irc_bruto = ebit_trib * irc_taxa

        # Tecto anual: 50 % do IRC liquidado (art. 23.º §6 CFI).
        # Aplicado aqui sobre IRC incremental do hub (conservador).
        # O limite legal incide sobre o IRC total da empresa — dado que
        # a Grestel core gera IRC substancialmente superior ao do hub,
        # a absorção real pode ser até 10× mais rápida do que este modelo
        # indica. O cenário conservador é preferível para efeitos de M6.
        aplicado = min(credito_restante, limite_pct * irc_bruto)
        aplicado = max(aplicado, 0.0)

        credito_restante -= aplicado
        result[y] = aplicado

    return result


def hub_dr_impact(
    hub: dict,
    crescimento_anual: float | None = None,
) -> dict[int, dict]:
    """Impacto anual do Hub no DR standalone da Grestel."""
    proj = hub["projeto_hub"]

    if crescimento_anual is None:
        crescimento_anual = float(proj["beneficios_anuais"]["crescimento_anual"])

    ben = proj["beneficios_anuais"]
    ben_pontual = proj["beneficios_pontuais"]
    inicio = int(proj["ano_inicio_beneficios"])

    # Gastos pré-operacionais não capitalizáveis (NCRF 6 §21): formação inicial.
    # Reconhecidos como gasto de FSE no ano em que ocorrem, antes do arranque operacional.
    gastos_preop: dict[int, float] = {}
    for gasto in proj.get("gastos_pre_operacionais", {}).values():
        ano_g = int(gasto.get("ano", 0))
        val_g = float(gasto.get("montante", 0.0))
        if ano_g and val_g:
            gastos_preop[ano_g] = gastos_preop.get(ano_g, 0.0) + val_g

    poupanca_op = float(ben["poupanca_operacional"])
    reducao_quebras = float(ben["reducao_quebras"])

    # Mantido por compatibilidade com o modelo atual.
    _ = abs(float(ben["opex_incremental"]))

    # Fator de ramp-up por ano (cenários adversos): reduz poupanças operacionais
    # nos primeiros anos de operação. Ausente no Base → 1.0 (100% dos benefícios).
    ramp_up = ben.get("ramp_up_por_ano", {})

    pessoal_pct = 0.68
    fse_pct = 0.32

    poupanca_pessoal_base = poupanca_op * pessoal_pct
    poupanca_fse_base = poupanca_op * fse_pct

    fse_opex_base = float(
        ben.get("opex_incremental")
        or proj.get("opex_detalhe", {}).get("total", 0)
    )

    subsidio = pt2030_reconhecimento(hub)

    libertacao_cronograma = ben_pontual.get("libertacao_cronograma")
    inventario_one_time = float(ben_pontual["libertacao_inventario"])
    ano_inventario = int(ben_pontual["ano"])

    # Benefícios comerciais: acréscimo de VN por canal B2C direto
    ben_com = proj.get("beneficios_comerciais", {})
    ano_com = int(ben_com.get("ano_inicio", 9999))
    vn_inc_map: dict = ben_com.get("vn_incremental", {})
    cmvmc_pct_com = float(ben_com.get("cmvmc_pct_incremental", 0.55))

    df_cap = hub_capex(hub)
    capex_map = df_cap.set_index("ano")

    result: dict[int, dict] = {}

    for y in YEARS:
        # Benefícios comerciais aplicáveis independentemente de ano_inicio_beneficios
        vn_inc = float(vn_inc_map.get(y, 0.0)) if y >= ano_com else 0.0
        cmvmc_inc = vn_inc * cmvmc_pct_com
        contrib_com = vn_inc - cmvmc_inc  # margem bruta incremental B2C

        if y < inicio:
            preop_y = gastos_preop.get(y, 0.0)
            result[y] = {
                "pessoal_reducao": 0.0,
                "fse_reducao": 0.0,
                "cmvmc_reducao": 0.0,
                "fse_opex_hub": 0.0,
                "gastos_preop_hub": preop_y,  # formação: gasto do exercício NCRF 6 §21
                "outros_rend_subsidio": 0.0,
                "depreciacao_hub": 0.0,
                "inventario_libertado": 0.0,
                "vn_incremental": vn_inc,
                "cmvmc_incremental": cmvmc_inc,
                "beneficio_liquido": contrib_com - preop_y,
                "ebitda_impact": contrib_com - preop_y,
                "ebit_impact": contrib_com - preop_y,
            }
            continue

        n = y - inicio
        fator = (1 + crescimento_anual) ** n
        ramp = float(ramp_up.get(y, 1.0))

        pessoal_red = poupanca_pessoal_base * fator * ramp
        fse_red = poupanca_fse_base * fator * ramp
        cmvmc_red = reducao_quebras * fator * ramp
        fse_opex = fse_opex_base * fator  # OPEX existe desde o arranque, sem ramp-up
        subsidio_y = subsidio.get(y, 0.0)

        dep_hub = (
            float(capex_map.loc[y, "depreciacao"])
            if y in capex_map.index
            else 0.0
        )

        if libertacao_cronograma:
            inventario = float(libertacao_cronograma.get(y, 0.0))
        else:
            inventario = inventario_one_time if y == ano_inventario else 0.0

        beneficio_liq = pessoal_red + fse_red + cmvmc_red - fse_opex
        ebitda_impact = beneficio_liq + subsidio_y + contrib_com
        ebit_impact = ebitda_impact - dep_hub

        result[y] = {
            "pessoal_reducao": pessoal_red,
            "fse_reducao": fse_red,
            "cmvmc_reducao": cmvmc_red,
            "fse_opex_hub": fse_opex,
            "gastos_preop_hub": 0.0,
            "outros_rend_subsidio": subsidio_y,
            "depreciacao_hub": dep_hub,
            "inventario_libertado": inventario,
            "vn_incremental": vn_inc,
            "cmvmc_incremental": cmvmc_inc,
            "beneficio_liquido": beneficio_liq,
            "ebitda_impact": ebitda_impact,
            "ebit_impact": ebit_impact,
        }

    return result


def hub_dfc_impact(hub: dict) -> dict[int, dict]:
    """
    Impacto do Hub nos fluxos de caixa consolidados da Grestel (DFC).

    Estrutura dos fluxos por categoria (NCRF 2):

    FLUXO DE INVESTIMENTO:
      • capex_hub          — pagamento de CAPEX (construção + equipamento)
      • pt2030_recebimento — subsídio PT2030 recebido em caixa (entrada)
      → O CAPEX de caixa NÃO inclui juros capitalizados (esses são fluxo
        de financiamento, não de investimento — pagados ao banco, não ao
        fornecedor de construção)

    FLUXO DE FINANCIAMENTO:
      • desembolso_banco   — entrada do empréstimo CGD/BPI
      • amortizacao_banco  — reembolso anual do capital
      • juros_banco        — total de juros pagos em caixa (SEMPRE saída,
                             independentemente de serem capitalizados ou não)
      • juros_capitalizados— subset dos juros pagos que são capitalizados
                             no AFT (NCRF 10); separados para reconciliação
                             DFC ↔ DR (a DFC usa o total; a DR usa só expensed)

    FLUXO OPERACIONAL (via var_nfm em dfc.py):
      • nfm_delta          — ΔNFM do hub (saída de caixa para capital circulante)
                             lido por build_dfc() e adicionado a var_nfm
    """
    proj = hub["projeto_hub"]
    pt = proj["financiamento"]["PT2030"]

    pt_montante = float(pt["montante"])
    pt_ano = int(pt["ano_recebimento"])

    df_cap = hub_capex(hub)
    df_fin = hub_financing(hub)

    capex_map = df_cap.set_index("ano")
    fin_map = df_fin.set_index("ano")

    nfm_map = hub_nfm(hub)

    result: dict[int, dict] = {}

    for y in YEARS:
        # CAPEX de caixa (não inclui juros capitalizados — esses pagam-se ao banco)
        capex_y = float(capex_map.loc[y, "capex"]) if y in capex_map.index else 0.0

        juros_y = float(fin_map.loc[y, "juros"]) if y in fin_map.index else 0.0
        jc_y = float(fin_map.loc[y, "juros_capitalizados"]) if y in fin_map.index else 0.0
        amort_y = float(fin_map.loc[y, "amortizacao"]) if y in fin_map.index else 0.0
        desembolso_y = float(fin_map.loc[y, "desembolso"]) if y in fin_map.index else 0.0

        pt2030_y = pt_montante if y == pt_ano else 0.0

        # ΔNFM: saída de caixa para capital circulante (fluxo operacional)
        nfm_y = nfm_map.get(y, 0.0)

        result[y] = {
            "capex_hub": -capex_y,
            "pt2030_recebimento": pt2030_y,
            "desembolso_banco": desembolso_y,
            "amortizacao_banco": -amort_y,
            "juros_banco": -juros_y,             # total pago em caixa
            "juros_capitalizados": jc_y,          # subset → reconciliação DFC/DR
            "nfm_delta": nfm_y,                   # ΔNFM → var_nfm em dfc.py
            "fluxo_investimento_hub": -capex_y + pt2030_y,
            "fluxo_financiamento_hub": desembolso_y - amort_y - juros_y,
        }

    return result


def hub_fcf(
    hub: dict,
    irc_taxa: float = 0.245,
    incluir_inventario: bool = True,
) -> pd.DataFrame:
    """
    FCF Livre Unlevered (FCFF) do Hub para análise de viabilidade (VAL/TIR).

    Fórmula académica:
    ┌──────────────────────────────────────────────────────────────────────┐
    │  FCF = NOPAT + D&A − CAPEX − ΔNFM ± Variações pontuais de capital  │
    │                                                                      │
    │  NOPAT = EBIT × (1 − t)   [Net Operating Profit After Tax]          │
    │  D&A   = Depreciações e Amortizações (não-caixa, somadas de volta)  │
    │  CAPEX = Investimento em Capital Fixo (saída de caixa)              │
    │  ΔNFM  = Variação das Necessidades de Fundo de Maneio               │
    └──────────────────────────────────────────────────────────────────────┘

    Esta é a medida de fluxo de caixa relevante para desconto ao WACC
    (abordagem entity value / firm value). Referências:
      • Brealey, Myers & Allen, 13.ª ed., §19.1
      • Damodaran, "Investment Valuation", 3.ª ed., §11

    Exclusões deliberadas (e justificação académica):
      1. Juros (carência 2025-2027 e período normal 2028+)
         Excluídos porque o FCF é UNLEVERED (desalavancado). O custo da
         dívida — incluindo o tax shield dos juros — está implicitamente
         incorporado no WACC. Incluir juros e usar WACC em simultâneo
         seria dupla contagem (Damodaran, §11.3).
         Os juros de carência (2025: ~118 k€; 2026: ~118 k€; 2027: ~118 k€)
         são REAIS e impactam a tesouraria — ver mapa_servico_divida() e
         mapa_tesouraria_mensal() para a análise de liquidez consolidada.
      2. Amortizações de capital (reembolso do principal)
         Fluxo de financiamento, não operacional. Capturado no DSCR e
         mapa de serviço da dívida, não no FCF para VAL.
      3. Desembolso do banco (entrada do empréstimo)
         Fluxo de financiamento — não integra o FCFF.

    Inclusões:
      • ΔNFM anual (hub_nfm): saída de caixa para capital circulante,
        real e materialmente relevante mesmo não transitando pela DR.
      • Libertação pontual de inventário (beneficio_pontual 2026): redução
        do inventário histórico da Grestel via WMS — entrada de caixa real.
      • Depreciação extra dos juros capitalizados (NCRF 10): incluída na
        depreciação total proveniente de hub_capex(). Efeito positivo líquido
        = D&A × t (tax shield adicional da maior depreciação).
      • Crédito fiscal RFAI (hub_rfai): redução directa do IRC pago, com
        valor integral (crédito × 1, não crédito × t). Tratado como componente
        separada do NOPAT para legibilidade e auditabilidade — permite isolar
        o efeito do benefício fiscal do benefício operacional. Ver hub_rfai()
        para a justificação académica da abordagem WACC vs. APV.
    """
    proj = hub["projeto_hub"]

    pt2030_cfg = proj["financiamento"]["PT2030"]
    pt2030_montante = float(pt2030_cfg["montante"])
    pt2030_ano_rec = int(pt2030_cfg["ano_recebimento"])
    capex_base_fcf = float(proj["capex"]["base"])

    dr_imp = hub_dr_impact(hub)
    df_cap = hub_capex(hub)
    nfm_map = hub_nfm(hub)
    rfai_map = hub_rfai(hub, irc_taxa=irc_taxa)

    capex_map = df_cap.set_index("ano")

    # Custo de oportunidade do terreno — saída única no primeiro ano de CAPEX
    # (UC API, Doc 3: ativos já detidos entram pelo custo de oportunidade; sem
    # este ajuste o investimento inicial fica subavaliado e o VAL artificialmente alto)
    terreno_cfg = proj.get("gastos_pre_operacionais", {}).get("terreno_custo_oportunidade", {})
    terreno_cof = 0.0
    terreno_ano: int | None = None
    if terreno_cfg.get("inclui_em_cfinv", False):
        terreno_cof = float(terreno_cfg.get("valor", 0.0))
        cronograma = proj.get("capex", {}).get("cronograma", {})
        if cronograma:
            terreno_ano = min(int(k) for k in cronograma)

    rows = []

    for y in YEARS:
        # CAPEX de caixa (excluí juros capitalizados — são fluxo de financiamento)
        capex_y = float(capex_map.loc[y, "capex"]) if y in capex_map.index else 0.0

        # Depreciação total inclui pools base + depreciação dos juros capitalizados
        dep_y = float(capex_map.loc[y, "depreciacao"]) if y in capex_map.index else 0.0

        imp = dr_imp[y]
        ebit_y = float(imp["ebit_impact"])

        # pt2030_accrual (dep_pools): usado em EBITDA/DR display — não muda EBIT
        pt2030_accrual_y = float(imp.get("outros_rend_subsidio", 0.0))

        # PT2030 [3a] (dep_total = dep_y): base tributável e reversão FCF [7]
        # dep_y já inclui dep_jc (de hub_capex) — alinhado com Excel [2] e [3a]
        pt2030_3a_y = round(pt2030_montante * dep_y / capex_base_fcf, 0) if capex_base_fcf > 0 else 0.0
        # PT2030 accrual e cash-in excluídos do FCF operacional — tratados no VALA
        ebit_trib_y = ebit_y
        pt2030_cash_y = pt2030_montante if y == pt2030_ano_rec else 0.0

        inventario_y = float(imp["inventario_libertado"]) if incluir_inventario else 0.0

        # ΔNFM: saída de caixa real que reduz o FCF (não está na DR)
        delta_nfm_y = nfm_map.get(y, 0.0)

        # Terreno: saída única no primeiro ano de CAPEX (custo de oportunidade)
        terreno_y = terreno_cof if (terreno_cof and y == terreno_ano) else 0.0

        rfai_y = rfai_map.get(y, 0.0)

        # NOPAT = EBIT_trib − IRC (RFAI excluído do FCF operacional — tratado no VALA)
        irc_bruto_y = max(0.0, ebit_trib_y) * irc_taxa
        irc_net_y = irc_bruto_y
        nopat = ebit_trib_y - irc_net_y if ebit_trib_y > 0 else ebit_trib_y

        # FCF operacional puro: sem PT2030 accrual, sem PT2030 cash-in, sem RFAI
        fcf = nopat + dep_y - capex_y - delta_nfm_y + inventario_y - terreno_y

        rows.append(
            {
                "ano": y,
                "ebitda_impact": imp["ebitda_impact"],
                "ebit_impact": ebit_y,
                "pt2030_accrual": pt2030_accrual_y,  # dep_pools — para EBITDA display
                "pt2030_3a": pt2030_3a_y,             # dep_total — base tributável [3a]
                "ebit_tributavel": ebit_trib_y,
                "nopat": nopat,
                "rfai_credito": rfai_y,
                "depreciacao": dep_y,
                "capex": -capex_y,
                "delta_nfm": -delta_nfm_y,
                "inventario_libertado": inventario_y,
                "terreno_oportunidade": -terreno_y,
                "pt2030_cash": pt2030_cash_y,
                "fcf_livre": fcf,
            }
        )

    return pd.DataFrame(rows)
