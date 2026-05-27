"""Hub Logístico M6 — financiamento bancário.

Plano de amortização do empréstimo bancário: saldos, juros (separados em
expensed vs. capitalizados NCRF 10) e amortizações de capital por ano.
"""
from __future__ import annotations

import pandas as pd

from ...inputs import YEARS
from .base import _iter_emprestimos, _juros_capitalizados_map, _juros_capitalizados_map_por_tranche


def hub_financing(hub: dict) -> pd.DataFrame:
    """
    Plano de amortização do empréstimo bancário do Hub.

    Desembolso no ano indicado no YAML. Amortizações a partir de
    `inicio_amortizacao` (após o período de carência de obra + ramp-up).

    Colunas adicionais vs. versão anterior:
      juros_capitalizados — parte dos juros incorporada no custo do AFT
                            (NCRF 10 §8); não reconhecida na DR como gasto.
      juros_expensed      — parte dos juros reconhecida na DR (= juros − cap.).
                            É esta coluna que alimenta financiamento_anual()
                            e, por cascata, o DR e o VAL desalavancado.

    Nota de tesouraria: ambas as componentes representam saídas de caixa reais
    (NCRF 2 §33b). A distinção é puramente contabilística (DR vs. AFT),
    não afeta os fluxos financeiros reais capturados na DFC.
    """
    proj = hub["projeto_hub"]
    jc_map = _juros_capitalizados_map(hub)

    # Acumuladores anuais agregados sobre todas as tranches de empréstimo
    agg: dict[int, dict] = {
        y: {"saldo_fim": 0.0, "emprestimos_nc": 0.0, "emprestimos_c": 0.0,
            "juros": 0.0, "amortizacao": 0.0, "desembolso": 0.0}
        for y in YEARS
    }

    for _, tranche in _iter_emprestimos(proj):
        capital = float(tranche["montante"])
        taxa = float(tranche["taxa_juro"])
        amort_anual = float(tranche["amortizacao_anual"])
        inicio_amort = int(tranche["inicio_amortizacao"])
        desembolso_ano = int(tranche["desembolso"])

        saldo = 0.0
        for y in YEARS:
            if y == desembolso_ano:
                saldo = capital

            juros = saldo * taxa
            amort = amort_anual if y >= inicio_amort and saldo > 0 else 0.0
            amort = min(amort, saldo)
            saldo = max(saldo - amort, 0.0)

            prox_amort = amort_anual if saldo > 0 else 0.0
            emp_c = min(prox_amort, saldo)
            emp_nc = max(saldo - emp_c, 0.0)

            a = agg[y]
            a["saldo_fim"] += saldo
            a["emprestimos_nc"] += emp_nc
            a["emprestimos_c"] += emp_c
            a["juros"] += juros
            a["amortizacao"] += amort
            a["desembolso"] += capital if y == desembolso_ano else 0.0

    rows = []
    for y in YEARS:
        a = agg[y]
        jc = jc_map.get(y, 0.0)
        rows.append(
            {
                "ano": y,
                "saldo_fim": a["saldo_fim"],
                "emprestimos_nc": a["emprestimos_nc"],
                "emprestimos_c": a["emprestimos_c"],
                "juros": a["juros"],
                "juros_capitalizados": jc,
                "juros_expensed": a["juros"] - jc,
                "amortizacao": a["amortizacao"],
                "desembolso": a["desembolso"],
            }
        )

    return pd.DataFrame(rows)


def hub_financing_por_tranche(hub: dict) -> dict[str, pd.DataFrame]:
    """Plano de amortização por tranche individual de capital alheio.

    Devolve {nome_tranche: DataFrame} com as mesmas colunas de hub_financing
    mas calculadas separadamente para cada fonte de dívida, sem agregação.
    Útil para construir o mapa de serviço da dívida por tranche.
    """
    proj = hub["projeto_hub"]
    jc_pt = _juros_capitalizados_map_por_tranche(hub)

    result: dict[str, pd.DataFrame] = {}

    for nome, tranche in _iter_emprestimos(proj):
        capital = float(tranche["montante"])
        taxa = float(tranche["taxa_juro"])
        amort_anual = float(tranche["amortizacao_anual"])
        inicio_amort = int(tranche["inicio_amortizacao"])
        desembolso_ano = int(tranche["desembolso"])
        jc_t = jc_pt.get(nome, {y: 0.0 for y in YEARS})

        rows = []
        saldo = 0.0
        for y in YEARS:
            if y == desembolso_ano:
                saldo = capital

            juros = saldo * taxa
            amort = amort_anual if y >= inicio_amort and saldo > 0 else 0.0
            amort = min(amort, saldo)
            saldo = max(saldo - amort, 0.0)

            prox_amort = amort_anual if saldo > 0 else 0.0
            emp_c = min(prox_amort, saldo)
            emp_nc = max(saldo - emp_c, 0.0)
            jc = jc_t.get(y, 0.0)

            rows.append({
                "ano": y,
                "saldo_fim": saldo,
                "emprestimos_nc": emp_nc,
                "emprestimos_c": emp_c,
                "juros": juros,
                "juros_capitalizados": jc,
                "juros_expensed": juros - jc,
                "amortizacao": amort,
                "desembolso": capital if y == desembolso_ano else 0.0,
            })

        result[nome] = pd.DataFrame(rows)

    return result
