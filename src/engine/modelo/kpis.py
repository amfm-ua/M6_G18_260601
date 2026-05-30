"""
Módulo: engine/analitica/kpis.py — KPIs Financeiros (Indicadores de Desempenho)
Versão: v2 — Estrutura modular temática
Idioma: Português Europeu

OBJETIVO ACADÉMICO:
Calcula um painel de Indicadores-Chave de Desempenho (KPIs) financeiros que permite
avaliação rápida da saúde financeira da empresa sem necessidade de ler demonstrações completas.

KPIs SÃO MÉTRICAS AGREGADAS CRÍTICAS:
  - Resumem informação de páginas de demonstrações em números-chave
  - Permitem comparação inter-anual (Ano 1 vs Ano 2)
  - Permitem benchmarking (empresa vs. indústria)
  - Guiam decisões de gestão e investimento

┌─────────────────────────────────────────────────────────────────┐
│ CATEGORIAS DE KPIs                                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ 1. KPIs DE RENTABILIDADE (Lucro ÷ Receita ou Ativo)           │
│    - Margem de EBITDA: EBITDA / VN × 100%                     │
│      Interpreta: lucro operacional antes de depr./juros        │
│      Benchmark: 15-25% para indústria (varia muito)            │
│                                                                 │
│    - Margem de EBIT: EBIT / VN × 100%                         │
│      Interpreta: lucro operacional após depreciação            │
│      Benchmark: 10-20% (produto de EBITDA - depr./VN)         │
│                                                                 │
│    - Margem Líquida: Resultado Líquido / VN × 100%            │
│      Interpreta: lucro final disponível para acionistas        │
│      Benchmark: 5-15% (após juros e impostos)                  │
│                                                                 │
│    - ROE (Return on Equity): Resultado Líquido / Patrimônio    │
│      Interpreta: rentabilidade do capital do acionista         │
│      Benchmark: >15% (bom), 10-15% (aceitável), <10% (fraco)  │
│                                                                 │
│    - ROA (Return on Assets): Resultado Líquido / Ativo Total   │
│      Interpreta: eficiência na utilização dos ativos           │
│      Benchmark: 5-10% (varia muito por setor)                  │
│                                                                 │
│    - ROIC (Return on Invested Capital): EBIT(1-IR) / Capital   │
│      Interpreta: retorno do capital total investido            │
│      Benchmark: >10% (positivo para valor)                     │
│                                                                 │
│ 2. KPIs DE LIQUIDEZ (Caixa vs. Obrigações Curto Prazo)        │
│    - Current Ratio: Ativo Corrente / Passivo Corrente          │
│      Interpreta: capacidade de pagar contas curto prazo        │
│      Benchmark: 1.0-2.0 (abaixo 1 = perigo)                   │
│                                                                 │
│    - Liquidez Imediata: Caixa / Passivo Corrente               │
│      Interpreta: capacidade de pagar HOJE (sem vender ativos)  │
│      Benchmark: >0.5 (conservador)                             │
│                                                                 │
│ 3. KPIs DE SOLVÊNCIA (Dívida vs. Patrimônio)                  │
│    - Debt-to-Equity: Dívida Total / Patrimônio                 │
│      Interpreta: alavancagem (quanto dinheiro emprestado)      │
│      Benchmark: <1.5 (conservador <1.0, agressivo >2.0)       │
│                                                                 │
│    - Debt-to-EBITDA: Dívida / EBITDA                           │
│      Interpreta: quantos anos até pagar dívida com lucro       │
│      Benchmark: <3 anos (capacidade de reembolso)              │
│                                                                 │
│    - Cobertura de Juros: EBIT / Juros                          │
│      Interpreta: quantas vezes o lucro cobre a carga juro      │
│      Benchmark: >5 (excelente), 3-5 (bom), <2 (risco)         │
│                                                                 │
│ 4. KPIs DE EFICIÊNCIA (Ciclo de Caixa)                         │
│    - Ciclo de Caixa: PMR + DMI - PMP (dias)                    │
│      Interpreta: dias de capital circulante necessário         │
│      Benchmark: <60 dias (bom), 60-90 (aceitável), >90 (risco)│
│      Fórmula: (Clientes + Inventário - Fornecedores) em dias   │
│                                                                 │
│    - Rotação de Ativo: VN / Ativo Total (vezes/ano)           │
│      Interpreta: eficiência de geração de receita com ativos   │
│      Benchmark: >1.5 (boa utilização de ativos)                │
│                                                                 │
│ 5. KPIs DE CRESCIMENTO (Evolução Ano a Ano)                   │
│    - Crescimento de Receita: (VN_ano2 / VN_ano1 - 1) × 100%   │
│      Interpreta: expansão do negócio                           │
│      Benchmark: 3-10% (sustentável)                            │
│                                                                 │
│    - Crescimento de EBITDA: (EBITDA_ano2 / EBITDA_ano1 - 1)   │
│      Interpreta: expansão de lucro operacional                 │
│      Benchmark: > Crescimento Receita (melhor margem)          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

UTILIDADE PRÁTICA:
  - Gestão: monitorar mensalmente para alertas rápidos
  - Bancos: para decisões de crédito (capacidade de reembolso)
  - Acionistas: para avaliar retorno do investimento
  - Investidores: para comparar empresas dentro do setor
  - Reguladores: para monitorar riscos sistémicos

LIMITAÇÕES:
  - KPIs são "retratos" (histórico) não "previsões" (futuro)
  - Não capturam qualidade de gestão (governança)
  - Podem ser manipulados ("creative accounting")
  - Requerem contexto de indústria para interpretação
  - Mudanças contabilísticas afetam comparabilidade
"""

from __future__ import annotations

import pandas as pd

from ..inputs import ALL_YEARS, YEARS
from ..demonstracoes.nfm import ciclo_caixa_dias
from ..operacional.clientes import iva_efetivo_vendas

# Janela da fase de maturidade (mesma convenção de extensao_maturidade: 2030-2034).
# Usada para estender os KPIs operacionais/ESG em regime de cruzeiro.
ANOS_MATURIDADE = list(range(2030, 2035))


def _effective_tax_rate(dr_row: pd.Series) -> float:
    """Calcula taxa efetiva de IRC a partir da DR.

    A versão anterior usava 0.20 hardcoded no ROIC.
    Aqui usamos a própria DR:
        taxa efetiva = IRC / RAI

    Nota:
        Na DR, o IRC está normalmente com sinal negativo.
        Por isso usamos abs(irc).
    """
    rai = float(dr_row.get("rai", 0.0))
    irc = float(dr_row.get("irc", 0.0))

    if rai <= 0:
        return 0.0

    taxa = abs(irc) / rai

    # Proteção contra valores anómalos.
    return max(0.0, min(taxa, 1.0))


def build_kpis(
    df_dr: pd.DataFrame,
    df_balanco: pd.DataFrame,
    df_dfc: pd.DataFrame,
    a,
) -> pd.DataFrame:
    """Calcula KPIs financeiros a partir da DR, Balanço e DFC."""
    rows = []

    iva_venda = iva_efetivo_vendas(a) if a is not None else 0.0
    iva_compra_cmvmc = float(a.impostos.get("IVA_CMVMC", 0.23)) if a is not None else 0.23
    iva_compra_fse   = float(a.impostos.get("IVA_FSE", 0.15)) if a is not None else 0.0

    # Itera sobre os anos efetivamente presentes na DR — assim os KPIs estendem-se
    # automaticamente a 2030-2034 quando o horizonte de maturidade está ligado, e
    # mantêm-se em 2024-2029 quando não está (sem hardcode de ALL_YEARS).
    anos_kpi = sorted(int(y) for y in df_dr["ano"].unique())
    for y in anos_kpi:
        dr = df_dr[df_dr.ano == y].iloc[0]
        bs = df_balanco[df_balanco.ano == y].iloc[0]

        vn = float(dr["vn"])

        ebitda = float(dr["ebitda"])
        ebit = float(dr["ebit"])
        rl = float(dr["rl"])

        # EBITDA operacional puro: exclui Outros Rendimentos (equivalência patrimonial,
        # cedências, subsídios). Usado no DSCR para análise bancária de solvência.
        outros_rend = float(dr.get("outros_rend", 0.0))
        ebitda_puro = ebitda - outros_rend

        margem_ebitda = ebitda / vn if vn else 0.0
        margem_ebit = ebit / vn if vn else 0.0
        margem_rl = rl / vn if vn else 0.0

        if y > 2024:
            dr_prev = df_dr[df_dr.ano == (y - 1)].iloc[0]
            vn_prev = float(dr_prev["vn"])
            cresc_vn = (vn / vn_prev - 1) if vn_prev else 0.0
        else:
            cresc_vn = 0.0

        ativo_corrente = float(bs["total_ac"])
        passivo = float(bs["total_passivo"])
        cp = float(bs["total_cp"])
        ativo = float(bs["total_ativo"])
        emprestimos_nc = float(bs["emprestimos_nc"])
        emprestimos_c = float(bs["emprestimos_c"])
        caixa = float(bs.get("caixa", 0.0))

        pc_components = ["fornecedores", "eoep_credor", "outros_pc", "emprestimos_c", "linha_credito_cp"]
        if "total_pc" in df_balanco.columns:
            passivo_corrente = float(bs["total_pc"])
        else:
            passivo_corrente = sum(float(bs.get(c, 0.0)) for c in pc_components)

        liquidez_geral = (
            ativo_corrente / passivo_corrente
            if passivo_corrente
            else 0.0
        )

        liquidez_reduzida = (
            (ativo_corrente - float(bs["inventarios"])) / passivo_corrente
            if passivo_corrente
            else 0.0
        )

        autonomia = cp / ativo if ativo else 0.0
        solvabilidade = cp / passivo if passivo else 0.0
        endividamento = passivo / ativo if ativo else 0.0
        debt_equity = passivo / cp if cp else 0.0

        divida_financeira = emprestimos_nc + emprestimos_c
        divida_liquida = divida_financeira - caixa

        nd_ebitda = divida_liquida / ebitda if ebitda else 0.0
        debt_ebitda = nd_ebitda

        roa = rl / ativo if ativo else 0.0
        roe = rl / cp if cp else 0.0
        roce = ebit / (cp + divida_financeira) if (cp + divida_financeira) else 0.0

        capital_investido = cp + divida_financeira
        taxa_irc_efetiva = _effective_tax_rate(dr)

        roic = (
            float(dr["ebit"]) * (1 - taxa_irc_efetiva) / capital_investido
            if capital_investido
            else 0.0
        )

        # PMR e PMP com IVA correcto: PMR com IVA efectivo de vendas (só PT);
        # PMP com IVA_CMVMC=23 % apenas sobre CMVMC (matérias-primas).
        # DMI usa custo de produção pleno — ver nfm.ciclo_caixa_dias().
        pessoal_val = abs(float(dr.get("gastos_pessoal", 0.0)))
        pmr, dmi, pmp, ciclo_caixa = ciclo_caixa_dias(
            float(bs["clientes"]),
            float(bs["inventarios"]),
            float(bs["fornecedores"]),
            vn,
            float(dr["cmvmc"]),
            float(dr["fse"]),
            iva_venda,
            iva_compra_cmvmc,
            pessoal=pessoal_val,
        )

        juros_abs = abs(float(dr["juros"]))

        cob_juros = ebit / juros_abs if juros_abs else 0.0

        # DSCR com EBITDA operacional puro (sem equivalência patrimonial, cedências
        # ou subsídios) — análise bancária usa EBITDA livre de não-recorrentes.
        # Amortização líquida de novos empréstimos para não penalizar anos de refinanciamento.
        dfc_row = df_dfc[df_dfc.ano == y]
        if not dfc_row.empty:
            _r = dfc_row.iloc[0]
            _pag = abs(float(_r.get("pag_emprestimos", 0.0)))
            _rec = max(0.0, float(_r.get("rec_emprestimos", 0.0)))
            amort_capital = max(0.0, _pag - _rec)
            juros_pagos_fin = abs(float(_r.get("juros_pagos_fin", juros_abs)))
        else:
            amort_capital = 0.0
            juros_pagos_fin = juros_abs
        servico_divida = juros_pagos_fin + amort_capital
        dscr = ebitda_puro / servico_divida if servico_divida else 0.0
        dscr_total = ebitda / servico_divida if servico_divida else 0.0  # com outros_rend (para comparação)

        cmvmc = float(dr["cmvmc"])
        cmvmc_vn = abs(cmvmc) / vn if vn else 0.0

        rows.append(
            {
                "ano": y,
                "vn": vn,
                "ebitda": ebitda,
                "ebitda_puro": ebitda_puro,
                "ebit": ebit,
                "rl": rl,
                "outros_rend": outros_rend,
                "cmvmc": cmvmc,
                "cmvmc_vn": cmvmc_vn,
                "fse": float(dr["fse"]),
                "gastos_pessoal": float(dr["gastos_pessoal"]),
                "ebitda_margin": margem_ebitda,
                "ebit_margin": margem_ebit,
                "rl_margin": margem_rl,
                "cresc_vn": cresc_vn,
                "liquidez_geral": liquidez_geral,
                "liquidez_reduzida": liquidez_reduzida,
                "autonomia_financeira": autonomia,
                "solvabilidade": solvabilidade,
                "endividamento": endividamento,
                "debt_equity": debt_equity,
                "debt_ebitda": debt_ebitda,
                "nd_ebitda": nd_ebitda,
                "emprestimos_nc": emprestimos_nc,
                "emprestimos_c": emprestimos_c,
                "caixa": caixa,
                "divida_liquida": divida_liquida,
                "total_ativo": ativo,
                "cp": cp,
                "roa": roa,
                "roe": roe,
                "roce": roce,
                "roic": roic,
                "taxa_irc_efetiva": taxa_irc_efetiva,
                "pmr_dias": pmr,
                "pmp_dias": pmp,
                "dmi_dias": dmi,
                "ciclo_caixa": ciclo_caixa,
                "cobertura_juros": cob_juros,
                "juros_abs": juros_abs,
                "dscr": dscr,
                "dscr_com_outros_rend": dscr_total,
                "amort_capital": amort_capital,
            }
        )

    df = pd.DataFrame(rows)
    # Official API contract aliases (API_CONTRACT.md)
    df["current_ratio"] = df["liquidez_geral"]
    df["PMR"] = df["pmr_dias"]
    df["PMP"] = df["pmp_dias"]
    df["DMI"] = df["dmi_dias"]
    return df


def gas_por_peca_anual(a, base) -> pd.DataFrame:
    """Projeta consumo de gás natural por peça produzida 2024-2029."""
    esg = base.raw.get("esg_2024", {})

    gas_base = esg.get("gas_natural_kwh", 0)
    pecas_base = esg.get("producao_total_pecas", 0)

    gpeca_base = esg.get(
        "gas_por_peca_kwh",
        gas_base / pecas_base if pecas_base else 0,
    )

    esg_a = a.raw.get("esg", {})
    cresc_pecas = esg_a.get("crescimento_producao_pecas", {})
    efic_gas = esg_a.get("eficiencia_gas_anual", {})

    def _rate(val, year, default):
        """Aceita scalar (aplica em todos os anos) ou dict (por ano)."""
        if isinstance(val, dict):
            return val.get(year, default)
        if isinstance(val, (int, float)):
            return float(val)
        return default

    rows = [
        {
            "ano": 2024,
            "gas_kwh_total": gas_base,
            "producao_pecas": pecas_base,
            "gas_por_peca_kwh": gpeca_base,
            "var_vs_2024": 0.0,
        }
    ]

    prev_pecas = pecas_base
    prev_gpeca = gpeca_base

    # Regime de cruzeiro (2030-2034): a produção cresce à inflação (mesma taxa g
    # da extensão das demonstrações) e a eficiência do gás estabiliza (sem novos
    # ganhos) — coerente com o estado estacionário, conservador para o ESG.
    from ..demonstracoes.extensao_maturidade import G_MATURIDADE_DEFAULT
    for y in list(YEARS) + ANOS_MATURIDADE:
        if y <= 2029:
            prev_pecas = prev_pecas * (1 + _rate(cresc_pecas, y, 0.03))
            prev_gpeca = prev_gpeca * (1 - _rate(efic_gas, y, 0.0))
        else:
            prev_pecas = prev_pecas * (1 + G_MATURIDADE_DEFAULT)
            # prev_gpeca mantido (eficiência estável em cruzeiro)

        gas_total = prev_pecas * prev_gpeca
        var = (prev_gpeca / gpeca_base - 1) if gpeca_base else 0.0

        rows.append(
            {
                "ano": y,
                "gas_kwh_total": gas_total,
                "producao_pecas": prev_pecas,
                "gas_por_peca_kwh": prev_gpeca,
                "var_vs_2024": var,
            }
        )

    return pd.DataFrame(rows)


def ecommerce_pct_anual(a, df_vn=None) -> pd.DataFrame:
    """Calcula % de vendas via E-Commerce por ano.
    
    Fonte: smart_objetivos.yaml → ecommerce_global_2025
    Objetivo SMART: E-Commerce ≥ 20% das vendas globais até 2025.
    """
    from ..inputs import ALL_YEARS
    
    result = {}
    for y in ALL_YEARS:
        if df_vn is not None and not df_vn.empty and "vn_total" in df_vn.columns:
            vn_total = float(df_vn[df_vn.ano == y]["vn_total"].sum()) if y in df_vn.ano.values else 0.0
        else:
            vn_total = 0.0
        
        # Check for E-Commerce channel data in assumptions
        canais = a.raw.get("canais", {}) if a is not None else {}
        ecom_data = canais.get("E_Commerce", {}) if canais else {}
        
        # Try to get E-Commerce percentage from assumptions or use default growth
        if ecom_data and "peso_global" in ecom_data:
            pct = float(ecom_data["peso_global"])
        else:
            # Fallback: estimate based on known 2024 growth (+40% online sales)
            # 2024 estimated ~15%, growing toward 20% target
            base_pct = float(a.raw.get("ecommerce_pct_base", 0.15)) if a is not None else 0.15
            if y == 2024:
                pct = base_pct
            elif y >= 2025:
                pct = min(base_pct + 0.01 * (y - 2024), 0.25)
            else:
                pct = base_pct
        
        result[y] = pct

    # Regime de cruzeiro (2030-2034): mix de canais mantido constante ao nível de
    # 2029 — a quota do E-Commerce consolida-se na sua quota madura (sem re-crescer,
    # o que contrariaria o estado estacionário).
    pct_2029 = result.get(2029, result.get(max(result), 0.0))
    for y in ANOS_MATURIDADE:
        result[y] = pct_2029

    anos_out = list(ALL_YEARS) + ANOS_MATURIDADE
    rows = [{"ano": y, "ecommerce_pct": result[y]} for y in anos_out]
    return pd.DataFrame(rows)
