"""Hub Logístico M6 — CAPEX e depreciação por pool de ativo.

CAPEX schedule, AFT rolling e depreciação com juros capitalizados
(NCRF 10) — base do «Mapa de investimento» do plano de negócios M6.
"""
from __future__ import annotations

import pandas as pd

from ...inputs import YEARS
from .base import _dep_por_ano, _juros_capitalizados_map


def hub_capex(hub: dict) -> pd.DataFrame:
    """CAPEX schedule do Hub, AFT rolling e depreciação com juros capitalizados (NCRF 10)."""
    proj = hub["projeto_hub"]
    cron = proj["capex"]["cronograma"]

    # Juros capitalizados: aumentam o custo do AFT (NCRF 10) mas NÃO o CAPEX
    # de caixa — o desembolso real está em fluxo_financiamento (pagamento de juros)
    jc_map = _juros_capitalizados_map(hub)

    # Pool virtual para depreciação dos juros capitalizados:
    # mesma taxa que a construção civil (4 % / 25 anos), pois são parte
    # integrante do custo de construção (NCRF 10 §8 + DR 25/2009 Anexo I)
    taxa_dep_jc = float(
        proj["capex"]["pools"]["construcao_civil"]["taxa_depreciacao"]
    )
    vida_jc = int(proj["capex"]["pools"]["construcao_civil"]["vida_util_anos"])
    ano_dep_jc_inicio = int(proj["ano_inicio_beneficios"])  # depreciação inicia com o ativo

    jc_acumulado = 0.0  # total de juros capitalizados até à data
    aft = 0.0           # AFT contabilístico (inclui juros capitalizados)
    rows = []

    for y in YEARS:
        capex_y = float(cron.get(y, 0.0))

        # Depreciação dos pools base (excluindo juros cap. — base separada para
        # que pt2030_reconhecimento() não seja contaminado pelo NCRF 10)
        dep_pools = _dep_por_ano(proj, y)

        # Juros capitalizados no próprio ano → somados ao AFT neste ano
        jc_y = jc_map.get(y, 0.0)
        jc_acumulado += jc_y

        # Depreciação sobre o pool virtual dos juros capitalizados
        # Inicia em ano_dep_jc_inicio, dura vida_jc anos
        dep_jc = 0.0
        if jc_acumulado > 0 and y >= ano_dep_jc_inicio:
            anos_dep = y - ano_dep_jc_inicio
            if anos_dep < vida_jc:
                dep_jc = jc_acumulado * taxa_dep_jc

        dep_y = dep_pools + dep_jc

        # AFT contabilístico = CAPEX cronograma + juros capitalizados − depreciações
        aft = aft + capex_y + jc_y - dep_y

        rows.append(
            {
                "ano": y,
                "capex": capex_y,                # CAPEX caixa (para DFC)
                "juros_capitalizados_aft": jc_y, # acrescimo AFT por NCRF 10
                "depreciacao": dep_y,            # total = pools + virtual jc
                "dep_pools": dep_pools,          # depreciação base (para PT2030)
                "dep_juros_cap": dep_jc,         # depreciação adicional NCRF 10
                "aft_liquido_fim": max(aft, 0.0),
            }
        )

    return pd.DataFrame(rows)
