"""Rotas do rolling forecast."""

import math

from fastapi import APIRouter, Query

from src.engine.inputs import load
from src.engine.demonstracoes.rolling_forecast_mensal import (
    build_rolling_forecast,
    build_rolling_dual,
)

router = APIRouter(prefix="/api")


def _df_to_records(df):
    if not hasattr(df, "to_dict"):
        return []
    records = df.to_dict(orient="records")
    return [
        {k: (None if isinstance(v, float) and not math.isfinite(v) else v)
         for k, v in row.items()}
        for row in records
    ]


@router.get("/rolling-forecast/mensal")
def get_rolling_forecast(scenario: str = Query("Base"), hub_on: bool = Query(True)):
    a, base, sched = load(cenario=scenario)
    a.raw.setdefault("hub_logistico", {})["incluir_hub"] = hub_on
    rf = build_rolling_forecast(a, base, sched)

    stmt_m6 = rf.get("stmt_m6", {})

    return {
        "dr_mensal": _df_to_records(rf.get("dr_mensal")),
        "balanco_mensal": _df_to_records(rf.get("balanco_mensal")),
        "dfc_mensal": _df_to_records(rf.get("dfc_mensal")),
        "nfm_mensal": _df_to_records(rf.get("nfm_mensal")),
        "tesouraria": _df_to_records(rf.get("tesouraria_completa")),
        "reconciliacao_anual": rf.get("reconciliacao_anual", {}),
        # Demonstrações anuais M6 — Opção B: Balanço 2025 ancorado no fecho mensal Dez
        "stmt_m6": {
            "dr": _df_to_records(stmt_m6.get("dr")),
            "balanco": _df_to_records(stmt_m6.get("balanco")),
            "dfc": _df_to_records(stmt_m6.get("dfc")),
        },
    }


@router.get("/rolling-forecast/dual")
def get_rolling_forecast_dual(scenario: str = Query("Base")):
    """Rolling forecast paralelo sem projeto (hub_on=False) e com projeto (hub_on=True).

    Devolve ambos os cenários completos + tabela comparativa das métricas da linha
    rotativa (pico, mês do pico, drawdown médio, juros anuais, saldo 31-Dez, alertas).
    """
    a, base, sched = load(cenario=scenario)
    dual = build_rolling_dual(a, base, sched)

    def _rf_to_api(rf: dict) -> dict:
        stmt_m6 = rf.get("stmt_m6", {})
        return {
            "tesouraria": _df_to_records(rf.get("tesouraria_completa")),
            "balanco_mensal": _df_to_records(rf.get("balanco_mensal")),
            "dfc_mensal": _df_to_records(rf.get("dfc_mensal")),
            "linha_summary": rf.get("linha_summary", {}),
            "stmt_m6": {
                "dr": _df_to_records(stmt_m6.get("dr")),
                "balanco": _df_to_records(stmt_m6.get("balanco")),
                "dfc": _df_to_records(stmt_m6.get("dfc")),
            },
        }

    return {
        "sem_projeto": _rf_to_api(dual["sem_projeto"]),
        "com_projeto": _rf_to_api(dual["com_projeto"]),
        "comparacao": dual["comparacao"],
        "alertas_sem": dual["alertas_sem"],
        "alertas_com": dual["alertas_com"],
    }


@router.post("/rolling-forecast/update")
def post_rolling_forecast(body: dict):
    """Atualiza rolling forecast com valores realizados."""
    return {"status": "ok", "message": "Not implemented"}
