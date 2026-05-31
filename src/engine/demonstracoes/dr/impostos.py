"""Cálculo de IRC por ano — Demonstracoes Financeiras.

Sequência de cálculo por ano (2025+):
  1. Base tributável: RAI − MEP (Anulação efeitos do MEP)
  2. Deduções à base: ICE (art. 41.º-A EBF) + Majoração energia (art. 92.º EBF,
     se toggle ligado — medida extraordinária, vigência 2025+ não confirmada)
  3. Coleta: taxa nominal (IRC + Derrama Municipal + Derrama Estadual 3 escalões)
  4. Deduções à coleta: SIFIDE II (art. 35.º CFI) + RFAI (art. 22-23 CFI, só Hub)
  5. Tributação autónoma (art. 88.º CIRC)

2024: lido diretamente do histórico auditado — não recalculado.
"""
from __future__ import annotations

from .loaders import _get_dr_2024_value


# ── helpers internos ──────────────────────────────────────────────────────────

def _derrama_estadual_escaloes(r_tributavel: float, imp: dict) -> float:
    """Derrama Estadual com três escalões — art. 87.º-A CIRC.

    Escalão 1: 3 % sobre (€1,5 M – €7,5 M)
    Escalão 2: 5 % sobre (€7,5 M – €35 M)
    Escalão 3: 9 % sobre (> €35 M)
    """
    t1 = imp.get("Derrama_Estadual", 0.03)
    l1 = float(imp.get("Derrama_Estadual_limiar", 1_500_000))
    t2 = float(imp.get("Derrama_Estadual_2_taxa", 0.05))
    l2 = float(imp.get("Derrama_Estadual_2_limiar", 7_500_000))
    t3 = float(imp.get("Derrama_Estadual_3_taxa", 0.09))
    l3 = float(imp.get("Derrama_Estadual_3_limiar", 35_000_000))

    de = 0.0
    de += max(0.0, min(r_tributavel, l2) - l1) * t1
    de += max(0.0, min(r_tributavel, l3) - l2) * t2
    de += max(0.0, r_tributavel - l3) * t3
    return de


# ── função principal ─────────────────────────────────────────────────────────

def _irc(
    rai: dict,
    a: Assumptions,
    base: Base2024,
    *,
    mep_map: "dict[int, float] | None" = None,
    hub_rfai_map: "dict[int, float] | None" = None,
) -> tuple[dict, dict]:
    """Calcula o IRC por ano. Devolve (irc_dict, sifide_carryforward_dict).

    PARÂMETROS:
      rai          — dict {ano: RAI}, RAI projetado (inclui MEP em outros_rendimentos)
      a            — Assumptions (bloco impostos:)
      base         — Base2024 (dados auditados 2024)
      mep_map      — {ano: MEP} mapa de equivalência patrimonial (não tributável)
                     Fonte: sched.investimento["rend_equiv_patrimonial"]
      hub_rfai_map — {ano: RFAI novo do Hub}, limit=25% coleta (opcional)

    CORREÇÕES DESTA VERSÃO (OE6 / auditoria MEP):
      - ACHADO A: MEP (equivalência patrimonial Costa Nova USA) subtraído à base
        tributável antes do cálculo da coleta, em paralelo ao ICE.
        Série: sched.investimento["rend_equiv_patrimonial"] (mesma que entra no RAI).
      - ACHADO C: Majoração energia 20% adicionada como dedução parametrizada
        à base, com toggle default DESLIGADO (medida extraordinária).
      - 2024: lido do histórico auditado — bypass completo do cálculo.

    SEQUÊNCIA DE CÁLCULO (2025+):
      1. Base = RAI − MEP (anulação MEP, Achado A)
      2. Base = Base − ICE − Majoração_energia (deduções à base)
      3. Coleta = taxa_nominal × Base + derramas
      4. Coleta = Coleta − SIFIDE − RFAI (deduções à coleta)
      5. Coleta = Coleta + Tributação Autónoma (acresce)
    """
    # ── 2024: histórico auditado, bypass total ──────────────────────────────
    irc_2024 = _get_dr_2024_value(base, "irc", 0.0)
    res: dict[int, float] = {2024: irc_2024}
    sifide_cf: dict[int, float] = {2024: 0.0}

    imp = a.impostos

    # ── parâmetros ICE ──────────────────────────────────────────────────────
    ice_base = float(imp.get("ICE_valor_base", 0.0))
    ice_g    = float(imp.get("ICE_taxa_crescimento", 0.03))

    # ── parâmetros SIFIDE II ────────────────────────────────────────────────
    taxa_geral_ano  = imp.get("IRC_taxa_geral_ano", {})
    taxa_red_ano    = imp.get("IRC_taxa_reduzida_ano", {})
    sifide_credito_ano = {int(k): float(v) for k, v in imp.get("SIFIDE_credito_coleta_ano", {}).items()}
    sifide_despesas    = float(imp.get("SIFIDE_despesas_anuais", 0.0))
    sifide_taxa        = float(imp.get("SIFIDE_taxa_credito", 0.325))
    sifide_recorrente  = int(imp.get("SIFIDE_ano_inicio_recorrente", 9999))
    sifide_carryforward_acum = 0.0

    # ── parâmetros Tributação Autónoma ─────────────────────────────────────
    ta_base = float(imp.get("Tributacao_Autonoma_valor_2024", 0.0))
    ta_g    = float(imp.get("Tributacao_Autonoma_crescimento", 0.03))

    # ── ACHADO C: Majoração energia (art. 92.º EBF) ────────────────────────
    # Medida extraordinária (apoio a custos energéticos) — vigência 2025+ incerta.
    # Parametrizada por VALOR auditado 2024 (não recalculada como energia×20%),
    # com toggle default DESLIGADO.ICE_já está em globais.yaml.
    me_aplicar   = bool(imp.get("Majoracao_Energia_aplicar_projecao", False))
    me_valor_2024 = float(imp.get("Majoracao_Energia_valor_2024", 0.0))
    me_g          = float(imp.get("Majoracao_Energia_crescimento", 0.03))

    # ── RFAI carry-forward (saldo corrente) ────────────────────────────────
    rfai_carryforward_acum = 0.0

    # ── mapa MEP: default = série de schedules se não fornecido ──────────────
    if mep_map is None:
        # Fallback: usar sched via acesso lazy (evita import circular)
        try:
            from ...inputs import load as _load
            _a, _base, _sched = _load("Base")
            mep_map = _sched.investimento["rend_equiv_patrimonial"]
        except Exception:
            mep_map = {}

    for y, r in rai.items():
        if y == 2024 or r is None:
            continue

        # ── Passo 1: Base tributável — anulação MEP (ACHADO A) ─────────────
        mep_y = float(mep_map.get(y, 0.0))
        base_tributavel = r - mep_y

        # ── Passo 2: Deduções à base (ICE + Majoração energia) ──────────────
        ice_ded = ice_base * (1.0 + ice_g) ** (y - 2024) if ice_base > 0 else 0.0

        me_ded = 0.0
        if me_aplicar and me_valor_2024 > 0:
            me_ded = me_valor_2024 * (1.0 + me_g) ** (y - 2024)

        # Floor a 0 após todas as deduções à base
        r_tributavel = max(0.0, base_tributavel - ice_ded - me_ded)

        # ── Passo 3: Coleta — taxa nominal + derramas ───────────────────────
        taxa_geral = taxa_geral_ano.get(y, imp["IRC_taxa_geral"])
        taxa_red   = taxa_red_ano.get(y, imp["IRC_taxa_reduzida"])

        _aplicar_reduzida = bool(imp.get("IRC_aplicar_taxa_reduzida", False))
        _limiar_reduzida  = float(imp.get("IRC_limiar_taxa_reduzida", 50_000))
        if _aplicar_reduzida:
            coleta_base = (
                min(r_tributavel, _limiar_reduzida) * taxa_red
                + max(0.0, r_tributavel - _limiar_reduzida) * taxa_geral
            )
        else:
            coleta_base = r_tributavel * taxa_geral

        coleta = max(
            0.0,
            coleta_base
            + r_tributavel * imp["Derrama_Municipal"]
            + _derrama_estadual_escaloes(r_tributavel, imp)
            - float(imp.get("Deducoes_Fiscais", 0.0)),
        )

        # ── Passo 4: Deduções à coleta — SIFIDE II ─────────────────────────
        sifide_c_ano = float(sifide_credito_ano.get(y, 0.0))
        if sifide_despesas > 0 and y >= sifide_recorrente:
            sifide_c_ano += sifide_despesas * sifide_taxa

        sifide_disponivel = sifide_c_ano + sifide_carryforward_acum
        sifide_usado      = min(sifide_disponivel, coleta)
        sifide_carryforward_acum = sifide_disponivel - sifide_usado
        coleta = max(0.0, coleta - sifide_usado)

        # ── Passo 4b: RFAI (CFI art. 22-23) — limite 25% da coleta ─────────
        rfai_novo = float(hub_rfai_map.get(y, 0.0)) if hub_rfai_map else 0.0
        rfai_disponivel = rfai_novo + rfai_carryforward_acum
        if rfai_disponivel > 0:
            _limiar_rfai = float(imp.get("RFAI_limite_pct_coleta", 0.25))
            limite_rfai  = coleta * _limiar_rfai
            rfai_usado   = min(rfai_disponivel, limite_rfai)
            coleta = max(0.0, coleta - rfai_usado)
            rfai_carryforward_acum = rfai_disponivel - rfai_usado

        # ── Passo 5: Tributação autónoma (acresce à coleta) ─────────────────
        ta = ta_base * (1.0 + ta_g) ** (y - 2024) if ta_base > 0 else 0.0

        res[y] = coleta + ta
        sifide_cf[y] = sifide_carryforward_acum

    return res, sifide_cf