"""Validação de schema YAML via Pydantic models.

Garante que os ficheiros YAML de pressupostos têm a estrutura esperada
antes de serem carregados pelo motor. Reduz erros silenciosos e facilita
o diagnóstico de configurações incorrectas.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class IRCConfig(BaseModel):
    taxa_geral_por_ano: dict[int, float] = {}
    taxa_reduzida_por_ano: dict[int, float] = {}
    aplicar_taxa_reduzida: bool = False
    limiar_taxa_reduzida: float = 50000


class DerramaEscalao(BaseModel):
    limiar_inferior: float = 0
    limiar_superior: float | None = None
    taxa: float = 0.03


class DerramaEstadualConfig(BaseModel):
    escaloes: list[DerramaEscalao] = Field(default_factory=list)


class FiscalConfig(BaseModel):
    irc: IRCConfig = Field(default_factory=IRCConfig)
    derrama_estadual: DerramaEstadualConfig = Field(default_factory=DerramaEstadualConfig)
    derrama_municipal: float = 0.015
    iva_taxa_standard: float = 0.23
    tsu_patronal: float = 0.2375


class ScenarioOverride(BaseModel):
    """Valida overrides de cenário."""
    impostos: dict | None = None
    macro: dict | None = None
    vendas: dict | None = None


def validate_fiscal_yaml(data: dict) -> "FiscalConfig | None":
    """Valida estrutura do fiscal.yaml. Retorna FiscalConfig ou None se inválido."""
    try:
        return FiscalConfig(**data)
    except Exception:
        return None


def validate_yaml_structure(data: dict, required_keys: list[str] | None = None) -> list[str]:
    """Valida que um dicionário YAML contém chaves obrigatórias.

    Returns list of missing keys (empty = valid).
    """
    if required_keys is None:
        return []
    return [k for k in required_keys if k not in data]
