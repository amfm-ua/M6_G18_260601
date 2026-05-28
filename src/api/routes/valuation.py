"""Rotas de avaliação — GrestelModel (DCF-FCFF, Múltiplos, FCFE, Monte Carlo)."""
from __future__ import annotations

from typing import Any

import numpy as np
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.engine.modelo.model import run_model
from src.engine.valuation import GrestelModel, load_params, monte_carlo_valuation
from src.engine.valuation.excel_reader import _DEFAULT_PATH

router = APIRouter(prefix="/api/valuation")

# Pressupostos Grestel — fallback quando Excel não disponível.
# Calibrados com OE5 (R&C 2024, run_model cenário Base). Todos os valores
# monetários em € (unidade usada pelo engine/run_model).
_GRESTEL_DEFAULTS: dict = {
    "WACC":             0.0621,
    "ke":               0.0935,
    "kd":               0.028,
    "tax_rate":         0.20,
    "g_terminal":       0.02,
    "g_phase1_avg":     0.06,
    "g_phase2_avg":     0.03,
    "net_debt":         13_337_000.0,   # € (= 13 337 k€ dívida líquida fin 2025E)
    "shares":           1.0,
    "E_equity":         14_448_000.0,   # € (= 14 448 k€ CP contabilístico 2025E)
    "EV_EBITDA_sector": 8.0,
    "EV_EBIT_sector":   10.0,
    "PE_sector":        14.0,
    "PBV_sector":       1.5,
    "EV_Sales_sector":  1.2,
    "negotiation_discount": -0.10,
    "w_dcf":            1 / 3,
    "w_multiples":      1 / 3,
    "w_fcfe":           1 / 3,
    # Operational base em € (overridden por _build_mc_params_from_run)
    "EBIT_base":        4_802_000.0,
    "EBITDA_base":      6_790_000.0,
    "DA_base":          1_988_000.0,
    "capex_base":       1_502_000.0,
    "delta_nwc_base":   213_000.0,
}


# ── Schemas de input ──────────────────────────────────────────────────────────

class ValuationParams(BaseModel):
    """Parâmetros mínimos para correr o modelo sem ficheiro Excel."""
    WACC: float
    ke: float
    g_terminal: float
    g_phase1_avg: float = 0.05
    g_phase2_avg: float = 0.03
    tax_rate: float = 0.245
    kd: float = 0.04
    net_debt: float = 0.0
    shares: float = 1.0
    EBIT_base: float = 0.0
    DA_base: float = 0.0
    capex_base: float = 0.0
    delta_nwc_base: float = 0.0
    EBITDA_base: float = 0.0
    EV_EBITDA_sector: float = 0.0
    EV_EBIT_sector: float = 0.0
    PE_sector: float = 0.0
    PBV_sector: float = 0.0
    EV_Sales_sector: float = 0.0
    E_equity: float = 0.0
    negotiation_discount: float = -0.10
    # Projecções opcionais (dict[ano, valor])
    projected_FCFF: dict[int, float] | None = None
    projected_FCFE: dict[int, float] | None = None
    projected_revenue: dict[int, float] | None = None


class MCParams(BaseModel):
    """Parâmetros para o endpoint POST /monte-carlo."""
    params: ValuationParams
    n_simulations: int = 1000
    seed: int | None = None
    distributions: dict[str, Any] | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_excel(excel_path: str | None, *, fallback: bool = False) -> dict:
    """Carrega params do Excel; usa _GRESTEL_DEFAULTS se fallback=True e ficheiro ausente."""
    try:
        return load_params(excel_path)
    except FileNotFoundError as exc:
        if fallback:
            return dict(_GRESTEL_DEFAULTS)
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _run_model(params: dict) -> dict:
    """Instancia o modelo e calcula a síntese."""
    try:
        model = GrestelModel(params)
        return model.compute_synthesis()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro no modelo: {exc}") from exc


def _serialize(obj: Any) -> Any:
    """Converte tipos numpy para Python nativo."""
    import numpy as np
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return None if (np.isnan(obj) or np.isinf(obj)) else float(obj)
    if isinstance(obj, np.ndarray):
        return [_serialize(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(x) for x in obj]
    if isinstance(obj, float) and (obj != obj or obj in (float("inf"), float("-inf"))):
        return None
    return obj


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/synthesis")
def get_synthesis_from_excel(
    excel_path: str = Query(None, description="Caminho para o .xlsx (omitir = default)"),
):
    """Lê o ficheiro Excel e devolve a síntese de avaliação ponderada.

    Carrega WACC, taxas de crescimento, FCFFs projetados e múltiplos de sector
    directamente das folhas do Excel e calcula equity value pelos 3 métodos.
    """
    params = _load_excel(excel_path)
    result = _run_model(params)
    return _serialize({
        "fonte": "excel",
        "excel_path": excel_path or _DEFAULT_PATH,
        **result,
    })


@router.post("/run")
def post_run(body: ValuationParams):
    """Calcula a síntese de avaliação a partir de parâmetros JSON.

    Permite sobrepor qualquer pressuposto sem depender do ficheiro Excel.
    Útil para análise de sensibilidade manual ou cenários ad-hoc.
    """
    params = body.model_dump()
    result = _run_model(params)
    return _serialize(result)


@router.get("/monte-carlo")
def get_monte_carlo(
    excel_path: str = Query(None, description="Caminho para o .xlsx (omitir = default)"),
    n: int = Query(1000, ge=100, le=10_000, description="Número de simulações"),
    seed: int = Query(None, description="Seed para reprodutibilidade"),
):
    """Simulação Monte Carlo carregando parâmetros do ficheiro Excel.

    Perturba WACC, g_terminal, EV/EBITDA_mult, g_revenue_shock e
    EBITDA_margin_shock com distribuições triangulares / normal truncada.
    Devolve distribuição do equity value ponderado + correlações de Spearman.
    """
    params = _load_excel(excel_path)
    model = GrestelModel(params)
    try:
        result = monte_carlo_valuation(model, n_simulations=n, seed=seed)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro no Monte Carlo: {exc}") from exc
    return _serialize(result)


@router.post("/monte-carlo")
def post_monte_carlo(body: MCParams):
    """Simulação Monte Carlo com parâmetros fornecidos via JSON.

    Permite configurar distribuições personalizadas por driver, por exemplo:
    ```json
    { "distributions": { "WACC": { "type": "triangular", "min": 0.07, "mode": 0.09, "max": 0.12 } } }
    ```
    """
    params = body.params.model_dump()
    model = GrestelModel(params)
    try:
        result = monte_carlo_valuation(
            model,
            n_simulations=body.n_simulations,
            distributions=body.distributions,
            seed=body.seed,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro no Monte Carlo: {exc}") from exc
    return _serialize(result)


# ── Helpers para endpoints operacionais ──────────────────────────────────────

def _build_mc_params_from_run(
    cenario: str,
    hub_on: bool,
    params_financeiros: dict,
) -> dict:
    """Encadeia run_model → extração FCF → parâmetros completos para GrestelModel."""
    try:
        dfs = run_model(cenario=cenario, hub_on=hub_on, ecogres_on=True)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro modelo operacional: {exc}") from exc

    dr = dfs["dr"]
    dfc = dfs.get("dfc")
    tax_rate = float(params_financeiros.get("tax_rate", 0.245))

    dr_proj = dr[dr["ano"] >= 2025]
    has_capex = dfc is not None and "capex" in dfc.columns
    has_nwc   = dfc is not None and "variacao_nwc" in dfc.columns

    projected_revenue: dict[int, float] = {}
    projected_FCFF:    dict[int, float] = {}
    projected_FCFE:    dict[int, float] = {}

    for _, row in dr_proj.iterrows():
        ano   = int(row["ano"])
        vn    = float(row.get("vn",     0) or 0)
        ebit  = float(row.get("ebit",   0) or 0)
        dep   = float(row.get("dep",    0) or row.get("depreciacoes", 0) or 0)
        juros = float(row.get("juros",  0) or 0)

        projected_revenue[ano] = vn

        if has_capex and has_nwc:
            dfc_row   = dfc[dfc["ano"] == ano]
            capex     = abs(float(dfc_row["capex"].iloc[0]))        if not dfc_row.empty else 0.0
            delta_nwc = float(dfc_row["variacao_nwc"].iloc[0])      if not dfc_row.empty else 0.0
            fcff = ebit * (1 - tax_rate) + dep - capex - delta_nwc
        else:
            fcff = ebit * (1 - tax_rate) + dep

        projected_FCFF[ano] = round(fcff, 1)
        projected_FCFE[ano] = round(fcff - abs(juros) * (1 - tax_rate), 1)

    rows_vals = [
        (
            float(r.get("ebit",    0) or 0),
            float(r.get("ebitda",  0) or 0),
            float(r.get("dep",     0) or r.get("depreciacoes", 0) or 0),
        )
        for _, r in dr_proj.iterrows()
    ]
    n_rows = len(rows_vals) or 1

    params = dict(params_financeiros)
    params.update({
        "EBIT_base":         round(sum(v[0] for v in rows_vals) / n_rows, 1),
        "EBITDA_base":       round(sum(v[1] for v in rows_vals) / n_rows, 1),
        "DA_base":           round(sum(v[2] for v in rows_vals) / n_rows, 1),
        "projected_FCFF":    projected_FCFF,
        "projected_FCFE":    projected_FCFE,
        "projected_revenue": projected_revenue,
    })
    return params


# g_terminal por cenário — WACC mantém-se constante (Damodaran: o desconto
# reflecte risco sistemático do negócio, não o resultado operacional do cenário).
# O ajuste recai sobre o crescimento terminal, que é o pressuposto mais sensível
# e o que mais razoavelmente muda com as perspectivas de longo prazo do sector.
_G_BY_SCENARIO: dict[str, float] = {
    "Base":     0.020,   # crescimento real de longo prazo + inflação moderada
    "Downside": 0.010,   # crescimento real próximo de zero
    "Stress":   0.000,   # crescimento nominal nulo — empresa em estagnação
}
_G_SPREAD = 0.005       # spread triangular ±0,5 p.p. em todos os cenários


def _scenario_distributions(cenario: str) -> dict:
    """Distribições MC com g_terminal centrado no cenário operacional."""
    g = _G_BY_SCENARIO.get(cenario, 0.020)
    return {
        "g_terminal": {
            "type": "triangular",
            "min":  max(-0.05, g - _G_SPREAD),
            "mode": g,
            "max":  min(0.10,  g + _G_SPREAD),
        }
    }


@router.get("/monte-carlo/operacional")
def get_monte_carlo_operacional(
    cenario: str  = Query("Base"),
    hub_on: bool  = Query(False),
    n: int        = Query(1000, ge=100, le=10_000),
    seed: int     = Query(None),
    excel_path: str = Query(None),
):
    """Monte Carlo sobre equity value Grestel encadeado com o motor operacional.

    Encadeia run_model(cenario, hub_on) → extrai projeções de FCF do DR →
    constrói GrestelModel → corre monte_carlo_valuation.
    Parâmetros financeiros (WACC, ke, g_terminal, múltiplos, net_debt, shares)
    são carregados do ficheiro Excel de avaliação.
    """
    params_financeiros = _load_excel(excel_path, fallback=True)
    params = _build_mc_params_from_run(cenario, hub_on, params_financeiros)
    model = GrestelModel(params)
    dists = _scenario_distributions(cenario)
    try:
        result = monte_carlo_valuation(model, n_simulations=n, seed=seed, distributions=dists)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro no Monte Carlo: {exc}") from exc
    return _serialize({**result, "cenario": cenario, "hub_on": hub_on})


@router.get("/monte-carlo/comparativo")
def get_monte_carlo_comparativo(
    cenario: str  = Query("Base"),
    n: int        = Query(1000, ge=100, le=10_000),
    seed: int     = Query(None),
    excel_path: str = Query(None),
):
    """Monte Carlo comparativo Grestel com e sem Hub Logístico.

    Corre dois blocos sequenciais (hub_on=False e hub_on=True) e devolve
    as distribuições completas de cada um mais os deltas do equity médio.
    """
    params_financeiros = _load_excel(excel_path, fallback=True)
    dists = _scenario_distributions(cenario)

    params_sem = _build_mc_params_from_run(cenario, False, params_financeiros)
    model_sem  = GrestelModel(params_sem)
    try:
        sem_hub = monte_carlo_valuation(model_sem, n_simulations=n, seed=seed, distributions=dists)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro Monte Carlo sem Hub: {exc}") from exc

    params_com = _build_mc_params_from_run(cenario, True, params_financeiros)
    model_com  = GrestelModel(params_com)
    try:
        com_hub = monte_carlo_valuation(model_com, n_simulations=n, seed=seed, distributions=dists)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro Monte Carlo com Hub: {exc}") from exc

    delta_we = (com_hub["weighted_equity"].get("mean") or 0) - (sem_hub["weighted_equity"].get("mean") or 0)
    delta_mp = (com_hub["min_price"].get("mean") or 0)       - (sem_hub["min_price"].get("mean") or 0)

    return _serialize({
        "sem_hub": sem_hub,
        "com_hub": com_hub,
        "delta_weighted_equity_medio": round(float(delta_we), 1),
        "delta_min_price_medio":       round(float(delta_mp), 1),
    })


@router.get("/sensitivity")
def get_sensitivity(
    excel_path: str = Query(None),
    wacc_min: float = Query(None, description="WACC mínimo (omitir = base−3p.p.)"),
    wacc_max: float = Query(None, description="WACC máximo (omitir = base+3p.p.)"),
    wacc_steps: int = Query(5, ge=2, le=10),
    g_min: float = Query(None, description="g_terminal mínimo (omitir = base−2p.p.)"),
    g_max: float = Query(None, description="g_terminal máximo (omitir = base+2p.p.)"),
    g_steps: int = Query(5, ge=2, le=10),
):
    """Tabela de sensibilidade WACC × g_terminal → equity value ponderado.

    Retorna matriz [g_steps × wacc_steps] com equity values e arrays de eixos.
    """
    params = _load_excel(excel_path)
    model = GrestelModel(params)
    base = model.get_params()

    w_center = float(base["WACC"])
    g_center = float(base["g_terminal"])

    waccs = list(np.linspace(
        wacc_min if wacc_min is not None else w_center - 0.03,
        wacc_max if wacc_max is not None else w_center + 0.03,
        wacc_steps,
    ))
    gs = list(np.linspace(
        g_min if g_min is not None else g_center - 0.02,
        g_max if g_max is not None else g_center + 0.02,
        g_steps,
    ))

    matrix: list[list[float | None]] = []
    for g in gs:
        row: list[float | None] = []
        for w in waccs:
            if w <= g:
                row.append(None)
                continue
            model.set_params({"WACC": w, "g_terminal": g})
            try:
                res = model.compute_synthesis()
                row.append(round(res["weighted_equity"], 1))
            except Exception:
                row.append(None)
        matrix.append(row)

    # Restaurar params base
    model.set_params(base)

    return _serialize({
        "wacc_axis": [round(w, 4) for w in waccs],
        "g_axis": [round(g, 4) for g in gs],
        "matrix": matrix,         # [g_idx][wacc_idx]
        "base_wacc": round(w_center, 4),
        "base_g": round(g_center, 4),
        "base_equity": round(float(model.compute_synthesis()["weighted_equity"]), 1),
    })
