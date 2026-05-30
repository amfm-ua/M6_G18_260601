"""Comparador de estruturas de financiamento do Hub Logístico 4.0.

Fase 1+2 (motor) — compara perfis de financiamento P0–P3 pelo VALOR que criam,
não pelo fundo perdido. O valor vem de financiar abaixo da TIR do projeto:

  1. Kd ↓ → WACC ↓ (mais peso em linhas bonificadas BEI/Garantia Mútua)
  2. Subsídio implícito da taxa bonificada (grant-equivalent) — camada APV nova
     em vala_hub, ativada por financiamento.taxa_mercado_ref.

Cada perfil é pontuado nas MESMAS métricas: Kd, Ke, WACC, VAL, VALA (decomposto),
TIR, IR, DSCR mínimo (risco) e intensidade de auxílio regional (legalidade ≤30%).

A estrutura de capital (Kd/Ke/WACC) é recalculada a partir do mix de cada perfil
— reproduz exatamente os valores do YAML base para P0 (validação):
    Ke = rf + β_u·(1+(1-t)·D/E)·ERP ; Kd = média ponderada ; WACC = wE·Ke + wD·Kd·(1-t)

Uso:  python -m tools.comparar_financiamento
"""
from __future__ import annotations

import copy
import sys

try:  # consola Windows (cp1252) não suporta €/→/× — força UTF-8
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

from src.engine.inputs import load as assumptions_load
from src.engine.operacional import vendas as vendas_mod
from src.engine.projetos.hub_logistico import (
    load as hub_load,
    viabilidade_hub,
    vala_hub,
    mapa_servico_divida,
)
from src.engine.projetos.hub_logistico.drivers import aplicar_drivers_derivados_hub

# Taxa de mercado de referência para o grant-equivalent.
# NÃO é arbitrária: é a taxa MARGINAL de dívida nova da própria Grestel,
# documentada em data/historico/2024/base.yaml → financiamento_2024.
# Taxa_variavel_estimada = Euribor 3M 2,90 % (BCE mar-2025) + spread 1,25 % = 4,15 %.
# Distingue-se do kd EMBEBIDO de 2,8 % usado na OE5 (média da carteira existente,
# puxada para baixo pelo IAPMEI a 0 % e pelo BPI legado a 2,81 %): a OE5 avalia a
# empresa COMO ESTÁ (custo médio embebido); o Hub financia dívida NOVA (custo
# marginal). As linhas bonificadas (3,70-3,85 %) batem esta taxa marginal → o
# grant-equivalent é real.
TAXA_MERCADO_REF = 0.0415

CAPEX = 6_000_000
RFAI_TAXA = 0.225            # crédito gerado = 1,35 M€ (auxílio regional)
SUBSIDIO_REGIONAL = 0        # PT2030 fundo perdido = 0 (base prudente)
TETO_REGIONAL = 0.30         # mapa de auxílios — grande empresa, Aveiro/Centro

# ── P4 · Upside Apoios — apoios FORA do teto regional (categorias RGIC distintas)
# Acessíveis a grande empresa e cumuláveis com o RFAI sem consumir os 30 %:
#   • Ambiental (RGIC art. 38/41 — eficiência energética / renováveis):
#     Sustentável 2030 / SI Transição Climática. Fundo perdido.
#   • I&D (SIFIDE II, CFI art. 35.º-42.º): crédito fiscal sobre despesa de I&D.
# Pressupostos CONSERVADORES — a confirmar com o aviso/candidatura concretos.
APOIO_AMBIENTAL = {
    "capex_elegivel": 270_000,   # pool energia_solar (200 kWp + bateria 50 kWh)
    "taxa": 0.30,                # grande empresa, base prudente (art. 41 admite mais)
    "ano_recebimento": 2027,
    "vida_util_anos": 20,        # NCRF 22: reconhecimento ao longo da vida do ativo solar
}
SIFIDE = {
    # Fração de I&D GENUÍNA (desenvolvimento experimental) dos pools digitais:
    # modelos de visão IA no picking (wms_software) + ML preditivo (Digital Twin)
    # + integração experimental. Conservador: ~300 k€ dos ~795 k€ digitais.
    "base_elegivel_capex": 300_000,
    "ano_capex": 2026,
    "opex_anual": 50_000,                 # técnico IA/MLOps interno (custo de I&D)
    "anos_opex": [2026, 2027, 2028, 2029],
    "taxa_base": 0.325,                   # SIFIDE II — taxa base (sem majoração incremental)
}


def _tranche(montante, taxa, desembolso):
    """Constrói uma tranche com amortização linear a 10 anos a partir de 2028."""
    return {
        "montante": montante,
        "taxa_juro": taxa,
        "amortizacao_anual": round(montante / 10, 2),
        "inicio_amortizacao": 2028,
        "desembolso": desembolso,
    }


# ── Perfis ───────────────────────────────────────────────────────────────────
# Espectro do conservador (P3) ao alavancado (P2); P0 base, P1 "free lunch".
PERFIS = {
    "P0 · Base atual": {
        "nota": "BEI 1,8 + Fomento/GM 1,7 + Comercial 1,0 · 75/25",
        "equity": 1_500_000,
        "tranches": {
            "Linha_BEI":        _tranche(1_800_000, 0.0370, 2026),
            "Linha_Fomento_GM": _tranche(1_700_000, 0.0385, 2025),
            "Banco_Comercial":  _tranche(1_000_000, 0.0415, 2025),
        },
    },
    "P1 · Sem dívida comercial": {
        "nota": "comercial → bonificadas · mesmo leverage 75/25 (Kd↓ a risco igual)",
        "equity": 1_500_000,
        "tranches": {
            "Linha_BEI":        _tranche(2_300_000, 0.0370, 2026),
            "Linha_Fomento_GM": _tranche(2_200_000, 0.0385, 2025),
        },
    },
    "P2 · Mais alavancagem (80/20)": {
        "nota": "dívida 4,8 / equity 1,2 · tudo bonificado · WACC↓ vs DSCR/Ke↑",
        "equity": 1_200_000,
        "tranches": {
            "Linha_BEI":        _tranche(2_500_000, 0.0370, 2026),
            "Linha_Fomento_GM": _tranche(2_300_000, 0.0385, 2025),
        },
    },
    "P3 · Conservador (70/30)": {
        "nota": "dívida 4,2 / equity 1,8 · WACC↑ mas DSCR/autonomia↑",
        "equity": 1_800_000,
        "tranches": {
            "Linha_BEI":        _tranche(1_800_000, 0.0370, 2026),
            "Linha_Fomento_GM": _tranche(1_600_000, 0.0385, 2025),
            "Banco_Comercial":  _tranche(  800_000, 0.0415, 2025),
        },
    },
}


def _estrutura(tranches: dict, equity: float, via: dict) -> dict:
    """Recalcula Kd, Ke, WACC a partir do mix (reproduz o YAML base em P0)."""
    rf = float(via["rf"])
    erp = float(via["erp"])
    beta_u = float(via["beta_u"])
    t = float(via["irc_taxa"])

    divida = sum(tr["montante"] for tr in tranches.values())
    kd = sum(tr["montante"] * tr["taxa_juro"] for tr in tranches.values()) / divida
    de = divida / equity
    beta_l = beta_u * (1 + (1 - t) * de)
    ke = rf + beta_l * erp
    v = divida + equity
    wacc = (equity / v) * ke + (divida / v) * kd * (1 - t)
    return {"kd": kd, "ke": ke, "wacc": wacc, "divida": divida,
            "equity": equity, "de": de, "beta_l": beta_l}


def _hub_base() -> dict:
    """Hub no cenário Base com drivers derivados populados (= dashboard)."""
    a, base, sched = assumptions_load(cenario="Base")
    df_prod = vendas_mod.vendas_anuais(a, base, sched)
    df_merc = vendas_mod.vendas_mercadorias_anuais(a, base)
    df_total = vendas_mod.resumo_anual(df_prod, df_merc)
    return aplicar_drivers_derivados_hub(
        a, base, sched, df_prod=df_prod, df_merc=df_merc, df_total=df_total,
        hub=copy.deepcopy(a.raw.get("hub_logistico", hub_load())),
    )


def _aplicar_perfil(hub_base: dict, perfil: dict) -> tuple[dict, dict]:
    """Devolve (hub com o perfil aplicado, estrutura de capital calculada)."""
    hub = copy.deepcopy(hub_base)
    proj = hub["projeto_hub"]
    via = proj["viabilidade"]

    est = _estrutura(perfil["tranches"], perfil["equity"], via)

    # Substituir as tranches de dívida (preservar PT2030 e taxa_mercado_ref)
    fin = proj["financiamento"]
    pt2030 = fin.get("PT2030")
    proj["financiamento"] = dict(perfil["tranches"])
    if pt2030 is not None:
        proj["financiamento"]["PT2030"] = pt2030
    proj["financiamento"]["taxa_mercado_ref"] = TAXA_MERCADO_REF

    # Injetar a estrutura de capital recalculada
    via["kd"] = est["kd"]
    via["ke"] = est["ke"]
    via["wacc"] = est["wacc"]
    via["equity_inicial"] = est["equity"]
    return hub, est


def _dscr_min(hub: dict) -> float | None:
    df = mapa_servico_divida(hub)
    pos = [r for r in df.to_dict("records")
           if not r["periodo_carencia"] and r["dscr_hub"] and r["dscr_hub"] > 0]
    return min(r["dscr_hub"] for r in pos) if pos else None


def _t(ano: int) -> int:
    """Período de desconto (t=1 para 2025, convenção fim-de-período do motor)."""
    return ano - 2025 + 1


def _pv_apoio_ambiental(rf: float, t_irc: float) -> dict:
    """Fundo perdido ambiental, líquido do IRC sobre o reconhecimento NCRF 22.

    Estruturalmente igual ao PT2030 (cash-in num ano − drag de IRC ao longo da
    vida do ativo), mas é auxílio AMBIENTAL — NÃO conta para o teto regional.
    """
    g = APOIO_AMBIENTAL["capex_elegivel"] * APOIO_AMBIENTAL["taxa"]
    ano_rec = APOIO_AMBIENTAL["ano_recebimento"]
    vida = APOIO_AMBIENTAL["vida_util_anos"]
    pv_cash = g / (1 + rf) ** _t(ano_rec)
    # Reconhecimento linear NCRF 22 sobre a vida do ativo, dentro do horizonte 2034
    pv_drag = sum(
        (g / vida) * t_irc / (1 + rf) ** _t(y)
        for y in range(ano_rec, 2035)
    )
    net = pv_cash - pv_drag
    return {"grant": g, "pv_cash": pv_cash, "pv_drag_irc": pv_drag, "pv_net": net}


def _pv_sifide(rf: float) -> dict:
    """SIFIDE II — crédito fiscal de I&D, VA a rf.

    Crédito sobre CAPEX de I&D (one-time) + sobre OPEX de I&D anual. Absorvível
    ao nível do IRC do GRUPO (não só do Hub), com carry-forward — assume-se
    absorção plena (conservador no horizonte). Categoria I&D: fora do teto regional.
    """
    tx = SIFIDE["taxa_base"]
    cred_capex = tx * SIFIDE["base_elegivel_capex"]
    pv = cred_capex / (1 + rf) ** _t(SIFIDE["ano_capex"])
    pv_opex = 0.0
    for y in SIFIDE["anos_opex"]:
        pv_opex += (tx * SIFIDE["opex_anual"]) / (1 + rf) ** _t(y)
    return {"credito_capex": cred_capex, "pv_capex": pv,
            "pv_opex": pv_opex, "pv_total": pv + pv_opex}


def main() -> None:
    hub_base = _hub_base()
    intensidade_reg = (RFAI_TAXA * CAPEX + SUBSIDIO_REGIONAL) / CAPEX
    legal = "✅ legal" if intensidade_reg <= TETO_REGIONAL else "❌ ILEGAL"

    linhas = []
    for nome, perfil in PERFIS.items():
        hub, est = _aplicar_perfil(hub_base, perfil)
        viab = viabilidade_hub(hub)
        vala = vala_hub(hub)
        dscr = _dscr_min(hub)
        soft = vala["pv_soft_loan"]
        linhas.append({
            "nome": nome, "nota": perfil["nota"], "est": est, "viab": viab,
            "vala": vala, "dscr": dscr, "soft": soft,
        })

    p0_val = linhas[0]["viab"]["val"]
    p0_vala = linhas[0]["vala"]["vala"]

    print("=" * 92)
    print("COMPARADOR DE ESTRUTURAS DE FINANCIAMENTO — Hub Logístico 4.0 (cenário Base)")
    print(f"CAPEX {CAPEX/1e6:.1f} M€ · taxa de mercado de referência (grant-equiv.) "
          f"{TAXA_MERCADO_REF:.2%}")
    print(f"Auxílio regional (RFAI {RFAI_TAXA:.1%} + subsídio {SUBSIDIO_REGIONAL/1e6:.1f}M) "
          f"= {intensidade_reg:.1%} do CAPEX → {legal} (teto {TETO_REGIONAL:.0%})")
    print("  nota: o subsídio implícito da taxa bonificada NÃO é auxílio regional —")
    print("        não consome o teto de 30 % (benefício de financiamento, não estatal).")
    print("=" * 92)

    hdr = (f"{'Perfil':<30}{'Kd':>7}{'WACC':>8}{'Ke':>8}"
           f"{'VAL':>11}{'VALA':>11}{'TIR':>7}{'IR':>6}{'DSCRmin':>9}")
    print(hdr)
    print("-" * 92)
    for L in linhas:
        e, v, va = L["est"], L["viab"], L["vala"]
        dscr = f"{L['dscr']:.2f}×" if L["dscr"] else "—"
        print(f"{L['nome']:<30}"
              f"{e['kd']:>6.2%}{e['wacc']:>8.2%}{e['ke']:>8.2%}"
              f"{v['val']:>11,.0f}{va['vala']:>11,.0f}"
              f"{v['tir']:>6.1%}{v['indice_rendibilidade']:>6.2f}{dscr:>9}")
    print("-" * 92)

    print("\nΔ face a P0 (criação/destruição de valor):")
    for L in linhas[1:]:
        dval = L["viab"]["val"] - p0_val
        dvala = L["vala"]["vala"] - p0_vala
        print(f"  {L['nome']:<30} ΔVAL {dval:>+10,.0f}   ΔVALA {dvala:>+10,.0f}")

    print("\nGrant-equivalent da taxa bonificada (camada APV nova, VA a rf, líq. imposto):")
    for L in linhas:
        bt = L["vala"]["soft_loan_por_tranche"]
        det = " · ".join(
            f"{k.replace('_', ' ')} {d['pv_grant_equivalent']/1e3:.1f}k"
            for k, d in bt.items() if d["spread"] > 0
        ) or "—"
        print(f"  {L['nome']:<30} Σ {L['soft']/1e3:>6.1f} k€   ({det})")

    print("\nDecomposição APV do perfil base (P0):")
    for c in linhas[0]["vala"]["decomposicao"]:
        print(f"    {c['componente']:<40} {c['valor']:>12,.0f}")
    print(f"    {'VALA':<40} {linhas[0]['vala']['vala']:>12,.0f}")

    print("\nLeitura:")
    print("  • P1 é o 'almoço grátis': mesmo risco (75/25) que P0, WACC mais baixo só")
    print("    por trocar dívida comercial por bonificada → ΔVAL>0 sem aumentar alavancagem.")
    print("  • P2 baixa o WACC ainda mais (80/20) mas sobe Ke e aperta o DSCR — trade-off.")
    print("  • P3 é o contrário: mais caro, mas DSCR/autonomia mais folgados.")
    print("  • O grant-equivalent é valor que JÁ existe nas linhas bonificadas e que o")
    print("    plano atual não estava a contabilizar no VALA.")

    # ── P4 · Upside Apoios (ambiental + I&D, fora do teto regional) ───────────
    via0 = linhas[0]["est"]
    rf = float(hub_base["projeto_hub"]["viabilidade"]["rf"])
    t_irc = float(hub_base["projeto_hub"]["viabilidade"]["irc_taxa"])
    amb = _pv_apoio_ambiental(rf, t_irc)
    sif = _pv_sifide(rf)
    p4_extra = amb["pv_net"] + sif["pv_total"]
    p4_vala = p0_vala + p4_extra          # P4 = mix P0 + apoios não-regionais
    intensidade_p4 = (RFAI_TAXA * CAPEX + SUBSIDIO_REGIONAL) / CAPEX  # inalterada

    print("\n" + "=" * 92)
    print("P4 · UPSIDE APOIOS — fundo perdido LEGAL fora do teto regional (sobre o mix P0)")
    print("=" * 92)
    print("Estes apoios são de categorias RGIC distintas do auxílio regional, logo")
    print(f"cumulam com o RFAI 22,5 % SEM o ultrapassar (intensidade regional fica "
          f"{intensidade_p4:.1%} ≤ {TETO_REGIONAL:.0%}).")
    print("\n  Apoio AMBIENTAL (Sustentável 2030 / SI Transição Climática — RGIC art. 38/41):")
    print(f"    elegível {APOIO_AMBIENTAL['capex_elegivel']/1e3:.0f} k€ (solar 200 kWp) "
          f"× {APOIO_AMBIENTAL['taxa']:.0%} = {amb['grant']/1e3:.0f} k€ fundo perdido")
    print(f"    PV líquido (cash {amb['pv_cash']/1e3:.1f}k − IRC NCRF22 {amb['pv_drag_irc']/1e3:.1f}k) "
          f"= {amb['pv_net']/1e3:.1f} k€")
    print("\n  SIFIDE II (crédito fiscal de I&D — CFI art. 35.º-42.º):")
    print(f"    CAPEX I&D {SIFIDE['base_elegivel_capex']/1e3:.0f} k€ × {SIFIDE['taxa_base']:.1%} "
          f"= {sif['credito_capex']/1e3:.1f} k€ → PV {sif['pv_capex']/1e3:.1f}k")
    print(f"    OPEX I&D {SIFIDE['opex_anual']/1e3:.0f} k€/ano (2026-29) × {SIFIDE['taxa_base']:.1%} "
          f"→ PV {sif['pv_opex']/1e3:.1f}k")
    print(f"    PV SIFIDE total = {sif['pv_total']/1e3:.1f} k€")
    print("-" * 92)
    print(f"  {'P4 = VALA(P0)':<28}{p0_vala:>14,.0f}")
    print(f"  {'+ apoio ambiental (líq.)':<28}{amb['pv_net']:>+14,.0f}")
    print(f"  {'+ SIFIDE I&D':<28}{sif['pv_total']:>+14,.0f}")
    print(f"  {'= VALA P4':<28}{p4_vala:>14,.0f}   (ΔVALA vs P0 {p4_extra:>+,.0f})")
    print("-" * 92)
    print("Leitura P4:")
    print(f"  • Os apoios não-regionais valem ~{p4_extra/1e3:.0f} k€ de VALA — meio de")
    print("    recuperar valor SEM tocar no teto de 30 % nem na estrutura de dívida.")
    print("  • MAS está muito longe dos 1,8-2,1 M€ da nota inicial: esse número assumia")
    print("    enquadramento REGIONAL (Inovação Produtiva), inacessível a grande empresa.")
    print("  • Pressupostos conservadores e SENSÍVEIS: a elegibilidade I&D (300 k€) e a")
    print("    taxa ambiental (30 %) decidem o resultado — a confirmar com os avisos reais.")
    print("  • Stack completo possível: P1 (estrutura) + grant-equiv + P4 (apoios).")


if __name__ == "__main__":
    main()
