"""Módulo: engine/produção.py — Orçamento de Produção (CIIP por produto)."""
# CIP unitário lido de master/produtos.yaml (MPSC + MOD + GGF por unidade).
# Calibrado ao CIIP_Produtos_2024 auditado (R&C) para garantir coerência histórica.
# cups_por_produto_2024 (MPSC) mantido para cmvmc.py/DR; cups_ciip_por_produto_2024
# (CIIP completo) usado no orçamento de produção.
from __future__ import annotations

import pandas as pd

from ..inputs import Assumptions, Base2024, Schedules, YEARS, ALL_YEARS, PRODUTOS, MESES


def _cip_unitarios(a: Assumptions) -> dict[str, float]:
    """CIP unitário por produto lido do catálogo master/produtos.yaml."""
    families = a.product_families
    return {
        p: float((families.get(p) or {}).get("cip_unitario", 0.0))
        for p in PRODUTOS
    }


def _qty_totais_2024(a: Assumptions, base: Base2024) -> dict[str, float]:
    """Quantidade total 2024 por produto."""
    from .vendas import _qty_2024_mixed

    return _qty_2024_mixed(a, base).groupby("produto")["qtd_2024"].sum().to_dict()


def _fator_calibracao_2024(a: Assumptions, base: Base2024) -> float:
    """Fator que escala os cip_unitario ao CMVMC_prod_2024 auditado.

    Garante que Σ(qty × cip_unitario × fator) == CMVMC_prod_2024,
    preservando a coerência com as demonstrações financeiras históricas.
    """
    cmvmc_prod = (
        float(base.raw["dr_2024_real"]["cmvmc"])
        - float(base.totais["CMVMC_Mercadorias_2024"])
    )

    qtd = _qty_totais_2024(a, base)
    cip = _cip_unitarios(a)

    denom = sum(qtd.get(p, 0.0) * cip[p] for p in PRODUTOS)

    return cmvmc_prod / denom if denom > 0 else 1.0


def cup_base_2024(a: Assumptions, base: Base2024) -> float:
    """Fator de calibração MPSC 2024 (usado por cmvmc.py para a linha CMVMC da DR)."""
    return _fator_calibracao_2024(a, base)


def _fator_calibracao_ciip_2024(a: Assumptions, base: Base2024) -> float:
    """Fator que escala os cip_unitario ao CIIP_Produtos_2024 auditado (MPSC+MOD+GGF).

    Garante que Σ(qty × cip_unitario × fator) == CIIP_Produtos_2024,
    onde CIIP inclui matérias consumidas, mão-de-obra direta e gastos gerais de fabrico.
    """
    ciip_prod = float(base.totais.get("CIIP_Produtos_2024", 0.0))
    if ciip_prod == 0:
        # Fallback se CIIP não estiver no YAML: MPSC + MOD (75% gastos pessoal)
        mpsc = (
            float(base.raw["dr_2024_real"]["cmvmc"])
            - float(base.totais["CMVMC_Mercadorias_2024"])
        )
        mod = float(base.raw["dr_2024_real"]["gastos_pessoal"]) * 0.75
        ciip_prod = mpsc + mod

    qtd = _qty_totais_2024(a, base)
    cip = _cip_unitarios(a)
    denom = sum(qtd.get(p, 0.0) * cip[p] for p in PRODUTOS)
    return ciip_prod / denom if denom > 0 else 1.0


def cups_ciip_por_produto_2024(a: Assumptions, base: Base2024) -> dict[str, float]:
    """CUP completo (CIIP = MPSC+MOD+GGF) calibrado por produto para 2024.

    cup_ciip[p] = cip_unitario[p] × fator_ciip
    Usado no orçamento de produção; NÃO usar na linha CMVMC da DR.
    """
    fator = _fator_calibracao_ciip_2024(a, base)
    cip = _cip_unitarios(a)
    return {p: cip[p] * fator for p in PRODUTOS}


def cups_por_produto_2024(a: Assumptions, base: Base2024) -> dict[str, float]:
    """CUP calibrado por produto para 2024.

    cup[p] = cip_unitario[p] × fator_calibração
    onde fator garante que Σ(qty × cup) == CMVMC_prod_2024.
    """
    fator = _fator_calibracao_2024(a, base)
    cip = _cip_unitarios(a)
    return {p: cip[p] * fator for p in PRODUTOS}


def _mp_fraction_per_produto(a: Assumptions) -> dict[str, float]:
    """Fração de matéria-prima (MPSC) no CIP por produto, lida de estrutura_custos.MP."""
    families = a.product_families
    return {
        p: float(((families.get(p) or {}).get("estrutura_custos") or {}).get("MP", 0.30))
        for p in PRODUTOS
    }


def _cost_growth_factors(a: Assumptions) -> dict[int, float]:
    """Fator de crescimento acumulado do custo de produção por ano."""
    from .vendas import _monthly_cum_index, _monthly_rates, _saz_to_dict

    block = a.cenario_block()

    cost_block = (
        block.get("custo_mercadorias")
        or a.raw.get("crescimento_custo_mercadorias", {})
    )

    cum = _monthly_cum_index(_monthly_rates(cost_block))
    saz = _saz_to_dict(a.sazonalidade.get("PT", []))

    f_2025 = sum(
        saz[m] * cum[m]
        for m in MESES
    )

    g_yr = a.cresc_2026_2029("custo_mercadorias")

    factors: dict[int, float] = {
        2024: 1.0,
        2025: f_2025,
    }

    f = f_2025

    for y in YEARS[1:]:
        f *= 1 + g_yr[y]
        factors[y] = f

    return factors


def producao_anual(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
) -> pd.DataFrame:
    """Produção anual por produto 2024-2029 (CIIP = MPSC+MOD+GGF).

    cup representa o custo industrial completo por unidade, calibrado ao
    CIIP_Produtos_2024 auditado. NÃO confundir com CMVMC_prod da DR
    (que inclui apenas MPSC — calculado em cmvmc.py).
    """
    from .vendas import vendas_anuais

    df_v = vendas_anuais(a, base, sched)

    qty_por_ano = (
        df_v.groupby(["ano", "produto"])["qtd"]
        .sum()
        .reset_index()
        .rename(columns={"qtd": "qty_vendida"})
    )

    # PVU médio ponderado por (ano, produto) — VN / qtd agregados por mercado
    _vn_sum = df_v.groupby(["ano", "produto"])["vn"].sum()
    _qtd_sum = df_v.groupby(["ano", "produto"])["qtd"].sum().replace(0.0, float("nan"))
    pvu_por_ano = (_vn_sum / _qtd_sum).fillna(0.0).rename("pvu").reset_index()

    # Bottom-up para todos os anos: cup = cip_unitario × factor.
    # 2024: factor=1.0, logo cup == cip_unitario (valor auditado dos pressupostos).
    # 2025+: cup = cip_unitario × factor de crescimento acumulado.
    cips = _cip_unitarios(a)

    factors = _cost_growth_factors(a)
    dmi_pa = a.prazos["DMI_PA_dias"]

    qtd_2024 = _qty_totais_2024(a, base)

    peso_total = sum(
        cips[p] * qtd_2024.get(p, 0.0)
        for p in PRODUTOS
    )

    # Stock PAIC auditado 2024 — base para pa_ei proporcional por produto
    paic_ef_2024 = float(base.totais.get("PAIC_EF_2024", 0.0))
    if paic_ef_2024 == 0:
        ciip = float(base.totais.get("CIIP_Produtos_2024", peso_total))
        paic_ef_2024 = (ciip / 365.0) * float(dmi_pa)

    rows = []
    pa_ef_prev: dict[str, float] = {}

    for y in ALL_YEARS:
        f = factors[y]

        for p in PRODUTOS:
            cup = cips[p] * f

            mask = (
                (qty_por_ano["ano"] == y)
                & (qty_por_ano["produto"] == p)
            )

            qty_v = (
                float(qty_por_ano[mask]["qty_vendida"].iloc[0])
                if mask.any()
                else 0.0
            )

            cmvmc_v = qty_v * cup
            pa_ef = (cmvmc_v / 365.0) * dmi_pa

            if y == 2024:
                peso_p = (
                    (cips[p] * qtd_2024.get(p, 0.0)) / peso_total
                    if peso_total > 0
                    else 0.0
                )

                pa_ei = paic_ef_2024 * peso_p
            else:
                pa_ei = pa_ef_prev.get(p, pa_ef)

            var_pa = pa_ef - pa_ei
            cmvmc_p = max(0.0, cmvmc_v + var_pa)

            qty_prod = cmvmc_p / cup if cup > 0 else 0.0

            pa_ef_prev[p] = pa_ef

            pvu_mask = (pvu_por_ano["ano"] == y) & (pvu_por_ano["produto"] == p)
            pvu_val = (
                float(pvu_por_ano.loc[pvu_mask, "pvu"].iloc[0])
                if pvu_mask.any()
                else 0.0
            )

            rows.append(
                {
                    "ano": y,
                    "produto": p,
                    "qty_vendida": qty_v,
                    "qty_produzida": qty_prod,
                    "cup": cup,
                    "pvu": pvu_val,
                    "cip_unitario": _cip_unitarios(a)[p],
                    "cmvmc_vendas": cmvmc_v,
                    "cmvmc_prod": cmvmc_p,
                    "pa_stock_ei": pa_ei,
                    "pa_stock_ef": pa_ef,
                    "var_pa": var_pa,
                }
            )

    return pd.DataFrame(rows)


def producao_mensal_2025(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
) -> pd.DataFrame:
    """Produção mensal 2025 por produto."""
    df_anual = producao_anual(a, base, sched)
    df_2025 = df_anual[df_anual["ano"] == 2025]

    saz = a.sazonalidade.get("PT", [])

    if isinstance(saz, list):
        saz = {
            m: saz[i]
            for i, m in enumerate(MESES)
        }

    rows = []

    for _, r in df_2025.iterrows():
        for m in MESES:
            rows.append(
                {
                    "mes": m,
                    "produto": r["produto"],
                    "qty_produzida": r["qty_produzida"] * saz[m],
                    "cmvmc_prod": r["cmvmc_prod"] * saz[m],
                    "cup": r["cup"],
                    "cip_unitario": r["cip_unitario"],
                }
            )

    return pd.DataFrame(rows)
