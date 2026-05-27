## GrestelPy — G18

Motor de planeamento financeiro da empresa Grestel desenvolvido em Python para suporte à UC PEF (2025-26), Grupo 18, ISCA-UA.

Cobre os Momentos M3 (Planeamento Financeiro) e M6 (Plano de Negócios), expondo todos os outputs através de uma API REST que alimenta a interface web.

---

## Linha de comandos (Python)

pip install -r requirements.txt

uvicorn server:app --reload --port 8000

| `http://localhost:8000/` | Interface web |
| `http://localhost:8000/health` | Estado do servidor |

---

## Calculado pelo modelo

### Demonstrações financeiras anuais (2024–2029)
- Demonstração de Resultados (DR)
- Balanço
- Demonstração de Fluxos de Caixa (DFC)
- KPIs e rácios financeiros

### Outputs mensais de 2025 (M3 — Fase 1)
| Output | Chave `run_model` | Conteúdo |
|---|---|---|
| Calendário EOEP | `eoep_mensal_2025` | IVA, SS e IRC PPC mês a mês |
| Vendas | `vendas_mensal_2025` | VN por produto × mercado × mês |
| DR mensal | `dr_mensal_2025` | P&L completo para cada mês |
| Tesouraria | `tesouraria_mensal_2025` | Recebimentos, pagamentos, saldo |
| FSE por rubrica | `fse_detalhe_mensal_2025` | 14 rubricas FSE por mês |
| Pessoal mensal | `pessoal_mensal_2025` | Gastos pessoal por mês (14 salários) |
| CMVMC mensal | `cmvmc_mensal_2025` | CMVMC por mês (sazonalidade ponderada) |

> **Princípio bottom-up para 2025:** os saldos EOEP do Balanço de 2025 são derivados do calendário mensal (IVA Nov+Dez pendentes, SS Dez pendente, IRC residual), não lidos directamente do YAML.

### Análise e projetos
- Rolling forecast mensal (Balanço + DFC + NFM mensais)
- Orçamento de produção por produto
- Análise de sensibilidade (tornado)
- Viabilidade do Hub Logístico M6 (VAL, TIR, Payback, Índice de Rendibilidade)
- Monte Carlo — 1 000 simulações sobre 6 drivers de risco (VAL + TIR)
- Subsidiária Ecogres

### OE4 — Plano de Financiamento do Investimento (integrado no Hub)
| Output | Onde | Conteúdo |
|---|---|---|
| Equilíbrio financeiro pré/pós-projeto | Separador Hub | Autonomia financeira, solvabilidade, endividamento, cobertura de juros — 2024 (pré) + 2025-2029 (pós); alerta se AF < 30% |
| Mapa de investimento | Separador Hub | CAPEX por pool de ativo (construção civil, VLMs, AMRs, WMS, Box-on-Demand, Solar) + cronograma anual + ΔNFM + PT2030 |
| Mapa de serviço da dívida | Separador Hub | Juros, amortizações, DSCR por ano; indicação do período de carência (2025-2027) |
| Solvabilidade (CP/Passivo) | Separador KPIs | Rácio adicionado à tabela de KPIs (2024-2029) |

---

## Cenários

| Cenário | Volume vendas | Preço (spread real) | FSE / Pessoal |
|---|---|---|---|
| **Base** | +3% a.a. | +0,8% real | YAML (referência) |
| **Upside** | +4,5% → +3% | +1,8% → +1,4% | FSE controlado |
| **Downside** | +1,5% → +2,5% | negativo → +0,4% | FSE+Pessoal acima |
| **Stress** | −3% em 2025, depois +1-3% | negativo → +0,9% | FSE choque +9,6% |

O toggle **Hub Logístico** é independente do cenário e aplica-se a **qualquer** combinação. Quando ativo, o engine incorpora automaticamente **todos** os benefícios do Hub no DR/Balanço/DFC:

| Efeito Hub | Fonte | Magnitude |
|---|---|---|
| Poupança operacional (pessoal + FSE) | `hub_dr_impact()` | €480k/ano base (cresce 4%/a nominal) |
| Redução de quebras | `hub_dr_impact()` | €80k/ano |
| VN incremental B2C / logística 3ª partes | `hub_dr_impact()` → `build_dr()` | €500k–€1 150k/ano (2026-2029) |
| CAPEX e depreciações | `hub_capex()` | €6 000k em 7 pools (fases 1+2 integradas) |
| Financiamento CGD/BPI | `hub_financing()` | €4 500k @ 4,15%, carência 3 anos |
| Subsídio PT2030 | `pt2030_reconhecimento()` | €2 700k (45% CAPEX, reconhecido a/c depr. — NCRF 22) |
| Libertação de inventário (faseada) | `hub_dr_impact()` + `balanco.py` | €1 250k em 2026 + €1 250k em 2027 |
| Crédito fiscal RFAI | `hub_rfai()` → `_irc()` | €600k total (CFI art. 22-23); integrado na coleta consolidada |
| Juros capitalizados | `hub_capex()` | NCRF 10 — capitalização até 2026, pool virtual 25 anos |
| NFM incremental | `hub_nfm()` | stock manutenção + crédito clientes (Fase 2) |

> **Limiar PEF M6:** CAPEX/ATL_operacional = 6 000k / 39 570k = **15,2 %** ≥ 15 % ✓  
> ATL operacional exclui EOEP_devedor (688,5k€ — timing fiscal, não capital produtivo — NCRF 15 §9).

Cenários customizados adicionais podem ser definidos em `src/engine/data/cenarios/custom_scenarios.yaml`. Os cenários built-in (Base, Upside, Downside, Stress, Hub_Ativo, Stress) são geridos exclusivamente em `loader.py` (`_SCENARIO_OVERRIDES`).

---

## Endpoints principais

```
GET  /api/scenarios/all                → DR/Balanço/DFC/KPIs todos os cenários
POST /api/run                          → execução com overrides custom
GET  /api/rolling-forecast/mensal      → Balanço+DFC+NFM mensais 2025
GET  /api/assumptions/effective        → pressupostos consolidados efectivos
GET  /api/hub/viability                → VAL, TIR, Payback, IR Hub M6
GET  /api/hub/tornado                  → análise sensibilidade Hub M6
GET  /api/hub/break-even               → ponto crítico VAL = 0 por driver
GET  /api/hub/viabilidade-cenarios     → VAL/TIR Hub para Base/Upside/Downside/Stress
GET  /api/hub/consolidado              → Hub + Ecogres + Grestel grupo (comparativo)
GET  /api/hub/monte-carlo              → Monte Carlo 100–5 000 simulações (VAL + TIR)
GET  /api/hub/debt-service             → mapa de serviço da dívida (DSCR anual) — OE4
GET  /api/hub/investment-map           → mapa de investimento (CAPEX pools + NFM) — OE4
GET  /api/ecogres                      → projecções Ecogres
GET  /api/custom-scenarios             → cenários customizados guardados
GET  /api/export/excel                 → exportação Excel (.xlsx) com todas as demonstrações
```

---

## Inputs (YAML)

```
src/engine/data/
├── historico/2024/          ← dados reais 2024 (imutáveis)
├── pressupostos/
│   ├── globais.yaml         ← fiscal, prazos (PMR 45d / PMP 55d 2025+), pessoal, caixa, rend. financeiros
│   │                           PMP 2024 histórico: 63d (saldo auditado); 55d = objetivo renegociação fornecedores
│   ├── 2025/                ← macro, vendas, custos, mix mensais
│   └── 2026_2029/           ← macro, vendas, custos anuais
├── master/                  ← catálogos estáveis (produtos, mercadorias, FSE)
├── computed/schedules.yaml  ← parâmetros BAU (CAPEX, amortizações, juros) — editável para ajustes de base
├── cenarios/                ← cenários customizados (built-in em loader.py)
└── subsidiarias/            ← Ecogres e Hub Logístico (fases 1+2)
```

### Scripts de extracção (export/)

Scripts standalone para imprimir dados no terminal — úteis para preparar os relatórios M6/OE4 sem servidor:

```
export/extract_hub_data.py    ← viabilidade Hub, FCF, DSCR, análise tornado
export/extract_scenarios.py   ← KPIs dos 4 cenários com e sem Hub
export/extract_sem_hub.py     ← AF e KPIs consolidados sem Hub (comparativo)
```

Executar a partir da raiz do projecto: `python export/extract_hub_data.py`

---

## Estrutura do projecto

Ver [docs/project_tree.md](docs/project_tree.md) para a árvore completa.
Ver [docs/guia_docentes.md](docs/guia_docentes.md) para documentação detalhada de endpoints e outputs.

---
