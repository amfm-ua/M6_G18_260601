"""Rotas de avaliação — GrestelModel (DCF-FCFF, Múltiplos, FCFE, Monte Carlo)."""
from __future__ import annotations

from typing import Any

import numpy as np
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.engine.modelo.model import run_model
from src.engine.valuation import GrestelModel, load_params, monte_carlo_valuation, compute_vala
from src.engine.valuation.excel_reader import _DEFAULT_PATH

router = APIRouter(prefix="/api/valuation")

# Pressupostos Grestel — fallback quando Excel não disponível.
# Calibrados com OE5 (R&C 2024, run_model cenário Base). Todos os valores
# monetários em € (unidade usada pelo engine/run_model).
_GRESTEL_DEFAULTS: dict = {
    # ── Taxas derivadas pelo motor (via /apv) ─────────────────────────────────
    # ke e CMPC são OUTPUTS da VALA (vala.compute_vala), não inputs fixos. Os
    # valores abaixo são o último resultado derivado one-shot com beta_u=0.71,
    # Rf=3.10%, ERP=5.78% (fonte única, ver YAML do Hub). Recalculados em
    # _build_mc_params_from_run; actualizar aqui sempre que se re-correr /api/valuation/vala.
    "WACC":             0.0687,
    "ke":               0.0803,
    # ── Dados de mercado para o APV ──────────────────────────────────────────
    # FONTE ÚNICA partilhada com o Hub (m6_hub_assumptions.yaml: rf/erp/beta_u).
    # βU é risco de negócio do sector — VAL_base desconta-se a Ku=Rf+βU·ERP; o ke
    # alavancado (Hamada) deriva do equity do VALA. NÃO usar back-out circular de βL.
    "beta_u":           0.71,    # Damodaran "Betas by Sector (Europe)", Household Products, 5-jan-2026
    "rf":               0.0310,  # OT Portugal 10 anos, média anual 2025 (BPstat Série 12099464)
    "erp":              0.0578,  # ERP Portugal — Damodaran ctryprem.html, 5-jan-2026 (4,23% + CRP 1,55%)
    "kd":               0.028,   # custo bruto da dívida (Rf + spread crédito)
    "tax_rate":         0.20,
    "g_terminal":       0.02,
    "g_phase1_avg":     0.06,
    "g_phase2_avg":     0.03,
    "net_debt":         13_337_000.0,   # € — overridden por _build_mc_params_from_run
    "shares":           526_318.0,      # capital social 526 318 € a valor nominal 1 €
    "E_equity":         14_448_000.0,   # € CP contabilístico 2025E (só para PBV)
    # ── Múltiplos sectoriais (Damodaran, calibrados OE5) ─────────────────────
    "EV_EBITDA_sector": 15.86,
    "EV_EBIT_sector":   19.00,
    "PE_sector":        23.20,
    "PBV_sector":       4.73,
    "EV_Sales_sector":  2.79,
    "negotiation_discount": -0.10,
    # Pesos por hierarquia de fiabilidade (ver model._W_DCF): intrínseco pesa o
    # preço; múltiplos = banda de confronto (peso 0 %, não contamina o intrínseco).
    "w_dcf":            0.60,   # DCF-FCFF — intrínseco, ótica da empresa
    "w_multiples":      0.00,   # múltiplos — relativo, só confronto/sanity-check
    "w_fcfe":           0.40,   # FCFE — intrínseco, ótica do acionista
    # ── Base operacional em € (overridden por _build_mc_params_from_run) ─────
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
    n_simulations: int = Field(default=1000, ge=100, le=50_000)
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
    """Encadeia run_model → extração FCF → parâmetros completos para GrestelModel.

    Usa o horizonte de 10 anos (2025-2034): a extensão de maturidade prolonga a
    série de FCF até 2034, ancorando o valor terminal (Gordon) no último ano da
    vida útil do projeto em vez de 2029 — ver docs/horizonte_10anos_extensao_motor.md.
    """
    try:
        dfs = run_model(
            cenario=cenario, hub_on=hub_on, ecogres_on=True,
            horizonte_maturidade=True,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro modelo operacional: {exc}") from exc

    dr = dfs["dr"]
    dfc = dfs.get("dfc")
    bal = dfs.get("balanco")
    tax_rate = float(params_financeiros.get("tax_rate", 0.245))

    dr_proj = dr[dr["ano"] >= 2025]

    # Colunas reais da DFC (build_dfc): capex em activos fixos/intangíveis e
    # ΔNFM operacional. A depreciação na DR está guardada NEGATIVA, pelo que o
    # add-back de D&A no FCFF é -depreciacoes (positivo).
    dfc_cols = set(dfc.columns) if dfc is not None else set()
    capex_cols = [c for c in ("capex_aft", "pag_intang", "hub_capex") if c in dfc_cols]
    has_var_nfm = "var_nfm" in dfc_cols

    # Dívida financeira e caixa por ano (do balanço do próprio run) — usados para
    # o net borrowing do FCFE e para o net_debt à data de avaliação (fim de 2024).
    debt_by_year: dict[int, float] = {}
    cash_by_year: dict[int, float] = {}
    if bal is not None:
        for _, br in bal.iterrows():
            yb = int(br["ano"])
            debt_by_year[yb] = (
                float(br.get("emprestimos_nc", 0) or 0)
                + float(br.get("emprestimos_c", 0) or 0)
                + float(br.get("linha_credito_cp", 0) or 0)
            )
            cash_by_year[yb] = (
                float(br.get("caixa", 0) or 0)
                + float(br.get("aplicacoes_fin_cp", 0) or 0)
            )

    projected_revenue: dict[int, float] = {}
    projected_FCFF:    dict[int, float] = {}
    projected_FCFE:    dict[int, float] = {}

    for _, row in dr_proj.iterrows():
        ano   = int(row["ano"])
        vn    = float(row.get("vn",     0) or 0)
        ebit  = float(row.get("ebit",   0) or 0)
        da    = -float(row.get("depreciacoes", 0) or 0)   # add-back (depreciacoes < 0)
        juros = float(row.get("juros",  0) or 0)

        projected_revenue[ano] = vn

        dfc_row = dfc[dfc["ano"] == ano] if dfc is not None else None
        if dfc_row is not None and not dfc_row.empty:
            # capex_aft/pag_intang/hub_capex são saídas de caixa (negativas na DFC).
            capex = sum(abs(float(dfc_row[c].iloc[0])) for c in capex_cols)
            # var_nfm = efeito de caixa do fundo de maneio (positivo = libertação).
            # FCFF = NOPAT + D&A − Capex − ΔNFM; como ΔNFM = −var_nfm, soma-se var_nfm.
            var_nfm_cash = float(dfc_row["var_nfm"].iloc[0]) if has_var_nfm else 0.0
        else:
            capex = 0.0
            var_nfm_cash = 0.0

        fcff = ebit * (1 - tax_rate) + da - capex + var_nfm_cash

        # FCFE = FCFF − juro líquido de imposto + net borrowing (ΔDívida financeira).
        # net borrowing > 0 (novos empréstimos) acresce caixa disponível ao acionista.
        net_borrowing = debt_by_year.get(ano, 0.0) - debt_by_year.get(ano - 1, 0.0)
        fcfe = fcff - abs(juros) * (1 - tax_rate) + net_borrowing

        projected_FCFF[ano] = round(fcff, 1)
        projected_FCFE[ano] = round(fcfe, 1)

    # Múltiplos: âncora forward (1.º ano projetado = 2025), não a média do
    # horizonte. Aplicar o múltiplo de sector a um EBITDA/EBIT forward é a
    # convenção (NTM); a média de uma série crescente enviesava para meados de
    # 2029-2030 e sobreavaliava o método dos Múltiplos.
    fwd = dr_proj.sort_values("ano").iloc[0] if not dr_proj.empty else None
    ebit_fwd   = float(fwd.get("ebit", 0) or 0) if fwd is not None else 0.0
    ebitda_fwd = float(fwd.get("ebitda", 0) or 0) if fwd is not None else 0.0
    da_fwd     = -float(fwd.get("depreciacoes", 0) or 0) if fwd is not None else 0.0

    params = dict(params_financeiros)
    params.update({
        "EBIT_base":         round(ebit_fwd, 1),
        "EBITDA_base":       round(ebitda_fwd, 1),
        "DA_base":           round(da_fwd, 1),
        "projected_FCFF":    projected_FCFF,
        "projected_FCFE":    projected_FCFE,
        "projected_revenue": projected_revenue,
    })

    # net_debt e book equity à data de avaliação (fim de 2024 — primeiro FCF em
    # t=1 corresponde a 2025), derivados do balanço do run em vez do valor
    # estático do Excel. Garante coerência entre EV e dívida líquida e, no
    # comparativo com/sem Hub, ambos partem da mesma dívida real de 2024.
    if 2024 in debt_by_year:
        params["net_debt"] = round(debt_by_year[2024] - cash_by_year.get(2024, 0.0), 1)
    if bal is not None:
        bal_2024 = bal[bal["ano"] == 2024]
        if not bal_2024.empty and "total_cp" in bal_2024.columns:
            params["E_equity"] = round(float(bal_2024["total_cp"].iloc[0]), 1)

    # VALA (método APV, Myers 1974) — substitui o CMPC iterativo. Ku=Rf+βU·ERP
    # não depende do equity, por isso ke/CMPC derivam numa só passagem (sem
    # circularidade nem âncora de múltiplos) e alimentam o DCF-FCFF principal.
    # Corre aqui porque já há FCFs projetados e net_debt real do balanço. Só
    # executa se os parâmetros de mercado estiverem presentes.
    _bu  = float(params.get("beta_u") or 0.0)
    _rf  = float(params.get("rf")     or 0.0)
    _erp = float(params.get("erp")    or 0.0)
    if _bu and _rf and _erp:
        _nd  = float(params.get("net_debt")   or 0.0)
        _kd  = float(params.get("kd")         or 0.028)
        _tax = float(params.get("tax_rate")   or 0.20)
        _g   = float(params.get("g_terminal") or 0.02)
        _fcffs = [v for _, v in sorted((params.get("projected_FCFF") or {}).items())]
        vala = compute_vala(
            beta_u=_bu, rf=_rf, erp=_erp,
            kd=_kd, tax_rate=_tax, net_debt=_nd,
            fcffs=_fcffs, g_terminal=_g,
        )
        params["ku"]          = vala.ku
        params["ke"]          = vala.ke
        params["WACC"]        = vala.wacc
        params["beta_l"]      = vala.beta_l    # disponível para diagnóstico
        params["equity_vala"] = vala.equity_vala

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


@router.get("/wacc-iterativo")
@router.get("/vala")
def get_vala(
    cenario: str   = Query("Base"),
    hub_on: bool   = Query(False),
    excel_path: str = Query(None),
    beta_u: float  = Query(None, description="βU desalavancado (omitir = default Grestel)"),
    rf: float      = Query(None, description="Taxa sem risco (omitir = default)"),
    erp: float     = Query(None, description="Prémio de risco de mercado (omitir = default)"),
):
    """Decomposição da VALA (Valor Atual Líquido Ajustado, método APV, Myers 1974).

    Encadeia run_model → FCFs projetados → VALA = VAL_base(Ku) + escudo fiscal,
    sem iteração (Ku não depende do equity). Devolve a decomposição e as taxas
    derivadas (ke, CMPC) numa só passagem, mais o DCF-FCFF (método principal da
    OE5) para confronto metodológico (VALA≈DCF valida ambos).

    Fluxo:
        Ku = Rf + βU·ERP
        VAL_base = PV(FCFF @ Ku) + VT_Gordon@Ku
        VA(escudo) = t·kd·D descontado a kd  (dívida constante → t·D)
        VALA = VAL_base + escudo;  equity_vala = VALA − dívida líquida
        D/E → βL (Hamada) → ke → CMPC   (one-shot; o CMPC alimenta o DCF-FCFF)

    O path /wacc-iterativo mantém-se por retrocompatibilidade (alias de /vala).
    """
    params_fin = _load_excel(excel_path, fallback=True)
    params = _build_mc_params_from_run(cenario, hub_on, params_fin)

    _bu  = beta_u if beta_u is not None else float(params_fin.get("beta_u") or _GRESTEL_DEFAULTS["beta_u"])
    _rf  = rf     if rf     is not None else float(params_fin.get("rf")     or _GRESTEL_DEFAULTS["rf"])
    _erp = erp    if erp    is not None else float(params_fin.get("erp")    or _GRESTEL_DEFAULTS["erp"])
    _kd  = float(params.get("kd")         or _GRESTEL_DEFAULTS["kd"])
    _tax = float(params.get("tax_rate")   or _GRESTEL_DEFAULTS["tax_rate"])
    _g   = float(params.get("g_terminal") or 0.02)
    _nd  = float(params.get("net_debt")   or 0.0)
    _fcffs = [v for _, v in sorted((params.get("projected_FCFF") or {}).items())]

    vala = compute_vala(
        beta_u=_bu, rf=_rf, erp=_erp,
        kd=_kd, tax_rate=_tax, net_debt=_nd,
        fcffs=_fcffs, g_terminal=_g,
    )

    # DCF-FCFF (método principal): mesmos FCFF descontados ao CMPC que a VALA dá.
    equity_dcf = GrestelModel(params)._equity_dcf(params, vala.wacc)

    return _serialize({
        # ── Taxas derivadas (one-shot) ───────────────────────────────────────
        "ku_pct":           round(vala.ku   * 100, 4),
        "ke_pct":           round(vala.ke   * 100, 4),
        "wacc_pct":         round(vala.wacc * 100, 4),
        "ku":               round(vala.ku,   6),
        "ke":               round(vala.ke,   6),
        "wacc":             round(vala.wacc, 6),
        "beta_l":           round(vala.beta_l, 4),
        "beta_u":           round(_bu, 4),
        "de_ratio":         round(vala.de_ratio, 4),
        # ── Decomposição VALA (em k€) ────────────────────────────────────────
        "val_base_keur":    round(vala.val_base   / 1000, 1),
        "pv_escudo_keur":   round(vala.pv_escudo  / 1000, 1),
        "vala_keur":        round(vala.vala        / 1000, 1),
        "equity_vala_keur": round(vala.equity_vala / 1000, 1),
        # ── DCF-FCFF (principal OE5) e confronto ─────────────────────────────
        "equity_dcf_keur":  round(equity_dcf / 1000, 1),
        "gap_vala_vs_dcf_pct": round(
            (vala.equity_vala / equity_dcf - 1.0) * 100, 2
        ) if equity_dcf else None,
        "inputs": {
            "rf_pct":  round(_rf  * 100, 4),
            "erp_pct": round(_erp * 100, 4),
            "kd_pct":  round(_kd  * 100, 4),
            "net_debt_keur": round(_nd / 1000, 1),
        },
        "cenario": cenario,
        "hub_on":  hub_on,
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
