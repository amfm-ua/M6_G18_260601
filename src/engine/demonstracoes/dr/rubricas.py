from __future__ import annotations

import pandas as pd

from ...inputs import ALL_YEARS, YEARS
from ...projetos import ecogres as ecogres_mod
from .loaders import _get_dr_2024_value


def _outros_rendimentos(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
    df_inv: pd.DataFrame | None = None,
    hub_dr: dict[int, dict] | None = None,
    eco: dict | None = None,
) -> tuple[dict, dict]:
    """
    Calcula Outros Rendimentos e Ganhos (receitas não operacionais).

    COMPONENTES:
      1. Cedência de Locações: aluguel de imóveis/espaços físicos (receita passiva)
      2. Cedência de Pessoal: faturação de funcionários cedidos a terceiros
      3. Equivalência Patrimonial: resultado proporcional de associadas/joint ventures
      4. Subsídios e Contribuições: Gov., programas (investimento, R&D, emprego)
      5. Ganhos de Câmbio: variações cambiais (se transações em moeda estrangeira)
      6. Subsídio Hub: se Hub Logístico ativo (subsídio específico)

    LÓGICA TEMPORAL:
      - 2024: usa valor real (input base.outros_rendimentos)
      - 2025: mescla componentes: cedências + equivalência + subsídios gov.
      - 2026-2029: crescimento estruturado (cedências sobem com inflação,
                    equivalência com investimento, subsídios estáveis)

    CRESCIMENTO (Plurianual):
      - Cedências: crescimento moderado (2,5% a 2,5%, depende de pressupostos)
      - Equivalência: depende de resultado investido em associadas
      - Subsídios: assumem constância (Gov. mantém programas)

    RETORNA:
      - (res, breakdown): dict anual + dict com detalhe por componente
        Permite rastreabilidade de origem de cada rendimento
    """
    ab = sched.plurianual_AB

    g = [
        ab.get("AB74", 0.02),
        ab.get("AB84", 0.025),
        ab.get("AB93", 0.025),
        ab.get("AB94", 0.025),
    ]

    outros_rend_2024 = _get_dr_2024_value(base, "outros_rend", 0.0)

    if df_inv is not None:
        req_2025 = float(
            df_inv[df_inv.ano == 2025]["rend_equiv_patrimonial"].iloc[0]
        )
    else:
        req_2025 = sched.investimento["rend_equiv_patrimonial"][2025]

    if eco is not None:
        df_ced = ecogres_mod.cedencia_pessoal_anual(eco)
        cedencia_map = dict(zip(df_ced["ano"], df_ced["cedencia_pessoal"]))
    else:
        cedencia_map = {y: 0.0 for y in ALL_YEARS}

    ced_pessoal_2025 = cedencia_map.get(2025, 0.0)
    ced_pessoal_2024 = cedencia_map.get(2024, 0.0)

    cedencia_loc_base = (
        base.outros_rendimentos["Cedencia_locacoes"]
        - ced_pessoal_2024
    )

    subs_cambio_base = (
        base.outros_rendimentos["Subs_Investimento"]
        + base.outros_rendimentos["Subs_Exploracao"]
        + float(base.outros_rendimentos.get("Cambio_Outros_base", 0.0))
    )

    hub_subsidio_2025 = (
        hub_dr[2025].get("outros_rend_subsidio", 0.0)
        if hub_dr
        else 0.0
    )

    base_2025 = (
        cedencia_loc_base
        + ced_pessoal_2025
        + req_2025
        + subs_cambio_base
        + hub_subsidio_2025
    )

    res = {
        2024: outros_rend_2024,
        2025: base_2025,
    }

    base_loc_subs = cedencia_loc_base + subs_cambio_base
    frac_loc = cedencia_loc_base / base_loc_subs if base_loc_subs > 0 else 0.5

    equiv_2024 = base.outros_rendimentos["Equivalencia_patrimonial"]
    ced_loc_2024 = cedencia_loc_base

    subs_2024 = (
        outros_rend_2024
        - ced_loc_2024
        - ced_pessoal_2024
        - equiv_2024
    )

    breakdown: dict[int, dict] = {
        2024: {
            "outros_rend_ced_loc": ced_loc_2024,
            "outros_rend_ced_pessoal": ced_pessoal_2024,
            "outros_rend_equiv_patr": equiv_2024,
            "outros_rend_subs_cambio": subs_2024,
        },
        2025: {
            "outros_rend_ced_loc": cedencia_loc_base,
            "outros_rend_ced_pessoal": ced_pessoal_2025,
            "outros_rend_equiv_patr": req_2025,
            "outros_rend_subs_cambio": subs_cambio_base + hub_subsidio_2025,
        },
    }

    if df_inv is not None:
        base_no_req_ced = (
            base_2025
            - req_2025
            - hub_subsidio_2025
            - ced_pessoal_2025
        )

        for i, y in enumerate(YEARS[1:]):
            req_y = float(
                df_inv[df_inv.ano == y]["rend_equiv_patrimonial"].iloc[0]
            )
            ced_p_y = cedencia_map.get(y, 0.0)

            hub_sub_y = (
                hub_dr[y].get("outros_rend_subsidio", 0.0)
                if hub_dr and y in hub_dr
                else 0.0
            )

            grown = base_no_req_ced * (1 + g[i]) ** (i + 1)

            res[y] = grown + req_y + ced_p_y + hub_sub_y

            breakdown[y] = {
                "outros_rend_ced_loc": grown * frac_loc,
                "outros_rend_ced_pessoal": ced_p_y,
                "outros_rend_equiv_patr": req_y,
                "outros_rend_subs_cambio": grown * (1 - frac_loc) + hub_sub_y,
            }
    else:
        cur = base_2025 - ced_pessoal_2025 - hub_subsidio_2025

        for i, y in enumerate(YEARS[1:]):
            ced_p_y = cedencia_map.get(y, 0.0)

            hub_sub_y = (
                hub_dr[y].get("outros_rend_subsidio", 0.0)
                if hub_dr and y in hub_dr
                else 0.0
            )

            cur = cur * (1 + g[i])

            res[y] = cur + ced_p_y + hub_sub_y

            breakdown[y] = {
                "outros_rend_ced_loc": cur * frac_loc,
                "outros_rend_ced_pessoal": ced_p_y,
                "outros_rend_equiv_patr": cur * (1 - frac_loc),
                "outros_rend_subs_cambio": hub_sub_y,
            }

    return res, breakdown


def _outros_gastos(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
) -> dict:
    """Outros gastos e perdas — crescem com inflação/pressupostos plurianuais."""
    ab = sched.plurianual_AB

    inflacao_raw = a.macro.get("inflacao", {})

    if isinstance(inflacao_raw, dict):
        inflacao = inflacao_raw.get(
            2025,
            inflacao_raw.get("anual", {}).get(2025, a.inflacao_anual(2025)),
        )
    else:
        inflacao = 0.023

    val_2024 = _get_dr_2024_value(base, "outros_gastos", 0.0)
    val_2025 = val_2024 * (1 + inflacao)

    res = {
        2024: val_2024,
        2025: val_2025,
    }

    g = [
        ab.get("AB68", 0.05),
        ab.get("AB84", 0.025),
        ab.get("AB93", 0.025),
        ab.get("AB94", 0.025),
    ]

    cur = val_2025

    for i, y in enumerate(YEARS[1:]):
        cur = cur * (1 + g[i])
        res[y] = cur

    return res


def _imparidades(
    df_clientes: pd.DataFrame,
    base: Base2024,
    a: "Assumptions | None" = None,
) -> dict:
    """
    Calcula Imparidades de Clientes (Provisão para Crédito Duvidoso).

    CONCEITO CONTABILÍSTICO (IAS 39 / IFRS 9):
      Uma imparidade é uma redução de valor estimada para cobrir o risco de
      que clientes não paguem as suas dívidas. É uma provisão prudencial.

    METODOLOGIA (Abordagem Simplificada):
      - Imparidade = taxa × saldo de clientes em carteira (default: 0,5%)
      - Taxa configurável via globais.yaml → imparidade_clientes_taxa
      - Em cenários Stress, a taxa pode ser elevada (ex: 1,0%) para capturar
        maior risco de crédito — NCRF 12 §58 (abordagem coletiva simplificada)

    NOTA SOBRE BALANÇO:
      O saldo de clientes no Balanço é BRUTO (baseado em PMR, sem dedução de
      provisões). As imparidades impactam apenas a DR. Esta opção é válida
      ao abrigo do SNC mas deve ser explicitada no Anexo (NCRF 12 §74).
    """
    imparidades_2024 = _get_dr_2024_value(base, "imparidades", 0.0)
    taxa_imp = float(
        (a.impostos if a else {}).get("imparidade_clientes_taxa", 0.005)
    ) if a else 0.005

    res = {
        2024: imparidades_2024,
    }

    for _, r in df_clientes.iterrows():
        if r["ano"] >= 2025:
            res[r["ano"]] = r["saldo_clientes"] * taxa_imp

    return res
