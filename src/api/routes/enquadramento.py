"""Rota do enquadramento estratégico M6 (Ansoff, 4Ps, ODS, Plano de Ação)."""

from fastapi import APIRouter

from src.engine.modelo import enquadramento as enq_mod

router = APIRouter(prefix="/api")


@router.get("/enquadramento")
def get_enquadramento_completo():
    """Devolve o enquadramento estratégico M6 completo.

    Blocos de resposta:
        regra_investimento   — verificação CAPEX/ATL (15%–30%)
        ansoff               — posicionamento matricial e justificação
        ideia_inovadora      — vetores Indústria 4.0
        marketing_mix        — análise 4Ps (Place, Product, Price, Promotion)
        ods                  — alinhamento ODS com indicadores quantitativos
        plano_acao           — quatro pilares com CAPEX, timing e responsáveis
        fatores_criticos_sucesso — FCS com probabilidade e impacto no VAL
    """
    return enq_mod.get_enquadramento_completo()


@router.get("/enquadramento/ansoff")
def get_ansoff():
    """Devolve o posicionamento Ansoff e justificação empírica."""
    return enq_mod.get_ansoff()


@router.get("/enquadramento/marketing-mix")
def get_marketing_mix():
    """Devolve a análise 4Ps (Place, Product, Price, Promotion)."""
    return enq_mod.get_marketing_mix()


@router.get("/enquadramento/ods")
def get_ods():
    """Devolve o alinhamento ODS com indicadores por objetivo."""
    return enq_mod.get_ods()


@router.get("/enquadramento/plano-acao")
def get_plano_acao():
    """Devolve o plano de ação por pilar com CAPEX, timing e entregáveis."""
    return enq_mod.get_plano_acao()


@router.get("/enquadramento/regra-investimento")
def get_regra_investimento():
    """Devolve a verificação da regra de investimento M6 (15%–30% ATL).

    Campos:
        capex_elegivel_k    — CAPEX capitalizável em k€
        atl_operacional_k   — Ativo Total Líquido operacional em k€
        racio_pct           — CAPEX/ATL em percentagem
        piso_pct            — limite inferior admissível (15%)
        teto_pct            — limite superior admissível (30%)
        estado              — 'cumprido' | 'incumprido'
    """
    return enq_mod.get_regra_investimento()


@router.get("/enquadramento/fatores-criticos")
def get_fatores_criticos():
    """Devolve os fatores críticos de sucesso com probabilidade e mitigação."""
    return {"fatores": enq_mod.get_fatores_criticos()}
