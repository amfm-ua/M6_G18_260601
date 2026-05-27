# GrestelPy — Project Tree

> Estado actual: Engine v0.9.5 · actualizado 2026-05-21

```
GrestelPy_G18/
├── server.py                              ← FastAPI entry point (porta 8000)
├── SETUP.bat                              ← Instala Python portátil + dependências (Windows, 1ª vez)
├── start.bat                              ← Lança o servidor (Windows, duplo-clique)
├── start.sh                               ← Lança o servidor (Linux/Mac)
├── pyproject.toml                         ← Configuração pacote (Python ≥ 3.10)
├── requirements.txt                       ← Dependências runtime
├── .gitignore
│
├── docs/
│   ├── guia_docentes.md                  ← Documentação endpoints e outputs
│   └── project_tree.md                   ← Este ficheiro
│
├── export/                                ← Scripts standalone de extracção de dados
│   ├── extract_hub_data.py               ← Imprime viabilidade Hub, FCF, DSCR para os relatórios M6/OE4
│   ├── extract_scenarios.py              ← Imprime KPIs dos 4 cenários com e sem Hub
│   └── extract_sem_hub.py               ← Imprime AF e KPIs consolidados sem Hub (comparativo)
│
├── interface/                             ← Interface web (HTML/JSX — sem bundler)
│   ├── index.html
│   ├── app.jsx                           ← Componente raiz React (carregado via CDN)
│   ├── views.jsx                         ← Separadores: DR, Balanço, DFC, Hub, KPIs, …
│   ├── charts.jsx                        ← Componentes de gráficos (Recharts)
│   ├── api.js                            ← Camada de fetch para a API REST
│   └── data.js                           ← Mapeamentos e constantes de UI
│
├── src/
│   ├── api/                              ← Camada HTTP (FastAPI)
│   │   ├── __init__.py
│   │   ├── constants.py                  ← Mapeamento famílias de produto
│   │   ├── schemas.py                    ← Schemas Pydantic (request/response)
│   │   ├── serializers.py                ← Serialização JSON + helpers FSE mensal
│   │   ├── summary.py                    ← Geração de relatórios sumário
│   │   └── routes/
│   │       ├── __init__.py               ← Agregador de rotas
│   │       ├── assumptions.py            ← GET/POST pressupostos
│   │       ├── pressupostos.py           ← Gestão orçamentos
│   │       ├── scenarios.py              ← Execução de cenários + /api/run
│   │       ├── custom_scenarios.py       ← CRUD cenários customizados
│   │       ├── rolling.py                ← Rolling forecast mensal
│   │       ├── export.py                 ← GET /api/export/excel → ficheiro .xlsx (openpyxl)
│   │       │                                 Folhas: DR, Balanço, DFC, KPIs, FSE, Pessoal,
│   │       │                                 Produção, Pressupostos, Hub_Viabilidade*, Hub_Divida*, Info
│   │       │                                 (* apenas quando hub_on=true)
│   │       ├── hub.py                    ← Projecto Hub Logístico (M6)
│   │       │                                 GET /api/hub/viability       → VAL, TIR, Payback, IR
│   │       │                                 GET /api/hub/tornado          → sensibilidade VAL
│   │       │                                 GET /api/hub/break-even       → ponto crítico VAL=0
│   │       │                                 GET /api/hub/viabilidade-cenarios → VAL por cenário
│   │       │                                 GET /api/hub/consolidado      → Hub+Ecogres+Grupo
│   │       │                                 GET /api/hub/monte-carlo      → Monte Carlo VAL/TIR
│   │       │                                 GET /api/hub/debt-service     → DSCR anual (OE4)
│   │       │                                 GET /api/hub/investment-map   → CAPEX pools + NFM (OE4)
│   │       ├── ecogres.py                ← Subsidiária Ecogres
│   │       ├── smart.py                  ← GET /api/smart/tracker (objetivos SMART)
│   │       └── yaml_editor.py            ← Edição de YAML em runtime (dev)
│   │
│   └── engine/                           ← Motor de cálculo financeiro
│       ├── __init__.py
│       ├── config.py
│       │
│       ├── inputs/                       ← Carregamento de dados e configuração
│       │   ├── __init__.py               ← Exporta: load, Assumptions, Base2024, Schedules, MESES, …
│       │   ├── loader.py                 ← Orquestrador YAML + cenários (_SCENARIO_OVERRIDES)
│       │   │                                 Cenários built-in: Base, Upside, Downside, Stress,
│       │   │                                 Hub_Ativo — overrides com spreads reais (Filosofia B)
│       │   │                                 Haircuts hub: Downside −15% / Stress −30% sobre
│       │   │                                 poupança base 480k€ (fases 1+2 integradas)
│       │   ├── models.py                 ← Dataclasses: Assumptions, Base2024, Schedules
│       │   ├── paths.py                  ← Caminhos absolutos para todos os YAML
│       │   ├── constants.py              ← MESES, ANOS, PRODUTOS, MERCADORIAS
│       │   ├── yaml_io.py                ← I/O, normalização e merge YAML
│       │   └── custom_scenarios.py       ← CRUD cenários customizados
│       │
│       ├── data/                         ← Dados de configuração (YAML)
│       │   ├── historico/
│       │   │   └── 2024/
│       │   │       ├── base.yaml         ← Balanço, DR, DFC reais 2024 (imutável)
│       │   │       ├── mix.yaml          ← Mix real 2024 por mercado/canal
│       │   │       ├── produtos.yaml     ← sales_mix e pvu_base 2024 por produto
│       │   │       └── mercadorias.yaml  ← sales_mix, pvu_base, mix_regiao, sazonalidade 2024
│       │   │
│       │   ├── pressupostos/
│       │   │   ├── globais.yaml          ← Fiscal (IVA/IRC/SS/TSU), prazos, caixa, distribuição,
│       │   │   │                             ESG, rendimentos_financeiros_crescimento (2,5%/a)
│       │   │   │                             PMR_dias: 45 · PMP_Inventarios_dias: 55
│       │   │   │                             (2025+, objetivo renegociação fornecedores;
│       │   │   │                              2024 usa saldo auditado R&C 2024 diretamente)
│       │   │   ├── investimento.yaml     ← CAPEX BAU Grestel, taxas de depreciação
│       │   │   ├── 2025/
│       │   │   │   ├── macro.yaml        ← Inflação mensal 2025, EUR/USD mensal 2025
│       │   │   │   ├── vendas.yaml       ← Crescimento volume/PVU por produto 2025
│       │   │   │   ├── custos.yaml       ← FSE, pessoal, CMVMC 2025
│       │   │   │   └── mix.yaml          ← Mix USA/ROW dentro EXT e mix por canal/produto × mercado
│       │   │   └── 2026_2029/
│       │   │       ├── macro.yaml        ← Inflação anual 2026-29, EUR/USD anual
│       │   │       ├── vendas.yaml       ← Crescimento volume/PVU plurianual (spreads reais)
│       │   │       └── custos.yaml       ← FSE, pessoal, CMVMC plurianual
│       │   │
│       │   ├── master/
│       │   │   ├── produtos.yaml         ← Estrutura de custos estável (cip, detalhe_mp)
│       │   │   ├── mercadorias.yaml      ← Custo de compra (pcu) por família
│       │   │   ├── fse_rubricas.yaml     ← Contrato 14 rubricas FSE
│       │   │   └── smart_objetivos.yaml  ← 5 objetivos SMART: targets, anos, operadores
│       │   │
│       │   ├── computed/
│       │   │   └── schedules.yaml        ← Gerado: investimento, financiamento, EOEP saldos
│       │   │
│       │   ├── cenarios/
│       │   │   └── custom_scenarios.yaml ← Apenas cenários customizados adicionais.
│       │   │                                 Os cenários built-in (Base/Upside/Downside/
│       │   │                                 Stress/Hub_Ativo) são definidos em loader.py
│       │   │                                 (_SCENARIO_OVERRIDES) e têm prioridade.
│       │   │                                 O toggle Hub é ortogonal ao cenário.
│       │   │
│       │   └── subsidiarias/
│       │       ├── ecogres/
│       │       │   └── ecogres_assumptions.yaml
│       │       └── hub_logistico/
│       │           └── m6_hub_assumptions.yaml
│       │               ← Hub Logístico 4.0 — Costa Nova (ZI Vagos)
│       │               ← CAPEX 6 000k€ (fases 1+2): 7 pools, cronograma 2025-2026
│       │               ← Financiamento: Banco 4 500k@4,15% + PT2030 2 700k (45%)
│       │               ← Benefícios: poupança 480k€/a + quebras 80k€/a + B2C 500-1150k€/a
│       │               ← Libertação inventário: 1 250k€ 2026 + 1 250k€ 2027 (faseada)
│       │               ← RFAI: 600k€ (10% × 6 000k€ elegível, CFI art. 22-23)
│       │               ← ATL_operacional: 39 570k€ → CAPEX/ATL = 15,2% ≥ 15% (PEF M6)
│       │
│       ├── operacional/                  ← Módulos operacionais (DR + mensais)
│       │   ├── __init__.py
│       │   ├── vendas.py                 ← VN anual e mensal (vendas_mensais_2025) ← MENSAL
│       │   ├── produção.py               ← Planeamento de produção anual
│       │   ├── inventarios.py            ← Saldos de inventário anual
│       │   ├── cmvmc.py                  ← CMVMC anual (produtos + mercadorias)
│       │   ├── pessoal.py                ← Remunerações, encargos, detalhe contabilístico e departamental
│       │   ├── fornecedores.py           ← Saldo de fornecedores anual
│       │   ├── clientes.py               ← Saldo de clientes anual
│       │   └── fse.py                    ← FSE anual + fse_detalhe_mensal_2025 ← MENSAL
│       │
│       ├── investimento/
│       │   ├── __init__.py
│       │   └── investimento.py           ← CAPEX e calendário de investimento
│       │
│       ├── financiamento/
│       │   ├── __init__.py
│       │   ├── financiamento.py          ← Empréstimos e mapas de dívida
│       │   └── tesouraria.py             ← build_eoep_mensal ← MENSAL
│       │                                   build_tesouraria_mensal ← MENSAL
│       │                                   build_dr_mensal ← MENSAL
│       │                                   rolling_update
│       │
│       ├── demonstracoes/
│       │   ├── __init__.py
│       │   ├── statements.py             ← Orquestrador: DR → Balanço (df_eoep_mensal) → DFC
│       │   ├── dr.py                     ← build_dr (anual 2024-2029)
│       │   │                                 _irc(): ICE → coleta → SIFIDE → RFAI → Trib.Aut.
│       │   │                                 rend_financeiros cresce 2,5%/a (globais.yaml)
│       │   ├── balanco.py                ← build_balanco (plug tesouraria: caixa_min 500k / caixa_max 3 500k)
│       │   ├── dfc.py                    ← build_dfc (método indirecto anual)
│       │   ├── nfm.py                    ← NFM anual
│       │   └── rolling_forecast_mensal.py← Balanço+DFC+NFM mensais integrados
│       │
│       ├── modelo/                       ← Orquestração principal
│       │   ├── __init__.py
│       │   ├── model.py                  ← run_model() → dfs com todos os outputs
│       │   │                               Outputs mensais 2025: eoep_mensal_2025,
│       │   │                               vendas_mensal_2025, dr_mensal_2025,
│       │   │                               tesouraria_mensal_2025, fse_detalhe_mensal_2025
│       │   ├── eoep.py                   ← eoep_calendario_mensal ← MENSAL (bottom-up 2025)
│       │   │                               eoep_anual (df_mensal= para derivar saldos 2025)
│       │   ├── kpis.py                   ← KPIs e rácios financeiros + gas_por_peca_anual (ESG)
│       │   ├── smart.py                  ← build_smart_tracker() → status cumprido/em_risco/nao_cumprido
│       │   ├── pressupostos.py           ← Análise de orçamentos
│       │   └── sensitivity.py            ← Análise de sensibilidade (tornado)
│       │
│       └── projetos/
│           ├── __init__.py
│           ├── ecogres.py                ← Modelo financeiro Ecogres
│           ├── hub_logistico.py          ← Modelo financeiro Hub Logístico 4.0
│           │                                 hub_capex()           — CAPEX + depr. + juros cap. (NCRF 10)
│           │                                 hub_financing()       — empréstimo CGD/BPI (carência 2025-27)
│           │                                 hub_nfm()             — ΔNFM anual (stock + clientes − forn.)
│           │                                 hub_rfai()            — crédito RFAI anual (CFI art. 22-23)
│           │                                 hub_dr_impact()       — poupanças + B2C + PT2030 + inventário
│           │                                                          libertacao_cronograma: split 2026/2027
│           │                                 hub_dfc_impact()      — fluxos caixa hub (investim./financ.)
│           │                                 hub_fcf()             — FCFF para VAL/TIR
│           │                                 mapa_servico_divida() — DSCR anual (OE4)
│           │                                 mapa_tesouraria_mensal() — desdobramento mensal 2025-26
│           │                                 viabilidade_hub()     — VAL, TIR, Payback, IR, Valor Residual
│           │                                 sensibilidade_hub()   — one-at-a-time VAL
│           │                                 tornado_hub()         — tornado 6 variáveis críticas
│           │                                 ponto_critico_hub()   — break-even VAL = 0 por driver
│           └── monte_carlo_hub.py        ← Monte Carlo Hub: N simulações, 6 drivers
│                                             distribuições triangulares + normal truncada
│                                             output: P(VAL>0), P(TIR>WACC), percentis, correlações
```

---

## Fluxo de dados: YAML → `run_model` → API

```
YAML inputs
  ├── historico/2024/      ─┐
  ├── pressupostos/2025/    ├── load(cenario) ──► Assumptions
  ├── pressupostos/2026-29/ │                    Base2024
  ├── master/               │                    Schedules
  └── computed/schedules ───┘
                                    │
                                    ▼
                              run_model()
                                    │
                         ┌──────────┴──────────────────────┐
                         │ Mensais 2025 (bottom-up)         │
                         │  build_eoep_mensal()             │
                         │  vendas_mensais_2025()           │
                         │  build_dr_mensal()               │
                         │  build_tesouraria_mensal()       │
                         │  fse_detalhe_mensal_2025()       │
                         └──────────┬──────────────────────┘
                                    │ df_eoep_mensal (2025 bottom-up)
                                    ▼
                         build_statements()
                           DR → Balanço → DFC
                           (EOEP 2025 derivado do mensal)
                                    │
                                    ▼
                              dfs (dict)
                                    │
                         dataframe_to_records()
                                    │
                                    ▼
                              API JSON
```

---

## Módulos com outputs mensais de 2025

| Módulo | Função | Output |
|---|---|---|
| `engine/modelo/eoep.py` | `eoep_calendario_mensal()` | IVA, SS, IRC PPC mensal |
| `engine/operacional/vendas.py` | `vendas_mensais_2025()` | VN por produto/mercado/mês |
| `engine/operacional/fse.py` | `fse_detalhe_mensal_2025()` | 14 rubricas FSE por mês |
| `engine/financiamento/tesouraria.py` | `build_eoep_mensal()` | wrapper público do calendário EOEP |
| `engine/financiamento/tesouraria.py` | `build_dr_mensal()` | DR mensal 2025 (26 colunas) |
| `engine/financiamento/tesouraria.py` | `build_tesouraria_mensal()` | Orçamento tesouraria 2025 |
| `engine/demonstracoes/rolling_forecast_mensal.py` | `build_rolling_forecast()` | Balanço+DFC+NFM mensais |

---

## Suite de testes

```
tests/
├── conftest.py                       ← Fixtures pytest (cenário Base pré-carregado)
├── check_logic.py                    ← Script de verificação de coerência lógica do modelo
├── test_api_detail.py                ← Detalhe dos campos da API
├── test_api_model.py                 ← Integridade do modelo (DR ↔ Balanço ↔ DFC)
├── test_api_reconcil.py              ← Reconciliações financeiras (identidades contabilísticas)
├── test_api_structure.py             ← Estrutura das respostas JSON
├── test_fse_mensal.py                ← FSE mensal: 14 rubricas por mês
├── test_fse_reconciliations.py       ← FSE anual ↔ mensal
├── test_hub_investment_map.py        ← Mapa de investimento Hub (CAPEX pools + NFM)
├── test_keys.py                      ← Contrato de chaves da API (sem regressões)
├── test_kpis_contract.py             ← KPIs: presença e tipos
└── test_mensais_reconciliacao.py     ← 41 testes: estrutura, reconciliação mensal↔anual, EOEP fiscal
```
