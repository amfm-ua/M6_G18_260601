"""Driver-derived operational benefits for the logistics hub.

This module keeps the hub's personnel and breakage savings tied to the same
organic activity base used by the consolidated model. It deliberately avoids
using the hub's own commercial uplift as a driver, so the commercial layer is
not counted twice.
"""
from __future__ import annotations

import copy
from typing import Any

import pandas as pd

from ...inputs import Assumptions, Base2024, Schedules, YEARS
from ...operacional import cmvmc as cmvmc_mod
from ...operacional import pessoal as pessoal_mod
from ...operacional import vendas as vendas_mod


def _year_value(mapping: dict, year: int, default: float = 0.0) -> float:
    return float(mapping.get(year, mapping.get(str(year), default)))


def _clean_hub_for_alpha(hub: dict, incluir_hub: bool) -> dict:
    hub_copy = copy.deepcopy(hub)
    hub_copy["incluir_hub"] = incluir_hub
    ben = (
        hub_copy
        .get("projeto_hub", {})
        .get("beneficios_anuais", {})
    )
    ben.pop("pessoal_saving_derivado", None)
    ben.pop("quebras_saving_derivado", None)
    return hub_copy


def hub_pessoal_saving_derivado(
    a: Assumptions,
    base: Base2024,
    df_total: pd.DataFrame,
    hub: dict,
) -> dict[int, float]:
    """Personnel saving from the alpha gap, measured on organic VN only.

    Returns the hub-attributable share of:
        pessoal(alpha_sem_hub) - pessoal(alpha_com_hub)

    The series is ready to be consumed by ``hub_dr_impact``; any scenario ramp-up
    is applied here so the impact layer can simply read the amount for each year.
    """
    proj = hub.get("projeto_hub", {})
    ben = proj.get("beneficios_anuais", {})
    cfg = ben.get("pessoal_driver", {})

    if not bool(cfg.get("aplicar", False)):
        return {}

    inicio = int(proj.get("ano_inicio_beneficios", 2026))
    share = float(cfg.get("share_alpha_diff", cfg.get("share", 1.0)))
    aplicar_ramp = bool(cfg.get("aplicar_ramp_up", True))
    ramp_up = ben.get("ramp_up_por_ano", {})

    a_sem = copy.deepcopy(a)
    a_sem.raw["hub_logistico"] = _clean_hub_for_alpha(hub, False)

    a_com = copy.deepcopy(a)
    a_com.raw["hub_logistico"] = _clean_hub_for_alpha(hub, True)

    sem = (
        pessoal_mod.pessoal_anual(a_sem, base, df_total)
        .set_index("ano")["gastos_pessoal"]
        .to_dict()
    )
    com = (
        pessoal_mod.pessoal_anual(a_com, base, df_total)
        .set_index("ano")["gastos_pessoal"]
        .to_dict()
    )

    result: dict[int, float] = {}
    for y in YEARS:
        if y < inicio:
            continue
        ramp = _year_value(ramp_up, y, 1.0) if aplicar_ramp else 1.0
        result[y] = max(0.0, float(sem.get(y, 0.0)) - float(com.get(y, 0.0))) * share * ramp

    return result


def hub_quebras_saving_derivado(
    a: Assumptions,
    base: Base2024,
    df_prod: pd.DataFrame,
    df_merc: pd.DataFrame,
    hub: dict,
) -> dict[int, float]:
    """Breakage saving indexed to organic production cost (CMVMC_prod).

    The base scalar ``reducao_quebras`` is anchored to the *lost conversion cost*
    of post-firing breakage (caco) attributable to handling — the energy + labour
    embedded in a fired piece that is sunk when it breaks and is NOT recovered by
    the Ecogres recycling loop (which only recovers material value at scrap price).
    See m6_hub_assumptions.yaml (beneficios_anuais.quebras_driver) for the physical
    derivation. Here that base is scaled by the growth of CMVMC_prod (volume proxy)
    and the adoption ramp.
    """
    proj = hub.get("projeto_hub", {})
    ben = proj.get("beneficios_anuais", {})
    cfg = ben.get("quebras_driver", {})

    if not bool(cfg.get("aplicar", False)):
        return {}

    inicio = int(proj.get("ano_inicio_beneficios", 2026))
    base_saving = float(ben.get("reducao_quebras", 0.0))
    aplicar_ramp = bool(cfg.get("aplicar_ramp_up", True))
    ramp_up = ben.get("ramp_up_por_ano", {})

    if base_saving == 0.0:
        return {}

    df_cmvmc = cmvmc_mod.cmvmc_anual(a, base, df_prod, df_merc)
    driver = df_cmvmc.set_index("ano")["cmvmc_prod"].to_dict()
    ref = float(driver.get(inicio, 0.0))
    if ref <= 0.0:
        return {}

    result: dict[int, float] = {}
    for y in YEARS:
        if y < inicio:
            continue
        ramp = _year_value(ramp_up, y, 1.0) if aplicar_ramp else 1.0
        result[y] = base_saving * (float(driver.get(y, ref)) / ref) * ramp

    return result


def aplicar_drivers_derivados_hub(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
    *,
    df_prod: pd.DataFrame | None = None,
    df_merc: pd.DataFrame | None = None,
    df_total: pd.DataFrame | None = None,
    hub: dict[str, Any] | None = None,
) -> dict:
    """Populate derived hub benefit series in a hub assumptions dict.

    If ``hub`` is omitted, ``a.raw["hub_logistico"]`` is updated in place.
    Returns the updated hub dict in both cases.
    """
    hub_cfg = copy.deepcopy(hub if hub is not None else a.raw.get("hub_logistico", {}))
    if not hub_cfg or "projeto_hub" not in hub_cfg:
        return hub_cfg

    if df_prod is None:
        df_prod = vendas_mod.vendas_anuais(a, base, sched)
    if df_merc is None:
        df_merc = vendas_mod.vendas_mercadorias_anuais(a, base)
    if df_total is None:
        df_total = vendas_mod.resumo_anual(df_prod, df_merc)

    ben = hub_cfg["projeto_hub"].setdefault("beneficios_anuais", {})

    pessoal_series = hub_pessoal_saving_derivado(a, base, df_total, hub_cfg)
    if pessoal_series:
        ben["pessoal_saving_derivado"] = pessoal_series

    quebras_series = hub_quebras_saving_derivado(a, base, df_prod, df_merc, hub_cfg)
    if quebras_series:
        ben["quebras_saving_derivado"] = quebras_series

    if hub is None:
        a.raw["hub_logistico"] = hub_cfg

    return hub_cfg
