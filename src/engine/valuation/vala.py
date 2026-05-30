"""VALA — Valor Atual Líquido Ajustado (método APV, Myers 1974).

Coerente com o VALA do Hub logístico (vala_hub):

    VALA = VAL_base(Ku) + VA(escudo fiscal)

VAL_base é o valor da empresa DESALAVANCADO — os FCFF descontados ao custo de
capital desalavancado Ku = Rf + βU·ERP (CAPM com beta de ativos). O escudo
fiscal da dívida é tratado em camada separada.

Papel no modelo (a VALA NÃO substitui o DCF-FCFF):
    1. Parte a circularidade do CMPC — Ku depende só de βU/Rf/ERP, nada que
       dependa do equity. Logo o CMPC deriva numa só passagem (sem loop nem
       âncora de múltiplos) e alimenta o DCF-FCFF (método principal da OE5).
    2. Serve de validação cruzada ao DCF-FCFF (VALA ≈ DCF valida ambos).

Pressuposto do escudo fiscal (decisão metodológica):
    Dívida CONSTANTE D = net_debt; escudo_t = t·kd·D descontado a kd
    (mundo MM / dívida fixa). Colapsa na perpetuidade para t·D. É a convenção
    coerente com (a) o escudo@kd do Hub e (b) a fórmula de re-alavancagem de
    Hamada-(1−t) usada para derivar o ke de reporte.
    NOTA: usa-se net_debt e kd bruto por serem o que o modelo expõe; a dívida
    BRUTA seria marginalmente mais correta para o escudo (ligeiramente
    conservador quando a caixa rende menos que kd).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class VALAResult:
    ku: float           # custo de capital desalavancado (taxa do VAL_base)
    val_base: float     # valor da empresa desalavancado = PV(FCFF @ Ku) + VT
    pv_escudo: float    # VA do escudo fiscal da dívida (€)
    vala: float         # VAL Ajustado = val_base + pv_escudo (valor da empresa)
    equity_vala: float  # vala − net_debt (€)
    de_ratio: float     # D/E de mercado derivado (uma vez, sem loop)
    beta_l: float       # beta alavancado (Hamada) — reporte/confronto
    ke: float           # custo do capital próprio alavancado — desconto do FCFE
    wacc: float         # CMPC one-shot — alimenta o DCF-FCFF e o confronto


def compute_vala(
    *,
    beta_u: float,
    rf: float,
    erp: float,
    kd: float,
    tax_rate: float,
    net_debt: float,
    fcffs: list[float],
    g_terminal: float,
) -> VALAResult:
    """Calcula o VALA da empresa-mãe (método APV, Myers 1974), sem iteração.

    Parâmetros
    ----------
    beta_u     : beta desalavancado do sector (risco de negócio)
    rf         : taxa sem risco (OT 10 anos)
    erp        : prémio de risco de mercado (Damodaran)
    kd         : custo BRUTO da dívida
    tax_rate   : taxa de imposto efectiva
    net_debt   : dívida líquida em € (positivo = empresa devedora)
    fcffs      : FCFF projetados em € (já com choques do MC, se aplicável)
    g_terminal : crescimento perpétuo do valor terminal de Gordon
    """
    # ── Ku — custo de capital desalavancado (sem circularidade) ──────────────
    ku = rf + beta_u * erp

    # ── VAL_base: FCFF unlevered descontado a Ku + valor terminal de Gordon ──
    val_base = 0.0
    if fcffs:
        n = len(fcffs)
        val_base = sum(cf / (1.0 + ku) ** t for t, cf in enumerate(fcffs, 1))
        if ku > g_terminal:
            vt = fcffs[-1] * (1.0 + g_terminal) / (ku - g_terminal)
            val_base += vt / (1.0 + ku) ** n

    # ── VA(escudo fiscal): dívida constante, escudo a kd ─────────────────────
    # escudo_t = tax·kd·net_debt; horizonte explícito + perpetuidade a kd.
    # Fecha analiticamente em tax·net_debt, mas calcula-se em camadas para
    # expor a decomposição (coerente com o escudo_por_ano do Hub).
    pv_escudo = 0.0
    if net_debt > 0 and kd > 0:
        escudo_anual = tax_rate * kd * net_debt
        n_h = len(fcffs) if fcffs else 0
        pv_horizonte = sum(escudo_anual / (1.0 + kd) ** t for t in range(1, n_h + 1))
        pv_terminal = (escudo_anual / kd) / (1.0 + kd) ** n_h
        pv_escudo = pv_horizonte + pv_terminal

    # ── VALA e equity ────────────────────────────────────────────────────────
    vala = val_base + pv_escudo
    equity_vala = vala - net_debt

    # ── Derivação one-shot (sem loop) para o CMPC e o confronto ──────────────
    # O equity do VALA já está fixado (não depende de ke), por isso o D/E de
    # mercado e o ke alavancado derivam numa só passagem — sem circularidade.
    if equity_vala > 0:
        de_ratio = net_debt / equity_vala
        w_e = equity_vala / (equity_vala + net_debt)
    else:
        de_ratio = 0.0
        w_e = 1.0
    w_d = 1.0 - w_e

    beta_l = beta_u * (1.0 + (1.0 - tax_rate) * de_ratio)   # Hamada
    ke = rf + beta_l * erp                                   # CAPM alavancado
    wacc = ke * w_e + kd * (1.0 - tax_rate) * w_d            # alimenta o DCF-FCFF

    return VALAResult(
        ku=ku,
        val_base=val_base,
        pv_escudo=pv_escudo,
        vala=vala,
        equity_vala=equity_vala,
        de_ratio=de_ratio,
        beta_l=beta_l,
        ke=ke,
        wacc=wacc,
    )
