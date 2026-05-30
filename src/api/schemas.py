"""Schemas Pydantic usados pela API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class RunRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    cenario: str = "Base"
    hub_on: bool = False
    ecogres_on: bool = True
    cozedura_on: bool = False
    assumptions: dict[str, Any] | None = None
    persist: bool = False


class CustomScenarioPayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    label: str = ""
    description: str = ""
    overrides: dict[str, Any] | None = None
