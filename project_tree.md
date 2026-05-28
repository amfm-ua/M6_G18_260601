# GrestelPy — Project Tree

> Engine v0.9.9 · actualizado 2026-05-28

```
GrestelPy_G18/
├── server.py                              ← FastAPI entry point (porta 8000)
├── SETUP.bat                              ← Instala Python portátil + dependências (Windows, 1ª vez)
├── start.bat / start.sh                   ← Lança o servidor (Windows / Linux-Mac)
├── pyproject.toml                         ← Configuração do pacote (Python ≥ 3.10)
├── requirements.txt                       ← Dependências runtime (usado pelo SETUP.bat com pip)
├── uv.lock                                ← Lock file do ambiente de desenvolvimento (uv)
├── README.md                              ← Visão geral e arranque rápido
├── guia_docentes.md                       ← Outputs, endpoints e cobertura PEF
├── project_tree.md                        ← Este ficheiro
├── .gitignore
│
├── docs/                                  ← Documentos de apoio ao relatório M6
│   ├── correcao_irc_taxa_efetiva.md
│   ├── fcf_modelacao_hub.md
│   ├── monte_carlo_distribuicoes.md
│   ├── plano_financiamento_hub.md
│   ├── pressupostos_sinteticos.md
│   ├── relatorio_m6_monte_carlo_hub.md
│   └── sintese_m6_enquadramento_estrategico.md
│
├── scripts/                               ← Scripts one-off (entrega OE4)
│   ├── audit_oe04_delivery.py
│   ├── patch_oe04_docx.py
│   └── patch_oe04_vala_xlsx.py
│
├── interface/                             ← Interface web (HTML/JSX — sem bundler)
│   ├── index.html
│   ├── app.jsx                           ← Componente raiz React (carregado via CDN)
│   ├── views.jsx                         ← Separadores: DR, Balanço, DFC, Hub, KPIs, …
│   ├── charts.jsx                        ← Componentes de gráficos (Recharts)
│   ├── api.js                            ← Camada de fetch para a API REST
│   └── data.js                           ← Mapeamentos e constantes de UI
│
├── tests/                                 ← Suite de testes pytest
│   ├── conftest.py                       ← Fixtures (cenário Base pré-carregado)
│   ├── check_logic.py                    ← Verificação de coerência lógica do modelo
│   ├── test_api_detail.py                ← Detalhe dos campos da API
│   ├── test_api_model.py                 ← Integridade DR ↔ Balanço ↔ DFC
│   ├── test_api_reconcil.py              ← Reconciliações financeiras
│   ├── test_api_structure.py             ← Estrutura das respostas JSON
│   ├── test_balanco_rt_regression.py     ← Regressão Balanço em runtime
│   ├── test_fse_mensal.py                ← FSE mensal: 14 rubricas × 12 meses
│   ├── test_fse_reconciliations.py       ← FSE anual ↔ mensal
│   ├── test_hub_investment_map.py        ← Mapa de investimento Hub (CAPEX pools + NFM)
│   ├── test_hub_viabilidade_cenarios.py  ← VAL/TIR Hub nos 4 cenários
│   ├── test_keys.py                      ← Contrato de chaves da API (sem regressões)
│   ├── test_kpis_contract.py             ← KPIs: presença e tipos
│   ├── test_mensais_reconciliacao.py     ← 41 testes: estrutura, mensal↔anual, EOEP fiscal
│   └── test_rolling_articulacao.py       ← Articulação rolling forecast
│
└── src/
    ├── api/                              ← Camada HTTP (FastAPI)
    │   ├── constants.py                  ← Mapeamento famílias de produto
    │   ├── schemas.py                    ← Schemas Pydantic (request/response)
    │   ├── serializers.py                ← Serialização JSON + helpers FSE mensal
    │   ├── summary.py                    ← Geração de relatórios sumário
    │   └── routes/
    │       ├── __init__.py               ← Agregador de rotas
    │       ├── assumptions.py            ← GET/POST pressupostos
    │       ├── custom_scenarios.py       ← CRUD cenários customizados
    │       ├── ecogres.py                ← Subsidiária Ecogres
    │       ├── enquadramento.py          ← GET /api/enquadramento (M6)
    │       ├── export.py                 ← GET /api/export/excel → .xlsx (openpyxl)
    │       ├── hub.py                    ← Hub Logístico M6 (todos os endpoints /api/hub/*)
    │       ├── pressupostos.py           ← Gestão orçamentos
    │       ├── rolling.py                ← Rolling forecast mensal
    │       ├── scenarios.py              ← Execução de cenários + POST /api/run
    │       ├── smart.py                  ← GET /api/smart/tracker
    │       └── yaml_editor.py            ← Edição de YAML em runtime (dev)
    │
    └── engine/                           ← Motor de cálculo financeiro
        ├── config.py
        │
        ├── inputs/                       ← Carregamento e configuração
        │   ├── constants.py              ← MESES, ANOS, PRODUTOS, MERCADORIAS
        │   ├── custom_scenarios.py       ← CRUD cenários customizados
        │   ├── loader.py                 ← Orquestrador YAML + _SCENARIO_OVERRIDES
        │   │                                 Cenários built-in: Base, Upside, Downside, Stress
        │   │                                 Haircuts hub: Downside −15% / Stress −30%
        │   ├── models.py                 ← Dataclasses: Assumptions, Base2024, Schedules
        │   ├── paths.py                  ← Caminhos absolutos para todos os YAML
        │   ├── validators.py             ← Validação de inputs
        │   └── yaml_io.py                ← I/O, normalização e merge YAML
        │
        ├── data/                         ← Dados de configuração (YAML)
        │   ├── _defaults/                ← Template inicial (valores por omissão)
        │   ├── historico/2024/           ← Dados reais 2024 (imutáveis)
        │   │   ├── base.yaml             ← Balanço, DR, DFC reais 2024
        │   │   ├── mix.yaml              ← Mix real 2024 por mercado/canal
        │   │   ├── produtos.yaml         ← sales_mix e pvu_base 2024 por produto
        │   │   └── mercadorias.yaml      ← sales_mix, pvu_base, sazonalidade 2024
        │   ├── pressupostos/
        │   │   ├── globais.yaml          ← Prazos (PMR 45d / PMP 55d 2025+), caixa, ESG
        │   │   ├── fiscal.yaml           ← Taxas IRC / IVA / SS / TSU
        │   │   ├── sazonalidade.yaml     ← Perfis mensais por mercado
        │   │   ├── investimento.yaml     ← CAPEX BAU Grestel, taxas de depreciação
        │   │   ├── 2025/                 ← macro · vendas · custos · mix
        │   │   └── 2026_2029/            ← macro · vendas · custos
        │   ├── master/
        │   │   ├── produtos.yaml         ← Estrutura de custos (CIP, MP) — estável
        │   │   ├── mercadorias.yaml      ← Custo de compra (pcu) por família
        │   │   ├── fse_rubricas.yaml     ← Contrato 14 rubricas FSE
        │   │   ├── smart_objetivos.yaml  ← 5 objetivos SMART: targets, anos, operadores
        │   │   └── enquadramento_estrategico.yaml ← Regras de investimento e rácios M6
        │   ├── computed/
        │   │   └── schedules.yaml        ← CAPEX, amortizações, juros, saldos BAU — editável
        │   └── subsidiarias/
        │       ├── ecogres/ecogres_assumptions.yaml
        │       └── hub_logistico/m6_hub_assumptions.yaml
        │           ← CAPEX 6 000k€ · Banco 4 500k@4,15% · PT2030 2 700k
        │           ← Poupança 480k€/a · RFAI 600k€ · ATL_op 39 570k€
        │
        ├── operacional/
        │   ├── vendas.py                 ← VN anual e vendas_mensais_2025 ← MENSAL
        │   ├── producao.py               ← Orçamento de produção anual
        │   ├── inventarios.py            ← Saldos de inventário anual
        │   ├── cmvmc.py                  ← CMVMC anual
        │   ├── pessoal.py                ← Remunerações, encargos, detalhe contabilístico/departamental
        │   ├── fornecedores.py           ← Saldo fornecedores anual
        │   ├── clientes.py               ← Saldo clientes anual
        │   └── fse.py                    ← FSE anual + fse_detalhe_mensal_2025 ← MENSAL
        │
        ├── investimento/
        │   └── investimento.py           ← CAPEX e calendário de investimento
        │
        ├── financiamento/
        │   ├── financiamento.py          ← Empréstimos e mapas de dívida
        │   └── tesouraria.py             ← build_eoep_mensal · build_dr_mensal
        │                                     build_tesouraria_mensal ← MENSAL
        │
        ├── demonstracoes/
        │   ├── statements.py             ← Orquestrador: DR → Balanço → DFC
        │   ├── balanco.py                ← build_balanco (plug tesouraria: caixa 500k–3 500k)
        │   ├── balanco_funcional.py      ← Análise da estrutura financeira
        │   ├── dfc.py                    ← build_dfc (método indirecto anual)
        │   ├── nfm.py                    ← NFM anual
        │   ├── dr/
        │   │   ├── build.py              ← build_dr (anual 2024-2029)
        │   │   ├── impostos.py           ← _irc(): ICE → coleta → SIFIDE → RFAI → Trib.Aut.
        │   │   ├── loaders.py
        │   │   └── rubricas.py
        │   └── rolling_forecast_mensal/  ← Balanço+DFC+NFM mensais integrados
        │       ├── forecast.py
        │       ├── integrado.py
        │       ├── mensais.py
        │       ├── auxiliares.py
        │       └── reconciliacao.py
        │
        ├── modelo/                       ← Orquestração principal
        │   ├── model.py                  ← run_model() → dict com todos os outputs
        │   ├── enquadramento.py          ← get_enquadramento_completo(), get_regra_investimento()
        │   ├── eoep.py                   ← eoep_calendario_mensal (bottom-up 2025) ← MENSAL
        │   ├── kpis.py                   ← KPIs, rácios, gas_por_peca_anual (ESG)
        │   ├── pressupostos.py           ← Análise de orçamentos
        │   ├── sensitivity.py            ← Análise de sensibilidade (tornado)
        │   └── smart.py                  ← build_smart_tracker()
        │
        └── projetos/
            ├── ecogres.py                ← Modelo financeiro Ecogres
            ├── monte_carlo_hub.py        ← Monte Carlo: N simulações, 6 drivers
            │                                 distribuições triangulares + normal truncada
            │                                 output: P(VAL>0), P(TIR>WACC), percentis
            └── hub_logistico/            ← Hub Logístico 4.0 — Costa Nova (ZI Vagos)
                ├── base.py               ← load() — carrega m6_hub_assumptions.yaml
                ├── capex.py              ← hub_capex(), juros capitalizados (NCRF 10)
                ├── financiamento.py      ← hub_financing(), mapa_servico_divida()
                ├── impacto.py            ← hub_dr_impact(), hub_dfc_impact(), hub_fcf()
                ├── tesouraria.py         ← mapa_tesouraria_mensal()
                └── viabilidade.py        ← viabilidade_hub(), tornado_hub(), ponto_critico_hub()
```

---

## Fluxo de dados: YAML → `run_model` → API

```
YAML inputs
  ├── historico/2024/      ─┐
  ├── pressupostos/2025/    ├── load(cenario) ──► Assumptions + Base2024 + Schedules
  ├── pressupostos/2026-29/ │
  ├── master/               │
  └── computed/schedules ───┘
                                    │
                                    ▼
                              run_model()
                                    │
                  ┌─────────────────┴─────────────────────┐
                  │ Bottom-up 2025 (antes das demonstrações)│
                  │  eoep_calendario_mensal()               │
                  │  vendas_mensais_2025()                  │
                  │  build_dr_mensal()                      │
                  │  build_tesouraria_mensal()              │
                  │  fse_detalhe_mensal_2025()              │
                  └─────────────────┬─────────────────────┘
                                    │ df_eoep_mensal (saldos Balanço 2025)
                                    ▼
                         build_statements()
                           DR → Balanço → DFC
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
| `engine/financiamento/tesouraria.py` | `build_eoep_mensal()` | Wrapper público do calendário EOEP |
| `engine/financiamento/tesouraria.py` | `build_dr_mensal()` | DR mensal 2025 |
| `engine/financiamento/tesouraria.py` | `build_tesouraria_mensal()` | Orçamento tesouraria 2025 |
| `engine/demonstracoes/rolling_forecast_mensal/` | `build_rolling_forecast()` | Balanço+DFC+NFM mensais |
