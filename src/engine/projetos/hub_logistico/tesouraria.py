"""Hub Logístico M6 — mapas de tesouraria e serviço da dívida.

Mapa anual de serviço da dívida com DSCR e desdobramento mensal dos
fluxos de caixa (2025-2026) — instrumentos de análise de liquidez
exigidos no plano de negócios M6.
"""
from __future__ import annotations

import pandas as pd

from .base import load, _iter_emprestimos, _juros_capitalizados_map
from .financiamento import hub_financing, hub_financing_por_tranche
from .impacto import hub_dr_impact


def mapa_servico_divida(hub: dict | None = None) -> pd.DataFrame:
    """
    Mapa anual de serviço da dívida do Hub com DSCR — análise de risco de liquidez.

    O Mapa de Serviço da Dívida é o instrumento central para avaliar o risco
    de liquidez associado ao financiamento do projeto, distinto do VAL:

    ┌─────────────────────────────────────────────────────────────────────┐
    │  SERVIÇO DA DÍVIDA = Juros Pagos (total) + Amortizações de Capital  │
    │                                                                      │
    │  DSCR = EBITDA incremental Hub / Serviço da Dívida                  │
    │  (Debt Service Coverage Ratio — rácio de cobertura do serviço)      │
    │                                                                      │
    │  DSCR > 1,0 → hub gera EBITDA suficiente para cobrir a dívida      │
    │  DSCR > 1,2 → confortável (critério mínimo bancário típico)         │
    │  DSCR > 1,5 → cobertura robusta (preferido por bancos de projeto)   │
    │  DSCR < 1,0 → tesouraria central Grestel subsidia o serviço         │
    │                                                                      │
    │  Ref: S&P Global, "Project Finance Methodology" (2014), §5.3;       │
    │       Finnerty, "Project Financing", 3.ª ed., cap. 6                │
    └─────────────────────────────────────────────────────────────────────┘

    Período de Carência (2025-2027):
      Durante a construção e ramp-up operacional, o hub apenas paga juros
      (sem amortização de capital). O DSCR neste período é calculado sobre
      o EBITDA incremental do hub, que é negativo ou nulo (o hub ainda não
      opera plenamente). A tesouraria da Grestel core (ceramics) deve
      absorver este serviço — risco de liquidez a monitorizar centralmente.

    Juros Capitalizados vs. Expensed:
      A tabela mostra ambos para clareza contabilística (NCRF 10):
      • juros_pagos_total = cash flow real saído (sempre saída, cap. ou exp.)
      • juros_capitalizados = porção adicionada ao AFT (não na DR)
      • juros_expensed_dr = porção na DR como gasto financeiro do período
    """
    if hub is None:
        hub = load()

    df_fin = hub_financing(hub)
    dr_imp = hub_dr_impact(hub)
    jc_map = _juros_capitalizados_map(hub)

    rows = []

    for _, row in df_fin.iterrows():
        y = int(row["ano"])
        juros_total = float(row["juros"])
        amort = float(row["amortizacao"])
        saldo = float(row["saldo_fim"])
        jc = jc_map.get(y, 0.0)
        juros_exp = juros_total - jc

        servico_divida = juros_total + amort

        ebitda_hub = float(dr_imp[y].get("ebitda_impact", 0.0)) if y in dr_imp else 0.0

        dscr = ebitda_hub / servico_divida if servico_divida > 0 else None

        rows.append(
            {
                "ano": y,
                "saldo_em_divida": saldo + amort,   # saldo início do ano
                "saldo_fim": saldo,
                "juros_pagos_total": juros_total,
                "juros_capitalizados": jc,
                "juros_expensed_dr": juros_exp,
                "amortizacao_capital": amort,
                "servico_total_divida": servico_divida,
                "ebitda_hub_incremental": ebitda_hub,
                "dscr_hub": dscr,
                "periodo_carencia": amort == 0.0,
            }
        )

    return pd.DataFrame(rows)


def mapa_servico_divida_por_tranche(hub: dict | None = None) -> dict[str, pd.DataFrame]:
    """Mapa de serviço da dívida individual por fonte de capital alheio.

    Calcula o mesmo conjunto de métricas de mapa_servico_divida mas separado
    por tranche, sem DSCR (que é um rácio consolidado EBITDA/serviço total).

    Colunas por tranche:
      ano, saldo_em_divida, saldo_fim, juros_pagos_total,
      juros_capitalizados, juros_expensed_dr, amortizacao_capital,
      servico_total_divida, periodo_carencia
    """
    if hub is None:
        hub = load()

    per_tranche = hub_financing_por_tranche(hub)
    result: dict[str, pd.DataFrame] = {}

    for nome, df_tr in per_tranche.items():
        rows = []
        for _, row in df_tr.iterrows():
            y = int(row["ano"])
            juros_total = float(row["juros"])
            amort = float(row["amortizacao"])
            saldo = float(row["saldo_fim"])
            jc = float(row["juros_capitalizados"])
            juros_exp = juros_total - jc
            servico = juros_total + amort
            rows.append({
                "ano": y,
                "saldo_em_divida": saldo + amort,
                "saldo_fim": saldo,
                "juros_pagos_total": juros_total,
                "juros_capitalizados": jc,
                "juros_expensed_dr": juros_exp,
                "amortizacao_capital": amort,
                "servico_total_divida": servico,
                "periodo_carencia": amort == 0.0,
            })
        result[nome] = pd.DataFrame(rows)

    return result


def mapa_tesouraria_mensal(hub: dict | None = None) -> pd.DataFrame:
    """
    Desdobramento mensal dos fluxos de caixa do Hub para 2025 e 2026.

    Base mensal obrigatória em M6 (alinhada com Fase 1 do M3):
    O M3 exige «previsão de base mensal» para o primeiro exercício económico.
    O M6, ao analisar o impacto do projeto sobre as projeções do M3, deve
    detalhar mensalmente o período de construção e arranque para:
      (a) Evidenciar o risco de liquidez dos juros da carência mês a mês
      (b) Identificar o momento exato da saída de caixa para NFM inicial
      (c) Modelar a recuperação de IVA sobre o CAPEX (pago antes do reembolso)
      (d) Servir como base para o «Orçamento de Tesouraria» e mapas de
          serviço da dívida — instrumentos exigidos no plano de negócios M6

    Estrutura dos fluxos mensais:
      INVESTIMENTO: CAPEX mensal (perfil de obra civil) + CAPEX equipamento
      FINANCIAMENTO: desembolso banco (mês 1/2025) + juros mensais
      OPERACIONAL: ΔNFM (arranque operacional, H2 2026)
      SUBSÍDIO PT2030: recebimento esperado (Q1 2027, fora desta janela)

    IVA sobre CAPEX:
      O CAPEX está sujeito a IVA (23 %). A empresa paga o IVA ao fornecedor
      e recupera-o via declaração periódica (tipicamente 1-3 meses depois).
      Este diferencial temporário é uma necessidade de financiamento adicional
      não capturada no modelo anual. A função mostra a exposição bruta.

    Nota: os totais anuais devem coincidir com os valores do modelo anual
    (consistência M3 ↔ M6). O primeiro mês de 2027 está fora da janela mas
    o PT2030 (recebimento 2027) aparece na DFC anual de 2027.
    """
    if hub is None:
        hub = load()

    proj = hub["projeto_hub"]
    pt = proj["financiamento"]["PT2030"]
    nfm_cfg = proj.get("necessidades_fundo_maneio", {})
    cron_mensal = proj.get("cronograma_mensal", {})

    # Dados por tranche para acompanhamento mensal de saldo e juros
    tranches = [
        {
            "capital": float(tr["montante"]),
            "taxa_mensal": float(tr["taxa_juro"]) / 12,
            "desembolso_ano": int(tr["desembolso"]),
            "saldo": 0.0,
        }
        for _, tr in _iter_emprestimos(proj)
    ]

    iva_taxa = 0.23  # IVA à taxa normal (CIVA art. 18.º §1 al. c))

    # Pré-calcular recuperação de IVA sobre CAPEX em M+2 (regime mensal CIVA art. 27.º)
    anos_janela = [2025, 2026]
    meses_lista = ["jan", "fev", "mar", "abr", "mai", "jun",
                   "jul", "ago", "set", "out", "nov", "dez"]
    iva_recuperacao: dict[tuple[int, int], float] = {}
    for _ano in anos_janela:
        _cron = cron_mensal.get(str(_ano), {})
        for _i, _mes in enumerate(meses_lista, start=1):
            _capex = float(_cron.get(_mes, 0.0))
            if _capex == 0.0:
                continue
            _rec_i = _i + 2
            _rec_ano = _ano
            if _rec_i > 12:
                _rec_i -= 12
                _rec_ano += 1
            if _rec_ano in anos_janela:
                key = (_rec_ano, _rec_i)
                iva_recuperacao[key] = iva_recuperacao.get(key, 0.0) + _capex * iva_taxa

    rows = []
    nfm_lancado = False

    for ano in anos_janela:
        cron_ano = cron_mensal.get(str(ano), {})

        for i, mes in enumerate(meses_lista, start=1):
            capex_mes = float(cron_ano.get(mes, 0.0))

            # Desembolso de cada tranche: Janeiro do seu ano de desembolso (mês 1)
            desembolso_mes = 0.0
            for t in tranches:
                if ano == t["desembolso_ano"] and i == 1:
                    t["saldo"] = t["capital"]
                    desembolso_mes += t["capital"]

            juros_mes = sum(t["saldo"] * t["taxa_mensal"] for t in tranches)
            saldo_total = sum(t["saldo"] for t in tranches)

            iva_capex = capex_mes * iva_taxa
            iva_recuperado = iva_recuperacao.get((ano, i), 0.0)

            # ΔNFM: lançado no 1.º mês de operação (Julho 2026 — arranque faseado)
            delta_nfm_mes = 0.0
            if ano == 2026 and i == 7 and not nfm_lancado:
                stock_manut = float(nfm_cfg.get("stock_manutencao_inicial", 0.0))
                consumiveis = float(nfm_cfg.get("consumiveis_arranque", 0.0))
                psp = float(nfm_cfg.get("psp_fornecedores_dias", 30))
                compras = float(nfm_cfg.get("compras_manutencao_anuais", 0.0))
                cred_forn = (psp / 360) * compras
                delta_nfm_mes = stock_manut + consumiveis - cred_forn
                nfm_lancado = True

            fluxo_inv = -capex_mes
            fluxo_fin = desembolso_mes - juros_mes
            fluxo_op = -delta_nfm_mes
            # IVA: saída no mês do CAPEX, recuperação em M+2
            fluxo_iva = -iva_capex + iva_recuperado

            rows.append(
                {
                    "ano": ano,
                    "mes": i,
                    "mes_nome": mes,
                    "capex_mensal": -capex_mes,
                    "iva_capex_pago": -iva_capex,
                    "iva_capex_recuperado": iva_recuperado,
                    "desembolso_banco": desembolso_mes,
                    "juros_mensais": -juros_mes,
                    "delta_nfm": -delta_nfm_mes,
                    "fluxo_investimento": fluxo_inv,
                    "fluxo_financiamento": fluxo_fin,
                    "fluxo_operacional": fluxo_op,
                    "variacao_caixa_mensal": fluxo_inv + fluxo_fin + fluxo_op + fluxo_iva,
                    "saldo_divida_fim": saldo_total,
                }
            )

    return pd.DataFrame(rows)
