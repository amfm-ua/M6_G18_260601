"""Monte Carlo — Avaliação GrestelModel.

Wraps GrestelModel e corre N simulações perturbando WACC, g_terminal,
EV_EBITDA_mult, g_revenue_shock e EBITDA_margin_shock.

Segue o mesmo estilo de monte_carlo_hub.py:
  • numpy puro (sem scipy)
  • amostragem vectorizada por driver
  • correlação de Spearman via transformação de ranks
  • histograma e percentis prontos para o frontend
"""
from __future__ import annotations

import copy
import math
from typing import Any

import numpy as np

from .model import GrestelModel


# ── Distribuições por defeito ─────────────────────────────────────────────────
# Cada driver: dict com "type" e parâmetros específicos do sampler.
# Os campos marcados None são resolvidos em runtime a partir dos params base.

DEFAULT_DISTRIBUTIONS: dict[str, dict] = {
    # WACC: triangular simétrica ±1,5 p.p. → E[WACC] = WACC_base
    "WACC": {
        "type": "triangular",
        "min": None,   # WACC_base − 0.015 (resolvido em runtime)
        "mode": None,  # WACC_base
        "max": None,   # WACC_base + 0.015
        "spread": 0.015,
    },
    # g_terminal: triangular simétrica ±0,5 p.p.
    "g_terminal": {
        "type": "triangular",
        "min": None,
        "mode": None,
        "max": None,
        "spread": 0.005,
    },
    # EV/EBITDA: normal truncada N(sector, std) ∈ [sector×0.5, sector×2.0].
    # std ≈ 19 % da média (alinhado com EV/EBITDA Damodaran ≈ 15.86 da OE5);
    # preserva a dispersão relativa que existia quando o múltiplo base era 8.0
    # (std 1.5 ≈ 19 %), para não subestimar a incerteza do método dos múltiplos.
    "EV_EBITDA_mult": {
        "type": "truncnorm",
        "mean": None,   # EV_EBITDA_sector (resolvido em runtime)
        "std": 3.0,
        "low": None,    # mean * 0.5
        "high": None,   # mean * 2.0
    },
    # Choque aditivo sobre o crescimento de receita (∈ [−5%, +10%])
    "g_revenue_shock": {
        "type": "truncnorm",
        "mean": 0.0,
        "std": 0.015,
        "low": -0.05,
        "high": 0.10,
    },
    # Choque aditivo sobre a margem EBITDA (∈ [−5%, +5%])
    "EBITDA_margin_shock": {
        "type": "truncnorm",
        "mean": 0.0,
        "std": 0.015,
        "low": -0.05,
        "high": 0.05,
    },
}

DRIVERS = list(DEFAULT_DISTRIBUTIONS.keys())

# Restrições: garantem consistência financeira das amostras
_CONSTRAINTS = [
    lambda p: p["WACC"] > p["g_terminal"],          # crescimento < desconto
    lambda p: 0.03 < p["WACC"] < 0.20,
    lambda p: -0.05 < p["g_terminal"] < 0.10,
]


# ── Samplers (numpy puro, idênticos a monte_carlo_hub) ───────────────────────

def _sample_triangular(
    rng: np.random.Generator,
    low: float,
    mode: float,
    high: float,
    n: int,
) -> np.ndarray:
    if math.isclose(low, high, rel_tol=1e-9):
        return np.full(n, low)
    return rng.triangular(low, mode, high, size=n)


def _sample_truncnorm(
    rng: np.random.Generator,
    mean: float,
    std: float,
    low: float,
    high: float,
    n: int,
) -> np.ndarray:
    collected: list[float] = []
    while len(collected) < n:
        batch = rng.normal(mean, std, size=max(n * 10, 500))
        valid = batch[(batch >= low) & (batch <= high)]
        collected.extend(valid.tolist())
    return np.array(collected[:n])


def _draw_samples(
    rng: np.random.Generator,
    dist_cfg: dict,
    n: int,
) -> np.ndarray:
    t = dist_cfg["type"]
    if t == "triangular":
        return _sample_triangular(
            rng,
            float(dist_cfg["min"]),
            float(dist_cfg["mode"]),
            float(dist_cfg["max"]),
            n,
        )
    if t == "truncnorm":
        return _sample_truncnorm(
            rng,
            float(dist_cfg["mean"]),
            float(dist_cfg["std"]),
            float(dist_cfg["low"]),
            float(dist_cfg["high"]),
            n,
        )
    raise ValueError(f"Tipo de distribuição desconhecido: {t!r}")


# ── Correlação de Spearman (numpy puro via transformação de ranks) ────────────

def _spearman(x: np.ndarray, y: np.ndarray) -> float:
    """ρ de Spearman entre dois vectores (numpy puro, sem scipy)."""
    mask = np.isfinite(x) & np.isfinite(y)
    if mask.sum() < 2:
        return 0.0
    rx = np.argsort(np.argsort(x[mask])).astype(float)
    ry = np.argsort(np.argsort(y[mask])).astype(float)
    corr = np.corrcoef(rx, ry)[0, 1]
    return float(corr)


# ── Histograma ────────────────────────────────────────────────────────────────

def _histogram(values: np.ndarray, bins: int = 60) -> dict:
    counts, edges = np.histogram(values[np.isfinite(values)], bins=bins)
    centers = 0.5 * (edges[:-1] + edges[1:])
    return {
        "bins": [round(float(c), 1) for c in centers],
        "counts": [int(c) for c in counts],
        "edges": [round(float(e), 1) for e in edges],
    }


# ── Estatísticas descritivas ──────────────────────────────────────────────────

def _stats(values: np.ndarray, bins: int = 60) -> dict:
    v = values[np.isfinite(values)]
    if len(v) == 0:
        return {}
    pcts = np.percentile(v, [5, 25, 50, 75, 95])
    return {
        "mean": round(float(v.mean()), 1),
        "std": round(float(v.std()), 1),
        "p5": round(float(pcts[0]), 1),
        "p25": round(float(pcts[1]), 1),
        "p50": round(float(pcts[2]), 1),
        "p75": round(float(pcts[3]), 1),
        "p95": round(float(pcts[4]), 1),
        "min": round(float(v.min()), 1),
        "max": round(float(v.max()), 1),
        "histograma": _histogram(v, bins),
    }


# ── Função principal ──────────────────────────────────────────────────────────

def monte_carlo_valuation(
    model: GrestelModel,
    n_simulations: int = 1000,
    distributions: dict | None = None,
    seed: int | None = None,
) -> dict[str, Any]:
    """Simulação Monte Carlo sobre GrestelModel.

    Parâmetros
    ----------
    model : GrestelModel
        Instância já inicializada com os parâmetros base.
    n_simulations : int
        Número de iterações (100–10 000).
    distributions : dict | None
        Override de parâmetros por driver. Mesma estrutura de DEFAULT_DISTRIBUTIONS.
    seed : int | None
        Seed para reprodutibilidade.

    Retorna
    -------
    dict com:
        weighted_equity  — estatísticas + histograma
        equity_dcf       — estatísticas
        equity_multiples — estatísticas
        equity_fcfe      — estatísticas
        min_price        — estatísticas
        correlacoes_spearman — ρ(driver, weighted_equity) por driver
        distribuicoes_usadas — parâmetros efectivos usados
        parametros_base  — caso determinístico de referência
        n_simulacoes     — iterações válidas
    """
    rng = np.random.default_rng(seed)
    base = model.get_params()

    # ── Resolver distribuições efectivas ────────────────────────────────────
    dist_ef: dict[str, dict] = {}
    for drv in DRIVERS:
        cfg = dict(DEFAULT_DISTRIBUTIONS[drv])
        if distributions and drv in distributions:
            cfg.update(distributions[drv])
        dist_ef[drv] = cfg

    # WACC: triangular centrada no valor base
    wacc_base = float(base["WACC"])
    if dist_ef["WACC"]["min"] is None:
        spread = float(dist_ef["WACC"].get("spread", 0.015))
        dist_ef["WACC"].update({
            "min": max(0.03, wacc_base - spread),
            "mode": wacc_base,
            "max": min(0.20, wacc_base + spread),
        })

    # g_terminal: triangular centrada no valor base
    g_base = float(base["g_terminal"])
    if dist_ef["g_terminal"]["min"] is None:
        spread = float(dist_ef["g_terminal"].get("spread", 0.005))
        dist_ef["g_terminal"].update({
            "min": max(-0.05, g_base - spread),
            "mode": g_base,
            "max": min(0.10, g_base + spread),
        })

    # EV_EBITDA_mult: centrado no múltiplo sector base
    ev_base = float(base.get("EV_EBITDA_sector") or 0.0)
    if dist_ef["EV_EBITDA_mult"]["mean"] is None:
        dist_ef["EV_EBITDA_mult"].update({
            "mean": ev_base,
            "low": max(0.0, ev_base * 0.5),
            "high": ev_base * 2.0 if ev_base else 20.0,
        })

    # ── Amostrar todos os drivers de uma vez (vectorizado) ───────────────────
    n = n_simulations
    samples: dict[str, np.ndarray] = {
        drv: _draw_samples(rng, dist_ef[drv], n) for drv in DRIVERS
    }

    # ── Caso base determinístico ─────────────────────────────────────────────
    res_base = model.compute_synthesis()

    # ── Iterações ────────────────────────────────────────────────────────────
    out_weighted = np.empty(n)
    out_dcf = np.empty(n)
    out_mult = np.empty(n)
    out_fcfe = np.empty(n)
    out_price = np.empty(n)

    n_valid = 0
    for i in range(n):
        s = {drv: float(samples[drv][i]) for drv in DRIVERS}

        # Verificar restrições
        p_check = {"WACC": s["WACC"], "g_terminal": s["g_terminal"]}
        if not all(c(p_check) for c in _CONSTRAINTS):
            out_weighted[i] = np.nan
            out_dcf[i] = np.nan
            out_mult[i] = np.nan
            out_fcfe[i] = np.nan
            out_price[i] = np.nan
            continue

        # Aplicar amostra ao modelo
        model.set_params({
            "WACC": s["WACC"],
            "g_terminal": s["g_terminal"],
            "EV_EBITDA_mult": s["EV_EBITDA_mult"],
            "g_revenue_shock": s["g_revenue_shock"],
            "EBITDA_margin_shock": s["EBITDA_margin_shock"],
        })

        try:
            res = model.compute_synthesis()
            out_weighted[i] = res["weighted_equity"]
            out_dcf[i] = res["equity_dcf"]
            out_mult[i] = res["equity_multiples"]
            out_fcfe[i] = res["equity_fcfe"]
            out_price[i] = res["min_price"]
            n_valid += 1
        except Exception:
            out_weighted[i] = np.nan
            out_dcf[i] = np.nan
            out_mult[i] = np.nan
            out_fcfe[i] = np.nan
            out_price[i] = np.nan

    # Restaurar params base
    model.set_params(base)
    # Limpar chaves de choque para não contaminar o estado base
    for key in ("EV_EBITDA_mult", "g_revenue_shock", "EBITDA_margin_shock"):
        model._params.pop(key, None)

    # ── Correlações de Spearman (driver → weighted_equity) ───────────────────
    w = out_weighted
    correlacoes: dict[str, float] = {}
    for drv in DRIVERS:
        correlacoes[drv] = round(_spearman(samples[drv], w), 4)
    correlacoes = dict(sorted(correlacoes.items(), key=lambda x: abs(x[1]), reverse=True))

    return {
        "weighted_equity": _stats(out_weighted),
        "equity_dcf": _stats(out_dcf),
        "equity_multiples": _stats(out_mult),
        "equity_fcfe": _stats(out_fcfe),
        "min_price": _stats(out_price),
        "correlacoes_spearman": correlacoes,
        "prob_acima_base": round(
            float(np.nansum(out_weighted > res_base["weighted_equity"]) / n_valid)
            if n_valid else 0.0,
            4,
        ),
        "distribuicoes_usadas": {
            drv: {k: v for k, v in cfg.items() if k != "spread"}
            for drv, cfg in dist_ef.items()
        },
        "parametros_base": {
            "WACC": wacc_base,
            "g_terminal": g_base,
            "EV_EBITDA_mult": ev_base,
            "weighted_equity": res_base["weighted_equity"],
            "equity_dcf": res_base["equity_dcf"],
            "equity_multiples": res_base["equity_multiples"],
            "equity_fcfe": res_base["equity_fcfe"],
            "min_price": res_base["min_price"],
        },
        "n_simulacoes": n_valid,
        "n_total_tentativas": n,
    }
