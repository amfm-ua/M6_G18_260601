"""Rotas do hub logistico."""

import copy

from fastapi import APIRouter, HTTPException, Query

from src.engine.projetos.hub_logistico import (
    load as hub_load,
    tornado_hub,
    viabilidade_hub,
    vala_hub,
    ponto_critico_hub,
    mapa_servico_divida,
    mapa_servico_divida_por_tranche,
    hub_capex,
    hub_nfm,
)
from src.engine.projetos.monte_carlo_hub import monte_carlo_hub, monte_carlo_vala_hub
from src.engine.projetos.ecogres import ecogres_dr, load as eco_load
from src.engine.modelo.model import dataframe_to_records, run_model
from src.engine.inputs.loader import _SCENARIO_OVERRIDES
from src.engine.inputs.yaml_io import _deep_update
from src.api.serializers import _wrap_rows

router = APIRouter(prefix="/api")

_SC_VIAB = ["Base", "Upside", "Downside", "Stress"]


def _hub_with_scenario(cenario: str) -> dict:
    """Carrega o Hub e aplica os overrides hub_logistico do cenario escolhido."""
    if cenario not in _SC_VIAB:
        raise HTTPException(status_code=400, detail=f"Cenario invalido: {cenario}")

    hub = copy.deepcopy(hub_load())
    hub_overrides = _SCENARIO_OVERRIDES.get(cenario, {}).get("hub_logistico", {})
    if hub_overrides:
        hub = _deep_update(hub, hub_overrides)
    return hub


@router.get("/hub/viability")
def get_hub_viability(
    cenario: str = Query("Base"),
    irc_taxa: float = Query(None),
    wacc: float = Query(None),
):
    hub = _hub_with_scenario(cenario)
    res = viabilidade_hub(hub, irc_taxa=irc_taxa, wacc=wacc)

    return {
        "cenario": cenario,
        "val": res.get("val"),
        "tir": res.get("tir"),
        "payback_simples": res.get("payback_simples"),
        "payback_atualizado": res.get("payback_atualizado"),
        "indice_rendibilidade": res.get("indice_rendibilidade"),
        "valor_terminal": res.get("valor_terminal"),
        "valor_residual_ativos": res.get("valor_residual_ativos"),
        "nfm_recovery_terminal": res.get("nfm_recovery_terminal"),
        "capital_vivo_t10": res.get("capital_vivo_t10"),
        "mais_valia": res.get("mais_valia"),
        "imposto_mais_valia": res.get("imposto_mais_valia"),
        "fcf": [float(v) for v in res.get("fcf_df", {}).get("fcf_livre", [])]
        if hasattr(res.get("fcf_df"), "get") else [],
        "parametros": res.get("parametros", {}),
        "nota_custos_afundados": res.get("nota_custos_afundados"),
    }


@router.get("/hub/tornado")
def get_hub_tornado(irc_taxa: float = Query(0.245)):
    df = tornado_hub(irc_taxa=irc_taxa)
    rows = [
        {
            "variavel": r["label"],
            "driver": r["driver"],
            "desc_low": r.get("desc_low", ""),
            "desc_high": r.get("desc_high", ""),
            "low": round((r["val_low"] - r["val_base"]) / 1e6, 3),
            "high": round((r["val_high"] - r["val_base"]) / 1e6, 3),
            "val_base": round(r["val_base"] / 1e6, 3),
            "val_low_abs": round(r["val_low"] / 1e6, 3),
            "val_high_abs": round(r["val_high"] / 1e6, 3),
            "impacto_total": round(r["impacto_total"] / 1e6, 3),
        }
        for r in df.to_dict(orient="records")
    ]
    return {"rows": rows, "val_base": round(df["val_base"].iloc[0] / 1e6, 3) if len(df) else 0}


@router.get("/hub/break-even")
def get_hub_break_even(
    irc_taxa: float = Query(0.245),
    drivers: str = Query("pessoal,inventario,capex,wacc,b2c,crescimento,pt2030_taxa"),
):
    """Ponto crítico por driver: valor que faz VAL = 0."""
    hub = hub_load()
    driver_list = [d.strip() for d in drivers.split(",")]
    results = []
    for drv in driver_list:
        try:
            pc = ponto_critico_hub(drv, hub, irc_taxa)
            results.append(pc)
        except Exception as exc:
            results.append({"driver": drv, "ponto_critico": None, "status": str(exc)})
    return {"break_even": results}


@router.get("/hub/debt-service")
def get_hub_debt_service():
    hub = hub_load()
    df = mapa_servico_divida(hub)
    pt = mapa_servico_divida_por_tranche(hub)
    rows_por_tranche = {
        nome: df_tr.to_dict(orient="records")
        for nome, df_tr in pt.items()
    }
    return {
        "rows": df.to_dict(orient="records"),
        "rows_por_tranche": rows_por_tranche,
    }


@router.get("/hub/investment-map")
def get_hub_investment_map():
    hub = hub_load()
    proj = hub["projeto_hub"]

    # CAPEX por pool de ativo
    pools = proj["capex"]["pools"]
    capex_rows = []
    for nome, pool in pools.items():
        capex_rows.append({
            "pool": nome,
            "descricao": pool.get("descricao", nome),
            "montante": float(pool["montante"]),
            "ano_inicio": int(pool["ano_inicio"]),
            "taxa_depreciacao": float(pool["taxa_depreciacao"]),
            "vida_util_anos": int(pool["vida_util_anos"]),
        })

    # Cronograma CAPEX por ano
    cron = proj["capex"]["cronograma"]
    capex_anual = [{"ano": int(y), "capex": float(v)} for y, v in cron.items()]
    capex_base = float(proj["capex"]["base"])

    # NFM por ano com acumulado e % do CAPEX
    nfm_map = hub_nfm(hub)
    nfm_acumulada = 0.0
    nfm_rows = []
    for y, delta in sorted(nfm_map.items()):
        nfm_acumulada += delta
        nfm_rows.append({
            "ano": y,
            "delta_nfm": delta,
            "nfm_acumulada": nfm_acumulada,
            "nfm_pct_capex": nfm_acumulada / capex_base if capex_base > 0 else 0.0,
        })
    nfm_total = nfm_acumulada

    # PT2030
    pt = proj["financiamento"]["PT2030"]
    pt2030_montante = float(pt["montante"])

    # Total de capital alheio: soma de todas as tranches de empréstimo (exclui PT2030)
    banco_montante = sum(
        float(v["montante"])
        for v in proj["financiamento"].values()
        if isinstance(v, dict) and "amortizacao_anual" in v
    )

    # Síntese: Origens e Aplicações de Fundos
    #
    # O PT2030 é um subsídio a FUNDO PERDIDO (não reembolsável) — NÃO é capital alheio.
    # A estrutura de financiamento do CAPEX é:
    #   Capital alheio  : Banco_Hub (empréstimo reembolsável)
    #   Capital próprio : equity residual (CAPEX − banco)
    #   Subsídio PT2030 : fundo perdido — chega em 2027, melhora a tesouraria
    #                     mas NÃO financia o CAPEX da mesma forma que a dívida.
    #
    # Aplicações = CAPEX + NFM
    # Origens CAPEX = Banco (capital alheio) + Fundos Próprios (capital próprio)
    # PT2030 reduz o custo líquido efetivo do projeto mas não altera a estrutura dívida/equity.
    total_investimento = capex_base + nfm_total

    # Capital alheio: soma das tranches de empréstimo reembolsável (Banco_Hub + BEI)
    capital_alheio = banco_montante

    # Capital próprio: autofinanciamento — 25 % do CAPEX (1 500 k€ via resultados retidos)
    fundos_proprios = capex_base - capital_alheio

    # CAPEX líquido efetivo após subsídio PT2030 (reduz custo real do projeto)
    capex_liquido_efetivo = capex_base - pt2030_montante

    # check_diferenca: verifica que banco + equity cobre exactamente o CAPEX da fase obra
    # (PT2030 chega em 2027 como desalavancagem — não financia o CAPEX directamente)
    check_diferenca = round(capital_alheio + fundos_proprios - capex_base, 2)

    # total_financiamento: perspectiva de projecto (inclui PT2030 como recurso total)
    total_financiamento = banco_montante + pt2030_montante + fundos_proprios
    total_fin_base = total_financiamento if total_financiamento > 0 else 1.0

    fonte_nfm = "Fundos Próprios / Autofinanciamento"

    # situacao_financiamento: "sobrefinanciado" quando total_fin > total_inv
    # (aparente sobrecontratação devida ao desfasamento temporal PT2030 — ver relatório OE4 §4)
    if check_diferenca != 0.0:
        situacao_financiamento = "desequilibrado"
    elif total_financiamento > total_investimento + 0.01:
        situacao_financiamento = "sobrefinanciado"
    else:
        situacao_financiamento = "equilibrado"

    sintese = {
        # Aplicações (usos)
        "total_investimento": total_investimento,
        "capex_base": capex_base,
        "nfm_acumulada": nfm_total,
        "nfm_pct_capex": nfm_total / capex_base if capex_base > 0 else 0.0,
        "fonte_nfm": fonte_nfm,
        # Origens — visão CAPEX (banco + equity = CAPEX exactamente)
        "capital_alheio": capital_alheio,
        "capital_alheio_pct": capital_alheio / capex_base if capex_base > 0 else 0.0,
        # Origens — visão projecto (banco + PT2030 + equity, percentagens sobre total)
        "total_financiamento": total_financiamento,
        "banco_hub_montante": banco_montante,
        "banco_hub_pct": banco_montante / total_fin_base,
        "pt2030_montante": pt2030_montante,
        "pt2030_pct": pt2030_montante / total_fin_base,
        "pt2030_pct_capex": pt2030_montante / capex_base if capex_base > 0 else 0.0,
        "fundos_proprios": fundos_proprios,
        "fundos_proprios_pct": fundos_proprios / total_fin_base,
        "capex_liquido_efetivo": capex_liquido_efetivo,
        # Validação e diagnóstico
        "check_diferenca": check_diferenca,
        "balanceado": check_diferenca == 0.0,
        "situacao_financiamento": situacao_financiamento,
    }

    emprestimos = [
        {
            "nome": nome,
            "montante": float(v["montante"]),
            "taxa_juro": float(v["taxa_juro"]),
            "amortizacao_anual": float(v["amortizacao_anual"]),
            "inicio_amortizacao": int(v["inicio_amortizacao"]),
            "desembolso": int(v["desembolso"]),
        }
        for nome, v in proj["financiamento"].items()
        if isinstance(v, dict) and "amortizacao_anual" in v
    ]

    return {
        "capex_base": capex_base,
        "pools": capex_rows,
        "capex_anual": capex_anual,
        "nfm": nfm_rows,
        "pt2030_montante": pt2030_montante,
        "pt2030_ano": int(pt["ano_recebimento"]),
        "emprestimos": emprestimos,
        "sintese": sintese,
    }


@router.get("/hub/viabilidade-cenarios")
def get_hub_viabilidade_cenarios(
    irc_taxa: float = Query(None),
    wacc: float = Query(None),
):
    """VAL, TIR e Payback do Hub para cada cenário (Base/Upside/Downside/Stress).

    Aplica os overrides de hub_logistico de cada cenário sobre os pressupostos
    base do YAML, permitindo calcular o Valor Esperado E[VAL] = Σ(VAL_i × p_i).
    """
    hub_base = hub_load()
    result = {}

    for sc in _SC_VIAB:
        hub_sc = copy.deepcopy(hub_base)
        hub_overrides = _SCENARIO_OVERRIDES.get(sc, {}).get("hub_logistico", {})
        if hub_overrides:
            hub_sc = _deep_update(hub_sc, hub_overrides)

        try:
            res = viabilidade_hub(hub_sc, irc_taxa=irc_taxa, wacc=wacc)
            result[sc] = {
                "val": res["val"],
                "tir": res["tir"],
                "payback_simples": res["payback_simples"],
                "payback_atualizado": res.get("payback_atualizado"),
                "indice_rendibilidade": res.get("indice_rendibilidade"),
            }
        except Exception as exc:
            result[sc] = {
                "val": None, "tir": None,
                "payback_simples": None, "payback_atualizado": None,
                "indice_rendibilidade": None, "error": str(exc),
            }

    return result


@router.get("/hub/comparativo")
def get_hub_comparativo(
    cenario: str = Query("Base"),
    ecogres_on: bool = Query(True),
):
    """DR/Balanço/DFC e KPIs comparativos: Grestel sem-Hub vs. com-Hub."""
    dfs_sem = run_model(cenario=cenario, hub_on=False, ecogres_on=ecogres_on)
    dfs_com = run_model(cenario=cenario, hub_on=True, ecogres_on=ecogres_on)
    rec_sem = dataframe_to_records(dfs_sem)
    rec_com = dataframe_to_records(dfs_com)
    return {
        "cenario": cenario,
        "sem_hub": {
            "dr":     _wrap_rows(rec_sem.get("dr")),
            "balanco": _wrap_rows(rec_sem.get("balanco")),
            "dfc":    _wrap_rows(rec_sem.get("dfc")),
            "kpis":   _wrap_rows(rec_sem.get("kpis")),
        },
        "com_hub": {
            "dr":     _wrap_rows(rec_com.get("dr")),
            "balanco": _wrap_rows(rec_com.get("balanco")),
            "dfc":    _wrap_rows(rec_com.get("dfc")),
            "kpis":   _wrap_rows(rec_com.get("kpis")),
        },
    }


@router.get("/hub/vala")
def get_hub_vala(
    cenario: str = Query("Base"),
    irc_taxa: float = Query(None),
):
    """VALA — Valor Actualizado Líquido Ajustado (APV) do Hub Logístico.

    Decompõe o valor do projeto nos quatro componentes APV:

    ```
    VALA = VAL_base(Ke) + Σ PV(escudo_fiscal_i × kd_i) + PV(PT2030_líq × rf) + PV(RFAI × rf)
    ```

    - **VAL_base**: FCFF puro (sem PT2030 em EBIT) descontado a Ke (CAPM).
    - **Escudo Fiscal**: VA(juros_expensed × t) por tranche a kd_i (Miles-Ezzell 1980).
    - **PT2030 líquido**: VA(cash-in 2027 − custo IRC NCRF 22) a rf=3,25 %.
    - **RFAI**: VA(crédito fiscal sobre CAPEX elegível) a rf=3,25 %.

    Retorna a decomposição completa por ano e por tranche, adequada para
    o dashboard dinâmico e para reconciliação com a Folha 11_VALA do Excel.
    """
    hub = _hub_with_scenario(cenario)
    result = vala_hub(hub, irc_taxa=irc_taxa)
    return {
        "cenario": cenario,
        "vala": result["vala"],
        "decomposicao": result["decomposicao"],
        "val_base_ke": result["val_base_ke"],
        "escudo_fiscal_total": result["escudo_fiscal_total"],
        "escudo_fiscal_por_tranche": result["escudo_fiscal_por_tranche"],
        "pv_pt2030_liquido": result["pv_pt2030_liquido"],
        "pv_rfai": result["pv_rfai"],
        "pt2030_net_por_ano": result["pt2030_net_por_ano"],
        "rfai_por_ano": result["rfai_por_ano"],
        "fcf_ajuste_pt2030_por_ano": result["fcf_ajuste_pt2030_por_ano"],
        "val_wacc_referencia": result["val_wacc_referencia"],
        "parametros": result["parametros"],
        "nota_metodologica": result["nota_metodologica"],
    }


@router.get("/hub/vala-sensibilidade")
def get_hub_vala_sensibilidade(
    cenario: str = Query("Base"),
    irc_taxa: float = Query(None),
):
    """Matriz de sensibilidade fiscal do VALA — variação por driver fiscal.

    Calcula o VALA (APV) para 6 cenários fiscais alternativos ao base:
    - PT2030 reduzido a 30% do CAPEX
    - Sem PT2030 (RFAI mantido)
    - Sem PT2030 nem RFAI (apenas operações + escudo fiscal)
    - IRC reduzido para 21%
    - Kd +100 bps (aumento do custo da dívida)
    """
    hub_base = _hub_with_scenario(cenario)
    proj = hub_base["projeto_hub"]
    irc_eff = irc_taxa if irc_taxa is not None else float(proj["viabilidade"].get("irc_taxa", 0.245))
    capex_base = float(proj["capex"]["base"])

    def _run(hub_cfg, irc_t):
        r = vala_hub(hub_cfg, irc_taxa=irc_t)
        return {
            "vala": r["vala"],
            "val_base_ke": r["val_base_ke"],
            "escudo_fiscal": r["escudo_fiscal_total"],
            "pv_pt2030": r["pv_pt2030_liquido"],
            "pv_rfai": r["pv_rfai"],
        }

    result = {}

    result["base"] = {"label": "Base — PT2030=45%, RFAI, IRC=24,5%", **_run(hub_base, irc_eff)}

    h = copy.deepcopy(hub_base)
    h["projeto_hub"]["financiamento"]["PT2030"]["montante"] = capex_base * 0.30
    result["pt2030_30pct"] = {"label": "PT2030 reduzido → 30% CAPEX", **_run(h, irc_eff)}

    h = copy.deepcopy(hub_base)
    h["projeto_hub"]["financiamento"]["PT2030"]["montante"] = 0.0
    result["sem_pt2030"] = {"label": "Sem PT2030 (RFAI mantido)", **_run(h, irc_eff)}

    h = copy.deepcopy(hub_base)
    h["projeto_hub"]["financiamento"]["PT2030"]["montante"] = 0.0
    h["projeto_hub"]["rfai"]["aplicar"] = False
    result["sem_subsidios"] = {"label": "Sem PT2030 nem RFAI", **_run(h, irc_eff)}

    result["irc_21pct"] = {"label": "IRC reduzido → 21%", **_run(hub_base, 0.21)}

    h = copy.deepcopy(hub_base)
    for v in h["projeto_hub"]["financiamento"].values():
        if isinstance(v, dict) and "taxa_juro" in v and "amortizacao_anual" in v:
            v["taxa_juro"] = float(v["taxa_juro"]) + 0.01
    result["kd_plus100bps"] = {"label": "Kd +100 bps", **_run(h, irc_eff)}

    return {
        "cenario": cenario,
        "irc_taxa_base": irc_eff,
        "capex_base": capex_base,
        "cenarios": result,
    }


@router.get("/hub/monte-carlo")
def get_hub_monte_carlo(
    cenario: str = Query("Base"),
    n: int = Query(1000, ge=100, le=5000, description="Número de simulações (100–5 000)"),
    irc_taxa: float = Query(0.245, description="Taxa combinada de IRC (Derrama incluída)"),
    seed: int = Query(None, description="Seed para reprodutibilidade (omitir = aleatório)"),
):
    """Monte Carlo da viabilidade do Hub Logístico 4.0.

    Corre N simulações amostrando 6 drivers de risco de distribuições contínuas
    (triangulares e normal truncada) e retorna:
    - Distribuição do VAL e TIR (percentis P5–P95)
    - P(VAL > 0): probabilidade de viabilidade do projeto
    - P(TIR > WACC_base): probabilidade de excesso de retorno
    - Correlações de Pearson driver → VAL (ranking de importância dos riscos)
    - Histograma do VAL (40 bins) para visualização

    O cenário condiciona os parâmetros base (poupança, inventário, benefícios comerciais,
    WACC) — cada cenário tem o seu próprio ponto central para as distribuições.
    """
    hub = _hub_with_scenario(cenario)
    return monte_carlo_hub(hub=hub, n_simulations=n, irc_taxa=irc_taxa, seed=seed)


@router.get("/hub/monte-carlo-vala")
def get_hub_monte_carlo_vala(
    cenario: str = Query("Base"),
    n: int = Query(1000, ge=100, le=5000, description="Número de simulações (100–5 000)"),
    irc_taxa: float = Query(0.245, description="Taxa combinada de IRC (Derrama incluída)"),
    seed: int = Query(None, description="Seed para reprodutibilidade"),
    stress: bool = Query(True, description="Incluir stress tests fiscais determinísticos"),
    pt2030_prob: float = Query(None, ge=0.0, le=1.0, description="Probabilidade de aprovação PT2030 (omitir = 0.75)"),
):
    """Monte Carlo do VALA (APV) com decomposição por componente e diagnóstico fiscal.

    Estende o Monte Carlo base com três drivers estocásticos fiscais:
    - **pt2030_approved**: Bernoulli — aprovação binária do PT2030
    - **rfai_utilization**: Triangular[50%, 100%, 100%] — absorção do crédito RFAI
    - **kd_shock**: Triangular[−100bps, 0, +200bps] — choque no spread bancário

    Cada simulação devolve os quatro componentes APV:
    ```
    VALA = VAL_base(Ke) + Escudo_Fiscal + PV(PT2030_líq) + PV(RFAI)
    ```

    O campo `diagnostico` responde à pergunta-chave:
    *"Em que % das simulações onde o projeto falha, o PT2030 não foi aprovado?"*

    Os `stress_fiscal` são cenários determinísticos complementares:
    PT2030 rejeitado, RFAI esgotado, IRC=28%.
    """
    hub = _hub_with_scenario(cenario)
    dists: dict | None = None
    if pt2030_prob is not None:
        dists = {"pt2030_approved": {"type": "bernoulli", "p": pt2030_prob}}
    return monte_carlo_vala_hub(
        hub=hub,
        n_simulations=n,
        irc_taxa=irc_taxa,
        seed=seed,
        distributions=dists,
        incluir_stress=stress,
    )


@router.get("/hub/consolidado")
def get_hub_consolidado(
    cenario: str = Query("Base"),
    irc_taxa: float = Query(None),
    wacc: float = Query(None),
):
    """VAL, TIR, Payback consolidados — Hub Logístico + Ecogres + Grestel grupo."""
    hub = _hub_with_scenario(cenario)
    hub_res = viabilidade_hub(hub, irc_taxa=irc_taxa, wacc=wacc)

    # Ecogres — P&L projetado (com hub ativo para capturar transferência interna)
    eco = eco_load()
    df_eco = ecogres_dr(eco, hub_ativo=True)
    eco_records = df_eco.to_dict(orient="records")
    eco_anos = [int(r["ano"]) for r in eco_records]
    eco_rl = [float(r["rl"]) for r in eco_records]
    eco_ebitda = [float(r["ebitda"]) for r in eco_records]
    eco_receita = [float(r["receita_total"]) for r in eco_records]
    # Excluir 2024 (histórico) para somas prospetivas
    eco_rl_proj = sum(eco_rl[1:])
    eco_ebitda_2029 = eco_ebitda[-1] if eco_ebitda else 0.0

    # Grestel grupo — DR sem e com hub para calcular impacto incremental
    dfs_sem = run_model(cenario=cenario, hub_on=False, ecogres_on=True)
    dfs_com = run_model(cenario=cenario, hub_on=True, ecogres_on=True)
    rec_sem = dataframe_to_records(dfs_sem)
    rec_com = dataframe_to_records(dfs_com)

    dr_sem = rec_sem.get("dr", [])
    dr_com = rec_com.get("dr", [])
    kpis_sem = rec_sem.get("kpis", [])
    kpis_com = rec_com.get("kpis", [])

    # Impacto incremental hub no grupo (delta EBITDA e RL)
    def _pick(rows, field, default=0.0):
        return [float(r.get(field, default)) for r in rows]

    ebitda_sem = _pick(dr_sem, "ebitda")
    ebitda_com = _pick(dr_com, "ebitda")
    rl_sem     = _pick(dr_sem, "rl")
    rl_com     = _pick(dr_com, "rl")
    anos_dr    = [int(r.get("ano", 0)) for r in dr_com]

    delta_ebitda = [c - s for c, s in zip(ebitda_com, ebitda_sem)]
    delta_rl     = [c - s for c, s in zip(rl_com, rl_sem)]

    return {
        "hub": {
            "val": hub_res["val"],
            "tir": hub_res["tir"],
            "payback_simples": hub_res["payback_simples"],
            "payback_atualizado": hub_res["payback_atualizado"],
            "indice_rendibilidade": hub_res["indice_rendibilidade"],
            "capex_base": hub_res["parametros"]["capex_base"],
            "wacc": hub_res["parametros"]["wacc"],
            "valor_terminal": hub_res["valor_terminal"],
            "valor_residual_ativos": hub_res.get("valor_residual_ativos"),
            "nfm_recovery_terminal": hub_res.get("nfm_recovery_terminal"),
            "pt2030_montante": hub_res["parametros"]["pt2030_montante"],
        },
        "ecogres": {
            "anos": eco_anos,
            "rl_anual": eco_rl,
            "ebitda_anual": eco_ebitda,
            "receita_anual": eco_receita,
            "rl_acumulado_projetado": eco_rl_proj,
            "ebitda_2029": eco_ebitda_2029,
        },
        "grupo": {
            "anos": anos_dr,
            "ebitda_sem_hub": ebitda_sem,
            "ebitda_com_hub": ebitda_com,
            "rl_sem_hub": rl_sem,
            "rl_com_hub": rl_com,
            "delta_ebitda_hub": delta_ebitda,
            "delta_rl_hub": delta_rl,
            "dr_sem_hub": _wrap_rows(dr_sem),
            "dr_com_hub": _wrap_rows(dr_com),
            "kpis_sem_hub": _wrap_rows(kpis_sem),
            "kpis_com_hub": _wrap_rows(kpis_com),
        },
    }
