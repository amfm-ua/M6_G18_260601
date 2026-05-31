"""
Módulo: engine/financas/financiamento.py — Financiamento: Empréstimos, Juros e Dívida
Versão: v2 — Estrutura modular temática
Idioma: Português Europeu

OBJETIVO ACADÉMICO:
Calcula a estrutura de financiamento (dívida) e respetiva carga financeira (juros).
Financiamento é crítico para empresas que investem em imobilizado (máquinas, edifícios).

CONCEITOS FUNDAMENTAIS:

┌─────────────────────────────────────────────────────────────────┐
│ DÍVIDA FINANCEIRA (CAPITAL EM DÍVIDA)                           │
│                                                                 │
│ Estrutura:                                                     │
│   - Empréstimo Principal (draw-down): montante total solicitado│
│   - Taxa de Juro: % a.a. (ex: 3% ao ano)                      │
│   - Prazo: nº de anos para amortizar (ex: 8 anos)             │
│   - Carência: período sem amortizações (ex: 2 anos)           │
│                                                                 │
│ EXEMPLO: Empréstimo €5.000.000 a 3% durante 8 anos            │
│   Ano 1-2 (Carência): Paga só juros (€150.000/ano)            │
│   Ano 3-10 (Amortização): Amortiza + juros (decrescente)      │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ CÁLCULO DE JUROS (Carga Financeira)                            │
│                                                                 │
│ Juros = Saldo da Dívida no início do período × Taxa de Juro   │
│                                                                 │
│ EXEMPLO AMORTIZAÇÃO LINEAR:                                    │
│   Empréstimo: €1.000.000                                       │
│   Taxa: 5% a.a.                                                │
│   Prazo: 5 anos (sem carência)                                 │
│                                                                 │
│   Ano 1:                                                       │
│     Saldo Inicial: €1.000.000                                  │
│     Juros: €1.000.000 × 5% = €50.000                          │
│     Amortização: €1.000.000 / 5 = €200.000                    │
│     Saldo Final: €800.000                                      │
│                                                                 │
│   Ano 2:                                                       │
│     Saldo Inicial: €800.000                                    │
│     Juros: €800.000 × 5% = €40.000 (desceu!)                  │
│     Amortização: €200.000 (linear)                             │
│     Saldo Final: €600.000                                      │
│                                                                 │
│   ... (similar para anos 3-5)                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

IMPACTO FINANCEIRO:

  1. Na DR (Demonstração de Resultados):
     - Juros são despesa financeira (reduz RAI)
     - Amortizações NÃO aparecem na DR (aparecem na DFC)
     - Impacto: Juros decrescem ano a ano (menos dívida = menos juros)

  2. Na DFC (Demonstração de Fluxos de Caixa):
     - Juros: saída de caixa (pagamento efetivo)
     - Amortizações: saída de caixa (reembolso do principal)
     - Total Fluxo Financiamento = Juros + Amortizações (saída)

  3. Na Análise de Rentabilidade:
     - EBIT (Earnings Before Interest & Tax): exclui juros
     - Comparável entre empresas (ignora estrutura financeira)
     - RAI (Result After Interest): inclui juros
     - EBIT > Juros anuais = saudável (cobre carga financeira)

MÉTRICAS IMPORTANTES:

  - Dívida Líquida = Dívida Total - Caixa
  - Rácio de Endividamento = Dívida / Patrimônio
    * <1.0: conservador
    * 1.0-2.0: moderado
    * >2.0: agressivo (risco)

  - Cobertura de Juros = EBIT / Juros
    * >5: excelente (folga para pagar juros)
    * 2-5: aceitável
    * <2: risco elevado (juros muitos grandes)

  - Vida Média da Dívida = (Σ Amortizações × Anos) / Dívida Total
    * Indica quantos anos até estar livre de dívida

EXEMPLO IMPACTO NO MODELO:
  - Empréstimo é input (YAML: sched.financiamento)
  - Plano de amortização é pré-calculado (não dinâmico com vendas)
  - Juros crescem/descem determinísticos (menos flexibilidade)
  - Se vendas caem e não pode pagar juros = risco de insolvência
"""

from __future__ import annotations

import logging
import pandas as pd

from ..inputs import Schedules, Assumptions, ALL_YEARS

logger = logging.getLogger(__name__)


def _hub_fin(a: Assumptions) -> dict[int, dict] | None:
    """Retorna impacto financeiro Hub por ano, ou None se Hub desativado."""
    try:
        raw_hub = a.raw.get("hub_logistico", {})

        if not raw_hub.get("incluir_hub", False):
            return None

        from ..projetos import hub_logistico as hub_mod

        df = hub_mod.hub_financing(raw_hub)

        return df.set_index("ano").to_dict(orient="index")

    except Exception as exc:
        logger.warning("_hub_fin falhou: %s", exc)
        return None


def _get_fin_value(
    fin: dict,
    section: str,
    year: int,
    default: float = 0.0,
) -> float:
    """Obtém valor de sched.financiamento com fallback seguro."""
    try:
        return float(fin[section][year])
    except (KeyError, TypeError, ValueError):
        return float(default)


def financiamento_anual(
    sched: Schedules,
    a: Assumptions | None = None,
) -> pd.DataFrame:
    """Tabela anual de financiamento: juros, capital em dívida e amortizações."""
    fin = sched.financiamento

    # Toggle: run-off contratual 2030-2034 (default OFF = dívida constante)
    runoff_on = bool(
        (a.raw.get("financiamento") or {}).get("terminal_debt_runoff", False)
    ) if a is not None else False
    runoff_data = sched.financiamento_runoff if runoff_on else {}

    # Choque de taxa variável (Euribor): ajuste em pontos base sobre o saldo de dívida variável
    risco = (a.raw.get("risco_taxa") or {}) if a is not None else {}
    euribor_choque_bps = float(risco.get("euribor_choque_bps", 0))
    aplica_variavel = bool(risco.get("aplica_a_taxa_variavel", True))
    pct_variavel = float(risco.get("pct_divida_variavel", 1.0))
    # Incremento de juros por euro de dívida variável (ex: 200bps = 0.02)
    choque_rate = (euribor_choque_bps / 10_000.0) if aplica_variavel else 0.0

    # Fallback antigo apenas se schedules.yaml não tiver juros_total[2024].
    juros_dr_2024_fallback = 528_161.02

    hub_impact = _hub_fin(a) if a is not None else None

    rows = []

    for y in ALL_YEARS:
        # Run-off override para anos 2030+ quando toggle está ativo
        use_runoff = runoff_on and y >= 2030 and runoff_data

        def _get(section: str, default: float = 0.0) -> float:
            if use_runoff and section in runoff_data and isinstance(runoff_data[section], dict):
                return float(runoff_data[section].get(y, default))
            return _get_fin_value(fin, section, y, default=default)

        juros = _get(
            "juros_total",
            default=juros_dr_2024_fallback if y == 2024 else 0.0,
        )

        cap_fim = _get("capital_divida_total_fim_ano")
        amort = _get("amortizacoes_capital")
        emp_nc = _get("emprestimos_NC")
        emp_c = _get("emprestimos_C")

        hub_juros = 0.0
        hub_cap_fim = 0.0
        hub_incluido = False

        if hub_impact and y in hub_impact:
            h = hub_impact[y]

            # Usa juros_expensed (não juros totais) para não reconhecer na DR
            # os juros capitalizados no AFT (NCRF 10). Os juros_capitalizados
            # aumentam o custo do ativo e são depreciados — não são gasto do período.
            hub_juros = float(h.get("juros_expensed", h.get("juros", 0.0)))
            hub_saldo = float(h.get("saldo_fim", 0.0))
            hub_amort = float(h.get("amortizacao", 0.0))
            hub_emp_nc = float(h.get("emprestimos_nc", 0.0))
            hub_emp_c = float(h.get("emprestimos_c", 0.0))

            cap_fim += hub_saldo
            amort += hub_amort
            emp_nc += hub_emp_nc
            emp_c += hub_emp_c

            hub_cap_fim = hub_saldo
            hub_incluido = True

        # Choque Euribor aplicado sobre o total de capital em dívida (base + Hub)
        juros_choque = cap_fim * pct_variavel * choque_rate

        rows.append(
            {
                "ano": y,
                "juros_total": juros + hub_juros + juros_choque,
                "juros_base": juros,
                "juros_hub": hub_juros,
                "juros_choque_euribor": juros_choque,
                "capital_divida_total_fim": cap_fim,
                "amortizacoes_capital": amort,
                "emprestimos_NC": emp_nc,
                "emprestimos_C": emp_c,
                "hub_capital_fim": hub_cap_fim,
                "hub_incluido": hub_incluido,
            }
        )

    return pd.DataFrame(rows)


def imposto_selo_anual(df_fin: pd.DataFrame, a: Assumptions | None = None) -> pd.DataFrame:
    """Imposto do Selo sobre financiamento por ano.

    Verba 17.3.1: 4% sobre juros pagos (CONFIRMADO R&C 2024).
    Verba 17.1: sobre utilização de crédito (estimativa, toggle separado).

    Args:
        df_fin: output de financiamento_anual() com coluna 'juros_total'.
        a: Assumptions — lê bloco 'imposto_selo' de globais.yaml.

    Returns:
        DataFrame com colunas: ano, selo_juros, selo_credito, selo_total.
    """
    cfg = (a.raw.get("imposto_selo") or {}) if a is not None else {}
    taxa_juros = float(cfg.get("taxa_juros", 0.04))
    aplicar_juros = bool(cfg.get("aplicar_juros", True))
    aplicar_utilizacao = bool(cfg.get("aplicar_utilizacao", False))
    taxa_longo = float(cfg.get("taxa_utilizacao_credito_longo", 0.006))

    rows = []
    for _, r in df_fin.iterrows():
        juros = abs(float(r.get("juros_total", 0.0)))
        cap_fim = abs(float(r.get("capital_divida_total_fim", 0.0)))

        selo_juros = taxa_juros * juros if aplicar_juros else 0.0

        # Verba 17.1: estimativa sobre saldo de dívida de longo prazo
        selo_credito = taxa_longo * cap_fim if aplicar_utilizacao else 0.0

        rows.append({
            "ano": int(r["ano"]),
            "selo_juros": selo_juros,
            "selo_credito": selo_credito,
            "selo_total": selo_juros + selo_credito,
        })

    return pd.DataFrame(rows)