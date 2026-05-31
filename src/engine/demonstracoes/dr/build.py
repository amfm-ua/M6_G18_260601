from __future__ import annotations

import pandas as pd

from ...inputs import Assumptions, Base2024, Schedules, ALL_YEARS, YEARS
from ...operacional import vendas
from ...operacional import fse
from ...operacional import pessoal
from ...investimento import investimento
from ...financiamento import financiamento
from ...operacional import cmvmc
from ...operacional import clientes as conta_clientes
from ...operacional import inventarios
from ...projetos import ecogres as ecogres_mod
from .loaders import _load_hub_dr, _load_ecogres, _load_cozedura
from .rubricas import _outros_rendimentos, _outros_gastos, _imparidades
from .impostos import _irc
from ...projetos.cozedura import impacto as coz_mod


def build_dr(
    a: Assumptions,
    base: Base2024,
    sched: Schedules,
    df_prod: "pd.DataFrame | None" = None,
    df_merc: "pd.DataFrame | None" = None,
    df_total: "pd.DataFrame | None" = None,
    juros_linha_cp: "dict[int, float] | None" = None,
    aplic_cp_rend: "dict[int, float] | None" = None,
) -> pd.DataFrame:
    """
    Constrói a Demonstração de Resultados Completa (2024-2029).

    FLUXO INTERNO (11 etapas sequenciais):
      1. Calcula vendas anuais: produtos + mercadorias → receita bruta
      2. Calcula FSE (custos operacionais): base + crescimento, detalha por rubrica
      3. Calcula pessoal: salários, contribuições sociais
      4. Calcula depreciação: do plano de investimento
      5. Calcula financiamento: juros e encargos da dívida
      6. Calcula CMVMC: custo de mercadorias e matérias primas (% da receita)
      7. Calcula inventário: variação do stock (acréscimo ou libertação de caixa)
      8. Calcula clientes: saldos a receber (para imparidades)
      9. Calcula outros rendimentos: equivalência patrimonial, cedência pessoal, subsídios
     10. Calcula outros gastos: gastos não operacionais
     11. Calcula impostos (IRC): MEP (anulado) → deduções base (ICE, maj.energia)
          → coleta (IRC+derramas) → deduções coleta (SIFIDE, RFAI) → trib.autónoma

    SAÍDA:
      DataFrame com 40+ colunas:
        - receitas: vn (vendas líquidas)
        - custos operacionais: cmvmc, fse (detalhe por rubrica), pessoal, imparidades
        - resultados operacionais: ebitda, ebit
        - resultados financeiros: juros, subsídios, outros_rend
        - resultado antes/depois impostos: rai, irc, resultado_liquido

    PRINCÍPIOS CONTABILÍSTICOS RESPEITADOS:
      - Acuidade: reconhecimento de receita ao momento da venda
      - Prudência: imparidades de clientes (0,5% do saldo) e riscos
      - Consistência: mesmos pressupostos ano a ano, com crescimentos aplicados
      - Materialidade: omissão de rubricas imateriais (rounding a 0,01€)
    """
    # ===== ETAPA 1: CÁLCULO DE VENDAS ANUAIS =====
    if df_prod is None:
        df_prod = vendas.vendas_anuais(a, base, sched)
    if df_merc is None:
        df_merc = vendas.vendas_mercadorias_anuais(a, base)
    if df_total is None:
        df_total = vendas.resumo_anual(df_prod, df_merc)

    # FATOR DE ESCALA 2025: rácio VN_2025 / VN_2024; usado para escalar a componente
    # variável do FSE (subcontratos, energia, transportes) em proporção à atividade.
    # A componente fixa do FSE escala por meses_2025/12 (=1.0 para ano completo).
    vn_2024 = float(df_total[df_total.ano == 2024]["vn_total"].iloc[0])
    vn_2025 = float(df_total[df_total.ano == 2025]["vn_total"].iloc[0])
    factor_2025 = vn_2025 / vn_2024 if vn_2024 else 1.0

    # ===== ETAPA 2: CÁLCULO DE FSE (Fornecimentos e Serviços Externos) =====
    # FSE: custos operacionais variáveis (eletricidade, água, comunicações, limpeza, etc.)
    # Cresce com base + crescimento definido em assumptions (redução custo, eficiência, etc.)
    # O factor_2025 escala a componente variável; a fixa usa meses_2025/12 (=1.0 em ano completo)
    df_fse = fse.fse_anual(a, base, factor_2025)

    # FSE DETALHADO: desagregação por rubrica (categoria)
    # Necessário para dashboard/reporting detalhado (ex: eletricidade, gás, comunicações)
    # Cada rubrica cresce independentemente (modelo não agregado)
    df_fse_det = fse.fse_detalhe_anual(a, base, factor_2025)
    fse_det_by_year: dict[int, dict[str, float]] = {}
    for _, r in df_fse_det.iterrows():
        y = int(r["ano"])
        rub = str(r["rubrica"])
        fse_det_by_year.setdefault(y, {})[rub] = float(r["valor"])

    fse_cols_by_rubrica = fse.FSE_DETALHE_KEYS

    # RECONCILIAÇÃO FSE: as rubricas detalhadas devem somar exatamente o total
    # Este bloco aplica um factor de escala para garantir fechamento (evita rounding errors)
    for y in ALL_YEARS:
        total_fse_y = float(df_fse[df_fse.ano == y]["fse"].iloc[0]) if not df_fse.empty else 0.0
        rub_sum = sum(
            float(fse_det_by_year.get(y, {}).get(rub, 0.0))
            for rub in fse_cols_by_rubrica.keys()
        )
        if rub_sum > 0:
            scale = total_fse_y / rub_sum
            for rub in fse_cols_by_rubrica.keys():
                fse_det_by_year.setdefault(y, {})[rub] = float(
                    fse_det_by_year.get(y, {}).get(rub, 0.0) * scale
                )

    # ===== ETAPA 3: CÁLCULO DE PESSOAL =====
    # Gastos com pessoal: salários, contribuições patronais, impostos sobre remunerações
    # Cresce com inflação + crescimento de headcount (evolução de efectivos)
    df_pessoal = pessoal.pessoal_anual(a, base, df_total)

    # ===== ETAPA 4: CÁLCULO DE DEPRECIAÇÃO =====
    # Depreciação: redução de valor dos ativos imobilizados (máquinas, instalações, software)
    # Segue o plano de investimento (entradas e saídas de ativos)
    df_inv = investimento.investimento_anual(a, base, sched, df_vn=df_total)

    # ===== ETAPA 5: CÁLCULO DE FINANCIAMENTO =====
    # Juros e encargos de dívida: capital emprestado ao banco × taxa de juro
    # Decresce com amortizações do empréstimo
    df_fin = financiamento.financiamento_anual(sched, a)
    df_selo = financiamento.imposto_selo_anual(df_fin, a)
    selo_por_ano: dict[int, float] = dict(zip(df_selo["ano"].astype(int), df_selo["selo_total"]))

    # ===== ETAPA 6: CÁLCULO DE CMVMC =====
    # CMVMC: Custo de Mercadorias Vendidas e Matérias-Primas Consumidas
    # Inclui: custo direto de produto vendido + consumo de matérias-primas
    # Expressa como % da receita (margem bruta = receita - CMVMC)
    df_cmvmc = cmvmc.cmvmc_anual(a, base, df_prod, df_merc)

    # ===== ETAPA 7: CÁLCULO DE INVENTÁRIO =====
    # Inventário (Stock): quantidade de mercadorias em armazém
    # Variação do inventário: acréscimo (caixa negativa) ou venda (caixa positiva)
    # Na DR: variação de inventários = -ΔStock (se stock sobe, caixa desce)
    df_inv_st = inventarios.inventarios_anual(a, base, df_cmvmc)

    # ===== ETAPA 8: CÁLCULO DE CLIENTES =====
    # Saldo de Clientes (Contas a Receber): crédito concedido aos clientes
    # Base para cálculo de imparidades (0,5% de crédito duvidoso estimado)
    df_cli = conta_clientes.clientes_anual(a, base, df_total)

    # ===== ETAPA 9: CARREGAMENTO DE SUBSIDIÁRIAS (Opcional) =====
    # Hub Logístico M6: se ativo, contribui com rendimentos (subsídios) e custos (pessoal, FSE)
    hub_dr = _load_hub_dr(a)

    # RFAI do Hub: crédito fiscal ao investimento (CFI art. 22-23), aplicado à coleta
    hub_rfai_map: "dict[int, float] | None" = None
    if hub_dr is not None:
        try:
            hub_raw = a.raw.get("hub_logistico", {})
            from ...projetos import hub_logistico as hub_mod
            hub_rfai_map = hub_mod.hub_rfai(hub_raw)
        except Exception:
            hub_rfai_map = None

    # Ecogres: se ativa, afeta CMVMC (redução, maior eficiência) e pessoal (cedência)
    eco = _load_ecogres(a)

    if eco is not None:
        # Subcontratação Ecogres: redução de CMVMC (outsourcing de produção)
        df_subc = ecogres_mod.subcontratacao_anual(eco)
        subc_map = dict(zip(df_subc["ano"], df_subc["subcontratacao_ecogres"]))

        # Redução de CMVMC pela eficiência de Ecogres
        eco_mpsc_red = ecogres_mod.reducao_mpsc(eco)
    else:
        subc_map = {y: 0.0 for y in ALL_YEARS}
        eco_mpsc_red = {y: 0.0 for y in ALL_YEARS}

    # Cozedura de Baixa Temperatura (toggle): poupança de energia (FSE) líquida
    # do incremento de CMVMC pela pasta reformulada (volastonite), faseada.
    coz = _load_cozedura(a)
    if coz is not None:
        cmvmc_by_year = {
            int(r["ano"]): float(r["cmvmc"]) for _, r in df_cmvmc.iterrows()
        }
        coz_fse_red_map = coz_mod.cozedura_fse_reducao(coz, fse_det_by_year)
        coz_cmvmc_inc_map = coz_mod.cozedura_cmvmc_incremento(coz, cmvmc_by_year)
    else:
        coz_fse_red_map = {y: 0.0 for y in ALL_YEARS}
        coz_cmvmc_inc_map = {y: 0.0 for y in ALL_YEARS}

    # ===== ETAPA 10: CÁLCULO DE OUTROS RENDIMENTOS =====
    # Outros Rendimentos: receitas não operacionais
    #   - Equivalência Patrimonial: resultado de participações em associadas
    #   - Cedência de Pessoal: faturação de pessoal cedido a terceiros
    #   - Subsídios (Gov./Programas): investimento, exploração, investigação
    #   - Ganhos de câmbio: variações cambiais (se ativo em moeda estrangeira)
    outros_rend, outros_rend_bk = _outros_rendimentos(
        a,
        base,
        sched,
        df_inv,
        hub_dr,
        eco,
    )

    # ===== ETAPA 11: CÁLCULO DE IMPOSTOS E GASTOS EXTRAORDINÁRIOS =====
    # Outros Gastos: despesas não operacionais (ajustes, perdas, penalidades)
    outros_gastos = _outros_gastos(a, base, sched)

    # Imparidades: provisões para crédito duvidoso — taxa configurável via globais.yaml
    imparidades = _imparidades(df_cli, base, a)

    rend_fin_base = float(
        a.raw.get("rendimentos_financeiros_base", None)
        or base.outros_rendimentos.get("Rendimentos_Financeiros", 64677.79)
    )
    rend_fin_g = float(a.raw.get("rendimentos_financeiros_crescimento", 0.0))

    rows = []
    rai_dict = {}

    r24 = base.raw["dr_2024_real"]

    rai_dict[2024] = r24["rai"]
    bk24 = outros_rend_bk[2024]

    rows.append(
        {
            "ano": 2024,
            "vn": r24["vn"],
            "var_inventarios": r24["var_inventarios"],
            "var_producao": r24.get("var_producao", 0.0),
            "outros_rend": r24["outros_rend"],
            "cmvmc": -r24["cmvmc"],
            "fse": -r24["fse"],
            # detalhe FSE por rubrica (custos negativos na DR)
            **{
                fse_cols_by_rubrica[rub]: -fse_det_by_year.get(2024, {}).get(rub, 0.0)
                for rub in fse_cols_by_rubrica.keys()
            },
            "gastos_pessoal": -r24["gastos_pessoal"],
            "imparidades": -r24["imparidades"],
            "outros_gastos": -r24["outros_gastos"],
            "ebitda": r24["ebitda"],
            "depreciacoes": -r24["depreciacoes"],
            "ebit": r24["ebit"],
            "juros": -r24["juros"],
            # 2024: selo já embebido nos gastos financeiros auditados (R&C); coluna informativa
            "imposto_selo": selo_por_ano.get(2024, 0.0),
            "rend_financeiros": r24["rend_financeiros"],
            "rai": r24["rai"],
            "irc": -r24["irc"],
            "rl": r24["rl"],
            "hub_pessoal_reducao": 0.0,
            "hub_fse_reducao": 0.0,
            "hub_cmvmc_reducao": 0.0,
            "hub_fse_opex": 0.0,
            "hub_vn_incremental": 0.0,
            "hub_cmvmc_incremental": 0.0,
            "hub_outros_rend_subsidio": 0.0,
            "fse_subcontratacao_ecogres": subc_map.get(2024, 0.0),
            "ecogres_reducao_mpsc": 0.0,
            "cozedura_fse_reducao": 0.0,
            "cozedura_cmvmc_incremento": 0.0,
            "outros_rend_ced_loc": bk24["outros_rend_ced_loc"],
            "outros_rend_ced_pessoal": bk24["outros_rend_ced_pessoal"],
            "outros_rend_equiv_patr": bk24["outros_rend_equiv_patr"],
            "outros_rend_subs_cambio": bk24["outros_rend_subs_cambio"],
        }
    )

    for y in YEARS:
        vn = float(df_total[df_total.ano == y]["vn_total"].iloc[0])
        f_base = float(df_fse[df_fse.ano == y]["fse"].iloc[0])
        p_base = float(
            df_pessoal[df_pessoal.ano == y]["gastos_pessoal"].iloc[0]
        )
        c_base = float(df_cmvmc[df_cmvmc.ano == y]["cmvmc"].iloc[0])
        d = float(df_inv[df_inv.ano == y]["total_dep_amort"].iloc[0])
        j = float(df_fin[df_fin.ano == y]["juros_total"].iloc[0])
        j_linha = juros_linha_cp.get(y, 0.0) if juros_linha_cp else 0.0
        j_selo = selo_por_ano.get(y, 0.0)
        j = j + j_linha + j_selo

        inv_ef = float(df_inv_st[df_inv_st.ano == y]["inventarios"].iloc[0])
        inv_ei = float(df_inv_st[df_inv_st.ano == y - 1]["inventarios"].iloc[0])
        var_inv = inv_ef - inv_ei

        # Variação da produção (R&C 2024: +131.378,22€) — not yet fully modeled
        # TODO: Model var_produção separately per NCRF/IAS 2
        var_producao = float(base.raw.get("dr_2024_real", {}).get("var_producao", 0.0)) if y == 2024 else 0.0

        out_rend = outros_rend[y]
        out_gast = outros_gastos[y]
        imp = imparidades.get(y, 0.0)

        rend_fin = (
            rend_fin_base * (1 + rend_fin_g) ** (y - 2025)
            + (aplic_cp_rend or {}).get(y, 0.0)
        )

        ecogres_subc = subc_map.get(y, 0.0)

        # A subcontratação Ecogres já está reflectida nos valores auditados 2024
        # (FSE e CMVMC). Reclassificar criaria double-counting: ecogres_subc (~8.26M)
        # é maior que o FSE total (~7.5M), tornando f_adj negativo.
        c_adj = c_base
        f_adj = f_base

        hub_pessoal_red = 0.0
        hub_fse_red = 0.0
        hub_cmvmc_red = 0.0
        hub_fse_opex = 0.0
        hub_gastos_preop = 0.0
        hub_vn_inc = 0.0
        hub_cmvmc_inc = 0.0
        hub_outros_rend = 0.0

        if hub_dr and y in hub_dr:
            h = hub_dr[y]
            hub_pessoal_red = h.get("pessoal_reducao", 0.0)
            hub_fse_red = h.get("fse_reducao", 0.0)
            hub_cmvmc_red = h.get("cmvmc_reducao", 0.0)
            hub_fse_opex = h.get("fse_opex_hub", 0.0)
            hub_gastos_preop = h.get("gastos_preop_hub", 0.0)
            hub_vn_inc = h.get("vn_incremental", 0.0)
            hub_cmvmc_inc = h.get("cmvmc_incremental", 0.0)
            hub_outros_rend = h.get("outros_rend_subsidio", 0.0)

        vn = vn + hub_vn_inc
        # hub_outros_rend (PT2030) já está incluído em outros_rend[y] via
        # _outros_rendimentos(); não somar de novo para evitar dupla contagem.
        p = p_base - hub_pessoal_red
        f = f_adj - hub_fse_red + hub_fse_opex
        c = c_adj - hub_cmvmc_red - eco_mpsc_red.get(y, 0.0) + hub_cmvmc_inc
        # hub_gastos_preop: gastos pré-operacionais não capitalizáveis (formação NCRF 6 §21)
        # Adicionados a outros_gastos para não contaminar a reconciliação FSE/detalhe.
        out_gast = out_gast + hub_gastos_preop

        # Cozedura de Baixa Temperatura: FSE ↓ (poupança de energia) e CMVMC ↑
        # (pasta reformulada). Efeito líquido recorrente no EBITDA, faseado.
        coz_fse_red = coz_fse_red_map.get(y, 0.0)
        coz_cmvmc_inc = coz_cmvmc_inc_map.get(y, 0.0)
        f = f - coz_fse_red
        c = c + coz_cmvmc_inc

        ebitda = vn + var_inv + var_producao + out_rend - c - f - p - imp - out_gast
        ebit = ebitda - d
        rai = ebit - j + rend_fin

        rai_dict[y] = rai
        bky = outros_rend_bk[y]

        rows.append(
            {
                "ano": y,
                "vn": vn,
                "var_inventarios": var_inv,
                "var_producao": var_producao,
                "outros_rend": out_rend,
                "cmvmc": -c,
                "fse": -f,
                # detalhe FSE por rubrica (custos negativos na DR)
                **{
                    fse_cols_by_rubrica[rub]: -fse_det_by_year.get(y, {}).get(rub, 0.0)
                    for rub in fse_cols_by_rubrica.keys()
                },
                # Hub net FSE adjustment overrides the 0.0 set by expansion above
                "hub_fse_ajuste_liq": hub_fse_red - hub_fse_opex,
                "gastos_pessoal": -p,
                "imparidades": -imp,
                "outros_gastos": -out_gast,
                "ebitda": ebitda,
                "depreciacoes": -d,
                "ebit": ebit,
                "juros": -j,
                "juros_linha_cp": -j_linha,
                "imposto_selo": j_selo,
                "rend_financeiros": rend_fin,
                "rai": rai,
                "hub_pessoal_reducao": hub_pessoal_red,
                "hub_fse_reducao": hub_fse_red,
                "hub_cmvmc_reducao": hub_cmvmc_red,
                "hub_fse_opex": hub_fse_opex,
                "hub_gastos_preop": hub_gastos_preop,
                "hub_vn_incremental": hub_vn_inc,
                "hub_cmvmc_incremental": hub_cmvmc_inc,
                "hub_outros_rend_subsidio": hub_outros_rend,
                "fse_subcontratacao_ecogres": ecogres_subc,
                "ecogres_reducao_mpsc": eco_mpsc_red.get(y, 0.0),
                "cozedura_fse_reducao": coz_fse_red,
                "cozedura_cmvmc_incremento": coz_cmvmc_inc,
                "outros_rend_ced_loc": bky["outros_rend_ced_loc"],
                "outros_rend_ced_pessoal": bky["outros_rend_ced_pessoal"],
                "outros_rend_equiv_patr": bky["outros_rend_equiv_patr"],
                "outros_rend_subs_cambio": bky["outros_rend_subs_cambio"],
            }
        )

    # Mapa MEP (Equivalência Patrimonial) — Achado A: anulado da base tributável.
    # Fonte canónica: sched.investimento["rend_equiv_patrimonial"].
    # Esta mesma série é a que entra no RAI via outros_rendimentos;
    # usar fonte idêntica garante reconciliação RAI ↔ dedução.
    mep_map = sched.investimento["rend_equiv_patrimonial"]

    irc, sifide_cf = _irc(
        rai_dict, a, base,
        mep_map=mep_map,
        hub_rfai_map=hub_rfai_map,
    )

    for r in rows:
        ano = r["ano"]
        if ano != 2024:
            r["irc"] = -irc.get(ano, 0.0)
            r["rl"] = r["rai"] + r["irc"]
        r["sifide_carryforward"] = sifide_cf.get(ano, 0.0)

    return pd.DataFrame(rows)
