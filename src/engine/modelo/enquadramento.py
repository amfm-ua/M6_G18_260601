"""engine/modelo/enquadramento.py — Framework Estratégico M6 (Ansoff, 4Ps, ODS, Plano de Ação).

Carrega enquadramento_estrategico.yaml e expõe funções de consulta
usadas pela rota GET /api/enquadramento.
"""

from __future__ import annotations

import functools
from pathlib import Path

import yaml

_YAML_PATH = Path(__file__).parent.parent / "data" / "master" / "enquadramento_estrategico.yaml"


@functools.lru_cache(maxsize=1)
def _load() -> dict:
    with open(_YAML_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_ansoff() -> dict:
    """Retorna o posicionamento Ansoff e justificação empírica."""
    return _load()["enquadramento_m6"]["ansoff"]


def get_marketing_mix() -> dict:
    """Retorna a análise 4Ps (Place, Product, Price, Promotion)."""
    return _load()["enquadramento_m6"]["marketing_mix"]


def get_ods() -> dict:
    """Retorna o alinhamento com os ODS (objetivos e indicadores)."""
    return _load()["enquadramento_m6"]["ods"]


def get_plano_acao() -> dict:
    """Retorna o plano de ação por pilar (Investimento, Operações, Marketing)."""
    return _load()["enquadramento_m6"]["plano_acao"]


def get_regra_investimento() -> dict:
    """Retorna a verificação da regra de investimento M6 (15%–30% ATL)."""
    return _load()["enquadramento_m6"]["regra_investimento"]


def get_fatores_criticos() -> list[dict]:
    """Retorna os fatores críticos de sucesso."""
    return _load()["enquadramento_m6"]["fatores_criticos_sucesso"]


def get_ideia_inovadora() -> dict:
    """Retorna a descrição da ideia inovadora (Indústria 4.0)."""
    return _load()["enquadramento_m6"]["ideia_inovadora"]


def get_enquadramento_completo() -> dict:
    """Retorna o enquadramento estratégico completo (todos os blocos)."""
    return _load()["enquadramento_m6"]
