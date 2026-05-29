"""Plano de Contingência do Hub Logístico — rejeição dos apoios fiscais (PT2030).

Responde à questão estratégica levantada na avaliação M6:

  «O Hub não é viável sem apoios fiscais. Se o PT2030 for rejeitado, é necessário
   um plano de financiamento alternativo. A sugestão é entrada de capitais próprios
   dos donos (Grestel). Analisar e quantificar.»

Conclusão metodológica que sustenta o módulo
---------------------------------------------
O PT2030 (2.700 k€, recebido em 2027) NÃO financia a construção: o CAPEX de
6.000 k€ já está integralmente coberto por dívida (4.500 k€) + capital próprio
(1.500 k€). O subsídio é um *reembolso a fundo perdido* posterior à obra. Logo:

  • A entrada de capital próprio NÃO é necessária para construir nem (dado o
    DSCR operacional ≥ 1,5×) para servir a dívida.
  • É necessária para (i) substituir o COLATERAL que o banco perde (cessão do
    subsídio — secção 6.1.2 do plano de financiamento) e (ii) para o banco
    aceitar manter a alavancagem sem subir o spread.
  • A recapitalização baixa o Ke mas SOBE o WACC (perde-se escudo fiscal da
    dívida barata) → não restaura o valor económico. Isso só se consegue
    re-dimensionando o CAPEX (faseamento de âmbito da Fase 2).

O módulo quantifica três variantes de recapitalização + um cenário de CAPEX
faseado (Fase 1), todos sem PT2030 (RFAI mantido — regime autónomo CFI art. 22.º).

Métricas por cenário: VALA (APV) decomposto, VAL(WACC), TIR e DSCR mínimo.

Dependências: copy + módulos hub_logistico (sem libs externas).
"""
from __future__ import annotations

import copy
from typing import Any

from .hub_logistico import (
    load,
    viabilidade_hub,
    vala_hub,
    mapa_servico_divida,
)

# ---------------------------------------------------------------------------
# Definição da Fase 1 (faseamento de âmbito — diferir a Fase 2)
# ---------------------------------------------------------------------------
# Reconciliado pool a pool com m6_hub_assumptions.yaml. A Fase 1 retém o núcleo
# operacional que gera a poupança; difere os componentes premium/expansão cujo
# retorno é mais incerto e que dependiam da folga de caixa do subsídio.
#
# MANTÉM: construcao_civil 2.535 + honorarios_futuros 120 + software_integracao 195
#         + vlm 1.305 + energia_solar 270 + robotica_amr (3/5) 375 + wms_software 400
#       = 5.200 k€  (CAPEX 2025 = 2.850 inalterado; CAPEX 2026 = 2.350)
# DIFERE: box_on_demand 350 + 2 AMRs extra 250 + camada IA-vision do WMS 200 = 800 k€
#
# Nota: energia_solar é mantido de propósito — cortá-lo baixaria 270 k€ de CAPEX
# mas DUPLICARIA o custo de energia no OPEX (perda do offset PV ~80.000 kWh/ano).
FASE1_POOLS: dict[str, float] = {
    "robotica_amr": 375_000.0,   # 3 de 5 AMRs (2 diferidos p/ Fase 2)
    "wms_software": 400_000.0,    # WMS base sem camada analytics/IA-vision plena (era 600)
    "box_on_demand": 0.0,         # diferido integralmente p/ Fase 2
}

FASE1_BENEFICIOS: dict[str, float] = {
    # poupanca_operacional 440 = Fase 1 (350) + Fase 2 (+90: 2 AMRs extra + Box-on-Demand)
    "poupanca_operacional": 350_000.0,
    # reducao_quebras 65 vinha do Box-on-Demand (embalagem por medida) → diferida
    "reducao_quebras": 0.0,
    # OPEX recalculado: VLM 60 + 3×AMR 24 + DT/MES reduzido 15 + energia 50 (solar mantido)
    #                   + técnico IA/MLOps 50 = 199 ≈ 200 k€ (base era 225)
    "opex_incremental": 200_000.0,
}
# Haircut no VN incremental B2C/3PL: −30 % (remove margem premium do Box-on-Demand
# e parte dos serviços logísticos a terceiros, que eram Fase 2).
FASE1_VN_HAIRCUT = 0.70


# ---------------------------------------------------------------------------
# Helpers de transformação do hub
# ---------------------------------------------------------------------------

def _capm(beta_u: float, rf: float, erp: float, t: float, de_ratio: float) -> tuple[float, float]:
    """Beta alavancado (Hamada) e Ke (CAPM) para um dado rácio D/E."""
    beta_l = beta_u * (1.0 + (1.0 - t) * de_ratio)
    ke = rf + beta_l * erp
    return beta_l, ke


def _wacc_estatico(ke: float, kd: float, t: float, equity: float, divida: float) -> float:
    """WACC estático = w_e·Ke + w_d·Kd·(1−t)."""
    v = equity + divida
    if v <= 0:
        return ke
    w_e = equity / v
    w_d = divida / v
    return w_e * ke + w_d * kd * (1.0 - t)


def _escala_divida(hub: dict, divida_alvo: float) -> float:
    """Escala proporcionalmente todas as tranches de dívida para o total alvo.

    Mantém o Kd ponderado constante (escala uniforme) e ajusta as amortizações
    na mesma proporção. Retorna o factor aplicado.
    """
    proj = hub["projeto_hub"]
    fin = proj["financiamento"]
    divida_atual = sum(
        float(v["montante"]) for v in fin.values()
        if isinstance(v, dict) and "amortizacao_anual" in v
    )
    if divida_atual <= 0:
        return 1.0
    factor = divida_alvo / divida_atual
    for v in fin.values():
        if isinstance(v, dict) and "amortizacao_anual" in v:
            v["montante"] = float(v["montante"]) * factor
            v["amortizacao_anual"] = float(v["amortizacao_anual"]) * factor
    return factor


def _aplicar_estrutura_capital(hub: dict, equity: float, divida: float) -> dict[str, float]:
    """Recalcula a estrutura de capital (equity, dívida) e actualiza o hub.

    APV correto (Myers 1974): o VAL_base é descontado ao **Ku** (custo do capital
    DESALAVANCADO, constante e independente da estrutura). Só o escudo fiscal —
    via montante de dívida — varia com a estrutura. Por isso `via["ku"]` (usado
    pelo vala_hub para descontar o FCFF base) é fixado em **Ku** (constante), e o
    `via["ke"]` mantém o Ke alavancado correto. Caso contrário, recapitalizar
    baixaria o Ke e inflaria espúriamente o VAL_base (dupla contagem da
    alavancagem → violaria MM).

    O Ke alavancado e o WACC são calculados na mesma — para REPORTE (perfil de
    risco do acionista, taxa FCFE) e para o WACC dinâmico, não para o VAL_base.

    Atualiza via["ku"]=Ku, via["ke"]=Ke_lev, via["wacc"], via["equity_inicial"]
    e escala as tranches.
    """
    proj = hub["projeto_hub"]
    via = proj["viabilidade"]

    beta_u = float(via.get("beta_u", 0.71))
    rf = float(via.get("rf", 0.0310))
    erp = float(via.get("erp", 0.0578))
    t = float(via.get("irc_taxa", 0.235))
    kd = float(via.get("kd", 0.0402))

    de_ratio = divida / equity if equity > 0 else 0.0
    beta_l, ke_lev = _capm(beta_u, rf, erp, t, de_ratio)   # Ke alavancado (reporte)
    ku = rf + beta_u * erp                                  # Ku desalavancado (VAL_base)
    wacc = _wacc_estatico(ke_lev, kd, t, equity, divida)

    _escala_divida(hub, divida)
    via["ku"] = ku            # ← APV: FCFF base descontado a Ku (constante, indep. da estrutura)
    via["ke"] = ke_lev        # Ke alavancado correto (reporte + WACC dinâmico)
    via["wacc"] = wacc
    via["equity_inicial"] = equity

    return {
        "equity": equity,
        "divida": divida,
        "de_ratio": de_ratio,
        "beta_l": beta_l,
        "ke": ke_lev,      # alias → Ke alavancado (reporte); lido por _avaliar e cenário base
        "ke_lev": ke_lev,
        "ku": ku,
        "kd": kd,
        "wacc": wacc,
    }


def _remover_pt2030(hub: dict) -> None:
    """Anula o subsídio PT2030 (rejeição da candidatura)."""
    hub["projeto_hub"]["financiamento"]["PT2030"]["montante"] = 0.0


def _aplicar_fase1(hub: dict) -> dict[str, float]:
    """Aplica o faseamento de âmbito (Fase 1): reduz CAPEX, pools e benefícios.

    Devolve um resumo do CAPEX resultante.
    """
    proj = hub["projeto_hub"]
    pools = proj["capex"]["pools"]

    # 1. Ajustar pools (Fase 2 diferida)
    capex_cortado = 0.0
    for nome, novo_montante in FASE1_POOLS.items():
        if nome in pools:
            capex_cortado += float(pools[nome]["montante"]) - novo_montante
            pools[nome]["montante"] = novo_montante

    # 2. Novo CAPEX base = soma dos pools capitalizáveis (exclui sunk costs)
    capex_base_novo = sum(
        float(p["montante"]) for p in pools.values()
        if not p.get("excluir_analise_incremental", False)
    )
    proj["capex"]["base"] = capex_base_novo

    # 3. Cronograma: o corte incide todo em 2026 (equipamento Fase 2)
    cron = proj["capex"]["cronograma"]
    anos = sorted(int(k) for k in cron)
    ano_equip = anos[-1]  # 2026
    cron[ano_equip] = float(cron[ano_equip]) - capex_cortado

    # 4. RFAI elegível alinha com o novo CAPEX capitalizável
    rfai = proj.get("rfai", {})
    if rfai.get("aplicar", False):
        rfai["capex_elegivel"] = capex_base_novo

    # 5. Benefícios: remover a parcela atribuível à Fase 2
    ben = proj["beneficios_anuais"]
    for chave, valor in FASE1_BENEFICIOS.items():
        ben[chave] = valor
    ben["beneficio_liquido_anual"] = (
        FASE1_BENEFICIOS["poupanca_operacional"]
        + FASE1_BENEFICIOS["reducao_quebras"]
        - FASE1_BENEFICIOS["opex_incremental"]
    )
    if "opex_detalhe" in proj:
        proj["opex_detalhe"]["total"] = FASE1_BENEFICIOS["opex_incremental"]

    # 6. VN incremental B2C/3PL com haircut (Box premium + 3PL eram Fase 2)
    ben_com = proj.get("beneficios_comerciais", {})
    vn_map = ben_com.get("vn_incremental", {})
    for yr in list(vn_map.keys()):
        vn_map[yr] = float(vn_map[yr]) * FASE1_VN_HAIRCUT

    return {
        "capex_base": capex_base_novo,
        "capex_cortado": capex_cortado,
        "capex_2026": cron[ano_equip],
    }


# ---------------------------------------------------------------------------
# Avaliação de um cenário
# ---------------------------------------------------------------------------

def _avaliar(hub: dict, irc_taxa: float, params_cap: dict | None = None) -> dict[str, Any]:
    """Corre VALA + viabilidade + DSCR sobre um hub já transformado."""
    res_vala = vala_hub(hub, irc_taxa=irc_taxa)
    res_via = viabilidade_hub(hub, irc_taxa=irc_taxa)  # wacc = via["wacc"] (já actualizado)

    df_dscr = mapa_servico_divida(hub)
    dscr_vals = [
        float(r["dscr_hub"]) for _, r in df_dscr.iterrows()
        if r["dscr_hub"] is not None and not r["periodo_carencia"]
    ]
    dscr_min = min(dscr_vals) if dscr_vals else None

    out = {
        "vala": res_vala["vala"],
        "val_base_ke": res_vala["val_base_ke"],
        "escudo_fiscal": res_vala["escudo_fiscal_total"],
        "pv_pt2030": res_vala["pv_pt2030_liquido"],
        "pv_rfai": res_vala["pv_rfai"],
        "val_wacc": res_via["val"],
        "tir": res_via["tir"],
        "dscr_min": dscr_min,
        "capex_base": float(hub["projeto_hub"]["capex"]["base"]),
        "pt2030_montante": float(hub["projeto_hub"]["financiamento"]["PT2030"]["montante"]),
    }
    if params_cap:
        out.update({
            "equity": params_cap["equity"],
            "divida": params_cap["divida"],
            "de_ratio": params_cap["de_ratio"],
            "beta_l": params_cap["beta_l"],
            "ke": params_cap.get("ke", params_cap.get("ke_lev")),   # Ke alavancado (reporte)
            "ke_lev": params_cap.get("ke_lev", params_cap.get("ke")),
            "ku": params_cap.get("ku"),                              # Ku desalavancado (APV)
            "wacc": params_cap["wacc"],
        })
    return out


# ---------------------------------------------------------------------------
# Função principal
# ---------------------------------------------------------------------------

def plano_contingencia_hub(
    hub: dict | None = None,
    irc_taxa: float | None = None,
) -> dict[str, Any]:
    """Matriz de cenários de contingência face à rejeição do PT2030.

    Cenários (todos sem PT2030, RFAI mantido salvo indicação):
      base                  Referência — com PT2030 + RFAI, estrutura 25/75.
      sem_apoios_atual      PT2030=0, estrutura inalterada (o "não fazer nada").
      recap_substituicao    Equity 1.500→4.200, dívida 4.500→1.800 (D/E 0,43).
      recap_standby         Equity 1.500→2.250, dívida 4.500→3.750 (D/E 1,67).
      recap_garantia        Equity/dívida inalterados — só garantia da mãe.
      capex_faseado         Fase 1 (CAPEX 5.200), equity 1.500, sem recap extra.
      capex_faseado_standby Fase 1 + standby parcial de equity.

    Cada cenário devolve VALA decomposto, VAL(WACC), TIR, DSCR mínimo e a
    estrutura de capital (equity, dívida, D/E, β, Ke, WACC).
    """
    if hub is None:
        hub = load()
    proj0 = hub["projeto_hub"]
    via0 = proj0["viabilidade"]
    if irc_taxa is None:
        irc_taxa = float(via0.get("irc_taxa", 0.235))

    capex_full = float(proj0["capex"]["base"])           # 6.000 k€
    divida_full = sum(
        float(v["montante"]) for v in proj0["financiamento"].values()
        if isinstance(v, dict) and "amortizacao_anual" in v
    )                                                     # 4.500 k€
    equity_full = float(via0.get("equity_inicial", 1_500_000))  # 1.500 k€

    cenarios: dict[str, dict] = {}

    # ── 1. Base (com apoios) ─────────────────────────────────────────────────
    _beta_u0 = float(via0.get("beta_u", 0.71))
    _rf0     = float(via0.get("rf",     0.0310))
    _erp0    = float(via0.get("erp",    0.0578))
    _t0      = float(via0.get("irc_taxa", 0.235))
    _ku0     = _rf0 + _beta_u0 * _erp0                       # 7.20 % — Ku base
    _ke_lev0 = float(via0.get("ke",   0.166))                # Ke alavancado YAML
    _beta_l0 = _beta_u0 * (1.0 + (1.0 - _t0) * (divida_full / equity_full))  # ≈ 2.34
    h = copy.deepcopy(hub)
    cenarios["base"] = {
        "label": "Base — com PT2030 + RFAI (25/75)",
        **_avaliar(h, irc_taxa, {
            "equity":   equity_full,
            "divida":   divida_full,
            "de_ratio": divida_full / equity_full,
            "beta_l":   _beta_l0,
            "ke":       _ke_lev0,
            "ke_lev":   _ke_lev0,
            "ku":       _ku0,
            "wacc":     float(via0.get("wacc", 0.0646)),
        }),
    }

    # ── 2. Sem apoios — estrutura atual (não fazer nada) ─────────────────────
    h = copy.deepcopy(hub)
    _remover_pt2030(h)
    p = _aplicar_estrutura_capital(h, equity_full, divida_full)
    cenarios["sem_apoios_atual"] = {
        "label": "Sem PT2030 — estrutura atual 25/75 (RFAI mantido)",
        **_avaliar(h, irc_taxa, p),
    }

    # ── 3. Recap (a) — substituição integral ─────────────────────────────────
    h = copy.deepcopy(hub)
    _remover_pt2030(h)
    p = _aplicar_estrutura_capital(h, 4_200_000.0, 1_800_000.0)
    cenarios["recap_substituicao"] = {
        "label": "Recap (a) substituição integral — E 4.200 / D 1.800",
        **_avaliar(h, irc_taxa, p),
    }

    # ── 4. Recap (b) — standby parcial ───────────────────────────────────────
    h = copy.deepcopy(hub)
    _remover_pt2030(h)
    p = _aplicar_estrutura_capital(h, 2_250_000.0, 3_750_000.0)
    cenarios["recap_standby"] = {
        "label": "Recap (b) standby parcial — E 2.250 / D 3.750",
        **_avaliar(h, irc_taxa, p),
    }

    # ── 5. Recap (c) — só garantia da mãe (estrutura inalterada) ─────────────
    h = copy.deepcopy(hub)
    _remover_pt2030(h)
    p = _aplicar_estrutura_capital(h, equity_full, divida_full)
    cenarios["recap_garantia"] = {
        "label": "Recap (c) só garantia da mãe — E 1.500 / D 4.500",
        **_avaliar(h, irc_taxa, p),
    }

    # ── 6. CAPEX faseado (Fase 1), equity inalterado ─────────────────────────
    h = copy.deepcopy(hub)
    _remover_pt2030(h)
    info_f1 = _aplicar_fase1(h)
    divida_f1 = info_f1["capex_base"] - equity_full      # dívida = CAPEX − equity
    p = _aplicar_estrutura_capital(h, equity_full, divida_f1)
    cenarios["capex_faseado"] = {
        "label": f"CAPEX faseado Fase 1 (€{info_f1['capex_base']/1e6:.1f}M) — equity 1.500",
        "fase1": info_f1,
        **_avaliar(h, irc_taxa, p),
    }

    # ── 7. CAPEX faseado + standby parcial de equity ─────────────────────────
    h = copy.deepcopy(hub)
    _remover_pt2030(h)
    info_f1 = _aplicar_fase1(h)
    equity_f1s = 2_250_000.0
    divida_f1s = info_f1["capex_base"] - equity_f1s
    p = _aplicar_estrutura_capital(h, equity_f1s, divida_f1s)
    cenarios["capex_faseado_standby"] = {
        "label": f"CAPEX faseado + standby — E 2.250 / D {divida_f1s/1e6:.2f}M",
        "fase1": info_f1,
        **_avaliar(h, irc_taxa, p),
    }

    # ── Síntese ──────────────────────────────────────────────────────────────
    vala_base = cenarios["base"]["vala"]
    for nome, c in cenarios.items():
        c["delta_vala_vs_base"] = round(c["vala"] - vala_base, 2)
        c["viavel"] = c["vala"] > 0

    return {
        "irc_taxa": irc_taxa,
        "referencia": {
            "capex_full": capex_full,
            "divida_full": divida_full,
            "equity_full": equity_full,
            "vala_base": vala_base,
        },
        "cenarios": cenarios,
    }


if __name__ == "__main__":
    import json

    res = plano_contingencia_hub()
    print(f"IRC: {res['irc_taxa']:.1%}\n")
    # Ku é constante para todos os cenários (APV — VAL_base descontado a Ku)
    hdr = (
        f"{'Cenário':<42}{'VALA':>10}{'VAL_base':>11}{'Escudo':>9}"
        f"{'RFAI':>8}{'VAL(WACC)':>11}{'TIR':>8}{'DSCR':>7}"
        f"{'Ku':>7}{'Ke_l':>7}{'WACC':>7}"
    )
    print(hdr)
    print("-" * len(hdr))
    for nome, c in res["cenarios"].items():
        tir  = f"{c['tir']:.1%}"      if c.get("tir")     is not None else "n.a."
        dscr = f"{c['dscr_min']:.2f}" if c.get("dscr_min") is not None else "n.a."
        ku   = f"{c['ku']:.2%}"       if c.get("ku")       is not None else "—"
        ke_l = f"{c['ke_lev']:.1%}"   if c.get("ke_lev")  is not None else "—"
        wacc = f"{c['wacc']:.2%}"     if c.get("wacc")     is not None else "—"
        print(
            f"{c['label']:<42}"
            f"{c['vala']/1e3:>9.0f}k"
            f"{c['val_base_ke']/1e3:>10.0f}k"
            f"{c['escudo_fiscal']/1e3:>8.0f}k"
            f"{c['pv_rfai']/1e3:>7.0f}k"
            f"{c['val_wacc']/1e3:>10.0f}k"
            f"{tir:>8}"
            f"{dscr:>7}"
            f"{ku:>7}"
            f"{ke_l:>7}"
            f"{wacc:>7}"
        )
