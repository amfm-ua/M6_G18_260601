"""Monte Carlo — Viabilidade do Hub Logístico 4.0.

Complementa a análise determinística (tornado, ponto crítico) com simulação estocástica:
em vez de 2 pontos por driver (pessimista/otimista), amostra distribuições contínuas e
corre N iterações completas do modelo de viabilidade.

Principais saídas:
  • Distribuição do VAL e TIR (percentis P5–P95, média, desvio-padrão)
  • P(VAL > 0)  — probabilidade de o projeto ser viável
  • P(TIR > WACC_base) — probabilidade de excesso de retorno sobre o custo de capital
  • Correlações de Pearson driver → VAL (ranking de importância dos riscos)
  • Dados de histograma prontos para renderização no frontend

Distribuições por driver (operacionais simétricas → E[driver] = valor_cenário → E[VAL_MC] ≈
VAL_determinístico; preço/câmbio log-normais → assimétricas com cauda direita, E[X] > mediana):
  dmi_pa_reducao      Triangular(8, 12, 15 dias)  — VLMs (VDMA); convertido em € via CMVMC_prod
  dmi_mp_reducao      Triangular(8,  8, 12 dias)  — Digital Twin (VDMA); idem
  dmi_clearing_dias   Triangular(12, 24, 36 dias) — clearing one-time de stock-excesso (mode≈€950 k)
  b2c                 Normal truncada N(1,0; σ=0,20) ∈ [0,3; 2,0] — incerteza de mercado
  pessoal             Triangular(70 %, 100 %, 130 % do cenário) — simétrica; mean = mode
  wacc                Triangular(WACC−2 p.p., WACC_cenário, WACC+2 p.p.) — simétrica; mean = wacc_cenário
  capex               Triangular(−15 %, base, +15 %)            — simétrica; mean = capex_base
  preco_eletricidade  Log-normal ln N(ln 0,12; σ=0,25) ∈ [0,06; 0,40] — inclui cenários crise OMIE 2021-22
  eur_usd             Log-normal ln N(ln 1,08; σ=0,08) ∈ [0,85; 1,30] — GBM cambial histórico 2018-2024

Dependências: apenas numpy + stdlib (sem scipy).
"""

from __future__ import annotations

import copy
import math
from typing import Any

import numpy as np

from .hub_logistico import load, viabilidade_hub, vala_hub


# ---------------------------------------------------------------------------
# Distribuições por defeito (calibradas com os ranges do tornado_hub)
# ---------------------------------------------------------------------------

DEFAULT_DISTRIBUTIONS: dict[str, dict] = {
    # Libertação de inventário modelada via dias de DMI (driver físico, VDMA), não €.
    # Convertido em € por hub_inventario_release (dias/365 × CMVMC_prod).
    #   dmi_pa_reducao   Triangular(8, 12, 15) — VLMs: redução de PA (VDMA 8-15 d)
    #   dmi_mp_reducao   Triangular(8,  8, 12) — Digital Twin: redução safety stock MP (VDMA 8-12 d)
    #   dmi_clearing_dias Triangular(12, 24, 36) — clearing one-time de stock-excesso (mode≈€950 k)
    "dmi_pa_reducao": {
        "type": "triangular",
        "min": 8.0,
        "mode": 12.0,
        "max": 15.0,
    },
    "dmi_mp_reducao": {
        "type": "triangular",
        "min": 8.0,
        "mode": 8.0,
        "max": 12.0,
    },
    "dmi_clearing_dias": {
        "type": "triangular",
        "min": 12.0,
        "mode": 24.0,
        "max": 36.0,
    },
    # PT2030 REMOVIDO (2025-05-30): Grande empresa sem elegibilidade a fundo perdido do
    # SI Inovação Produtiva. Qualquer apoio seria upside residual (≤ 7,5% CAPEX após RFAI),
    # com custo de oportunidade superior ao benefício líquido. O modelo base usa PT2030=€0.
    # Drivers de b2c, pessoal, wacc, capex, preço energia, câmbio e crescimento
    # continuam a ser simulados estocasticamente para capturar incerteza operacional.
    # Normal truncada: incerteza de mercado em torno do cenário base (×1.0).
    "b2c": {
        "type": "truncnorm",
        "mean": 1.0,
        "std": 0.20,
        "low": 0.30,
        "high": 2.00,
    },
    "pessoal": {
        "type": "triangular",
        "min": 200_000.0,
        "mode": 380_000.0,
        "max": 500_000.0,
    },
    "wacc": {
        "type": "triangular",
        "min": 0.06,
        "mode": 0.073,
        "max": 0.10,
    },
    # capex: min/mode/max calculados em runtime (±15 % sobre proj["capex"]["base"])
    "capex": {
        "type": "triangular",
        "min": None,
        "mode": None,
        "max": None,
    },
    # Preço da eletricidade (€/kWh) — log-normal centrada em 0,12 (OMIE base),
    # cauda direita inclui cenários de crise OMIE 2021-22. mu = ln(0,12).
    "preco_eletricidade": {
        "type": "lognormal",
        "mu": -2.12026,  # ln(0.12)
        "sigma": 0.25,
        "low": 0.06,
        "high": 0.40,
    },
    # Taxa de câmbio EUR/USD (USD por 1 EUR) — oscilação histórica 2020-2024.
    # EUR/USD ↑ (EUR aprecia) → cada USD recebido vale MENOS em EUR → impacto negativo no VAL.
    # EUR/USD ↓ (EUR desvaloriza) → cada USD recebido vale MAIS em EUR → impacto positivo no VAL.
    # Afeta apenas a fracção usd_fraction do vn_incremental (B2C internacional / exportações EUA).
    # Correlação de Pearson esperada com o VAL: negativa.
    "eur_usd": {
        "type": "lognormal",
        "mu": 0.07696,   # ln(1.08)
        "sigma": 0.08,
        "low": 0.85,
        "high": 1.30,
    },
    # Taxa de crescimento nominal dos benefícios (substitui crescimento_anual fixo do YAML)
    "crescimento_logistico": {
        "type": "triangular",
        "min": 0.02,
        "mode": 0.04,
        "max": 0.07,
    },
}

DRIVERS = [
    "dmi_pa_reducao", "dmi_mp_reducao", "dmi_clearing_dias",
    "b2c", "pessoal", "wacc", "capex",
    "preco_eletricidade", "eur_usd", "crescimento_logistico",
]

# ---------------------------------------------------------------------------
# Drivers e distribuições adicionais para Monte Carlo VALA (APV)
# ---------------------------------------------------------------------------

# rfai_utilization: Triangular(0.5, 1.0, 1.0) — fração do crédito RFAI efetivamente absorvida
# kd_shock        : Triangular(−100 bps, 0, +200 bps) — choque aditivo ao Kd bancário
# PT2030 REMOVIDO: grande empresa sem elegibilidade a fundo perdido (2025-05-30)
VALA_EXTRA_DRIVERS = ["rfai_utilization", "kd_shock"]

DEFAULT_VALA_EXTRA_DISTRIBUTIONS: dict[str, dict] = {
    # PT2030 REMOVIDO: Bernoulli(p=0) — não aplicável a grande empresa (2025-05-30)
    "rfai_utilization": {
        "type": "triangular",
        "min": 0.50,
        "mode": 1.00,
        "max": 1.00,
    },
    "kd_shock": {
        "type": "triangular",
        "min": -0.010,
        "mode": 0.000,
        "max": 0.020,
    },
}


# ---------------------------------------------------------------------------
# Samplers (numpy puro)
# ---------------------------------------------------------------------------

def _sample_triangular(
    rng: np.random.Generator,
    low: float,
    mode: float,
    high: float,
    n: int,
) -> np.ndarray:
    """Amostrador triangular usando numpy.random.Generator.triangular."""
    # Caso degenerado: se low == high (distribuição pontual), retorna constante.
    if math.isclose(low, high, rel_tol=1e-9):
        return np.full(n, low)
    # numpy aceita mode == low ou mode == high (casos degenerados válidos)
    return rng.triangular(low, mode, high, size=n)


def _sample_truncated_normal(
    rng: np.random.Generator,
    mean: float,
    std: float,
    low: float,
    high: float,
    n: int,
) -> np.ndarray:
    """Normal truncada por rejection sampling.

    Para os parâmetros b2c (N(1.0, 0.20) em [0.3, 2.0]) a taxa de rejeição é
    < 0,3 % — o over-sampling de 10× é suficiente para qualquer n prático.
    """
    collected: list[float] = []
    while len(collected) < n:
        batch = rng.normal(mean, std, size=max(n * 10, 500))
        valid = batch[(batch >= low) & (batch <= high)]
        collected.extend(valid.tolist())
    return np.array(collected[:n])


def _sample_lognormal(
    rng: np.random.Generator,
    mu: float,       # média do logaritmo natural
    sigma: float,    # desvio-padrão do logaritmo natural
    low: float,      # clip inferior
    high: float,     # clip superior
    n: int,
) -> np.ndarray:
    samples = rng.lognormal(mean=mu, sigma=sigma, size=n)
    return np.clip(samples, low, high)


def _draw_samples(
    rng: np.random.Generator,
    dist_cfg: dict,
    n: int,
) -> np.ndarray:
    """Despacha para o sampler correto conforme dist_cfg["type"]."""
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
        return _sample_truncated_normal(
            rng,
            float(dist_cfg["mean"]),
            float(dist_cfg["std"]),
            float(dist_cfg["low"]),
            float(dist_cfg["high"]),
            n,
        )
    if t == "lognormal":
        return _sample_lognormal(
            rng,
            float(dist_cfg["mu"]),
            float(dist_cfg["sigma"]),
            float(dist_cfg["low"]),
            float(dist_cfg["high"]),
            n,
        )
    if t == "bernoulli":
        # Devolve 1.0 (aprovado) com probabilidade p, 0.0 (rejeitado) com 1−p.
        p = float(dist_cfg["p"])
        return (rng.random(n) < p).astype(float)
    raise ValueError(f"Tipo de distribuição desconhecido: {t!r}")


# ---------------------------------------------------------------------------
# Mutação do hub (espelha sensibilidade_hub() de hub_logistico.py)
# ---------------------------------------------------------------------------

def _apply_sample(hub_base: dict, s: dict[str, float]) -> tuple[dict, float]:
    """Aplica um conjunto de valores amostrados a uma cópia profunda do hub.

    Retorna (hub_mutado, wacc_amostrado).
    O wacc NÃO é mutado no dicionário — é passado como kwarg a viabilidade_hub()
    (mesmo comportamento de sensibilidade_hub() nas linhas 1515-1527 do módulo original).
    """
    h = copy.deepcopy(hub_base)
    proj = h["projeto_hub"]

    def _scale_series(ben: dict, key: str, factor: float) -> None:
        series = ben.get(key)
        if not isinstance(series, dict):
            return
        for yr in list(series.keys()):
            series[yr] = float(series[yr]) * factor

    # 1. Inventário via dias de DMI (driver físico). hub_inventario_release converte
    #    estes dias em € de libertação (dias/365 × CMVMC_prod): clearing one-time +
    #    step-down estrutural + recorrente. Substitui o antigo escalar libertacao_inventario.
    proj["dmi_reducao_hub"]["DMI_PA_reducao_dias"] = s["dmi_pa_reducao"]
    proj["dmi_reducao_hub"]["DMI_MP_reducao_dias"] = s["dmi_mp_reducao"]
    proj.setdefault("inventario_dmi", {})["clearing_dias"] = s["dmi_clearing_dias"]

    # 2. CAPEX — escala base + cronograma anual proporcionalmente.
    #    A mesma proporção é aplicada ao capex_elegivel do RFAI para manter
    #    consistência interna (se mais é investido, mais é elegível a crédito fiscal).
    capex_base_val = float(proj["capex"]["base"])
    factor = s["capex"] / capex_base_val if capex_base_val else 1.0
    proj["capex"]["base"] = s["capex"]
    for y in list(proj["capex"]["cronograma"].keys()):
        proj["capex"]["cronograma"][y] = float(proj["capex"]["cronograma"][y]) * factor
    rfai_cfg = proj.get("rfai", {})
    if rfai_cfg.get("aplicar", False) and "capex_elegivel" in rfai_cfg:
        rfai_cfg["capex_elegivel"] = float(rfai_cfg["capex_elegivel"]) * factor

    # 3. PT2030 REMOVIDO (2025-05-30): Grande empresa sem elegibilidade a fundo perdido.
    #    O financiamento do Hub baseia-se exclusivamente em operações + RFAI + deuda bancária.
    #    O modelo mantém a chave PT2030 no YAML para integridade de estrutura, mas o montante
    #    permanece em €0 em todas as simulações (sem sampling estocástico).
    #
    # 4. Poupança operacional (pessoal + automação)
    ben = proj["beneficios_anuais"]
    base_poup = float(ben.get("poupanca_operacional", 0.0))
    pessoal_factor = s["pessoal"] / base_poup if base_poup else 1.0
    ben["poupanca_operacional"] = s["pessoal"]
    _scale_series(ben, "pessoal_saving_derivado", pessoal_factor)
    quebras = float(ben.get("reducao_quebras", 0.0))
    opex = abs(float(
        ben.get("opex_incremental")
        or proj.get("opex_detalhe", {}).get("total", 0.0)
        or 0.0
    ))
    ben["beneficio_liquido_anual"] = s["pessoal"] + quebras - opex

    # 5. B2C — factor de escala sobre o VN incremental por ano
    vn_map = proj.get("beneficios_comerciais", {}).get("vn_incremental", {})
    for yr in list(vn_map.keys()):
        vn_map[yr] = float(vn_map[yr]) * s["b2c"]

    # 6. Preço da eletricidade — delta sobre beneficio_liquido_anual
    #    O opex_incremental do YAML já embute um custo energético base (energia líq. de PV);
    #    este step modela a volatilidade desse componente face ao preço OMIE amostrado.
    energia_cfg = proj.get("opex_detalhe", {}).get("energia", {})
    consumo_kwh = float(energia_cfg.get("consumo_liquido_kwh", 90_000))
    preco_kwh_base = float(energia_cfg.get("preco_kwh_base", 0.12))
    energia_delta = (s["preco_eletricidade"] - preco_kwh_base) * consumo_kwh
    ben["beneficio_liquido_anual"] = ben["beneficio_liquido_anual"] - energia_delta

    # 7. EUR/USD — ajuste da fracção USD do VN incremental (aplica-se depois do step b2c)
    #
    #    Lógica: a empresa recebe dólares (vendas B2C internacionais) e converte a EUR.
    #      USD recebidos → EUR = USD / EUR_USD_rate
    #    Logo EUR/USD ↑ (EUR aprecia) → conversão produz menos EUR → VAL desce.
    #         EUR/USD ↓ (EUR desvaloriza) → conversão produz mais EUR → VAL sobe.
    #
    #    fx_factor = eur_usd_base / eur_usd_amostrado
    #      • = 1,0 exatamente no caso base (sem efeito)
    #      • > 1,0 quando EUR desvaloriza (eur_usd amostrado < base) → amplifica receita
    #      • < 1,0 quando EUR aprecia   (eur_usd amostrado > base) → reduz receita
    #
    #    Apenas usd_fraction do vn_incremental é USD-denominado; a parte EUR mantém-se inalterada.
    #    Fórmula: vn_ajustado = vn × [1 − usd_frac × (1 − fx_factor)]
    #      equivalente a: vn_eur_puro + vn_usd_puro × fx_factor
    usd_frac = float(proj.get("beneficios_comerciais", {}).get("usd_fraction", 0.15))
    eur_usd_base = float(proj.get("viabilidade", {}).get("eur_usd_base", 1.08))
    fx_factor = eur_usd_base / s["eur_usd"]
    for yr in list(vn_map.keys()):
        vn_map[yr] = vn_map[yr] * (1.0 - usd_frac * (1.0 - fx_factor))

    # 8. Taxa de crescimento nominal dos benefícios (substitui o valor fixo do YAML)
    proj["beneficios_anuais"]["crescimento_anual"] = s["crescimento_logistico"]

    # wacc devolvido separadamente (não mutado no dict)
    return h, float(s["wacc"])


# ---------------------------------------------------------------------------
# Estatísticas e histograma
# ---------------------------------------------------------------------------

def _percentiles(values: np.ndarray, pcts: list[int]) -> dict[str, float]:
    """Dicionário de percentis a partir de um array numpy."""
    return {f"p{p}": float(np.percentile(values, p)) for p in pcts}


def _build_histogram(values: np.ndarray, n_bins: int = 40) -> dict[str, Any]:
    """Histograma JSON-serializable com centros de bins, contagens e arestas."""
    counts, edges = np.histogram(values, bins=n_bins)
    centers = [(float(edges[i]) + float(edges[i + 1])) / 2.0 for i in range(n_bins)]
    return {
        "bins": centers,
        "counts": [int(c) for c in counts],
        "edges": [float(e) for e in edges],
    }


def _pearson(x: list[float], y: list[float]) -> float:
    """Correlação de Pearson entre dois vetores (ignora NaN via máscara)."""
    xa = np.array(x, dtype=float)
    ya = np.array(y, dtype=float)
    mask = np.isfinite(xa) & np.isfinite(ya)
    if mask.sum() < 2:
        return 0.0
    corr_matrix = np.corrcoef(xa[mask], ya[mask])
    return float(corr_matrix[0, 1])


# ---------------------------------------------------------------------------
# Função principal
# ---------------------------------------------------------------------------

def monte_carlo_hub(
    hub: dict | None = None,
    n_simulations: int = 1000,
    irc_taxa: float | None = None,
    distributions: dict | None = None,
    seed: int | None = None,
) -> dict:
    """Simulação Monte Carlo da viabilidade do Hub Logístico 4.0.

    Parâmetros
    ----------
    hub : dict | None
        Dicionário de pressupostos (carregado de m6_hub_assumptions.yaml).
        Se None, carrega automaticamente via load().
    n_simulations : int
        Número de iterações (recomendado: 1 000–5 000).
    irc_taxa : float | None
        Taxa combinada de IRC. Se None, usa o valor do YAML (por defeito 22,5 %).
    distributions : dict | None
        Override de parâmetros por driver. Mesma estrutura de DEFAULT_DISTRIBUTIONS.
        Apenas as chaves fornecidas são substituídas; as restantes mantêm o defeito.
    seed : int | None
        Seed do gerador aleatório (para reprodutibilidade). None = seed aleatório.

    Retorna
    -------
    dict com:
      val          — estatísticas e histograma do VAL (€)
      tir          — estatísticas da TIR (exclui iterações sem convergência)
      correlacoes_val — Pearson r entre cada driver e o VAL (ranking de risco)
      distribuicoes_usadas — parâmetros efetivos usados na simulação
      parametros_base      — caso base determinístico para referência
    """
    if hub is None:
        hub = load()

    proj = hub["projeto_hub"]
    via = proj["viabilidade"]

    if irc_taxa is None:
        irc_taxa = float(via.get("irc_taxa", 0.21))
    wacc_base = float(via["wacc"])
    capex_base = float(proj["capex"]["base"])

    # ── Resolver distribuições efetivas ─────────────────────────────────────
    dist_efetivas: dict[str, dict] = {}
    for drv in DRIVERS:
        cfg = dict(DEFAULT_DISTRIBUTIONS[drv])
        if distributions and drv in distributions:
            cfg.update(distributions[drv])
        dist_efetivas[drv] = cfg

    # WACC: distribuição simétrica ±2 p.p. em torno do WACC do cenário.
    # Distribuição simétrica garante E[WACC] = wacc_cenário → E[VAL_MC] ≈ VAL_determinístico.
    # Limites fixos [6%, mode, 10%] criavam assimetria: para Upside (mode=6,9%) a média
    # subia para 7,6%, deprimindo sistematicamente o VAL médio do MC.
    if not (distributions and "wacc" in distributions):
        _wacc_spread = 0.02  # ±2 p.p. de incerteza sobre o custo de capital
        dist_efetivas["wacc"] = {
            "type": "triangular",
            "min": max(0.04, wacc_base - _wacc_spread),
            "mode": wacc_base,
            "max": min(0.15, wacc_base + _wacc_spread),
        }
    elif "mode" not in (distributions.get("wacc") or {}):
        dist_efetivas["wacc"]["mode"] = wacc_base

    # Pessoal e inventário: distribuições simétricas centradas no valor do cenário.
    # Intervalos simétricos garantem E[driver] = valor_cenário → E[VAL_MC] ≈ VAL_determinístico.
    #   pessoal:    Triangular[mode × 0,70 ; mode ; mode × 1,30]  (mean = mode)
    # Os drivers de DMI (dmi_pa_reducao, dmi_mp_reducao, dmi_clearing_dias) usam ranges
    # fixos em dias (VDMA) — sem recalibração runtime.
    pessoal_cenario = float(proj["beneficios_anuais"].get("poupanca_operacional", 380_000))

    if not (distributions and "pessoal" in distributions):
        dist_efetivas["pessoal"] = {
            "type": "triangular",
            "min": pessoal_cenario * 0.70,
            "mode": pessoal_cenario,
            "max": pessoal_cenario * 1.30,
        }

    # Calcular limites do CAPEX em runtime (dependem do capex_base do YAML)
    if dist_efetivas["capex"]["min"] is None:
        dist_efetivas["capex"]["min"] = capex_base * 0.85
        dist_efetivas["capex"]["mode"] = capex_base
        dist_efetivas["capex"]["max"] = capex_base * 1.15

    # ── Caso base (determinístico, para referência) ──────────────────────────
    res_base = viabilidade_hub(hub, irc_taxa=irc_taxa, wacc=wacc_base)
    val_base = float(res_base["val"])
    tir_base = res_base.get("tir")

    # ── Gerar amostras antecipadamente (mais eficiente que amostrar no loop) ─
    rng = np.random.default_rng(seed)
    samples_arr: dict[str, np.ndarray] = {
        drv: _draw_samples(rng, dist_efetivas[drv], n_simulations)
        for drv in DRIVERS
    }

    # ── Loop principal ────────────────────────────────────────────────────────
    val_list: list[float] = []
    tir_list: list[float | None] = []
    driver_samples: dict[str, list[float]] = {d: [] for d in DRIVERS}

    for i in range(n_simulations):
        s = {drv: float(samples_arr[drv][i]) for drv in DRIVERS}
        for drv in DRIVERS:
            driver_samples[drv].append(s[drv])

        h_mut, wacc_i = _apply_sample(hub, s)
        res = viabilidade_hub(h_mut, irc_taxa=irc_taxa, wacc=wacc_i)

        val_list.append(float(res["val"]))
        tir_list.append(res.get("tir"))  # None quando IRR não converge

    # ── Estatísticas VAL ─────────────────────────────────────────────────────
    val_arr = np.array(val_list, dtype=float)
    pcts = [5, 10, 25, 50, 75, 90, 95]

    val_stats: dict[str, Any] = {
        "mean": float(np.mean(val_arr)),
        "std": float(np.std(val_arr, ddof=1)),
        **_percentiles(val_arr, pcts),
        "min": float(np.min(val_arr)),
        "max": float(np.max(val_arr)),
        # Probabilidade de viabilidade: P(VAL > 0)
        "prob_positivo": float(np.mean(val_arr > 0)),
        "histogram": _build_histogram(val_arr),
    }

    # ── Estatísticas TIR ─────────────────────────────────────────────────────
    tir_validas = [t for t in tir_list if t is not None]
    n_validas = len(tir_validas)
    n_invalidas = n_simulations - n_validas

    if n_validas >= 2:
        tir_arr = np.array(tir_validas, dtype=float)
        tir_stats: dict[str, Any] = {
            "mean": float(np.mean(tir_arr)),
            "std": float(np.std(tir_arr, ddof=1)),
            **_percentiles(tir_arr, pcts),
            # P(TIR > wacc_base): usa o WACC base como limiar fixo para interpretabilidade
            "prob_supera_wacc_base": float(np.mean(tir_arr > wacc_base)),
        }
    else:
        tir_stats = {k: None for k in ["mean", "std"] + [f"p{p}" for p in pcts] + ["prob_supera_wacc_base"]}

    tir_stats["n_validas"] = n_validas
    tir_stats["n_invalidas"] = n_invalidas

    # ── Correlações de Pearson: driver → VAL ────────────────────────────────
    # r > 0 → driver aumenta VAL; r < 0 → driver reduz VAL.
    # Ordenado por |r| decrescente (maior impacto primeiro).
    correlacoes_raw = {
        drv: _pearson(driver_samples[drv], val_list)
        for drv in DRIVERS
    }
    correlacoes_val = dict(
        sorted(correlacoes_raw.items(), key=lambda kv: abs(kv[1]), reverse=True)
    )

    return {
        "n_simulations": n_simulations,
        "irc_taxa": float(irc_taxa),
        "val": val_stats,
        "tir": tir_stats,
        "correlacoes_val": {k: float(v) for k, v in correlacoes_val.items()},
        # Parâmetros efetivos usados — útil para o frontend mostrar os ranges
        "distribuicoes_usadas": {
            drv: {k: (float(v) if isinstance(v, (int, float)) and v is not None else v)
                  for k, v in cfg.items()}
            for drv, cfg in dist_efetivas.items()
        },
        # Caso base determinístico para comparação
        "parametros_base": {
            "val_base": val_base,
            "tir_base": float(tir_base) if tir_base is not None else None,
            "wacc_base": float(wacc_base),
            "capex_base": float(capex_base),
            "irc_taxa": float(irc_taxa),
        },
    }


# ---------------------------------------------------------------------------
# Monte Carlo VALA (APV) — distribuição desagregada por componente
# ---------------------------------------------------------------------------

def _apply_sample_vala(hub_base: dict, s: dict[str, float]) -> dict:
    """Aplica amostra base + mutações dos 2 drivers fiscais extras ao hub.

    Sequência:
      1. _apply_sample()  — drivers operacionais + wacc + capex (PT2030=€0 fixo)
      2. rfai_utilization — escala rfai.capex_elegivel pela taxa de utilização
      3. kd_shock         — adiciona choque aditivo ao Kd de cada tranche

    Retorna o hub mutado (wacc_i descartado — vala_hub usa Ke fixo do YAML).
    """
    h, _ = _apply_sample(hub_base, s)
    proj = h["projeto_hub"]

    # 1. PT2030 já está a €0 no YAML — sem sampling estocástico (2025-05-30)
    #    Mantém-se a chave para integridade de estrutura, mas o montante é imutável.

    # 2. Utilização parcial do crédito RFAI (escala capex_elegivel)
    util = float(s.get("rfai_utilization", 1.0))
    if util < 1.0 - 1e-6:
        rfai_cfg = proj.get("rfai", {})
        if rfai_cfg.get("aplicar", False) and "capex_elegivel" in rfai_cfg:
            rfai_cfg["capex_elegivel"] = float(rfai_cfg["capex_elegivel"]) * util

    # 3. Choque no spread bancário (Kd aditivo)
    shock = float(s.get("kd_shock", 0.0))
    if abs(shock) > 1e-9:
        for v in proj["financiamento"].values():
            if isinstance(v, dict) and "taxa_juro" in v and "amortizacao_anual" in v:
                v["taxa_juro"] = max(0.005, float(v["taxa_juro"]) + shock)

    return h


def _component_stats(values: list[float], *, histogram: bool = False) -> dict[str, Any]:
    """Estatísticas descritivas de um componente VALA (mean, std, percentis, prob_positivo)."""
    arr = np.array(values, dtype=float)
    pcts = [5, 10, 25, 50, 75, 90, 95]
    d: dict[str, Any] = {
        "mean": float(np.mean(arr)),
        "std": float(np.std(arr, ddof=1)),
        **_percentiles(arr, pcts),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "prob_positivo": float(np.mean(arr > 0)),
    }
    if histogram:
        d["histogram"] = _build_histogram(arr)
    return d


def _stress_fiscal(hub_base: dict, irc_taxa_base: float) -> dict[str, dict]:
    """Dois cenários de stress fiscal determinísticos (sem MC).

    Cenários:
      base             — pressupostos nominais (referência), PT2030=€0
      rfai_esgotado    — RFAI.aplicar = False (carry-forward não absorvido)
      irc_28pct        — IRC sobe de 24,5 % para 28 %
    """
    def _run(h: dict, irc_t: float) -> dict:
        r = vala_hub(h, irc_taxa=irc_t)
        return {
            "vala": r["vala"],
            "val_base_ke": r["val_base_ke"],
            "escudo_fiscal": r["escudo_fiscal_total"],
            # PT2030 = €0: pv_pt2030 = 0 sempre
            "pv_rfai": r["pv_rfai"],
        }

    result: dict[str, dict] = {
        "base": {"label": "Base — PT2030=€0, RFAI ativo, IRC nominal", **_run(hub_base, irc_taxa_base)},
    }

    h = copy.deepcopy(hub_base)
    if "rfai" in h["projeto_hub"]:
        h["projeto_hub"]["rfai"]["aplicar"] = False
    result["rfai_esgotado"] = {
        "label": "RFAI carry-forward esgota (crédito não absorvido)",
        **_run(h, irc_taxa_base),
    }

    result["irc_28pct"] = {
        "label": "IRC sobe para 28%",
        **_run(hub_base, 0.28),
    }

    return result


def monte_carlo_vala_hub(
    hub: dict | None = None,
    n_simulations: int = 1000,
    irc_taxa: float | None = None,
    distributions: dict | None = None,
    seed: int | None = None,
    incluir_stress: bool = True,
) -> dict:
    """Monte Carlo do VALA (APV) — distribuição desagregada por componente.

    Estende o monte_carlo_hub() com dois drivers estocásticos fiscais:
      rfai_utilization  Triangular[0.50, 1.00, 1.00] — absorção do crédito RFAI
      kd_shock          Triangular[−1%, 0%, +2%] — choque aditivo no spread bancário

    PT2030 = €0 fixo: grande empresa sem elegibilidade a fundo perdido (2025-05-30).

    Em cada iteração chama vala_hub() e regista os três componentes APV:
      VAL_base(Ke), Escudo Fiscal, PV(RFAI)

    Saídas principais
    -----------------
    vala / val_base_ke / escudo_fiscal / pv_rfai
        Estatísticas (mean, std, P5–P95, prob_positivo) de cada componente.
    diagnostico
        P(VALA>0), P(VAL_base>0).
        Análise de causa das falhas operacionais.
    correlacoes_vala
        Pearson r para todos os drivers (incluindo fiscais) ordenado por |r|.
    stress_fiscal
        Dois cenários determinísticos: RFAI esgotado, IRC=28%.
    """
    if hub is None:
        hub = load()

    proj = hub["projeto_hub"]
    via = proj["viabilidade"]

    if irc_taxa is None:
        irc_taxa = float(via.get("irc_taxa", 0.21))
    wacc_base = float(via["wacc"])
    capex_base = float(proj["capex"]["base"])

    # ── Resolver distribuições efetivas (espelha monte_carlo_hub) ────────────
    dist_efetivas: dict[str, dict] = {}
    for drv in DRIVERS:
        cfg = dict(DEFAULT_DISTRIBUTIONS[drv])
        if distributions and drv in distributions:
            cfg.update(distributions[drv])
        dist_efetivas[drv] = cfg

    if not (distributions and "wacc" in distributions):
        _wacc_spread = 0.02
        dist_efetivas["wacc"] = {
            "type": "triangular",
            "min": max(0.04, wacc_base - _wacc_spread),
            "mode": wacc_base,
            "max": min(0.15, wacc_base + _wacc_spread),
        }
    elif "mode" not in (distributions.get("wacc") or {}):
        dist_efetivas["wacc"]["mode"] = wacc_base

    pessoal_cenario = float(proj["beneficios_anuais"].get("poupanca_operacional", 380_000))

    if not (distributions and "pessoal" in distributions):
        dist_efetivas["pessoal"] = {
            "type": "triangular",
            "min": pessoal_cenario * 0.70,
            "mode": pessoal_cenario,
            "max": pessoal_cenario * 1.30,
        }
    if dist_efetivas["capex"]["min"] is None:
        dist_efetivas["capex"]["min"] = capex_base * 0.85
        dist_efetivas["capex"]["mode"] = capex_base
        dist_efetivas["capex"]["max"] = capex_base * 1.15

    # Drivers fiscais extras
    for drv in VALA_EXTRA_DRIVERS:
        cfg = dict(DEFAULT_VALA_EXTRA_DISTRIBUTIONS[drv])
        if distributions and drv in distributions:
            cfg.update(distributions[drv])
        dist_efetivas[drv] = cfg

    # ── Caso base determinístico ─────────────────────────────────────────────
    res_base = vala_hub(hub, irc_taxa=irc_taxa)
    vala_base_det = float(res_base["vala"])

    # ── Amostras antecipadas ─────────────────────────────────────────────────
    all_vala_drivers = DRIVERS + VALA_EXTRA_DRIVERS
    rng = np.random.default_rng(seed)
    samples_arr: dict[str, np.ndarray] = {
        drv: _draw_samples(rng, dist_efetivas[drv], n_simulations)
        for drv in all_vala_drivers
    }

    # ── Loop principal ────────────────────────────────────────────────────────
    vala_list: list[float] = []
    val_base_ke_list: list[float] = []
    escudo_list: list[float] = []
    pv_rfai_list: list[float] = []
    driver_samples: dict[str, list[float]] = {d: [] for d in all_vala_drivers}

    for i in range(n_simulations):
        s = {drv: float(samples_arr[drv][i]) for drv in all_vala_drivers}
        for drv in all_vala_drivers:
            driver_samples[drv].append(s[drv])

        h_mut = _apply_sample_vala(hub, s)
        res = vala_hub(h_mut, irc_taxa=irc_taxa)

        vala_list.append(float(res["vala"]))
        val_base_ke_list.append(float(res["val_base_ke"]))
        escudo_list.append(float(res["escudo_fiscal_total"]))
        pv_rfai_list.append(float(res["pv_rfai"]))

    # ── Estatísticas por componente ───────────────────────────────────────────
    vala_arr = np.array(vala_list, dtype=float)
    val_base_arr = np.array(val_base_ke_list, dtype=float)
    escudo_arr = np.array(escudo_list, dtype=float)
    rfai_arr = np.array(pv_rfai_list, dtype=float)

    # ── Diagnóstico de falhas ─────────────────────────────────────────────────
    mask_falha = vala_arr < 0
    n_falhas = int(mask_falha.sum())

    n_falhas_val_base_neg = int((mask_falha & (val_base_arr < 0)).sum())
    pct_falhas_val_base = n_falhas_val_base_neg / n_falhas if n_falhas > 0 else 0.0

    diagnostico: dict[str, Any] = {
        "prob_vala_positivo": float(np.mean(vala_arr > 0)),
        "prob_val_base_positivo": float(np.mean(val_base_arr > 0)),
        "n_falhas": n_falhas,
        "pct_falhas_com_val_base_negativo": round(pct_falhas_val_base, 4),
        "interpretacao": (
            f"{n_falhas} simulações com VALA < 0. "
            f"{pct_falhas_val_base:.0%} devem-se a VAL_base negativo (operacional). "
            f"PT2030 = €0 (grande empresa sem elegibilidade a fundo perdido)."
        ),
    }

    # ── Correlações driver → VALA ─────────────────────────────────────────────
    correlacoes_raw = {
        drv: _pearson(driver_samples[drv], vala_list)
        for drv in all_vala_drivers
    }
    correlacoes_vala = dict(
        sorted(correlacoes_raw.items(), key=lambda kv: abs(kv[1]), reverse=True)
    )

    # ── Stress tests fiscais (determinísticos) ────────────────────────────────
    stress = _stress_fiscal(hub, irc_taxa) if incluir_stress else {}

    return {
        "n_simulations": n_simulations,
        "irc_taxa": float(irc_taxa),
        "vala": _component_stats(vala_list, histogram=True),
        "val_base_ke": _component_stats(val_base_ke_list),
        "escudo_fiscal": _component_stats(escudo_list),
        "pv_rfai": _component_stats(pv_rfai_list),
        "diagnostico": diagnostico,
        "correlacoes_vala": {k: float(v) for k, v in correlacoes_vala.items()},
        "stress_fiscal": stress,
        "distribuicoes_usadas": {
            drv: {k: (float(v) if isinstance(v, (int, float)) and v is not None else v)
                  for k, v in cfg.items()}
            for drv, cfg in dist_efetivas.items()
        },
        "parametros_base": {
            "vala_base": vala_base_det,
            "val_base_ke": float(res_base["val_base_ke"]),
            "escudo_fiscal": float(res_base["escudo_fiscal_total"]),
            # PT2030 = €0: pv_pt2030 = 0, removido do return (2025-05-30)
            "pv_rfai": float(res_base["pv_rfai"]),
            "wacc_base": float(wacc_base),
            "capex_base": float(capex_base),
            "irc_taxa": float(irc_taxa),
        },
    }
