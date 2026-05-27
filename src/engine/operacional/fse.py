"""Módulo: engine/fse.py — Fornecimentos e Serviços Externos."""

from __future__ import annotations

import pandas as pd

from ..inputs import Assumptions, Base2024, ALL_YEARS, YEARS, DATA_DIR, MESES

import yaml


def fse_detalhe_mensal_2025(
    a: Assumptions,
    base: Base2024,
    vendas_factor_2025: float,
    dist_sazonal: dict[str, float] | None = None,
) -> dict[str, dict[str, float]]:
    """Detalhe mensal de FSE 2025 por rubrica.

    Args:
        a: Pressupostos do cenário.
        base: Dados base de 2024.
        vendas_factor_2025: Fator de crescimento das vendas em 2025.
        dist_sazonal: Distribuição mensal opcional (default: uniforme 1/12).

    Returns:
        Dict {rubrica: {mes: valor}} com custos positivos.
    """
    if dist_sazonal is None:
        dist_sazonal = {m: 1.0 / 12.0 for m in MESES}

    df_det_anual = fse_detalhe_anual(a, base, vendas_factor_2025)
    df_2025 = df_det_anual[df_det_anual.ano == 2025]
    annual_2025_by_rub = dict(zip(df_2025["rubrica"], df_2025["valor"]))

    result: dict[str, dict[str, float]] = {}

    for rubica in FSE_DETALHE_KEYS.keys():
        if rubica == "fse_total":
            continue

        val_2025 = annual_2025_by_rub.get(rubica, 0.0)
        result[rubica] = {m: val_2025 * dist_sazonal[m] for m in MESES}

    return result


_CONTRATO_FSE_YAML = (DATA_DIR / "master" / "fse_rubricas.yaml").resolve()


def _load_fse_contrato() -> tuple[dict[str, str], dict[str, str], dict[str, float]]:
    """Carrega o contrato de rubricas de FSE (YAML) com fallback compatível.

    Returns:
        (yaml_key_to_dr_col, yaml_key_to_label, yaml_key_to_pct_variavel)
    """
    _FALLBACK_PCV: dict[str, float] = {
        "Subcontratos":       1.0,
        "Eletricidade":       0.8,
        "Gas_Natural":        0.8,
        "Agua":               0.8,
        "Manutencao":         0.0,
        "Transportes_Fretes": 1.0,
        "Seguros":            0.0,
        "Comunicacoes":       0.0,
        "Honorarios":         0.0,
        "Rendas":             0.0,
        "Limpeza":            0.0,
        "Vigilancia":         0.0,
        "Outros_FSE":         0.4,
    }
    try:
        if not _CONTRATO_FSE_YAML.exists():
            raise FileNotFoundError

        with open(_CONTRATO_FSE_YAML, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        rubricas = raw.get("rubricas") or []
        map_y2col: dict[str, str] = {}
        labels: dict[str, str] = {}
        pcv: dict[str, float] = {}

        for r in rubricas:
            yaml_key = r.get("yaml_key")
            dr_col = r.get("dr_col")
            label = r.get("label")
            if not yaml_key or not dr_col:
                continue
            map_y2col[str(yaml_key)] = str(dr_col)
            if label:
                labels[str(yaml_key)] = str(label)
            pct_v = r.get("pct_variavel")
            if pct_v is not None:
                pcv[str(yaml_key)] = float(pct_v)
            else:
                pcv[str(yaml_key)] = _FALLBACK_PCV.get(str(yaml_key), 0.4)

        if not map_y2col:
            raise ValueError("Contrato FSE sem rubricas válidas")

        return map_y2col, labels, pcv
    except Exception:
        # Fallback compatibility - keeps old columns without special chars.
        return (
            {
                "Subcontratos": "fse_subcontratos",
                "Eletricidade": "fse_eletricidade",
                "Gas_Natural": "fse_gas_natural",
                "Agua": "fse_agua",
                "Manutencao": "fse_manutencao",
                "Transportes_Fretes": "fse_transportes_fretes",
                "Seguros": "fse_seguros",
                "Comunicacoes": "fse_comunicacoes",
                "Honorarios": "fse_honorarios",
                "Rendas": "fse_rendas_alugueres",
                "Limpeza": "fse_limpeza",
                "Vigilancia": "fse_vigilancia",
                "Outros_FSE": "fse_outros_fse",
            },
            {
                "Subcontratos": "Subcontratos",
                "Eletricidade": "Eletricidade",
                "Gas_Natural": "Gas Natural",
                "Agua": "Agua",
                "Manutencao": "Manutencao e Reparacao",
                "Transportes_Fretes": "Transportes e Fretes",
                "Seguros": "Seguros",
                "Comunicacoes": "Comunicacoes",
                "Honorarios": "Honorarios",
                "Rendas": "Rendas e Alugueres",
                "Limpeza": "Limpeza",
                "Vigilancia": "Seguranca e Vigilancia",
                "Outros_FSE": "Outros FSE",
            },
            _FALLBACK_PCV,
        )


FSE_DETALHE_KEYS, FSE_DETALHE_LABELS, FSE_PCV = _load_fse_contrato()
# Hub FSE net adjustment — captures hub opex and savings not in the base rubrica YAML.
# Stored in the DR as hub_fse_ajuste_liq = hub_fse_reducao - hub_fse_opex (signed).
FSE_DETALHE_KEYS["Hub_FSE_ajuste"] = "hub_fse_ajuste_liq"
FSE_DETALHE_LABELS["Hub_FSE_ajuste"] = "Hub FSE ajustamento líquido"
FSE_PCV["Hub_FSE_ajuste"] = 0.0


def fse_rubricas_ordered() -> list[tuple[str, str, str]]:
    """Devolve lista ordenada: (yaml_key, dr_col, label)."""
    try:
        if not _CONTRATO_FSE_YAML.exists():
            raise FileNotFoundError
        with open(_CONTRATO_FSE_YAML, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        rubricas = raw.get("rubricas") or []
        out: list[tuple[str, str, str]] = []
        for r in rubricas:
            yaml_key = r.get("yaml_key")
            dr_col = r.get("dr_col")
            label = r.get("label")
            if not yaml_key or not dr_col:
                continue
            out.append((str(yaml_key), str(dr_col), str(label or yaml_key)))
        return out
    except Exception:
        return [
            (k, v, FSE_DETALHE_LABELS.get(k, k))
            for k, v in FSE_DETALHE_KEYS.items()
        ]


def fse_rubricas_shares_2024(base: Base2024) -> dict[str, float]:
    """Shares (0..1) das rubricas de FSE calculadas a partir de 2024.

    Exclui `fse_total` e normaliza pelo somatório das rubricas.
    """
    raw = getattr(base, "fse_detalhe", {}) or {}
    vals: dict[str, float] = {}
    for rub_key in FSE_DETALHE_KEYS.keys():
        try:
            vals[rub_key] = float(raw.get(rub_key, 0.0))
        except Exception:
            vals[rub_key] = 0.0

    total = float(sum(vals.values()))
    if total <= 0:
        # fallback determinístico (evita divisões por zero)
        n = max(1, len(vals))
        return {k: 1.0 / n for k in vals.keys()}

    return {k: v / total for k, v in vals.items()}



def _cresc_fse_2025_efetivo(a: Assumptions) -> float:
    """Taxa anual efectiva de FSE para 2025, com suporte a acréscimos mensais.

    Se `acrescimos_mensais` não estiver definido, devolve directamente `base_2025`
    (comportamento idêntico ao anterior).  Quando está presente, calcula a taxa
    anual composta a partir dos 12 factores mensais:
        taxa_ef = ∏(1 + r_m  para m em MESES) - 1
    """
    block = a._driver_block("fse")
    acrescimos = block.get("acrescimos_mensais") or block.get("overrides_mensais") or {}

    if not acrescimos:
        # cresc_2025_anual já compõe inflação (Filosofia B)
        return a.cresc_2025_anual("fse")

    from .vendas import _monthly_rates

    # Com acréscimos mensais: compor inflação mensal sobre spread real
    rates = _monthly_rates(block, inflation_monthly=a.inflacao_mensal_2025())
    factor = 1.0
    for m in MESES:
        factor *= 1.0 + rates[m]
    return factor - 1.0


def _get_fse_2024_dr(base: Base2024) -> float:
    """Obtém o FSE real de 2024 a partir do YAML/base2024.

    Prioridade:
      1. base.raw["dr_2024_real"]["fse"]
      2. soma de base.fse_detalhe.values()

    Isto evita usar valores hardcoded no modelo.
    """
    try:
        return float(base.raw["dr_2024_real"]["fse"])
    except (AttributeError, KeyError, TypeError, ValueError):
        return float(sum(base.fse_detalhe.values()))


def fse_anual(
    a: Assumptions,
    base: Base2024,
    vendas_factor_2025: float,
) -> pd.DataFrame:
    """FSE anual 2024-2029 — total bottom-up a partir do detalhe por rubrica.

    O total de cada ano é a soma das rubricas em fse_detalhe_anual(), onde cada
    rubrica usa o seu próprio pct_variavel. 2024 usa o valor real da DR para
    preservar a consistência histórica.

    Args:
        a: Pressupostos do cenário.
        base: Dados base de 2024.
        vendas_factor_2025: Rácio VN_2025 / VN_2024.

    Returns:
        DataFrame com colunas: ano, fse.
    """
    fse_2024_dr = _get_fse_2024_dr(base)

    df_det = fse_detalhe_anual(a, base, vendas_factor_2025)
    totais = df_det.groupby("ano")["valor"].sum()

    rows = []
    for y in ALL_YEARS:
        # 2024: valor real da DR (histórico); restantes: soma bottom-up das rubricas
        fse_val = fse_2024_dr if y == 2024 else float(totais.get(y, 0.0))
        rows.append({"ano": y, "fse": fse_val})

    return pd.DataFrame(rows)


def fse_detalhe_anual(
    a: Assumptions,
    base: Base2024,
    vendas_factor_2025: float,
) -> pd.DataFrame:
    """Detalhe anual de FSE por rubrica com fator fixo/variável por rubrica.

    Cada rubrica usa o seu próprio `pct_variavel` (lido de fse_rubricas.yaml):
      - componente variável escala com `vendas_factor_2025`
      - componente fixa escala com `meses_2025 / 12`

    O total de FSE 2025+ resulta da soma bottom-up das rubricas (não é imposto
    de cima para baixo), pelo que não existe passo de reconciliação.

    Args:
        a: Pressupostos do cenário.
        base: Dados base de 2024.
        vendas_factor_2025: Rácio VN_2025 / VN_2024.

    Returns:
        DataFrame com colunas: ano, rubrica, valor.
    """
    g_fse_2025 = _cresc_fse_2025_efetivo(a)
    meses_2025 = int(a.fse_params.get("meses_2025", 12))
    fator_tempo_fixo = meses_2025 / 12.0

    # Fallback global para rubricas sem pct_variavel no YAML
    pct_prod_global = float(a.fse_params.get("pct_producao", 0.4))

    g_yr = a.cresc_2026_2029("fse")

    rows = []
    base_vals = getattr(base, "fse_detalhe", {}) or {}

    # Reconciliar os valores brutos de 2024 ao total real da DR.
    # Os valores do YAML base são estimativas que podem não somar ao DR auditado;
    # o scale garante que o detalhe fecha com o histórico e que 2025 projeta
    # a partir da base correcta.
    fse_2024_dr = _get_fse_2024_dr(base)
    sum_raw_2024 = sum(
        float(base_vals.get(rub, 0.0) or 0.0)
        for rub in FSE_DETALHE_KEYS.keys()
        if rub != "fse_total"
    )
    scale_2024 = fse_2024_dr / sum_raw_2024 if sum_raw_2024 > 0 else 1.0

    for rubica in FSE_DETALHE_KEYS.keys():
        if rubica == "fse_total":
            continue

        val_2024 = float(base_vals.get(rubica, 0.0) or 0.0) * scale_2024

        # Per-rubric fixed/variable split — com fallback para pct_producao global
        pct_var = FSE_PCV.get(rubica, pct_prod_global)
        pct_fix = 1.0 - pct_var

        factor_2025 = (1 + g_fse_2025) * (
            pct_var * vendas_factor_2025
            + pct_fix * fator_tempo_fixo
        )

        v = {
            2024: val_2024,
            2025: val_2024 * factor_2025,
        }

        for y in YEARS[1:]:
            v[y] = v[y - 1] * (1 + g_yr[y])

        for y in ALL_YEARS:
            rows.append({"ano": y, "rubrica": rubica, "valor": v[y]})

    return pd.DataFrame(rows)
