"""Rolling Forecast Mensal — Balanço, DFC e NFM mensais para 2025.

Fase 1 do planeamento M3: demonstrações financeiras mensais articuladas,
integrando Investimento, Financiamento, EOEP e Necessidades de Fundo de Maneio.

Metodologia: DFC-first (fluxos de caixa determinam a posição de Caixa).
  1. Mapa de Investimento → variações ANC (AFT)
  2. Demonstração de Resultados → RL acumulado no CP
  3. Todos os itens do Balanço calculados de forma determinística (exceto Caixa)
  4. ΔNFM apurado a partir desses itens
  5. DFC: fluxo_op + fluxo_inv + fluxo_fin → var_caixa
  6. caixa_fecho = caixa_abertura + var_caixa  (nunca negativa; défice → Linha CP)
  7. Balanço fecha naturalmente sem ajuste manual (controlo = 0 por construção)

Caixa NUNCA é plug algébrico do Balanço. O saldo de Caixa resulta sempre do
apuramento dos fluxos de tesouraria. Se insuficiente, activa-se a Linha de
Crédito CP (decisão de gestão sobre défice); se excessivo, aplica-se em
Depósitos/Aplicações CP.

Funções exportadas:
  build_balanco_mensal()      → Balanço sequencial (abertura → Dez)
  build_dfc_mensal()          → DFC indireta (reconciliada com o Balanço)
  build_nfm_mensal()          → NFM e CCC mensais (derivado do Balanço)
  build_tesouraria_completa() → Tesouraria operacional + serviço dívida + CAPEX
  build_linha_summary()       → Resumo linha rotativa com alertas (por cenário)
  build_rolling_forecast()    → Ponto de entrada: devolve dict com tudo
  build_rolling_dual()        → Paralelo sem/com projeto + tabela comparativa

Simplificações (itens de baixa frequência mensal):
  • Inventários            — interpolação linear abertura→ano-fim 2025
  • EOEP devedor/credor    — interpolação linear entre refs anuais
  • Outros Passivos CP     — interpolação linear
  • Amortizações e CAPEX   — distribuição uniforme (÷12)
  • Empréstimos NC/C       — interpolação linear (amortização uniforme implícita)
"""
from .forecast import build_rolling_forecast, build_rolling_dual
from .mensais import (
    build_balanco_mensal,
    build_dfc_mensal,
    build_nfm_mensal,
    build_tesouraria_completa,
    build_linha_summary,
)
from .reconciliacao import build_reconciliacao_mensal_anual

__all__ = [
    "build_rolling_forecast",
    "build_rolling_dual",
    "build_balanco_mensal",
    "build_dfc_mensal",
    "build_nfm_mensal",
    "build_tesouraria_completa",
    "build_linha_summary",
    "build_reconciliacao_mensal_anual",
]
