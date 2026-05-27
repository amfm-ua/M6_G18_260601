# -*- coding: utf-8 -*-
"""
Script de diagnostico: outputs do modelo vs. relatorio OE4.
Uso: python _compare_outputs.py
"""
from __future__ import annotations
import sys, os
from pathlib import Path

# force UTF-8 output on Windows
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "src"))

from engine.projetos.hub_logistico.base import load
from engine.projetos.hub_logistico.viabilidade import viabilidade_hub
from engine.projetos.hub_logistico.impacto import hub_fcf


def run():
    hub = load()
    proj = hub["projeto_hub"]
    via  = proj["viabilidade"]
    irc_taxa = float(via.get("irc_taxa", 0.225))
    wacc     = float(via["wacc"])

    SEP = "=" * 64

    print(f"\n{SEP}")
    print(f"  WACC configurado : {wacc*100:.2f}%   IRC : {irc_taxa*100:.1f}%")
    print(f"{SEP}\n")

    # ── Modelo ATUAL ─────────────────────────────────────────────────────────
    res = viabilidade_hub(hub=hub, irc_taxa=irc_taxa, wacc=wacc)

    print("MODELO ATUAL (codigo):")
    print(f"  VAL  @ {wacc*100:.1f}%  : {(res['val'] or 0)/1e6:+.3f} M EUR")
    print(f"  TIR             : {(res['tir'] or 0)*100:.2f}%")
    print(f"  Payback simples : {res['payback_simples']:.2f} anos" if res['payback_simples'] else "  Payback simples : N/A")
    print(f"  Payback atual.  : {res['payback_atualizado']:.2f} anos" if res['payback_atualizado'] else "  Payback atual.  : N/A")
    print(f"  Valor Terminal  : {(res['valor_terminal'] or 0)/1e3:.0f} kEUR")
    print(f"  Valor Residual Ativos: {(res['valor_residual_ativos'] or 0)/1e3:.0f} kEUR")
    print(f"  NFM recovery    : {(res['nfm_recovery_terminal'] or 0)/1e3:.0f} kEUR")

    # ── FCF detalhado por ano ─────────────────────────────────────────────────
    df = hub_fcf(hub, irc_taxa=irc_taxa)
    print("\nFCF por ano (modelo, anos de projecao base):")
    print(f"{'Ano':>5} {'EBIT_trib':>12} {'RFAI':>10} {'NOPAT':>12} "
          f"{'Dep':>10} {'PT030_3a':>10} {'PT030_cash':>12} {'FCF':>12}")
    for _, r in df.iterrows():
        print(f"{int(r['ano']):>5} "
              f"{r['ebit_tributavel']:>12,.0f} "
              f"{r.get('rfai_credito', 0):>10,.0f} "
              f"{r['nopat']:>12,.0f} "
              f"{r['depreciacao']:>10,.0f} "
              f"{r['pt2030_3a']:>10,.0f} "
              f"{r.get('pt2030_cash', 0):>12,.0f} "
              f"{r['fcf_livre']:>12,.0f}")

    print(f"\n  FCF total (sem VT) : {df['fcf_livre'].sum()/1e3:.0f} kEUR")

    # ── Cashflows finais (com VT) ─────────────────────────────────────────────
    cfs = res["cashflows_val"]
    print(f"\nCashflows com Valor Terminal (ultimos 3 anos):")
    anos_full = list(res["fcf_df"]["ano"].astype(int))
    for i, (y, cf) in enumerate(zip(anos_full, cfs)):
        if i >= len(anos_full) - 3:
            print(f"  {y}: {cf/1e3:,.0f} kEUR")

    # ── Referencia OE4 ────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("RELATORIO OE4 (referencia):")
    print(f"  VAL  @ {wacc*100:.1f}%  :  +2.760 kEUR  (~2,76 M EUR)")
    print(f"  TIR             :  17.70%")
    print(f"  Payback simples :  6.10 anos")
    print(f"  Payback atual.  :  7.29 anos")

    # ── Delta ─────────────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("DELTA (Modelo - Relatorio):")
    dv  = (res["val"] or 0) - 2_760_000
    dt  = ((res["tir"] or 0) - 0.177) * 100
    dp  = (res["payback_simples"] or 0)  - 6.10  if res["payback_simples"]  else None
    dpa = (res["payback_atualizado"] or 0) - 7.29 if res["payback_atualizado"] else None
    print(f"  Delta VAL             : {dv/1e6:+.3f} M EUR")
    print(f"  Delta TIR             : {dt:+.2f} pp")
    if dp  is not None: print(f"  Delta Payback simpl.  : {dp:+.2f} anos")
    if dpa is not None: print(f"  Delta Payback atual.  : {dpa:+.2f} anos")

    # ── Decomposicao do desvio (PV dos 3 elementos) ───────────────────────────
    print(f"\n{SEP}")
    print("DECOMPOSICAO DO DESVIO (PV estimado a WACC):")
    # PT2030 cash-in: 2.700.000 em t=2027 (ano 3 do projeto, 2025 = t=1)
    pv_pt2030_cash = 2_700_000 / (1 + wacc)**3
    # RFAI: somado do dataframe
    rfai_total_pv = sum(
        float(df[df.ano == y]["rfai_credito"].iloc[0]) / (1 + wacc)**(y - 2024)
        for y in df["ano"].astype(int)
        if not df[df.ano == y]["rfai_credito"].empty
    )
    print(f"  1. PT2030 cash-in (PV, t=2027)    : +{pv_pt2030_cash/1e3:.0f} kEUR  (origem 1)")
    print(f"  2. RFAI no NOPAT  (PV, 2026-2029) : +{rfai_total_pv/1e3:.0f} kEUR  (origem 2)")
    print(f"  Soma estimada                      : +{(pv_pt2030_cash+rfai_total_pv)/1e3:.0f} kEUR")
    print(f"  Delta VAL observado                : {dv/1e3:+.0f} kEUR")
    print(f"\n{SEP}\n")


if __name__ == "__main__":
    run()
