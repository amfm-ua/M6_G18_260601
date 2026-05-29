#!/usr/bin/env python3
"""
Extração de valores financeiros da Grestel (run_model) para OE5.
Corre cenário Base com hub_on=True, ecogres_on=True.
"""

import sys
import os
from pathlib import Path

# Ajusta sys.path para imports do engine
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# UTF-8
os.environ["PYTHONIOENCODING"] = "utf-8"

from engine.modelo.model import run_model
import pandas as pd

def main():
    print("=" * 80)
    print("EXTRAÇÃO OE5 — VALORES FINANCEIROS GRESTEL")
    print("=" * 80)
    print()

    # ─────────────────────────────────────────────────────────────────────────
    # 1. RUN MODEL
    # ─────────────────────────────────────────────────────────────────────────
    print("[1] Correndo run_model(cenario='Base', hub_on=True, ecogres_on=True, horizonte_maturidade=False)...")
    try:
        dfs = run_model(
            cenario="Base",
            hub_on=True,
            ecogres_on=True,
            horizonte_maturidade=False
        )
        print("     ✓ Modelo executado com sucesso.")
    except Exception as e:
        print(f"     ✗ ERRO: {e}")
        return 1

    # ─────────────────────────────────────────────────────────────────────────
    # 2. INSPEÇÃO DE ESTRUTURA
    # ─────────────────────────────────────────────────────────────────────────
    print()
    print("[2] Estrutura dos DataFrames retornados:")
    for key in dfs.keys():
        df = dfs[key]
        if isinstance(df, pd.DataFrame):
            print(f"     • {key}: {df.shape[0]} linhas, {df.shape[1]} colunas")
            if "ano" in df.columns:
                anos = sorted(df["ano"].unique())
                print(f"       Anos: {anos}")
        else:
            print(f"     • {key}: {type(df).__name__}")

    # ─────────────────────────────────────────────────────────────────────────
    # 3. EXTRAÇÃO DE DADOS
    # ─────────────────────────────────────────────────────────────────────────
    dr = dfs.get("dr")
    dfc = dfs.get("dfc")
    balanco = dfs.get("balanco")

    print()
    print("[3] Inspeção de colunas:")
    print(f"     DR: {list(dr.columns) if dr is not None else 'N/A'}")
    print(f"     DFC: {list(dfc.columns) if dfc is not None else 'N/A'}")
    print(f"     BALANCO: {list(balanco.columns) if balanco is not None else 'N/A'}")

    # Verificar presença de 2024 e 2025-2029
    if dr is not None:
        anos_dr = sorted(dr["ano"].unique())
        print(f"     Anos em DR: {anos_dr}")

    # ─────────────────────────────────────────────────────────────────────────
    # 4. EXTRAÇÃO POR CELL
    # ─────────────────────────────────────────────────────────────────────────
    print()
    print("[4] EXTRAÇÃO DE VALORES:")
    print()

    # ─ A) PRESSUPOSTOS (2024 e parâmetros únicos) ─
    print("═ FOLHA '⚙️ PRESSUPOSTOS' (valores de 2024) ═")

    # C8: Ano base (último ano real)
    c8_ano_base = 2024
    print(f"C8  (Ano base):                {c8_ano_base}")

    # C16: Taxa de imposto efetiva
    c16_tax_rate = 0.20
    print(f"C16 (Taxa imposto efetiva):    {c16_tax_rate} (20% — IRC 2024 em fiscal.yaml)")

    # C17: Custo da dívida bruto (kd)
    c17_kd = 0.028
    print(f"C17 (Custo dívida bruto kd):   {c17_kd} (2.8% — _GRESTEL_DEFAULTS valuation.py)")

    # Extrair dados de 2024 do balanço
    if balanco is not None:
        bal_2024 = balanco[balanco["ano"] == 2024]
        if not bal_2024.empty:
            # C19: Dívida financeira 2024
            empr_nc = float(bal_2024.get("emprestimos_nc", [0]).iloc[0] if "emprestimos_nc" in bal_2024.columns else 0)
            empr_c = float(bal_2024.get("emprestimos_c", [0]).iloc[0] if "emprestimos_c" in bal_2024.columns else 0)
            linha_cp = float(bal_2024.get("linha_credito_cp", [0]).iloc[0] if "linha_credito_cp" in bal_2024.columns else 0)
            c19_divida_fin = (empr_nc + empr_c + linha_cp) / 1000  # em k€
            print(f"C19 (Dívida fin 2024):         {c19_divida_fin:.1f} k€ (empr_nc + empr_c + linha_cp)")

            # C20: Capital próprio 2024
            total_cp = float(bal_2024.get("total_cp", [0]).iloc[0] if "total_cp" in bal_2024.columns else 0)
            c20_cp = total_cp / 1000  # em k€
            print(f"C20 (Capital próprio 2024):    {c20_cp:.1f} k€ (total_cp)")

            # C36: Dívida líquida 2024
            caixa = float(bal_2024.get("caixa", [0]).iloc[0] if "caixa" in bal_2024.columns else 0)
            aplic_fin = float(bal_2024.get("aplicacoes_fin_cp", [0]).iloc[0] if "aplicacoes_fin_cp" in bal_2024.columns else 0)
            caixa_total = (caixa + aplic_fin) / 1000  # em k€
            c36_divida_liquida = c19_divida_fin - caixa_total
            print(f"C36 (Dívida líquida 2024):     {c36_divida_liquida:.1f} k€ (dívida fin - caixa)")

    # C37: Número de ações (capital social / valor nominal)
    # Base.yaml: Capital_Social = 526318 €
    c37_shares = 1.0  # Simplificado: 1 ação = empresa inteira (typical para privadas)
    print(f"C37 (Nº ações em circulação): {c37_shares} (assumido para empresa privada)")

    # Extrair dados de 2024 da DR
    if dr is not None:
        dr_2024 = dr[dr["ano"] == 2024]
        if not dr_2024.empty:
            # C31: EBIT 2024
            ebit_2024 = float(dr_2024.get("ebit", [0]).iloc[0] if "ebit" in dr_2024.columns else 0)
            c31_ebit = ebit_2024 / 1000  # em k€
            print(f"C31 (EBIT 2024):               {c31_ebit:.1f} k€")

            # C32: D&A 2024 (= -depreciacoes, positivo)
            deprec_2024 = float(dr_2024.get("depreciacoes", [0]).iloc[0] if "depreciacoes" in dr_2024.columns else 0)
            c32_da = -deprec_2024 / 1000  # em k€ (deprec é negativa, então -neg = positivo)
            print(f"C32 (D&A 2024):                {c32_da:.1f} k€ (-depreciacoes)")

    # C33 e C34: CapEx e ΔNWC 2024
    if dfc is not None:
        dfc_2024 = dfc[dfc["ano"] == 2024]
        if not dfc_2024.empty:
            # C33: CapEx 2024 (soma capex_aft, pag_intang, hub_capex, valor absoluto)
            capex_aft = abs(float(dfc_2024.get("capex_aft", [0]).iloc[0] if "capex_aft" in dfc_2024.columns else 0))
            pag_intang = abs(float(dfc_2024.get("pag_intang", [0]).iloc[0] if "pag_intang" in dfc_2024.columns else 0))
            hub_capex = abs(float(dfc_2024.get("hub_capex", [0]).iloc[0] if "hub_capex" in dfc_2024.columns else 0))
            c33_capex = (capex_aft + pag_intang + hub_capex) / 1000  # em k€
            print(f"C33 (CapEx 2024):              {c33_capex:.1f} k€ (capex_aft + pag_intang + hub_capex)")

            # C34: ΔNWC 2024 (= -var_nfm)
            var_nfm_2024 = float(dfc_2024.get("var_nfm", [0]).iloc[0] if "var_nfm" in dfc_2024.columns else 0)
            c34_delta_nwc = -var_nfm_2024 / 1000  # em k€
            print(f"C34 (ΔNWC 2024):               {c34_delta_nwc:.1f} k€ (-var_nfm)")

    # C25, C26: Crescimento receita
    print()
    print("═ CRESCIMENTO RECEITA (anos 1-3 e 4-5) ═")
    if dr is not None:
        dr_proj = dr[dr["ano"].between(2025, 2029)].sort_values("ano")
        if not dr_proj.empty:
            vn_por_ano = {}
            for _, row in dr_proj.iterrows():
                ano = int(row["ano"])
                vn = float(row.get("vn", 0) or 0)
                vn_por_ano[ano] = vn

            # C25: crescimento médio 2025, 2026, 2027
            growth_1_3 = []
            for ano in [2025, 2026, 2027]:
                if ano in vn_por_ano and ano - 1 in vn_por_ano:
                    g = (vn_por_ano[ano] - vn_por_ano[ano - 1]) / vn_por_ano[ano - 1]
                    growth_1_3.append(g)
            c25_growth = sum(growth_1_3) / len(growth_1_3) if growth_1_3 else 0.0
            print(f"C25 (Crescimento avg anos 1-3): {c25_growth:.4f} ({c25_growth*100:.2f}%)")

            # C26: crescimento médio 2028, 2029
            growth_4_5 = []
            for ano in [2028, 2029]:
                if ano in vn_por_ano and ano - 1 in vn_por_ano:
                    g = (vn_por_ano[ano] - vn_por_ano[ano - 1]) / vn_por_ano[ano - 1]
                    growth_4_5.append(g)
            c26_growth = sum(growth_4_5) / len(growth_4_5) if growth_4_5 else 0.0
            print(f"C26 (Crescimento avg anos 4-5): {c26_growth:.4f} ({c26_growth*100:.2f}%)")

    # ─ B) SÉRIE DCF-FCFF (2025-2029) ─
    print()
    print("═ FOLHA '📊 DCF-FCFF' (séries 2025-2029) ═")

    if dr is not None and dfc is not None:
        dr_proj = dr[dr["ano"].between(2025, 2029)].sort_values("ano")
        anos_dcf = sorted([int(row["ano"]) for _, row in dr_proj.iterrows()])

        print(f"Anos disponíveis: {anos_dcf}")
        print()

        # Linha 9: Receita (VN)
        print("Linha 9 (Receita/VN):")
        receita_serie = {}
        for _, row in dr_proj.iterrows():
            ano = int(row["ano"])
            vn = float(row.get("vn", 0) or 0) / 1000
            receita_serie[ano] = vn
        for ano in anos_dcf:
            print(f"  {ano}: {receita_serie.get(ano, 0):.1f} k€")

        # Linha 11: EBITDA
        print("Linha 11 (EBITDA):")
        ebitda_serie = {}
        for _, row in dr_proj.iterrows():
            ano = int(row["ano"])
            ebitda = float(row.get("ebitda", 0) or 0) / 1000
            ebitda_serie[ano] = ebitda
        for ano in anos_dcf:
            print(f"  {ano}: {ebitda_serie.get(ano, 0):.1f} k€")

        # Linha 13: D&A
        print("Linha 13 (D&A):")
        da_serie = {}
        for _, row in dr_proj.iterrows():
            ano = int(row["ano"])
            deprec = -float(row.get("depreciacoes", 0) or 0) / 1000
            da_serie[ano] = deprec
        for ano in anos_dcf:
            print(f"  {ano}: {da_serie.get(ano, 0):.1f} k€")

        # Linhas 21, 22: CapEx e ΔNWC
        dfc_proj = dfc[dfc["ano"].between(2025, 2029)].sort_values("ano")

        print("Linha 21 (CapEx):")
        capex_serie = {}
        for _, row in dfc_proj.iterrows():
            ano = int(row["ano"])
            capex = (abs(float(row.get("capex_aft", 0) or 0)) +
                     abs(float(row.get("pag_intang", 0) or 0)) +
                     abs(float(row.get("hub_capex", 0) or 0))) / 1000
            capex_serie[ano] = capex
        for ano in anos_dcf:
            print(f"  {ano}: {capex_serie.get(ano, 0):.1f} k€")

        print("Linha 22 (ΔNWC):")
        nwc_serie = {}
        for _, row in dfc_proj.iterrows():
            ano = int(row["ano"])
            delta_nwc = -float(row.get("var_nfm", 0) or 0) / 1000
            nwc_serie[ano] = delta_nwc
        for ano in anos_dcf:
            print(f"  {ano}: {nwc_serie.get(ano, 0):.1f} k€")

    # ─ C) SÉRIE FCFE (2025-2029) ─
    print()
    print("═ FOLHA '💰 FCFE' (séries 2025-2029) ═")

    tax_rate = 0.20  # Parâmetro fixo

    if dr is not None and dfc is not None and balanco is not None:
        dr_proj = dr[dr["ano"].between(2025, 2029)].sort_values("ano")
        dfc_proj = dfc[dfc["ano"].between(2025, 2029)].sort_values("ano")
        balanco_proj = balanco[balanco["ano"].between(2024, 2029)].sort_values("ano")

        anos_fcfe = sorted([int(row["ano"]) for _, row in dr_proj.iterrows()])

        # Mapa de dívida financeira por ano
        debt_by_year = {}
        for _, row in balanco_proj.iterrows():
            ano = int(row["ano"])
            debt = (float(row.get("emprestimos_nc", 0) or 0) +
                    float(row.get("emprestimos_c", 0) or 0) +
                    float(row.get("linha_credito_cp", 0) or 0))
            debt_by_year[ano] = debt

        print(f"Anos disponíveis: {anos_fcfe}")
        print()

        # Linha 9: Lucro Líquido
        print("Linha 9 (Lucro Líquido / Resultado Líquido):")
        rl_serie = {}
        for _, row in dr_proj.iterrows():
            ano = int(row["ano"])
            # Procura: resultado_liquido, rl, res_liquido
            rl = None
            for col in ["resultado_liquido", "rl", "res_liquido", "lucro_liquido"]:
                if col in dr_proj.columns:
                    rl = float(row.get(col, 0) or 0)
                    break
            if rl is None:
                # Fallback: RAI - IRC
                rai = float(row.get("rai", 0) or 0)
                irc = float(row.get("irc", 0) or 0)
                rl = rai - irc
            rl_serie[ano] = rl / 1000
        for ano in anos_fcfe:
            print(f"  {ano}: {rl_serie.get(ano, 0):.1f} k€")

        # Linha 10: CapEx líquido (CapEx - D&A)
        print("Linha 10 (CapEx líquido = CapEx - D&A):")
        capex_net_serie = {}
        for ano in anos_fcfe:
            capex_net = capex_serie.get(ano, 0) - da_serie.get(ano, 0)
            capex_net_serie[ano] = capex_net
        for ano in anos_fcfe:
            print(f"  {ano}: {capex_net_serie.get(ano, 0):.1f} k€")

        # Linha 12: Nova Dívida Líquida (net borrowing)
        print("Linha 12 (Nova Dívida Líquida = ΔDívida):")
        net_borrow_serie = {}
        for ano in anos_fcfe:
            net_borrow = (debt_by_year.get(ano, 0) - debt_by_year.get(ano - 1, 0)) / 1000
            net_borrow_serie[ano] = net_borrow
        for ano in anos_fcfe:
            print(f"  {ano}: {net_borrow_serie.get(ano, 0):.1f} k€")

    # ─────────────────────────────────────────────────────────────────────────
    # 5. SANITY CHECK: FCFF 2025
    # ─────────────────────────────────────────────────────────────────────────
    print()
    print("═ SANITY CHECK: FCFF 2025 ═")
    if dr is not None and dfc is not None:
        dr_2025 = dr[dr["ano"] == 2025]
        dfc_2025 = dfc[dfc["ano"] == 2025]

        if not dr_2025.empty and not dfc_2025.empty:
            ebit_2025 = float(dr_2025.get("ebit", [0]).iloc[0] if "ebit" in dr_2025.columns else 0)
            deprec_2025 = -float(dr_2025.get("depreciacoes", [0]).iloc[0] if "depreciacoes" in dr_2025.columns else 0)

            capex_2025 = (abs(float(dfc_2025.get("capex_aft", [0]).iloc[0] if "capex_aft" in dfc_2025.columns else 0)) +
                          abs(float(dfc_2025.get("pag_intang", [0]).iloc[0] if "pag_intang" in dfc_2025.columns else 0)) +
                          abs(float(dfc_2025.get("hub_capex", [0]).iloc[0] if "hub_capex" in dfc_2025.columns else 0)))

            var_nfm_2025 = float(dfc_2025.get("var_nfm", [0]).iloc[0] if "var_nfm" in dfc_2025.columns else 0)

            nopat = ebit_2025 * (1 - tax_rate)
            fcff_2025 = nopat + deprec_2025 - capex_2025 + var_nfm_2025

            print(f"EBIT 2025: {ebit_2025/1000:.1f} k€")
            print(f"NOPAT (EBIT × (1-t)): {nopat/1000:.1f} k€ (t={tax_rate})")
            print(f"D&A 2025: {deprec_2025/1000:.1f} k€")
            print(f"CapEx 2025: {capex_2025/1000:.1f} k€")
            print(f"var_nfm 2025: {var_nfm_2025/1000:.1f} k€")
            print(f"")
            print(f"FCFF 2025 = NOPAT + D&A - CapEx + var_nfm")
            print(f"FCFF 2025 = {nopat/1000:.1f} + {deprec_2025/1000:.1f} - {capex_2025/1000:.1f} + {var_nfm_2025/1000:.1f}")
            print(f"FCFF 2025 = {fcff_2025/1000:.1f} k€")
            print()
            if abs(fcff_2025) > 0:
                print("✓ FCFF 2025 é um número plausível (não nulo).")
            else:
                print("⚠ FCFF 2025 é nulo — verificar dados.")

    print()
    print("=" * 80)
    print("FIM DA EXTRAÇÃO")
    print("=" * 80)

    return 0

if __name__ == "__main__":
    sys.exit(main())
