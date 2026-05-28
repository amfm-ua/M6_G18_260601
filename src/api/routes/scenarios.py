"""Rotas para execução e comparação de cenários."""

from fastapi import APIRouter, Query

from src.api.schemas import RunRequest
from src.api.serializers import _fse_mensal_to_rows, _wrap_rows
from src.engine.inputs import upsert_custom_scenario, load
from src.engine.inputs.loader import CENARIOS
from src.engine.modelo.model import dataframe_to_records, run_model
from src.engine.modelo.sensitivity import sensitivity_ui
from src.engine.operacional import producao as producao_mod

_CENARIOS_COMPARACAO = ["Base", "Upside", "Downside", "Stress"]

router = APIRouter(prefix="/api")


@router.get("/scenarios/all")
def get_scenarios_all(
    hub_on: bool = Query(False),
    ecogres_on: bool = Query(True),
):
    """Corre todos os cen?rios e devolve DR/Balan?o/DFC/KPIs + detalhe FSE."""
    result = {}

    for sc in CENARIOS:
        dfs = run_model(cenario=sc, hub_on=hub_on, ecogres_on=ecogres_on)
        rec = dataframe_to_records(dfs)

        fse_det_anual_rec = rec.get("fse_detalhe_anual", [])
        fse_det_mensal = dfs.get("fse_detalhe_mensal_2025", {})

        result[sc] = {
            "dr": _wrap_rows(rec.get("dr")),
            "balanco": _wrap_rows(rec.get("balanco")),
            "dfc": _wrap_rows(rec.get("dfc")),
            "kpis": _wrap_rows(rec.get("kpis")),
            "fse_detalhe_anual": _wrap_rows(fse_det_anual_rec) if fse_det_anual_rec else {"rows": []},
            "fse_detalhe_mensal_2025": {"rows": _fse_mensal_to_rows(fse_det_mensal)},
            "pessoal_contab_anual": _wrap_rows(rec.get("pessoal_contab_anual", [])),
            "pessoal_depart_anual": _wrap_rows(rec.get("pessoal_depart_anual", [])),
            "producao_anual": _wrap_rows(rec.get("producao_anual", [])),
            "eoep_mensal_2025": _wrap_rows(rec.get("eoep_mensal_2025", [])),
            "vendas_mensal_2025": _wrap_rows(rec.get("vendas_mensal_2025", [])),
            "dr_mensal_2025": _wrap_rows(rec.get("dr_mensal_2025", [])),
            "tesouraria_mensal_2025": _wrap_rows(rec.get("tesouraria_mensal_2025", [])),
        }

    return result


@router.get("/producao")
def get_producao(
    cenario: str = Query("Base"),
    hub_on: bool = Query(False),
    ecogres_on: bool = Query(True),
):
    """Orçamento de produção anual e mensal (2024-2029) com custos unitários reais do YAML."""
    dfs = run_model(cenario=cenario, hub_on=hub_on, ecogres_on=ecogres_on)
    rec = dataframe_to_records(dfs)

    return {
        "cenario": cenario,
        "producao_anual": _wrap_rows(rec.get("producao_anual", [])),
        "producao_mensal_2025": _wrap_rows(rec.get("producao_mensal_2025", [])),
    }


@router.get("/scenarios/hub-delta")
def get_scenarios_hub_delta(ecogres_on: bool = Query(True)):
    """Impacto incremental do Hub em cada cenário: Δ EBITDA e Δ RL por ano."""
    result = {}
    for sc in _CENARIOS_COMPARACAO:
        dfs_sem = run_model(cenario=sc, hub_on=False, ecogres_on=ecogres_on)
        dfs_com = run_model(cenario=sc, hub_on=True, ecogres_on=ecogres_on)
        dr_sem = dataframe_to_records(dfs_sem).get("dr", [])
        dr_com = dataframe_to_records(dfs_com).get("dr", [])
        deltas = []
        for r_com in dr_com:
            ano = r_com.get("ano")
            r_sem = next((r for r in dr_sem if r.get("ano") == ano), {})
            deltas.append({
                "ano": ano,
                "delta_ebitda": float(r_com.get("ebitda", 0)) - float(r_sem.get("ebitda", 0)),
                "delta_rl": float(r_com.get("rl", 0)) - float(r_sem.get("rl", 0)),
            })
        result[sc] = deltas
    return result


@router.get("/sensitivity")
def get_sensitivity(
    cenario: str = Query("Base"),
    hub_on: bool = Query(False),
    ecogres_on: bool = Query(True),
):
    """Análise de sensibilidade completa (one-at-a-time) — todos os runs no backend."""
    _ = ecogres_on  # reservado para uso futuro
    result = sensitivity_ui(cenario=cenario, hub_on=hub_on)
    return result


@router.post("/run")
def post_run(body: RunRequest):
    overrides = body.assumptions or {}

    if overrides and body.persist:
        upsert_custom_scenario(body.cenario, {
            "label": body.cenario,
            "description": "Custom run",
            "overrides": overrides,
        })

    dfs = run_model(
        cenario=body.cenario,
        hub_on=body.hub_on,
        ecogres_on=body.ecogres_on,
        cozedura_on=body.cozedura_on,
        assumptions_overrides=overrides,
    )

    return {"status": "ok", "outputs": dataframe_to_records(dfs)}


@router.get("/oe5/delta")
async def oe5_delta():
    """Compara resultados com e sem alterações OE5."""
    from ...engine.modelo.model import run_model, dataframe_to_records

    try:
        res_base = run_model("Base")
        res_oe5 = run_model("OE5")
    except Exception as exc:
        return {"error": f"Falha ao executar modelo: {exc}"}

    delta = {}
    for key in ["dr", "balanco", "dfc"]:
        if key in res_base and key in res_oe5:
            df_b = res_base[key]
            df_o = res_oe5[key]
            if "ano" in df_b.columns and "ano" in df_o.columns:
                merged = df_b.merge(df_o, on="ano", suffixes=("_base", "_oe5"), how="outer")
                key_delta = {}
                for col in df_b.columns:
                    if col != "ano" and f"{col}_base" in merged.columns and f"{col}_oe5" in merged.columns:
                        diffs = {}
                        for _, row in merged.iterrows():
                            v_b = float(row.get(f"{col}_base", 0) or 0)
                            v_o = float(row.get(f"{col}_oe5", 0) or 0)
                            if abs(v_o - v_b) > 0.01:
                                diffs[int(row["ano"])] = round(v_o - v_b, 2)
                        if diffs:
                            key_delta[col] = diffs
                if key_delta:
                    delta[key] = key_delta

    return {
        "base_scenario": "Base",
        "oe5_scenario": "OE5",
        "delta": delta,
    }

