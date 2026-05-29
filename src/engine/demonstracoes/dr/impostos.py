from __future__ import annotations

from .loaders import _get_dr_2024_value


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


def _irc(
    rai: dict,
    a: Assumptions,
    base: Base2024,
    hub_rfai_map: "dict[int, float] | None" = None,
) -> tuple[dict, dict]:
    """Calcula o IRC por ano. Devolve (irc_dict, sifide_carryforward_dict).

    SEQUÊNCIA DE CÁLCULO (por ano de projeção):
      1. ICE — Incentivo à Capitalização das Empresas (art. 41.º-A EBF):
         Dedução à matéria coletável = ICE_valor_base × (1 + g)^(ano-2024).

      2. COLETA BASE (sobre lucro tributável = RAI − ICE):
         - Taxa geral (Grestel = grande empresa)
         - Derrama Municipal: 1,5% sobre lucro tributável
         - Derrama Estadual: 3 escalões (art. 87.º-A CIRC)
           • 3 % sobre €1,5 M–€7,5 M
           • 5 % sobre €7,5 M–€35 M
           • 9 % acima de €35 M

      3. SIFIDE II (art. 35.º CFI): crédito pontual + recorrente.
         Saldo não absorvido acumula como carry-forward (art. 35.º §4 CFI — 8 anos).
         O carry-forward é devolvido em sifide_carryforward_dict e exposto no
         Balanço como Imposto Diferido Ativo (NCRF 25 §24).

      4. TRIBUTAÇÃO AUTÓNOMA (art. 88.º CIRC): acrescida ao IRC.

    Nota: 2024 lido do histórico auditado (taxa efetiva real ≈ 8%).
    """
    irc_2024 = _get_dr_2024_value(base, "irc", 0.0)
    res: dict[int, float] = {2024: irc_2024}
    sifide_cf: dict[int, float] = {2024: 0.0}  # carry-forward acumulado por ano

    imp = a.impostos
    taxa_geral_ano = imp.get("IRC_taxa_geral_ano", {})
    taxa_red_ano   = imp.get("IRC_taxa_reduzida_ano", {})

    ice_base = float(imp.get("ICE_valor_base", 0.0))
    ice_g    = float(imp.get("ICE_taxa_crescimento", 0.03))

    sifide_credito_ano = {int(k): float(v) for k, v in imp.get("SIFIDE_credito_coleta_ano", {}).items()}
    sifide_despesas    = float(imp.get("SIFIDE_despesas_anuais", 0.0))
    sifide_taxa        = float(imp.get("SIFIDE_taxa_credito", 0.325))
    sifide_recorrente  = int(imp.get("SIFIDE_ano_inicio_recorrente", 9999))

    ta_base = float(imp.get("Tributacao_Autonoma_valor_2024", 0.0))
    ta_g    = float(imp.get("Tributacao_Autonoma_crescimento", 0.03))

    sifide_carryforward_acum = 0.0  # carry-forward acumulado de anos anteriores
    rfai_carryforward_acum = 0.0    # RFAI carry-forward acumulado (saldo corrente)

    for y, r in rai.items():
        if y == 2024 or r is None:
            continue

        taxa_geral = taxa_geral_ano.get(y, imp["IRC_taxa_geral"])
        taxa_red   = taxa_red_ano.get(y, imp["IRC_taxa_reduzida"])

        # 1. ICE
        ice_ded = ice_base * (1.0 + ice_g) ** (y - 2024) if ice_base > 0 else 0.0
        r_tributavel = max(0.0, r - ice_ded)

        # 2. Coleta base (taxa geral + derramas multi-escalão)
        _aplicar_reduzida = bool(imp.get("IRC_aplicar_taxa_reduzida", False))
        _limiar_reduzida = float(imp.get("IRC_limiar_taxa_reduzida", 50_000))
        if _aplicar_reduzida:
            coleta_base = min(r_tributavel, _limiar_reduzida) * taxa_red + max(0.0, r_tributavel - _limiar_reduzida) * taxa_geral
        else:
            coleta_base = r_tributavel * taxa_geral
        coleta = max(
            0.0,
            coleta_base
            + r_tributavel * imp["Derrama_Municipal"]
            + _derrama_estadual_escaloes(r_tributavel, imp)
            - float(imp.get("Deducoes_Fiscais", 0.0)),
        )

        # 3. SIFIDE II: crédito do ano + carry-forward acumulado
        sifide_c_ano = float(sifide_credito_ano.get(y, 0.0))
        if sifide_despesas > 0 and y >= sifide_recorrente:
            sifide_c_ano += sifide_despesas * sifide_taxa

        sifide_disponivel = sifide_c_ano + sifide_carryforward_acum
        sifide_usado = min(sifide_disponivel, coleta)
        sifide_carryforward_acum = sifide_disponivel - sifide_usado  # excesso → carry-forward
        coleta = max(0.0, coleta - sifide_usado)

        # 3b. RFAI (CFI art. 22-23) — limite art. 23.º n.º 2 al. c): 25 % da coleta.
        # Carry-forward acumulado num saldo corrente (mesmo padrão do SIFIDE acima):
        # crédito novo do ano + saldo transitado, consumido até ao limite, o
        # remanescente fica em saldo. A expiração a 10 anos (art. 23.º n.º 2 al. e))
        # é imaterial no horizonte 2025-2034 (gaps < 10 anos), pelo que um
        # acumulador escalar é suficiente e evita a dupla contagem do saldo.
        rfai_novo = float(hub_rfai_map.get(y, 0.0)) if hub_rfai_map else 0.0
        rfai_disponivel = rfai_novo + rfai_carryforward_acum
        if rfai_disponivel > 0:
            _limiar_rfai = float(imp.get("RFAI_limite_pct_coleta", 0.25))
            limite_rfai = coleta * _limiar_rfai
            rfai_usado = min(rfai_disponivel, limite_rfai)
            coleta = max(0.0, coleta - rfai_usado)
            rfai_carryforward_acum = rfai_disponivel - rfai_usado  # excesso → carry-forward

        # 4. Tributação autónoma
        ta = ta_base * (1.0 + ta_g) ** (y - 2024) if ta_base > 0 else 0.0

        res[y] = coleta + ta
        sifide_cf[y] = sifide_carryforward_acum

    return res, sifide_cf
