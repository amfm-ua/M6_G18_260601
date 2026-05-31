# Implementação T1-T5: Serviço de Dívida, Covenants e Imposto do Selo
## Resultado — 2026-05-31 · Baseline: 120 → 151 passed

## T1 — Gearing (kpis.py)
Gearing = DL / (DL + CP). Coluna `gearing` no DataFrame de KPIs.
Gearing < 0 = posição de caixa líquida (caixa > dívida financeira).

## T2 — Covenants (covenants.py, globais.yaml, model.py)
Covenants bancários contratuais: nd_ebitda ≤ 3,5× e AF ≥ 30% → `covenants_todos_ok`.
Política estratégica (flags): gearing 40-65%, AF meta 35%.
DSCR: informativo (sem covenant contratual Grestel).
`dfs["covenants"]` via run_model(). `headroom_divida()` em covenants.py.

## T3 — Imposto do Selo (financiamento.py, dr/build.py, extensao_maturidade.py)
Ancoragem R&C 2024: 42978.56€ × 4% = 1719.14€ (Verba 17.3.1).
Toggle: `imposto_selo.aplicar_juros: true` (ON). Verba 17.1: default OFF.
Integrado em `juros` na DR → reduz RAI → flui DFC. Coluna `imposto_selo` para breakdown.

## T4 — Run-off 2030-2034 (schedules.yaml, extensao_maturidade.py)
Toggle: `financiamento.terminal_debt_runoff: false` (default OFF = constant leverage).
BPI run-off: 1337.5k/ano → liquida 2032. Dados em schedules.yaml `financiamento_runoff_2030_2034`.
INTERAÇÃO CRÍTICA: gearing já abaixo de 40% em 2027+ mesmo sem run-off.
Run-off agrava: gearing negativo em 2032+. Evidência de desalavancagem excessiva.

## T5 — Taxa Variável + Headroom (financiamento.py, covenants.py)
Toggle: `risco_taxa.euribor_choque_bps: 0`. Choque aplicado ao capital total.
Coluna `juros_choque_euribor` no DataFrame de financiamento.
`headroom_divida()` calcula espaço para mais dívida face ao teto de gearing.
