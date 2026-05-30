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
    """Fator de crescimento acumulado do custo de produção por ano.

    Nota: custo_mercadorias está em INFLATION_LINKED_DRIVERS (Filosofia B),
    pelo que as taxas mensais devem ser compostas com a inflação.
    """
    from .vendas import _monthly_cum_index, _monthly_rates, _saz_to_dict

    block = a.cenario_block()

    cost_block = (
        block.get("custo_mercadorias")
        or a.raw.get("crescimento_custo_mercadorias", {})
    )

    # custo_mercadorias é inflation-linked — compor inflação (Filosofia B)
    cum = _monthly_cum_index(_monthly_rates(cost_block, inflation_monthly=a.inflacao_mensal_2025()))
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
    coz_fse_reducao: "dict[int, float] | None" = None,
    energia_fabril_by_year: "dict[int, float] | None" = None,
) -> pd.DataFrame:
    """Produção anual por produto 2024-2029 (CIIP = MPSC+MOD+GGF).

    cup representa o custo industrial completo por unidade, calibrado ao
    CIIP_Produtos_2024 auditado. NÃO confundir com CMVMC_prod da DR
    (que inclui apenas MPSC — calculado em cmvmc.py).

    coz_fse_reducao: quando fornecido (toggle cozedura_on ativo), adiciona
    colunas analíticas delta_energia_unit, delta_materia_unit, cup_cozedura.

    energia_fabril_by_year: FSE de energia (gás+eletricidade, valor positivo)
    por ano. Quando fornecido, adiciona a VISTA ANALÍTICA DE ABSORÇÃO:
      - cup_variavel_unit / cup_fixo_unit: decomposição fixo/variável do CIIP,
        com o custo fixo/unidade a refletir a alavancagem operacional (desce
        quando o volume sobe);
      - energia_unit: energia fabril imputada por unidade (ponderada por GGF);
      - cup_absorcao (CIIP fixo+variável) e cup_energia (CIIP + energia).

    TODAS estas colunas são display-only: NÃO alteram cup, cmvmc_*, qty nem
    alimentam a DR/CMVMC/EBITDA/stock (que continuam a usar o CIIP headline).
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

    df = pd.DataFrame(rows)

    # ── Vista analítica de absorção: decomposição fixo/variável + energia ─────
    # Display-only — NÃO altera cup/cmvmc_*/qty (CIIP headline preservado).
    # Base de volume: qty_produzida (a energia consome-se ao produzir e o custo
    # fixo absorve-se sobre o que se produz). Em 2024 (factor=1, qty=qty_2024)
    # cup_absorcao == cup == cip_unitario, preservando a calibração auditada.
    if energia_fabril_by_year is not None:
        fv = a.custeio_fv
        est = a.product_families

        def _shares(p):
            ec = (est.get(p) or {}).get("estrutura_custos") or {}
            return float(ec.get("MP", 0.0)), float(ec.get("MOD", 0.0)), float(ec.get("GGF", 0.0))

        pct_var: dict[str, float] = {}
        ggf_unit: dict[str, float] = {}
        for p in PRODUTOS:
            mp_s, mod_s, ggf_s = _shares(p)
            pct_var[p] = mp_s * fv["MP"] + mod_s * fv["MOD"] + ggf_s * fv["GGF"]
            ggf_unit[p] = cips[p] * ggf_s

        en_pct = float(fv.get("energia_pct_producao", 0.40))

        qty_prod_2024 = df[df["ano"] == 2024].set_index("produto")["qty_produzida"].to_dict()
        qty_prod_idx = {
            (int(r["ano"]), r["produto"]): float(r["qty_produzida"]) for _, r in df.iterrows()
        }
        # Denominador de imputação da energia (overhead): Σ(ggf_unit × qty) por ano.
        ggf_qty_ano: dict[int, float] = {}
        for _, r in df.iterrows():
            y = int(r["ano"])
            ggf_qty_ano[y] = ggf_qty_ano.get(y, 0.0) + ggf_unit[r["produto"]] * float(r["qty_produzida"])

        var_u, fix_u, en_u, cup_abs, cup_en = [], [], [], [], []
        for _, row in df.iterrows():
            y, p, f = int(row["ano"]), row["produto"], factors[int(row["ano"])]
            qprod = qty_prod_idx.get((y, p), 0.0)
            qbase = qty_prod_2024.get(p, 0.0)

            variavel = cips[p] * pct_var[p] * f
            fixo_unit_base = cips[p] * (1.0 - pct_var[p]) * f
            # Custo fixo/unidade = pool fixo (cresce c/ inflação, não c/ volume) / volume.
            fixo = (fixo_unit_base * qbase / qprod) if qprod > 0 else fixo_unit_base

            energia_tot = en_pct * float(energia_fabril_by_year.get(y, 0.0))
            denom = ggf_qty_ano.get(y, 0.0)
            energia = energia_tot * ggf_unit[p] / denom if denom > 0 else 0.0

            var_u.append(variavel)
            fix_u.append(fixo)
            en_u.append(energia)
            cup_abs.append(variavel + fixo)
            cup_en.append(variavel + fixo + energia)

        df["cup_variavel_unit"] = var_u
        df["cup_fixo_unit"] = fix_u
        df["energia_unit"] = en_u
        df["cup_absorcao"] = cup_abs
        df["cup_energia"] = cup_en

    # ── Overlay Cozedura BT: poupança de energia − custo da pasta reformulada ──
    if coz_fse_reducao is not None:
        from ..projetos.cozedura.impacto import _ramp
        coz = a.raw.get("cozedura_baixa_temp", {})
        cmvmc_pct = float(coz.get("cmvmc_incremento_pct", 0.0))
        mp_pct = _mp_fraction_per_produto(a)

        # Quando a energia está no CUP (vista de absorção), a poupança é imputada
        # com a mesma ponderação por GGF que a energia; caso contrário, uniforme.
        ggf_unit_coz: dict[str, float] = {}
        ggf_qty_prod: dict[int, float] = {}
        if energia_fabril_by_year is not None:
            for p in PRODUTOS:
                ggf_s = float(((est.get(p) or {}).get("estrutura_custos") or {}).get("GGF", 0.0))
                ggf_unit_coz[p] = cips[p] * ggf_s
            for _, r in df.iterrows():
                y = int(r["ano"])
                ggf_qty_prod[y] = ggf_qty_prod.get(y, 0.0) + ggf_unit_coz[r["produto"]] * float(r["qty_produzida"])
        qty_per_year = df.groupby("ano")["qty_produzida"].sum().to_dict()

        base_cup_col = "cup_energia" if "cup_energia" in df.columns else "cup"

        d_en, d_mat, cup_coz = [], [], []
        for _, row in df.iterrows():
            y = int(row["ano"])
            p = row["produto"]
            fse_red = float(coz_fse_reducao.get(y, 0.0))
            ramp = _ramp(coz, y)

            if ggf_qty_prod.get(y, 0.0) > 0:
                # poupança/un = fse_red × ggf_unit[p] / Σ(ggf_unit × qty_prod)
                delta_en = fse_red * ggf_unit_coz[p] / ggf_qty_prod[y]
            else:
                qty_y = qty_per_year.get(y, 0.0)
                delta_en = fse_red / qty_y if qty_y > 0 else 0.0

            cup_mpsc = cips[p] * mp_pct[p] * factors[y]
            delta_mat = ramp * cmvmc_pct * cup_mpsc
            d_en.append(delta_en)
            d_mat.append(delta_mat)
            cup_coz.append(row[base_cup_col] - delta_en + delta_mat)

        df["delta_energia_unit"] = d_en
        df["delta_materia_unit"] = d_mat
        df["cup_cozedura"] = cup_coz

    return df


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
