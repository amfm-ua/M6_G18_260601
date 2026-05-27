from __future__ import annotations

from ...inputs import Assumptions, Base2024
from ...projetos import ecogres as ecogres_mod


def _get_dr_2024_value(base: Base2024, key: str, default: float = 0.0) -> float:
    """Lê uma rubrica da DR real 2024 a partir de base.raw, com fallback."""
    try:
        return float(base.raw["dr_2024_real"][key])
    except (AttributeError, KeyError, TypeError, ValueError):
        return float(default)


def _load_hub_dr(a: Assumptions) -> dict[int, dict] | None:
    """Carrega os impactos do Hub na DR, ou None se o Hub estiver desativado."""
    try:
        hub_raw = a.raw.get("hub_logistico", {})
        if not hub_raw.get("incluir_hub", False):
            return None

        from ...projetos import hub_logistico as hub_mod

        return hub_mod.hub_dr_impact(hub_raw)
    except Exception:
        return None


def _load_ecogres(a: Assumptions) -> dict | None:
    """Carrega os pressupostos da Ecogres de a.raw se ativa em runtime."""
    try:
        eco = a.raw.get("ecogres", {})
        if not eco or not eco.get("incluir_ecogres", False):
            return None
        return eco
    except Exception:
        return None
