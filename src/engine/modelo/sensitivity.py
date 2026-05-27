"""Módulo: engine/sensitivity.py — Análise de Sensibilidade e Tornado."""

from __future__ import annotations

import copy
from typing import Sequence

import pandas as pd

from ..inputs import load as _inputs_load
from ..demonstracoes import statements


def _block(a, key: str) -> dict:
    """Obtém bloco de cenário/driver de forma compatível com a nova estrutura YAML."""
    aliases = {
        "volume_vendas": "crescimento_volume_vendas",
        "preco_vendas": "crescimento_pvu_vendas",
        "fse": "crescimento_fse",
        "pessoal": "crescimento_pessoal",
        "custo_mercadorias": "crescimento_custo_mercadorias",
        "mpsc": "crescimento_pcu_mpsc",
    }

    cb = a.cenario_block()
    block = cb.get(key)

    if isinstance(block, dict) and "annual_2025" in block:
        return block

    raw_key = aliases.get(key, key)
    block = a.raw.get(raw_key, block if isinstance(block, dict) else {})

    if not isinstance(block, dict):
        block = {}

    a.raw[raw_key] = block

    return block


def _apply_volume_vn(a, b, s, delta):
    """Aplica choque ao crescimento de volume de vendas."""
    _ = b, s

    block = _block(a, "volume_vendas")
    block["annual_2025"] = float(block.get("annual_2025", 0.0)) + float(delta)

    for y in [2026, 2027, 2028, 2029]:
        block[y] = float(block.get(y, 0.0)) + float(delta)


def _apply_irc_taxa(a, b, s, delta):
    """Aplica choque à taxa geral de IRC."""
    _ = b, s

    a.raw["impostos"]["IRC_taxa_geral"] = (
        float(a.raw["impostos"].get("IRC_taxa_geral", 0.20))
        + float(delta)
    )


def _apply_euribor(a, b, s, delta):
    """Aplica choque aos juros via capital em dívida."""
    _ = a, b

    fin = s.raw["financiamento"]

    for y in list(fin.get("juros_total", {}).keys()):
        cap = float(fin.get("capital_divida_total_fim_ano", {}).get(y, 0.0))
        fin["juros_total"][y] = float(fin["juros_total"].get(y, 0.0)) + cap * float(delta)


def _apply_cmvmc_pct(a, b, s, delta):
    """Aplica choque ao custo de mercadorias."""
    _ = b, s

    block = _block(a, "custo_mercadorias")
    block["annual_2025"] = float(block.get("annual_2025", 0.0)) + float(delta)

    for y in [2026, 2027, 2028, 2029]:
        block[y] = float(block.get(y, 0.0)) + float(delta)


def _apply_fse_pct(a, b, s, delta):
    """Aplica choque ao crescimento de FSE."""
    _ = b, s

    block = _block(a, "fse")
    block["annual_2025"] = float(block.get("annual_2025", 0.0)) + float(delta)

    for y in [2026, 2027, 2028, 2029]:
        block[y] = float(block.get(y, 0.0)) + float(delta)


def _apply_pessoal_cresc(a, b, s, delta):
    """Aplica choque ao crescimento do custo de pessoal."""
    _ = b, s

    val = a.raw["pessoal"].get("taxa_cresc_custo_2025", 0.01)

    if isinstance(val, dict):
        val[a.cenario] = float(val.get(a.cenario, val.get("Base", 0.01))) + float(delta)
    else:
        a.raw["pessoal"]["taxa_cresc_custo_2025"] = float(val) + float(delta)


def _apply_capex(a, b, s, delta):
    """Aplica choque ao nível de CAPEX anual."""
    _ = a, b

    inv = s.raw["investimento"]

    for y in list(inv.get("novo_investimento_aft", {}).keys()):
        inv["novo_investimento_aft"][y] = (
            float(inv["novo_investimento_aft"].get(y, 0.0))
            * (1 + float(delta))
        )


def _apply_vendas_ext(a, b, s, delta):
    """Aplica uplift às vendas externas."""
    _ = b, s

    mu = a.raw["triggers"].setdefault("market_uplift", {})
    mu.setdefault("EXT", {})[a.cenario] = {
        "enabled": True,
        "value": float(delta),
    }


def _apply_mix_produtos(a, b, s, delta):
    """Aplica choque ao mix de produtos, favorecendo produtos de maior PVU."""
    _ = s

    from .vendas import _qty_2024_excel
    from ..inputs import PRODUTOS

    pvu = {
        p: float(b.pvu_base[p])
        for p in PRODUTOS
    }

    df = _qty_2024_excel()
    total_qty = float(df["qtd_2024"].sum())

    base_shares = {
        p: float(df[df["produto"] == p]["qtd_2024"].sum()) / total_qty
        for p in PRODUTOS
    }

    pvu_avg = sum(base_shares[p] * pvu[p] for p in PRODUTOS)

    dev = {
        p: pvu[p] - pvu_avg
        for p in PRODUTOS
    }

    dev_norm = sum(abs(v) for v in dev.values()) or 1.0

    direction = {
        p: dev[p] / dev_norm
        for p in PRODUTOS
    }

    new_shares = {
        p: max(0.0, base_shares[p] + float(delta) * direction[p])
        for p in PRODUTOS
    }

    total = sum(new_shares.values()) or 1.0

    a.raw["mix_produto_override"] = {
        p: v / total
        for p, v in new_shares.items()
    }


def _apply_margem_bruta(a, b, s, delta):
    """Aplica choque à margem bruta via custo de mercadorias."""
    _ = b, s

    block = _block(a, "custo_mercadorias")
    block["annual_2025"] = float(block.get("annual_2025", 0.0)) - float(delta)

    for y in [2026, 2027, 2028, 2029]:
        block[y] = float(block.get(y, 0.0)) - float(delta)


def _apply_fse_peso_vn(a, b, s, delta):
    """Aplica choque ao peso FSE/VN."""
    _ = b, s

    block = a.cenario_block()
    vn_vol = _block(a, "volume_vendas")

    vn_preco = (
        block.get("preco_vendas")
        if isinstance(block.get("preco_vendas"), dict)
        else {"annual_2025": 0.0}
    )

    fse_block = _block(a, "fse")

    vn_2025 = (
        (1 + float(vn_vol.get("annual_2025", 0.03)))
        * (1 + float(vn_preco.get("annual_2025", 0.02)))
        - 1
    )

    fse_block["annual_2025"] = vn_2025 + float(delta)

    for y in [2026, 2027, 2028, 2029]:
        vn_y = (
            (1 + float(vn_vol.get(y, 0.03)))
            * (1 + float(vn_preco.get(y, 0.02)))
            - 1
        )

        fse_block[y] = vn_y + float(delta)


def _apply_pessoal_peso(a, b, s, delta):
    """Aplica choque ao peso do pessoal."""
    _apply_pessoal_cresc(a, b, s, delta)


def _apply_hub_poupanca(a, b, s, delta):
    """Activa hub e aplica choque fraccional à poupança operacional (pessoal + FSE)."""
    _ = b, s
    hub = a.raw.setdefault("hub_logistico", {})
    hub["incluir_hub"] = True
    ben = hub.setdefault("projeto_hub", {}).setdefault("beneficios_anuais", {})
    base = float(ben.get("poupanca_operacional", 480000))
    ben["poupanca_operacional"] = base * (1 + float(delta))


def _apply_hub_quebras(a, b, s, delta):
    """Activa hub e aplica choque fraccional à redução de quebras (VLM/picking)."""
    _ = b, s
    hub = a.raw.setdefault("hub_logistico", {})
    hub["incluir_hub"] = True
    ben = hub.setdefault("projeto_hub", {}).setdefault("beneficios_anuais", {})
    base = float(ben.get("reducao_quebras", 50000))
    ben["reducao_quebras"] = base * (1 + float(delta))


def _apply_tarifa_usa(a, b, s, delta):
    """Aplica choque ao impacto de tarifas EUA nas vendas USA.
    
    delta > 0 → tarifas sobem → vendas USA caem.
    delta < 0 → tarifas descem → vendas USA sobem.
    """
    _ = b, s
    mercados = a.raw.setdefault("mercados", {})
    usa = mercados.setdefault("USA", {})
    current_uplift = float(usa.get("tarifa_impacto", 0.0))
    usa["tarifa_impacto"] = current_uplift + float(delta)


def _apply_preco_vendas(a, b, s, delta):
    """Aplica choque ao crescimento do preço de venda."""
    _ = b, s

    block = _block(a, "preco_vendas")
    block["annual_2025"] = float(block.get("annual_2025", 0.0)) + float(delta)

    for y in [2026, 2027, 2028, 2029]:
        block[y] = float(block.get(y, 0.0)) + float(delta)


def _apply_eur_usd(a, b, s, delta):
    """Aplica choque proporcional à taxa EUR/USD em todos os anos.

    delta > 0 → EUR/USD sobe → USD deprecia → VN EXT cai.
    delta < 0 → EUR/USD desce → USD aprecia → VN EXT sobe.
    O choque é multiplicativo sobre a taxa de cada ano.
    """
    _ = b, s
    eurusd = a.raw.setdefault("macro", {}).setdefault("eur_usd", {})
    anual = eurusd.setdefault("anual", {})
    for y in [2025, 2026, 2027, 2028, 2029]:
        base_y = float(anual.get(y, 1.08))
        anual[y] = base_y * (1.0 + float(delta))
    mensal = eurusd.get("mensal_2025", [1.08] * 12)
    eurusd["mensal_2025"] = [v * (1.0 + float(delta)) for v in mensal]


DRIVERS = {
    "volume_vn": (
        "Crescimento Volume",
        [-0.05, -0.025, 0, 0.025, 0.05],
        _apply_volume_vn,
    ),
    "preco_vendas": (
        "Preço de Venda",
        [-0.03, -0.02, -0.01, 0, 0.01, 0.02, 0.03],
        _apply_preco_vendas,
    ),
    "eur_usd": (
        "EUR/USD (câmbio)",
        [-0.10, -0.05, 0, 0.05, 0.10],
        _apply_eur_usd,
    ),
    "irc_taxa": (
        "Taxa IRC",
        [-0.04, -0.02, 0, 0.02, 0.04],
        _apply_irc_taxa,
    ),
    "euribor": (
        "Choque Euribor",
        [-0.01, -0.005, 0, 0.005, 0.01],
        _apply_euribor,
    ),
    "cmvmc_pct_vn": (
        "Custo Mercadorias",
        [-0.05, -0.025, 0, 0.025, 0.05],
        _apply_cmvmc_pct,
    ),
    "fse_pct_vn": (
        "Gastos FSE",
        [-0.05, -0.025, 0, 0.025, 0.05],
        _apply_fse_pct,
    ),
    "pessoal_cresc": (
        "Crescimento Pessoal",
        [-0.05, -0.025, 0, 0.025, 0.05],
        _apply_pessoal_cresc,
    ),
    "capex_anual": (
        "Nível CAPEX",
        [-0.1, -0.05, 0, 0.05, 0.1],
        _apply_capex,
    ),
    "vendas_ext": (
        "Vendas Externas",
        [-0.1, -0.05, 0, 0.05, 0.1],
        _apply_vendas_ext,
    ),
    "mix_produtos": (
        "Mix de Produtos",
        [-0.1, -0.05, 0, 0.05, 0.1],
        _apply_mix_produtos,
    ),
    "margem_bruta": (
        "Margem Bruta",
        [-0.05, -0.025, 0, 0.025, 0.05],
        _apply_margem_bruta,
    ),
    "fse_peso_vn": (
        "FSE / VN",
        [-0.05, -0.025, 0, 0.025, 0.05],
        _apply_fse_peso_vn,
    ),
    "pessoal_peso": (
        "Peso Pessoal",
        [-0.05, -0.025, 0, 0.025, 0.05],
        _apply_pessoal_peso,
    ),
    "hub_poupanca": (
        "Hub · Poupança Operacional",
        [-0.30, -0.15, 0, 0.15, 0.30],
        _apply_hub_poupanca,
    ),
    "hub_quebras": (
        "Hub · Redução de Quebras",
        [-1.00, -0.50, 0, 0.50, 1.00],
        _apply_hub_quebras,
    ),
    "tarifa_usa": (
        "Tarifas EUA",
        [-0.10, -0.05, 0, 0.05, 0.10, 0.15, 0.20, 0.25],
        _apply_tarifa_usa,
    ),
}


def _run_with_delta(
    cenario: str,
    driver_key: str,
    delta: float,
    year: int,
    metric: str,
) -> float:
    """Executa o modelo com um choque e devolve uma métrica."""
    a, b, s = _inputs_load(cenario=cenario)
    a_backup = copy.deepcopy(a.raw)
    s_backup = copy.deepcopy(s.raw) if hasattr(s, 'raw') else None
    try:
        apply_fn = DRIVERS[driver_key][2]
        apply_fn(a, b, s, delta)

        dr = statements.build_dr(a, b, s)
        bal = statements.build_balanco(a, b, s, dr)
        dfc = statements.build_dfc(a, dr, bal, s, b)

        row = dr[dr.ano == year]

        if not row.empty and metric in row.iloc[0].index:
            return float(row.iloc[0][metric])

        bal_row = bal[bal.ano == year]

        if not bal_row.empty and metric in bal_row.columns:
            return float(bal_row.iloc[0][metric])

        dfc_row = dfc[dfc.ano == year]

        if not dfc_row.empty and metric in dfc_row.columns:
            return float(dfc_row.iloc[0][metric])

        return float("nan")
    finally:
        a.raw = a_backup
        if s_backup is not None:
            s.raw = s_backup


def one_at_a_time(
    driver_key: str,
    deltas: Sequence[float] | None = None,
    year: int = 2025,
    metric: str = "rl",
    cenario: str = "Base",
) -> pd.DataFrame:
    """Varia um driver e devolve a métrica escolhida."""
    if driver_key not in DRIVERS:
        raise ValueError(
            f"Unknown driver '{driver_key}'. Choose from: {list(DRIVERS)}"
        )

    d_list = deltas if deltas is not None else DRIVERS[driver_key][1]

    rows = []

    for d in d_list:
        val = _run_with_delta(cenario, driver_key, float(d), year, metric)

        rows.append(
            {
                "driver": driver_key,
                "delta": float(d),
                "ano": year,
                metric: val,
            }
        )

    return pd.DataFrame(rows)


def get_sensitivity_series(
    driver_key: str,
    metric: str = "rl",
    year: int = 2025,
    cenario: str = "Base",
) -> dict:
    """Série de resultados para a tabela de sensibilidade da UI."""
    df = one_at_a_time(
        driver_key,
        year=year,
        metric=metric,
        cenario=cenario,
    )

    base_rows = df[df["delta"] == 0]
    base_val = base_rows[metric].values[0] if not base_rows.empty else None

    series = []

    for _, row in df.iterrows():
        val = row[metric]
        diff_pct = ((val - base_val) / base_val * 100) if base_val else 0.0

        series.append(
            {
                "delta": row["delta"],
                "value": val,
                "diff_pct": round(diff_pct, 2),
            }
        )

    if len(series) > 1 and base_val:
        vals = [s["value"] for s in series]
        delta_range = max(df["delta"]) - min(df["delta"])

        sensitivity = (
            (max(vals) - min(vals)) / delta_range
            if delta_range
            else 0.0
        )

        sensitivity_pct = sensitivity / base_val * 100
    else:
        sensitivity_pct = 0.0

    return {
        "series": series,
        "sensitivity": round(sensitivity_pct, 2),
        "base_value": base_val,
    }


def tornado(
    year: int = 2025,
    metric: str = "rl",
    cenario: str = "Base",
    swing: float | None = None,
) -> pd.DataFrame:
    """Dados para gráfico tornado."""
    base_val = _run_with_delta(cenario, "volume_vn", 0.0, year, metric)

    rows = []

    for key, cfg in DRIVERS.items():
        deltas = cfg[1]

        low_d = -abs(float(swing)) if swing is not None else min(deltas)
        high_d = abs(float(swing)) if swing is not None else max(deltas)

        low_val = _run_with_delta(cenario, key, low_d, year, metric)
        high_val = _run_with_delta(cenario, key, high_d, year, metric)

        rows.append(
            {
                "driver": key,
                "label": cfg[0],
                "delta_low": low_d,
                "delta_high": high_d,
                f"{metric}_low": low_val,
                f"{metric}_base": base_val,
                f"{metric}_high": high_val,
                "impacto_total": abs(high_val - low_val),
            }
        )

    return (
        pd.DataFrame(rows)
        .sort_values("impacto_total", ascending=False)
        .reset_index(drop=True)
    )


def sensitivity_2d(
    driver_x: str,
    driver_y: str,
    deltas_x: Sequence[float] | None = None,
    deltas_y: Sequence[float] | None = None,
    year: int = 2025,
    metric: str = "rl",
    cenario: str = "Base",
) -> pd.DataFrame:
    """Tabela de sensibilidade 2D."""
    if driver_x not in DRIVERS:
        raise ValueError(f"Unknown driver_x '{driver_x}'. Choose from: {list(DRIVERS)}")

    if driver_y not in DRIVERS:
        raise ValueError(f"Unknown driver_y '{driver_y}'. Choose from: {list(DRIVERS)}")

    dx = deltas_x if deltas_x is not None else DRIVERS[driver_x][1]
    dy = deltas_y if deltas_y is not None else DRIVERS[driver_y][1]

    rows = []

    for d_x in dx:
        for d_y in dy:
            a, b, s = _inputs_load(cenario=cenario)

            DRIVERS[driver_x][2](a, b, s, float(d_x))
            DRIVERS[driver_y][2](a, b, s, float(d_y))

            dr = statements.build_dr(a, b, s)
            bal = statements.build_balanco(a, b, s, dr)
            dfc = statements.build_dfc(a, dr, bal, s, b)

            if metric in dr.columns:
                val = float(dr[dr.ano == year].iloc[0][metric])
            elif metric in bal.columns:
                val = float(bal[bal.ano == year].iloc[0][metric])
            elif metric in dfc.columns:
                val = float(dfc[dfc.ano == year].iloc[0][metric])
            else:
                val = float("nan")

            rows.append(
                {
                    driver_x: float(d_x),
                    driver_y: float(d_y),
                    metric: val,
                }
            )

    df = pd.DataFrame(rows)

    return df.pivot(
        index=driver_y,
        columns=driver_x,
        values=metric,
    )


def sensitivity_2025_volume(
    deltas=(-0.05, -0.025, 0.0, 0.025, 0.05),
) -> pd.DataFrame:
    """Sensibilidade 2025 ao volume de vendas."""
    return one_at_a_time(
        "volume_vn",
        deltas=deltas,
        year=2025,
        metric="rl",
    )


def sensitivity_2025_irc(
    taxas=(0.17, 0.20, 0.21, 0.23, 0.25),
) -> pd.DataFrame:
    """Sensibilidade 2025 à taxa de IRC."""
    base_irc = float(_inputs_load()[0].raw["impostos"]["IRC_taxa_geral"])

    deltas = [
        float(t) - base_irc
        for t in taxas
    ]

    df = one_at_a_time(
        "irc_taxa",
        deltas=deltas,
        year=2025,
        metric="rl",
    )

    df["irc_taxa"] = [
        base_irc + d
        for d in df["delta"]
    ]

    return df[["irc_taxa", "ano", "rl"]]


def sensitivity_juros(
    deltas=(-0.005, 0.0, 0.005, 0.01),
) -> pd.DataFrame:
    """Sensibilidade 2025 a choque de juros/Euribor."""
    return one_at_a_time(
        "euribor",
        deltas=deltas,
        year=2025,
        metric="rl",
    )


# ── API de sensibilidade para o frontend (endpoint único) ──────────────────

_UI_VARS_STD = [
    ("vol",     "volume_vn",    "Volume de Vendas",  "pp", 0.030),
    ("preco",   "preco_vendas", "Preço de Venda",    "pp", 0.030),
    ("fse",     "fse_pct_vn",   "FSE",               "pp", 0.030),
    ("pessoal", "pessoal_cresc","Gastos c/ Pessoal", "pp", 0.035),
    ("cmvmc",   "cmvmc_pct_vn", "CMVMC",             "pp", 0.030),
]

_UI_VARS_HUB = [
    ("hub_poupanca", "hub_poupanca", "Hub · Poupança Op.",    "%", 480_000),
    ("hub_quebras",  "hub_quebras",  "Hub · Redução Quebras", "%",  80_000),
]

_STEPS_STD = [-0.03, -0.02, -0.01, 0.0, 0.01, 0.02, 0.03]
_STEPS_HUB = [-0.30, -0.15, 0.0, 0.15, 0.30]


def _run_metrics_2025(
    cenario: str,
    driver_key: str | None,
    delta: float,
    hub_on: bool = False,
) -> dict:
    """Executa o modelo e devolve {vn, ebitda, margem_ebitda, rl} para 2025."""
    a, b, s = _inputs_load(cenario=cenario)

    a.raw.setdefault("hub_logistico", {})["incluir_hub"] = hub_on

    if driver_key is not None:
        DRIVERS[driver_key][2](a, b, s, delta)

    dr = statements.build_dr(a, b, s)
    row = dr[dr.ano == 2025]

    if row.empty:
        return {"vn": 0.0, "ebitda": 0.0, "margem_ebitda": 0.0, "rl": 0.0}

    r = row.iloc[0]

    def _g(col: str) -> float:
        return float(r[col]) if col in r.index else 0.0

    vn = _g("vn")
    ebitda = _g("ebitda")
    return {
        "vn": vn,
        "ebitda": ebitda,
        "margem_ebitda": ebitda / vn if vn else 0.0,
        "rl": _g("rl"),
    }


def sensitivity_ui(cenario: str = "Base", hub_on: bool = False) -> dict:
    """Análise de sensibilidade completa para a UI — executa tudo no backend."""
    base = _run_metrics_2025(cenario, None, 0.0, hub_on)

    all_vars = list(_UI_VARS_STD)
    if hub_on:
        all_vars.extend(_UI_VARS_HUB)

    variables: dict = {}
    for fe_key, be_key, label, unit, base_rate in all_vars:
        is_hub = fe_key in ("hub_poupanca", "hub_quebras")
        steps_list = _STEPS_HUB if is_hub else _STEPS_STD
        steps = []
        for delta in steps_list:
            m = _run_metrics_2025(cenario, be_key, delta, hub_on)
            steps.append({"delta": delta, **m})
        variables[fe_key] = {
            "label": label,
            "unit": unit,
            "base_rate": base_rate,
            "steps": steps,
        }

    return {"base": base, "variables": variables}
