"""Hub Logístico M6 — análise de viabilidade e sensibilidade.

VAL, TIR, Payback (simples e atualizado), Índice de Rendibilidade, WACC
dinâmico, valor residual, ponto crítico e tornado — núcleo da «Análise da
viabilidade económica e financeira» e da «Análise de sensibilidade» do M6.
"""
from __future__ import annotations

import copy
from typing import Sequence

import pandas as pd

from .base import (
    load,
    _dep_por_ano,
    _iter_emprestimos,
    _juros_capitalizados_map,
    _kd_ponderado,
)
from .financiamento import hub_financing
from .impacto import hub_fcf, hub_nfm, hub_rfai
from ...inputs import YEARS


def _wacc_dinamico_por_ano(
    hub: dict,
    anos: Sequence[int],
    irc_taxa: float,
) -> dict[int, float]:
    """WACC anual com estrutura de capital variável (Miles-Ezzell / WACC padrão).

    À medida que o empréstimo bancário é amortizado, o peso da dívida (D/V)
    decresce e o peso do capital próprio (E/V) aumenta. Como Ke > Kd(1-t),
    o WACC cresce ao longo do tempo — penalizando FCFs mais distantes
    (efeito de desalavancagem que o WACC estático ignora).

    Fórmula:
      WACC_y = (E / V_y) × Ke + (D_y / V_y) × Kd × (1 − t)
      onde V_y = E + D_y (capitalização total no início de y)

    Nota: E é fixo no capital próprio inicial (simplificação; equity cresce
    com resultados retidos mas estes são da Grestel core, não do hub isolado).
    """
    via = hub["projeto_hub"]["viabilidade"]
    ke = float(via.get("ke", 0.192))
    kd = float(via.get("kd", _kd_ponderado(hub["projeto_hub"])))
    equity = float(via.get("equity_inicial", 1_500_000))

    df_fin = hub_financing(hub)
    saldo_map = dict(zip(df_fin["ano"].astype(int), df_fin["saldo_fim"].astype(float)))

    wacc_by_year: dict[int, float] = {}
    for y in anos:
        # Saldo de dívida no início do ano (= saldo_fim do ano anterior)
        d_y = float(saldo_map.get(y - 1, saldo_map.get(y, 0.0)))
        v_y = equity + d_y
        if v_y <= 0:
            wacc_y = ke
        else:
            w_e = equity / v_y
            w_d = d_y / v_y
            wacc_y = w_e * ke + w_d * kd * (1 - irc_taxa)
        wacc_by_year[y] = wacc_y

    return wacc_by_year


def _npv_variable_wacc(
    cashflows: Sequence[float],
    waccs: Sequence[float],
) -> float:
    """VAL com taxas de desconto variáveis por período.

    O factor de desconto no período t é o produto de (1+WACC_k) para k=1..t.
    """
    cum_factor = 1.0
    total = 0.0
    for t, (cf, w) in enumerate(zip(cashflows, waccs)):
        if t > 0:
            cum_factor *= (1 + w)
        total += cf / cum_factor
    return total


def _npv(cashflows: Sequence[float], rate: float) -> float:
    """Valor Presente Líquido — convenção fim-de-período (NPV Excel, t=1 para CF[0])."""
    return sum(
        cf / (1 + rate) ** t
        for t, cf in enumerate(cashflows, start=1)
    )


def _irr(
    cashflows: Sequence[float],
    low: float = -0.99,
    high: float = 10.0,
    tol: float = 1e-7,
    max_iter: int = 300,
) -> float | None:
    """Taxa Interna de Rentabilidade por bissecção."""
    try:
        v_low = _npv(cashflows, low)
        v_high = _npv(cashflows, high)

        if v_low * v_high > 0:
            return None

        for _ in range(max_iter):
            mid = (low + high) / 2.0
            v_mid = _npv(cashflows, mid)

            if abs(v_mid) < tol:
                return mid

            if _npv(cashflows, low) * v_mid < 0:
                high = mid
            else:
                low = mid

        return (low + high) / 2.0

    except Exception:
        return None


def _payback(cashflows: Sequence[float]) -> float | None:
    """Payback simples."""
    acum = 0.0

    for t, cf in enumerate(cashflows):
        prev_acum = acum
        acum += cf

        if prev_acum < 0 and acum >= 0 and t > 0:
            frac = (-prev_acum) / cf if cf else 0.0
            return t + frac

    return None


def _discounted_payback(
    cashflows: Sequence[float],
    rate: float,
) -> float | None:
    """Payback atualizado."""
    disc = [
        cf / (1 + rate) ** t
        for t, cf in enumerate(cashflows)
    ]

    return _payback(disc)


def _vlq_ativos(hub: dict, ano_fim: int) -> float:
    """
    Valor Líquido Contabilístico (VLQ) de todos os pools + juros capitalizados
    no final do horizonte de análise — componente base do Valor Residual (NCRF 7).

    VLQ_pool = montante × max(ano_dep_fim − ano_fim, 0) / vida_util
    onde ano_dep_fim = max(ano_pool, ano_inicio_op) + vida_util − 1.
    """
    proj = hub["projeto_hub"]
    pools = proj["capex"]["pools"]
    ano_inicio_op = int(proj["ano_inicio_beneficios"])

    vlq = 0.0
    for pool in pools.values():
        if pool.get("excluir_analise_incremental", False):
            continue
        montante = float(pool["montante"])
        vida_util = int(pool["vida_util_anos"])
        ano_pool = int(pool["ano_inicio"])
        ano_dep_inicio = max(ano_pool, ano_inicio_op)
        ano_dep_fim = ano_dep_inicio + vida_util - 1
        anos_restantes = max(ano_dep_fim - ano_fim, 0)
        vlq += montante * anos_restantes / vida_util

    # Pool virtual dos juros capitalizados (NCRF 10) — mesma vida útil da construção civil
    jc_map = _juros_capitalizados_map(hub)
    jc_total = sum(jc_map.values())
    if jc_total > 0:
        vida_jc = int(pools["construcao_civil"]["vida_util_anos"])
        ano_dep_jc_fim = ano_inicio_op + vida_jc - 1
        anos_restantes_jc = max(ano_dep_jc_fim - ano_fim, 0)
        vlq += jc_total * anos_restantes_jc / vida_jc

    # Terreno — custo de oportunidade (UC API, Doc 3): não depreciável → valor
    # pleno recuperado no VR terminal, simétrico à saída registada em CFinv_t0.
    terreno_cfg = proj.get("gastos_pre_operacionais", {}).get("terreno_custo_oportunidade", {})
    if terreno_cfg.get("inclui_em_cfinv", False):
        vlq += float(terreno_cfg.get("valor", 0.0))

    return vlq


def _capital_vivo(hub: dict, ano_fim: int) -> float:
    """Saldo total da dívida bancária no final do horizonte (todas as tranches)."""
    proj = hub["projeto_hub"]
    total = 0.0
    for _, tranche in _iter_emprestimos(proj):
        capital = float(tranche["montante"])
        amort_anual = float(tranche["amortizacao_anual"])
        inicio_amort = int(tranche["inicio_amortizacao"])
        desembolso_ano = int(tranche["desembolso"])
        if ano_fim < desembolso_ano:
            continue
        anos_amort = max(0, ano_fim - inicio_amort + 1)
        amortizado = min(amort_anual * anos_amort, capital)
        total += max(capital - amortizado, 0.0)
    return total


def ponto_critico_hub(
    driver: str,
    hub_base: dict | None = None,
    irc_taxa: float | None = None,
    tol: float = 1.0,
    max_iter: int = 100,
) -> dict:
    """
    Ponto crítico do VAL: valor do driver que faz VAL = 0.

    Usa bissecção sobre sensibilidade_hub(). A margem de segurança indica
    o desvio percentual máximo admissível face ao valor base do driver antes
    de o projeto se tornar não viável (VAL < 0).

    Retorna: {driver, valor_base, ponto_critico, val_base, margem_seguranca_pct, status}
    """
    if hub_base is None:
        hub_base = load()

    proj = hub_base["projeto_hub"]

    _cfg: dict[str, dict] = {
        "pessoal":     {"base": float(proj["beneficios_anuais"]["poupanca_operacional"]),
                        "low": 0.0, "high": float(proj["beneficios_anuais"]["poupanca_operacional"]) * 4},
        "inventario":  {"base": float(proj["beneficios_pontuais"]["libertacao_inventario"]),
                        "low": 0.0, "high": float(proj["beneficios_pontuais"]["libertacao_inventario"]) * 4},
        "capex":       {"base": float(proj["capex"]["base"]),
                        "low": float(proj["capex"]["base"]) * 0.3,
                        "high": float(proj["capex"]["base"]) * 3.0},
        "wacc":        {"base": float(proj["viabilidade"]["wacc"]),
                        "low": 0.001, "high": 0.80},
        "b2c":         {"base": 1.0, "low": 0.0, "high": 3.0},
        "crescimento": {"base": float(proj["beneficios_anuais"]["crescimento_anual"]),
                        "low": 0.0, "high": 0.50},
        "pt2030_taxa": {"base": float(proj["financiamento"]["PT2030"]["montante"])
                               / float(proj["capex"]["base"]),
                        "low": 0.0, "high": 0.75},
        "quebras":     {"base": float(proj["beneficios_anuais"]["reducao_quebras"]),
                        "low": 0.0, "high": float(proj["beneficios_anuais"]["reducao_quebras"]) * 10},
    }

    if driver not in _cfg:
        raise ValueError(f"Driver não suportado para ponto crítico: {driver!r}")

    cfg = _cfg[driver]
    base = cfg["base"]
    low, high = cfg["low"], cfg["high"]

    def _val(v: float) -> float:
        df = sensibilidade_hub(driver, [v], hub_base, irc_taxa)
        return float(df["val"].iloc[0])

    val_base = _val(base)
    val_low = _val(low)
    val_high = _val(high)

    if val_low * val_high > 0:
        return {
            "driver": driver,
            "valor_base": base,
            "ponto_critico": None,
            "val_base": val_base,
            "margem_seguranca_pct": None,
            "status": "sem_cruzamento_no_intervalo",
        }

    for _ in range(max_iter):
        mid = (low + high) / 2.0
        val_mid = _val(mid)
        if abs(val_mid) < tol:
            break
        if val_low * val_mid < 0:
            high = mid
            val_high = val_mid
        else:
            low = mid
            val_low = val_mid

    pc = (low + high) / 2.0
    margem = abs(base - pc) / abs(base) if base != 0 else None

    return {
        "driver": driver,
        "valor_base": base,
        "ponto_critico": pc,
        "val_base": val_base,
        "margem_seguranca_pct": margem,
        "status": "ok",
    }


def viabilidade_hub(
    hub: dict | None = None,
    irc_taxa: float | None = None,
    wacc: float | None = None,
    incluir_inventario: bool = True,
    incluir_liquidacao_divida: bool = False,
    taxa_realizacao_ativos: float = 1.0,
) -> dict:
    """Análise de viabilidade completa do Hub Logístico 4.0.

    Parâmetros adicionais:
      incluir_liquidacao_divida — se True, subtrai o capital bancário vivo
        no ano horizonte do FCF terminal (perspetiva acionista / FCFE).
        Por defeito False: abordagem FCFF pura (dívida no WACC).
      taxa_realizacao_ativos — rácio valor de mercado / VLQ no final do
        horizonte. 1,0 = VLQ = valor de saída (mais-valia zero, sem imposto).
        >1,0 gera mais-valia: imposto = (realizacao − VLQ) × irc_taxa.
    """
    if hub is None:
        hub = load()

    proj = hub["projeto_hub"]
    via = proj["viabilidade"]

    if irc_taxa is None:
        irc_taxa = float(via.get("irc_taxa", 0.21))

    if wacc is None:
        wacc = float(via["wacc"])

    horizonte = int(via["horizonte_anos"])

    df_fcf = hub_fcf(
        hub,
        irc_taxa=irc_taxa,
        incluir_inventario=incluir_inventario,
    )

    anos_modelo = list(df_fcf["ano"])
    ultimo_ano = anos_modelo[-1]

    fcf_ultimo = float(df_fcf[df_fcf.ano == ultimo_ano]["fcf_livre"].iloc[0])
    ebitda_ultimo = float(df_fcf[df_fcf.ano == ultimo_ano]["ebitda_impact"].iloc[0])
    dep_ultimo = float(df_fcf[df_fcf.ano == ultimo_ano]["depreciacao"].iloc[0])

    # ---------------------------------------------------------------------------
    # Carry-forward RFAI para os anos de extensão (2030–2034)
    #
    # Fundamento: o crédito gerado em 2025-2026 sobre o CAPEX elegível tem
    # carry-forward legal de 10 exercícios (CFI art. 23.º §6). O horizonte
    # do modelo estende-se até 2034, pelo que saldos não absorvidos em YEARS
    # (2025-2029) devem continuar a ser aplicados nos anos de extensão.
    #
    # Relevância para o VAL: quanto mais tarde for absorvido o crédito, menor
    # o seu valor presente. O crédito gerado em 2026 e absorvido apenas em
    # 2032 perde, ao WACC de 7,3 %, cerca de 35 % do seu valor inicial
    # (1 − 1/1.073⁶ ≈ 0.35). Este efeito de timing penaliza o VAL no cenário
    # conservador (limite sobre IRC hub) vs. o cenário real (IRC Grestel total).
    # ---------------------------------------------------------------------------
    rfai_cfg = proj.get("rfai", {})
    rfai_restante_ext = 0.0
    rfai_limite_pct_ext = float(rfai_cfg.get("limite_irc_pct", 0.50))
    if rfai_cfg.get("aplicar", False):
        rfai_total = float(rfai_cfg.get("taxa", 0.10)) * float(rfai_cfg.get("capex_elegivel", 0.0))
        rfai_aplicado = float(df_fcf["rfai_credito"].sum()) if "rfai_credito" in df_fcf.columns else 0.0
        rfai_restante_ext = max(rfai_total - rfai_aplicado, 0.0)

    ext_rows = []
    g = float(proj["beneficios_anuais"]["crescimento_anual"])
    pt2030_montante_ext = float(proj["financiamento"]["PT2030"]["montante"])
    capex_base_ext = float(proj["capex"]["base"])

    # dep_jc anual para extensão: JC_total / vida_útil construção (NCRF 10)
    jc_map_ext = _juros_capitalizados_map(hub)
    jc_total_ext = sum(jc_map_ext.values())
    vida_jc_ext = int(proj["capex"]["pools"]["construcao_civil"]["vida_util_anos"]) if "construcao_civil" in proj["capex"]["pools"] else 25
    dep_jc_anual = jc_total_ext / vida_jc_ext if vida_jc_ext > 0 else 0.0

    # Projeta o EBITDA completo (inclui PT2030 dep_pools) — alinhado com Excel
    # que cresce [1] EBITDA total × (1+g) sem stripping do accrual subsídio.
    ebitda_prev = ebitda_ultimo

    for k in range(1, horizonte - len(anos_modelo) + 1):
        y_ext = ultimo_ano + k

        ebitda_ext = ebitda_prev * (1 + g)
        dep_pools_ext = _dep_por_ano(proj, y_ext)
        dep_total_ext = dep_pools_ext + dep_jc_anual  # inclui dep_jc (NCRF 10)
        ebit_ext = ebitda_ext - dep_total_ext

        # PT2030 [3a] em extensão: dep_total / capex_base × montante (Excel [3a])
        pt2030_3a_ext = (
            round(pt2030_montante_ext * dep_total_ext / capex_base_ext, 0)
            if capex_base_ext > 0 else 0.0
        )
        # PT2030 accrual excluído do FCF operacional — tratado no VALA
        ebit_trib_ext = ebit_ext

        # Apply RFAI carry-forward in extension years (CFI art. 23.º §6 — 10 year carry-forward)
        if rfai_restante_ext > 0 and ebit_trib_ext > 0:
            coleta_ext_approx = max(0.0, ebit_trib_ext) * irc_taxa
            rfai_limite_ext_val = coleta_ext_approx * rfai_limite_pct_ext
            rfai_ext = min(rfai_restante_ext, rfai_limite_ext_val)
            rfai_restante_ext -= rfai_ext
        else:
            rfai_ext = 0.0

        # NOPAT = EBIT − IRC (com RFAI carry-forward, sem PT2030 accrual na base tributável)
        irc_bruto_ext = max(0.0, ebit_trib_ext) * irc_taxa
        irc_net_ext = irc_bruto_ext - rfai_ext
        nopat_ext = ebit_trib_ext - irc_net_ext if ebit_trib_ext > 0 else ebit_trib_ext
        fcf_ext = nopat_ext + dep_total_ext

        ext_rows.append(
            {
                "ano": y_ext,
                "ebitda_impact": ebitda_ext,
                "ebit_impact": ebit_ext,
                "pt2030_accrual": pt2030_3a_ext,  # dep_total em extensão
                "pt2030_3a": pt2030_3a_ext,
                "ebit_tributavel": ebit_trib_ext,
                "nopat": nopat_ext,
                "rfai_credito": rfai_ext,
                "depreciacao": dep_total_ext,
                "capex": 0.0,
                "delta_nfm": 0.0,
                "inventario_libertado": 0.0,
                "terreno_oportunidade": 0.0,
                "pt2030_cash": 0.0,
                "fcf_livre": fcf_ext,
            }
        )

        ebitda_prev = ebitda_ext

    if ext_rows:
        df_fcf = pd.concat(
            [df_fcf, pd.DataFrame(ext_rows)],
            ignore_index=True,
        )

    # ── Valor Residual ──────────────────────────────────────────────────────
    # O projeto cessa financeiramente no ano horizonte; não se usa perpetuidade.
    ano_horizonte = int(df_fcf["ano"].iloc[-1])
    vr_ativos = _vlq_ativos(hub, ano_horizonte)

    # Mais-valias: se valor de realização > VLQ (taxa_realizacao_ativos > 1)
    valor_realizacao = vr_ativos * taxa_realizacao_ativos
    mais_valia = max(valor_realizacao - vr_ativos, 0.0)
    imposto_mais_valia = mais_valia * irc_taxa

    # NFM acumulada — capital circulante que reverte quando o projeto termina
    nfm_map = hub_nfm(hub)
    nfm_recovery_terminal = sum(nfm_map.values())

    # Dívida viva no final do horizonte (sempre calculada para informação)
    capital_vivo_t10 = _capital_vivo(hub, ano_horizonte)
    deducao_divida = capital_vivo_t10 if incluir_liquidacao_divida else 0.0

    vt = (valor_realizacao - imposto_mais_valia) + nfm_recovery_terminal - deducao_divida

    cfs = list(df_fcf["fcf_livre"])
    cfs[-1] += vt

    val = _npv(cfs, wacc)
    tir = _irr(cfs)
    pb = _payback(cfs)
    pb_disc = _discounted_payback(cfs, wacc)

    # WACC Dinâmico: VAL com taxas de desconto anuais baseadas na estrutura D/E real
    via = proj["viabilidade"]
    wacc_dinamico_flag = bool(via.get("wacc_dinamico", False))
    anos_fcf = list(df_fcf["ano"].astype(int))
    wacc_by_year: dict[int, float] = {}
    val_dinamico: float | None = None

    if wacc_dinamico_flag:
        wacc_by_year = _wacc_dinamico_por_ano(hub, anos_fcf, irc_taxa)
        wacc_seq = [wacc_by_year.get(y, wacc) for y in anos_fcf]
        # t=0 placeholder WACC = 0 (cash flow do ano 0 não é descontado)
        val_dinamico = _npv_variable_wacc([0.0] + cfs, [0.0] + wacc_seq)

    capex_base = float(proj["capex"]["base"])
    indice_rendibilidade = (1 + val / capex_base) if capex_base else None
    indice_rendibilidade_dinamico = (
        (1 + val_dinamico / capex_base)
        if val_dinamico is not None and capex_base
        else None
    )

    # NFM total acumulado ao longo do horizonte (soma das ΔNFM > 0)
    nfm_total_saida = sum(v for v in nfm_map.values() if v > 0)

    # Juros capitalizados totais (informação para reconciliação)
    jc_map = _juros_capitalizados_map(hub)
    juros_cap_total = sum(jc_map.values())

    nfm_cfg = proj.get("necessidades_fundo_maneio", {})
    jc_cfg = proj.get("juros_capitalizaveis", {})

    rfai_total_gerado = (
        float(rfai_cfg.get("taxa", 0.0)) * float(rfai_cfg.get("capex_elegivel", 0.0))
        if rfai_cfg.get("aplicar", False) else 0.0
    )
    rfai_aplicado_total = float(df_fcf["rfai_credito"].sum()) if "rfai_credito" in df_fcf.columns else 0.0

    # Nota de auditoria — custos afundados excluídos da análise incremental
    _sunk_pools = {
        k: v for k, v in proj["capex"]["pools"].items()
        if v.get("excluir_analise_incremental", False)
    }
    _sunk_total = sum(float(v["montante"]) for v in _sunk_pools.values())
    nota_custos_afundados = (
        f"Custos afundados de exploração ({_sunk_total / 1000:.0f} k€) excluídos da análise "
        f"incremental por corresponderem a honorários incorridos antes da decisão de "
        f"investimento (princípio dos cash flows incrementais — Brealey, Myers & Allen, Cap. 6)."
        if _sunk_total > 0 else None
    )

    return {
        "nota_custos_afundados": nota_custos_afundados,
        "fcf_df": df_fcf,
        "valor_terminal": vt,
        "valor_residual_ativos": vr_ativos,
        "mais_valia": mais_valia,
        "imposto_mais_valia": imposto_mais_valia,
        "nfm_recovery_terminal": nfm_recovery_terminal,
        "capital_vivo_t10": capital_vivo_t10,
        "deducao_divida_terminal": deducao_divida,
        "cashflows_val": cfs,
        "val": val,
        "tir": tir,
        "payback_simples": pb,
        "payback_atualizado": pb_disc,
        "indice_rendibilidade": indice_rendibilidade,
        # WACC dinâmico: VAL com taxa de desconto variável por ano (desalavancagem)
        "val_wacc_dinamico": val_dinamico,
        "indice_rendibilidade_dinamico": indice_rendibilidade_dinamico,
        "wacc_por_ano": wacc_by_year if wacc_dinamico_flag else {},
        "parametros": {
            "wacc": wacc,
            "irc_taxa": irc_taxa,
            "metodologia_vt": "valor_residual_ativos_nfm",
            "valor_residual_ativos": vr_ativos,
            "nfm_recovery_terminal": nfm_recovery_terminal,
            "capital_vivo_t10": capital_vivo_t10,
            "incluir_liquidacao_divida": incluir_liquidacao_divida,
            "taxa_realizacao_ativos": taxa_realizacao_ativos,
            "mais_valia": mais_valia,
            "imposto_mais_valia": imposto_mais_valia,
            "horizonte_anos": horizonte,
            "incluir_inventario": incluir_inventario,
            "capex_base": capex_base,
            "capex_2025": float(proj["capex"]["cronograma"].get(2025, 0)),
            "capex_2026": float(proj["capex"]["cronograma"].get(2026, 0)),
            "depreciacao_descricao": (
                "4 %–25 % por pool · construção 25 a · VLM 8 a · AMR 5 a"
                " · WMS 4 a · integração 3 a · juros cap. 25 a (NCRF 10)"
            ),
            "poupanca_operacional": float(proj["beneficios_anuais"]["poupanca_operacional"]),
            "reducao_quebras": float(proj["beneficios_anuais"]["reducao_quebras"]),
            "opex_incremental": float(
                proj["beneficios_anuais"].get("opex_incremental")
                or proj.get("opex_detalhe", {}).get("total", 0)
            ),
            "beneficio_liquido_anual": float(proj["beneficios_anuais"]["beneficio_liquido_anual"]),
            "crescimento_anual": float(proj["beneficios_anuais"]["crescimento_anual"]),
            "libertacao_inventario": float(proj["beneficios_pontuais"]["libertacao_inventario"]),
            "ano_inventario": int(proj["beneficios_pontuais"]["ano"]),
            "banco_montante": sum(float(tr["montante"]) for _, tr in _iter_emprestimos(proj)),
            "banco_taxa_juro": _kd_ponderado(proj),
            "emprestimos": {
                n: {"montante": float(tr["montante"]), "taxa_juro": float(tr["taxa_juro"])}
                for n, tr in _iter_emprestimos(proj)
            },
            "pt2030_montante": float(proj["financiamento"]["PT2030"]["montante"]),
            "pt2030_ano": int(proj["financiamento"]["PT2030"]["ano_recebimento"]),
            "ano_inicio_beneficios": int(proj["ano_inicio_beneficios"]),
            # NFM
            "nfm_stock_manutencao": float(nfm_cfg.get("stock_manutencao_inicial", 0)),
            "nfm_consumiveis_arranque": float(nfm_cfg.get("consumiveis_arranque", 0)),
            "nfm_psp_fornecedores_dias": float(nfm_cfg.get("psp_fornecedores_dias", 30)),
            "nfm_pmr_clientes_externos_dias": float(nfm_cfg.get("pmr_clientes_externos_dias", 45)),
            "nfm_total_saida_caixa": nfm_total_saida,
            # Juros capitalizados (NCRF 10)
            "juros_capitalizados_total": juros_cap_total,
            "juros_capitalizaveis_ativo": jc_cfg.get("capitalizar", False),
            "juros_cap_ano_inicio": jc_cfg.get("ano_inicio_capitalizacao", None),
            "juros_cap_ano_fim": jc_cfg.get("ano_fim_capitalizacao", None),
            # RFAI
            "rfai_aplicar": rfai_cfg.get("aplicar", False),
            "rfai_taxa": float(rfai_cfg.get("taxa", 0.0)) if rfai_cfg.get("aplicar", False) else 0.0,
            "rfai_capex_elegivel": float(rfai_cfg.get("capex_elegivel", 0.0)) if rfai_cfg.get("aplicar", False) else 0.0,
            "rfai_credito_total_gerado": rfai_total_gerado,
            "rfai_credito_aplicado_horizonte": rfai_aplicado_total,
            "rfai_credito_restante_pos_horizonte": max(rfai_total_gerado - rfai_aplicado_total, 0.0),
        },
    }


def sensibilidade_hub(
    driver: str,
    valores: Sequence[float],
    hub_base: dict | None = None,
    irc_taxa: float | None = None,
) -> pd.DataFrame:
    """One-at-a-time sensibilidade do VAL do Hub."""
    if hub_base is None:
        hub_base = load()

    rows = []

    for v in valores:
        h = copy.deepcopy(hub_base)
        proj = h["projeto_hub"]

        if driver == "beneficio":
            ben = proj["beneficios_anuais"]
            factor = v / float(ben["beneficio_liquido_anual"])

            ben["poupanca_operacional"] = (
                float(ben["poupanca_operacional"]) * factor
            )
            ben["reducao_quebras"] = (
                float(ben["reducao_quebras"]) * factor
            )

        elif driver == "capex":
            old = float(proj["capex"]["base"])
            factor = v / old if old else 1.0

            proj["capex"]["base"] = v

            for y in proj["capex"]["cronograma"]:
                proj["capex"]["cronograma"][y] = (
                    float(proj["capex"]["cronograma"][y]) * factor
                )

        elif driver == "wacc":
            res = viabilidade_hub(h, irc_taxa=irc_taxa, wacc=v)

            rows.append(
                {
                    "driver": driver,
                    "valor": v,
                    "val": res["val"],
                    "tir": res["tir"],
                }
            )

            continue

        elif driver == "inventario":
            proj["beneficios_pontuais"]["libertacao_inventario"] = v

        elif driver == "quebras":
            proj["beneficios_anuais"]["reducao_quebras"] = v

        elif driver == "crescimento":
            proj["beneficios_anuais"]["crescimento_anual"] = v

        elif driver == "pt2030_taxa":
            # v = fracção do CAPEX (ex: 0.20 = 20 %, 0.45 = 45 %)
            capex_val = float(proj["capex"]["base"])
            proj["financiamento"]["PT2030"]["montante"] = v * capex_val

        elif driver == "pessoal":
            # v = poupança operacional total (€/ano); base = 380 000 €
            ben = proj["beneficios_anuais"]
            ben["poupanca_operacional"] = v
            quebras = float(ben.get("reducao_quebras", 0))
            opex = abs(float(
                ben.get("opex_incremental")
                or proj.get("opex_detalhe", {}).get("total", 0)
                or 0
            ))
            ben["beneficio_liquido_anual"] = v + quebras - opex

        elif driver == "b2c":
            # v = factor de escala sobre vn_incremental (1.0 = base; 0.5 = pessimista; 1.5 = otimista)
            ben_com = proj.get("beneficios_comerciais", {})
            vn_map = ben_com.get("vn_incremental", {})
            for yr in list(vn_map.keys()):
                vn_map[yr] = float(vn_map[yr]) * v

        else:
            raise ValueError(f"Driver desconhecido: {driver}")

        res = viabilidade_hub(h, irc_taxa=irc_taxa)

        rows.append(
            {
                "driver": driver,
                "valor": v,
                "val": res["val"],
                "tir": res["tir"],
            }
        )

    return pd.DataFrame(rows)


def tornado_hub(
    hub_base: dict | None = None,
    irc_taxa: float | None = None,
) -> pd.DataFrame:
    """Tornado do VAL Hub — análise de sensibilidade one-at-a-time.

    6 variáveis críticas identificadas no diagnóstico financeiro da Grestel:
      1. Libertação de inventário  — maior motor de liquidez a curto prazo
      2. Co-financiamento PT2030   — subsidio a fundo perdido que determina viabilidade
      3. Crescimento B2C           — canal de margem superior (+18 pp vs retalho)
      4. Poupança operacional      — eficácia da automação (AMR + VLM) no custo de pessoal
      5. WACC                      — reflecte risco percebido pelo mercado/bancos
      6. Desvio no CAPEX           — risco de derrapagem orçamental em projetos 4.0
    """
    if hub_base is None:
        hub_base = load()

    proj = hub_base["projeto_hub"]
    capex_base = float(proj["capex"]["base"])

    val_base = viabilidade_hub(hub_base, irc_taxa=irc_taxa)["val"]

    # --- 6 variáveis críticas com ranges calibrados ao diagnóstico Grestel ----
    # Convenção: vals = [pessimista, otimista]
    # low e high no output referem-se ao impacto no VAL (não ao valor da variável):
    #   val_low = VAL quando a variável assume o valor vals[0] (pessimista)
    #   val_high = VAL quando a variável assume o valor vals[1] (otimista)
    cfg = {
        # 1. Inventário — €2,0 M base; 13 M€ imobilizados → meta conservadora de 15 %
        "inventario": {
            "vals": [1_000_000.0, 2_500_000.0],
            "label": "Libertação de inventário (€)",
            "desc_low": "€1,0 M (pess.)",
            "desc_high": "€2,5 M (otim.)",
        },
        # 2. PT2030 — 20 % (aprovação parcial) vs 45 % (aprovação majorada)
        "pt2030_taxa": {
            "vals": [0.20, 0.45],
            "label": "Co-financiamento PT2030 (% CAPEX)",
            "desc_low": "20 % (€760 k)",
            "desc_high": "45 % (€1 710 k)",
        },
        # 3. B2C — escala do VN incremental: +40 % 2024 → abrandamento vs aceleração
        "b2c": {
            "vals": [0.50, 1.50],
            "label": "Crescimento B2C/e-commerce (×base)",
            "desc_low": "×0,5 (abrand.)",
            "desc_high": "×1,5 (aceleração)",
        },
        # 4. Poupança operacional — automação sem vs com impacto pleno
        "pessoal": {
            "vals": [200_000.0, 500_000.0],
            "label": "Poupança operacional (€/ano)",
            "desc_low": "€200 k (pess.)",
            "desc_high": "€500 k (otim.)",
        },
        # 5. WACC — perfil de risco elevado 2024 (rating deteriorou); intervalo 6%–10%
        "wacc": {
            "vals": [0.10, 0.06],
            "label": "WACC (%)",
            "desc_low": "10 % (risco alto)",
            "desc_high": "6 % (risco baixo)",
        },
        # 6. CAPEX — derrapagem orçamental ±15 % (benchmark projetos 4.0)
        "capex": {
            "vals": [capex_base * 1.15, capex_base * 0.85],
            "label": "CAPEX ±15% (€)",
            "desc_low": "+15 % (derrap.)",
            "desc_high": "−15 % (poupança)",
        },
    }

    rows = []

    for key, info in cfg.items():
        low_v, high_v = info["vals"]

        df_low = sensibilidade_hub(key, [low_v], hub_base, irc_taxa)
        df_high = sensibilidade_hub(key, [high_v], hub_base, irc_taxa)

        val_low = float(df_low["val"].iloc[0])
        val_high = float(df_high["val"].iloc[0])

        rows.append(
            {
                "driver": key,
                "label": info["label"],
                "desc_low": info.get("desc_low", str(round(low_v, 4))),
                "desc_high": info.get("desc_high", str(round(high_v, 4))),
                "valor_low": low_v,
                "valor_high": high_v,
                "val_low": val_low,
                "val_base": val_base,
                "val_high": val_high,
                "impacto_total": abs(val_high - val_low),
            }
        )

    return (
        pd.DataFrame(rows)
        .sort_values("impacto_total", ascending=False)
        .reset_index(drop=True)
    )


def vala_hub(
    hub: dict | None = None,
    irc_taxa: float | None = None,
    incluir_inventario: bool = True,
) -> dict:
    """APV — Valor Actualizado Líquido Ajustado do Hub Logístico (Folha 11_VALA).

    VALA = VAL_base(Ke) + Σ PV(escudo_fiscal_i × kd_i) + PV(PT2030_líquido × rf) + PV(RFAI × rf)

    Componentes
    -----------
    VAL_base(Ke)
        FCFF puro — excluindo o reconhecimento NCRF 22 do PT2030 do EBIT —
        descontado ao custo do capital próprio desalavancado (Ke, CAPM).
        Ajuste por período: FCF_clean_y = FCF_hub_y − accrual_PT2030_y × (1 − t)
        onde FCF_hub_y já vem de viabilidade_hub() (inclui valor terminal no
        último fluxo). Cobre o horizonte completo 2025-2034.

    Escudo Fiscal
        VA(juros_expensed_y × irc_taxa) por tranche, descontado à taxa kd de
        cada tranche (Miles-Ezzell 1980: o tax shield é tão arriscado quanto a
        dívida subadjacente). Juros capitalizados (NCRF 10, 2025-2026) não
        geram escudo corrente — o benefício chega via maior depreciação futura.
        Horizonte: 2025-2034 (inclui amortizações da extensão).

    PT2030 líquido
        VA(cash-in 2027 − custo IRC NCRF 22) descontado a rf.
        O subsídio recebido em 2027 é reconhecido na DR ao longo da vida útil
        dos activos subsidiados (NCRF 22). Cada reconhecimento anual aumenta
        o lucro tributável gerando um custo IRC = reconhecimento_y × irc_taxa.
        PT2030_net_y = (+montante se y=2027) − dep_pools_y / capex × montante × t

    RFAI
        VA(crédito fiscal anual aplicado ao IRC) descontado a rf.
        Crédito determinístico (10 % × CAPEX elegível = 600 k€) — risco
        próximo de rf (único risco é a não-geração de IRC suficiente para
        absorção, modelizado pelo limite 50 % × IRC_hub).

    Referências
    -----------
    Myers, S.C. (1974). JoF 29(1). — Teoria APV.
    Miles, J.A. & Ezzell, J.R. (1980). JoF 35(4). — Tax shields a kd.
    Damodaran, A. (2002). Investment Valuation, 3.ª ed., §10.5.
    """
    if hub is None:
        hub = load()

    proj = hub["projeto_hub"]
    via = proj["viabilidade"]

    if irc_taxa is None:
        irc_taxa = float(via.get("irc_taxa", 0.21))

    ke = float(via.get("ke", 0.161794))
    rf = float(via.get("rf", 0.0325))
    horizonte = int(via.get("horizonte_anos", 10))

    # ── Horizonte completo: YEARS + anos de extensão ─────────────────────────
    # YEARS = [2025-2029]; horizonte = 10; extensão = [2030-2034]
    ano_base = YEARS[0]  # 2025 — t=1 por convenção _npv()
    todos_anos: list[int] = list(range(ano_base, ano_base + horizonte))

    def _t(y: int) -> int:
        """Período de desconto: t=1 para 2025 (convenção fim-de-período)."""
        return y - ano_base + 1

    # ── 1. VAL_base(Ke) ── FCFF puro descontado a Ke ─────────────────────────
    # viabilidade_hub() com wacc=Ke fornece os FCF (incluindo extensão e VT).
    # O FCF_hub inclui o reconhecimento NCRF 22 no EBIT (via hub_dr_impact),
    # o que aumenta o IRC em accrual_y × irc_taxa. Removemos este efeito para
    # isolar o FCFF operacional puro — o PT2030 é tratado separadamente abaixo.
    res_via = viabilidade_hub(
        hub, irc_taxa=irc_taxa, wacc=ke, incluir_inventario=incluir_inventario
    )
    df_fcf_full = res_via["fcf_df"]
    cfs_com_vt = list(res_via["cashflows_val"])  # VT somado ao último CF
    anos_via = list(df_fcf_full["ano"].astype(int))

    # pt2030_accrual: dep_pools para YEARS; pt2030_3a (≈dep_pools, dep_jc=0) para extensão
    accrual_map: dict[int, float] = dict(
        zip(df_fcf_full["ano"].astype(int), df_fcf_full["pt2030_accrual"].astype(float))
    )
    ebit_map: dict[int, float] = dict(
        zip(df_fcf_full["ano"].astype(int), df_fcf_full["ebit_impact"].astype(float))
    )

    cfs_clean: list[float] = []
    fcf_ajuste_pt2030: dict[int, float] = {}
    for y, fcf_y in zip(anos_via, cfs_com_vt):
        accrual_y = accrual_map.get(y, 0.0)
        ebit_y = ebit_map.get(y, 0.0)
        # Remover lucro líquido do reconhecimento não-caixa do NOPAT:
        #   FCF_hub = FCF_pure + accrual_y×(1-t)   [quando EBIT > 0]
        #   ⇒ FCF_pure = FCF_hub − accrual_y×(1-t)
        ajuste = accrual_y * (1.0 - irc_taxa) if (ebit_y > 0 and accrual_y > 0) else 0.0
        cfs_clean.append(fcf_y - ajuste)
        fcf_ajuste_pt2030[y] = round(ajuste, 2)

    val_base = _npv(cfs_clean, ke)

    # ── 2. Escudo Fiscal por tranche (Miles-Ezzell) ───────────────────────────
    # Iteramos todos_anos manualmente para cobrir o horizonte completo,
    # sem depender de hub_financing() que só cobre YEARS.
    jc_cfg = proj.get("juros_capitalizaveis", {})
    jc_ativo = bool(jc_cfg.get("capitalizar", False))
    jc_ini = int(jc_cfg.get("ano_inicio_capitalizacao", 9999)) if jc_ativo else 9999
    jc_fim = int(jc_cfg.get("ano_fim_capitalizacao", 0)) if jc_ativo else 0

    escudo_por_tranche: dict[str, dict] = {}
    total_escudo_fiscal = 0.0

    for nome, tranche in _iter_emprestimos(proj):
        capital = float(tranche["montante"])
        kd_tr = float(tranche["taxa_juro"])
        amort_anual = float(tranche["amortizacao_anual"])
        inicio_amort = int(tranche["inicio_amortizacao"])
        desembolso_ano = int(tranche["desembolso"])

        saldo = 0.0
        escudo_anual: dict[int, float] = {}

        for y in todos_anos:
            if y == desembolso_ano:
                saldo = capital
            juros_y = saldo * kd_tr
            # Juros capitalizados (NCRF 10) não transitam pelo DR; sem escudo direto
            jc_y = juros_y if (jc_ativo and jc_ini <= y <= jc_fim) else 0.0
            juros_exp_y = max(juros_y - jc_y, 0.0)
            # Amortização
            amort_y = amort_anual if (y >= inicio_amort and saldo > 0) else 0.0
            amort_y = min(amort_y, saldo)
            saldo = max(saldo - amort_y, 0.0)
            escudo_anual[y] = juros_exp_y * irc_taxa

        pv_escudo = sum(
            escudo_anual[y] / (1.0 + kd_tr) ** _t(y)
            for y in todos_anos
        )
        escudo_por_tranche[nome] = {
            "taxa_juro": kd_tr,
            "pv_escudo_fiscal": round(pv_escudo, 2),
            "escudo_por_ano": {
                y: round(v, 2) for y, v in escudo_anual.items() if v > 0
            },
        }
        total_escudo_fiscal += pv_escudo

    # ── 3. PT2030 líquido: cash-in − custo IRC NCRF 22, VA a rf ──────────────
    pt2030_cfg = proj["financiamento"]["PT2030"]
    pt2030_montante = float(pt2030_cfg["montante"])
    pt2030_ano_rec = int(pt2030_cfg["ano_recebimento"])
    capex_base_val = float(proj["capex"]["base"])

    pt2030_net_por_ano: dict[int, dict] = {}
    for y in todos_anos:
        # Reconhecimento NCRF 22 proporcional à dep_pools (excl. dep_jc)
        dep_pools_y = _dep_por_ano(proj, y)
        rec_y = (
            pt2030_montante * dep_pools_y / capex_base_val
            if capex_base_val > 0 else 0.0
        )
        custo_irc_y = rec_y * irc_taxa
        cash_in_y = pt2030_montante if y == pt2030_ano_rec else 0.0
        net_y = cash_in_y - custo_irc_y
        pt2030_net_por_ano[y] = {
            "cash_in": round(cash_in_y, 2),
            "dep_pools": round(dep_pools_y, 2),
            "reconhecimento_ncrf22": round(rec_y, 2),
            "custo_irc": round(custo_irc_y, 2),
            "net": round(net_y, 2),
        }

    pv_pt2030 = sum(
        pt2030_net_por_ano[y]["net"] / (1.0 + rf) ** _t(y)
        for y in todos_anos
    )

    # ── 4. RFAI: crédito fiscal anual, VA a rf ────────────────────────────────
    rfai_map = hub_rfai(hub, irc_taxa=irc_taxa)  # apenas YEARS
    rfai_por_ano = {y: round(rfai_map.get(y, 0.0), 2) for y in YEARS}

    pv_rfai = sum(
        rfai_por_ano[y] / (1.0 + rf) ** _t(y)
        for y in YEARS
    )

    # ── 5. VALA ───────────────────────────────────────────────────────────────
    vala = val_base + total_escudo_fiscal + pv_pt2030 + pv_rfai

    # ── Metadados ─────────────────────────────────────────────────────────────
    rfai_cfg = proj.get("rfai", {})
    rfai_total_gerado = (
        float(rfai_cfg.get("taxa", 0.0)) * float(rfai_cfg.get("capex_elegivel", 0.0))
        if rfai_cfg.get("aplicar", False) else 0.0
    )
    rfai_aplicado = sum(rfai_por_ano.values())

    return {
        # ── Resultado principal ────────────────────────────────────────────────
        "vala": round(vala, 2),
        # ── Decomposição APV ──────────────────────────────────────────────────
        "decomposicao": [
            {
                "componente": "VAL_base (Ke)",
                "valor": round(val_base, 2),
                "descricao": (
                    f"FCFF puro (sem reconhecimento NCRF 22 em EBIT) "
                    f"descontado a Ke={ke:.4%}. "
                    "Horizonte 2025-2034 + valor terminal (VLQ + NFM)."
                ),
            },
            {
                "componente": "Escudo Fiscal",
                "valor": round(total_escudo_fiscal, 2),
                "descricao": (
                    "PV(juros_expensed × irc_taxa) por tranche a kd_i "
                    "(Miles-Ezzell). Exclui juros capitalizados 2025-2026 "
                    "(NCRF 10 — sem escudo direto na DR)."
                ),
            },
            {
                "componente": "PT2030 líquido",
                "valor": round(pv_pt2030, 2),
                "descricao": (
                    f"PV(+{pt2030_montante / 1e3:.0f} k€ cash {pt2030_ano_rec} "
                    "− IRC sobre reconhecimentos NCRF 22) "
                    f"a rf={rf:.2%}."
                ),
            },
            {
                "componente": "RFAI",
                "valor": round(pv_rfai, 2),
                "descricao": (
                    f"PV({rfai_aplicado / 1e3:.1f} k€ crédito fiscal aplicado "
                    f"de {rfai_total_gerado / 1e3:.0f} k€ gerado) "
                    f"a rf={rf:.2%}."
                ),
            },
        ],
        # ── Valores individuais para dashboards ───────────────────────────────
        "val_base_ke": round(val_base, 2),
        "escudo_fiscal_total": round(total_escudo_fiscal, 2),
        "escudo_fiscal_por_tranche": escudo_por_tranche,
        "pv_pt2030_liquido": round(pv_pt2030, 2),
        "pv_rfai": round(pv_rfai, 2),
        # ── Detalhes por ano ───────────────────────────────────────────────────
        "pt2030_net_por_ano": pt2030_net_por_ano,
        "rfai_por_ano": rfai_por_ano,
        "fcf_ajuste_pt2030_por_ano": fcf_ajuste_pt2030,
        # ── Referência WACC (para confronto metodológico) ─────────────────────
        "val_wacc_referencia": round(res_via.get("val", 0.0), 2),
        # ── Parâmetros usados ─────────────────────────────────────────────────
        "parametros": {
            "ke": ke,
            "rf": rf,
            "irc_taxa": irc_taxa,
            "horizonte_anos": horizonte,
            "todos_anos": todos_anos,
            "pt2030_montante": pt2030_montante,
            "pt2030_ano_recebimento": pt2030_ano_rec,
            "rfai_total_gerado": rfai_total_gerado,
            "rfai_aplicado_horizonte": rfai_aplicado,
            "capex_base": capex_base_val,
        },
        "nota_metodologica": (
            "APV — Myers (1974). "
            f"VAL_base a Ke={ke:.4%} (CAPM, β_l≈2,35, rf={rf:.2%}, ERP=5,5 %). "
            "Escudo fiscal a kd por tranche (Miles-Ezzell 1980). "
            f"PT2030 e RFAI a rf={rf:.2%} (fluxos quasi-determinísticos). "
            "FCF base limpo de NCRF 22 — reconhecimento separado no componente PT2030."
        ),
    }
