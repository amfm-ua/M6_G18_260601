"""Costa Nova Logistics Hub 4.0 — Projeto M6.

Hub logístico automatizado (ZI Vagos, Lotes 77-85) com AMR, VLM, Cobots
Vision AI, WMS integrado e Digital Twin.

Pacote organizado em módulos alinhados aos deliverables do plano de
negócios M6:
  base          — carregamento de pressupostos e primitivas partilhadas
  capex         — CAPEX, depreciação e juros capitalizados (NCRF 10)
  financiamento — plano de amortização do empréstimo bancário
  impacto       — PT2030, NFM, RFAI e impacto no DR/DFC/FCF da Grestel
  tesouraria    — mapa de serviço da dívida e desdobramento mensal
  viabilidade   — VAL, TIR, Payback, ponto crítico, sensibilidade, tornado

A API pública é re-exportada aqui para que `from ..projetos import
hub_logistico` e `from ...projetos.hub_logistico import X` continuem a
funcionar sem qualquer alteração nos módulos que consomem o pacote.

Notas metodológicas:
  • FCF livre = FCFF (Free Cash Flow to the Firm) — unlevered, descontado
    ao WACC
  • Juros de carência (2025-2027) excluídos do FCFF; capturados na DFC
    consolidada
  • Juros 2025 capitalizados no AFT (NCRF 10) — aumentam a base
    depreciável, não a DR
  • ΔNFM incluído no FCFF: saída de caixa real que não transita pela DR
"""
from .base import (
    load,
    _hub_assumptions_path,
    _dep_por_ano,
    _juros_capitalizados_map,
    _iter_emprestimos,
    _kd_ponderado,
)
from .capex import hub_capex
from .financiamento import hub_financing
from .impacto import (
    pt2030_reconhecimento,
    hub_nfm,
    hub_rfai,
    hub_dr_impact,
    hub_dfc_impact,
    hub_fcf,
)
from .tesouraria import mapa_servico_divida, mapa_servico_divida_por_tranche, mapa_tesouraria_mensal
from .viabilidade import (
    _wacc_dinamico_por_ano,
    _npv_variable_wacc,
    _npv,
    _irr,
    _payback,
    _discounted_payback,
    _vlq_ativos,
    _capital_vivo,
    ponto_critico_hub,
    viabilidade_hub,
    sensibilidade_hub,
    tornado_hub,
    vala_hub,
)

__all__ = [
    "load",
    "hub_capex",
    "hub_financing",
    "pt2030_reconhecimento",
    "hub_nfm",
    "hub_rfai",
    "hub_dr_impact",
    "hub_dfc_impact",
    "hub_fcf",
    "mapa_servico_divida",
    "mapa_servico_divida_por_tranche",
    "mapa_tesouraria_mensal",
    "ponto_critico_hub",
    "viabilidade_hub",
    "sensibilidade_hub",
    "tornado_hub",
    "vala_hub",
]
