# GrestelPy — Guia do Docente

> Motor financeiro da empresa Grestel · PEF 2025-26 · Grupo 18 · ISCA-UA · Engine v0.9.9

---

## 1. Iniciar o servidor

**Windows (sem Python instalado):** `setup-win.bat` uma vez → `start-win.bat`

**Mac (sem Python instalado):** `./setup-mac.sh` uma vez → `./start-mac.sh`

> Mac: na primeira vez pode ser necessário: `chmod +x setup-mac.sh start-mac.sh`

**Com Python instalado:**

```bash
pip install -r requirements.txt
python server.py
```

| Endereço | Descrição |
|---|---|
| `http://localhost:8000/` | Interface web |
| `http://localhost:8000/interface/` | Interface web (direto) |
| `http://localhost:8000/docs` | Swagger UI — documentação interactiva de todos os endpoints |
| `http://localhost:8000/health` | Estado do servidor (`{"ok": true}`) |

---

## 2. O que o sistema produz

**Anuais (2024–2029):**
- Demonstração de Resultados (DR)
- Balanço
- Demonstração de Fluxos de Caixa (DFC)
- KPIs e rácios financeiros
- FSE por rubrica (14 rubricas)
- Pessoal — detalhe contabilístico e departamental
- Orçamento de produção por produto

**Mensais de 2025 (M3):**

| Output | Chave em `run_model` | Dimensão |
|---|---|---|
| Calendário fiscal EOEP | `eoep_mensal_2025` | 12 meses × 9 colunas |
| Vendas por produto/mercado | `vendas_mensal_2025` | 216 linhas × 4 colunas |
| DR mensal completa | `dr_mensal_2025` | 12 meses × 26 colunas |
| Orçamento de tesouraria | `tesouraria_mensal_2025` | 12 meses × 15 colunas |
| FSE por rubrica | `fse_detalhe_mensal_2025` | 14 rubricas × 12 meses |
| Pessoal mensal | `pessoal_mensal_2025` | 12 meses × 2 colunas |
| CMVMC mensal | `cmvmc_mensal_2025` | 12 meses × 2 colunas |

> **Princípio bottom-up para 2025:** os saldos EOEP no Balanço de 2025 são derivados do calendário mensal — não lidos de YAML.
> - EOEP devedor/credor IVA = saldo IVA de Nov + Dez (pagamento M+2)
> - EOEP credor SS = SS de Dezembro (pagamento M+1)
> - EOEP credor IRC = IRC do ano menos pagamentos por conta efectuados

**Rolling Forecast:** `GET /api/rolling-forecast/mensal` — Balanço+DFC+NFM mensais (loop integrado DFC→Caixa→Balanço)

---

## 3. Cenários

| Cenário | Volume vendas | PVU (spread real) | FSE | Pessoal |
|---|---|---|---|---|
| **Base** | YAML | YAML | YAML | YAML |
| **Upside** | +5%/a (2025-28), +4% em 2029 | +2,7% (2025) → +1,4% (2029) | +2,3–2,4% (2028-29) | — |
| **Downside** | +2%/a (2025-27), +1% em 2028-29 | −1,2% (2025) → −0,6% (2029) | +1,8–4,3% | — |
| **Stress** | −2% em 2025, recupera +1–2% | −2,2% (2025) → +0,4% (2029) | +3,7–4,3% | +2,7% |

Os spreads são **reais** — o motor compõe com a inflação de `macro.yaml` em runtime:
`taxa_nominal = (1 + inflação) × (1 + spread_real) − 1`

O toggle **Hub Logístico** é ortogonal ao cenário (aplica-se a qualquer combinação). Quando activo, incorpora automaticamente no DR/Balanço/DFC:

| Efeito Hub | Magnitude |
|---|---|
| Poupança operacional (pessoal + FSE) | €480k/ano base (cresce 4%/a nominal) |
| Redução de quebras | €80k/ano |
| VN incremental B2C / logística 3ª partes | €500k–€1 150k/ano (2026-2029) |
| CAPEX e depreciações | €6 000k em 7 pools (fases 1+2) |
| Financiamento CGD/BPI | €4 500k @ 4,15%, carência 2025-2027 |
| Subsídio PT2030 | €2 700k (45% CAPEX, NCRF 22) |
| Libertação de inventário | €1 250k em 2026 + €1 250k em 2027 |
| Crédito fiscal RFAI | €600k total (CFI art. 22-23) |
| NFM incremental | Stock manutenção + crédito clientes (Fase 2) |

> **Limiar PEF M6:** CAPEX/ATL_operacional = 6 000k / 39 570k = **15,2%** ≥ 15% ✓

Cenários customizados adicionais em `src/engine/data/cenarios/custom_scenarios.yaml` (gerido pela API). Os built-in são definidos em `loader.py` (`_SCENARIO_OVERRIDES`).

---

## 4. Endpoints

### 4.1 Todos os cenários

```
GET /api/scenarios/all?hub_on=false&ecogres_on=false
```

DR, Balanço, DFC, KPIs, FSE anual e mensal, Pessoal e Produção para os quatro cenários.

---

### 4.2 Cenário único com overrides

```
POST /api/run
```

```json
{
  "cenario": "Base",
  "hub_on": false,
  "ecogres_on": false,
  "assumptions": { "crescimento_volume_vendas": { "2026": 0.04 } },
  "persist": false
}
```

---

### 4.3 Rolling Forecast Mensal

```
GET /api/rolling-forecast/mensal?scenario=Base
```

| Chave | Conteúdo |
|---|---|
| `dr_mensal` | DR mensal 2025 (12 linhas) |
| `balanco_mensal` | Balanço mensal 2025 (Caixa derivada do DFC) |
| `dfc_mensal` | DFC mensal pelo método indirecto |
| `nfm_mensal` | NFM e Ciclo de Conversão de Caixa por mês |
| `tesouraria_completa` | Recebimentos, pagamentos, serviço dívida, CAPEX |

---

### 4.4 Pressupostos efectivos

```
GET /api/assumptions/effective?cenario=Base&hub_on=false&ecogres_on=false
```

Pressupostos consolidados tal como o motor os usa — útil para auditar inputs.

---

### 4.5 Hub Logístico (M6)

```
GET /api/hub/viability?irc_taxa=0.225
GET /api/hub/tornado?irc_taxa=0.225
GET /api/hub/break-even
GET /api/hub/viabilidade-cenarios
GET /api/hub/consolidado
GET /api/hub/monte-carlo?n=1000
GET /api/hub/debt-service
GET /api/hub/investment-map
```

| Endpoint | Retorna |
|---|---|
| `/hub/viability` | VAL, TIR, Payback simples e actualizado, valor terminal, IR, FCF |
| `/hub/tornado` | Análise de sensibilidade one-at-a-time às variáveis críticas |
| `/hub/break-even` | Ponto crítico (VAL = 0) por driver |
| `/hub/viabilidade-cenarios` | VAL/TIR Hub nos 4 cenários |
| `/hub/consolidado` | Hub + Ecogres + Grestel grupo (comparativo) |
| `/hub/monte-carlo` | Monte Carlo 100–5 000 simulações (VAL + TIR, 6 drivers) |
| `/hub/debt-service` | Mapa de serviço da dívida (DSCR anual) — OE4 |
| `/hub/investment-map` | Mapa de investimento (CAPEX pools + NFM) — OE4 |

---

### 4.6 Enquadramento Estratégico M6

```
GET /api/enquadramento
```

Regras de investimento, rácios de referência e limites para o Plano de Negócios M6.

---

### 4.7 Subsidiária Ecogres

```
GET /api/ecogres
```

Parâmetros opcionais: `hub_on`, `cresc_subc`, `cresc_ced`, `cresc_custos`, `cresc_dep`, `alpha_sem_hub`, `alpha_com_hub`, `transfer_price`, `transfer_inicio`, `irc_taxa`.

---

### 4.8 SMART Tracker

```
GET /api/smart/tracker?cenario=Base&hub_on=false&ecogres_on=false
```

| Campo | Descrição |
|---|---|
| `id` | Identificador do objetivo (`vn_2025`, `ebitda_margin_2025`, …) |
| `categoria` | `economica` / `financeira` / `operacional` / `esg` |
| `valor` | Valor projetado pelo modelo |
| `alvo` | Target definido em `smart_objetivos.yaml` |
| `status` | `cumprido` / `em_risco` (desvio ≤5%) / `nao_cumprido` |
| `desvio_pct` | `(valor − alvo) / |alvo|` |

| ID | KPI | Alvo | Ano(s) |
|---|---|---|---|
| `vn_2025` | `kpis.vn` | ≥ 45,6 M€ | 2025 |
| `ebitda_margin_2025` | `kpis.margem_ebitda` | ≥ 19,5% | 2025 |
| `autonomia_financeira` | `kpis.autonomia_financeira` | ≥ 35% | 2025–2029 |
| `ccc_2027` | `kpis.ciclo_caixa` | ≤ 260 dias | 2027 |
| `pmp_2025` | `kpis.pmp_dias` | ≤ 55 dias | 2025 |
| `gas_peca_2026` | `gas_por_peca_anual.var_vs_2024` | ≤ −10% | 2026 |

---

### 4.9 Cenários Customizados

```
GET    /api/custom-scenarios
POST   /api/custom-scenarios/{nome}
DELETE /api/custom-scenarios/{nome}
```

---

### 4.10 Exportação Excel

```
GET /api/export/excel?cenario=Base&hub_on=false&ecogres_on=true
```

| Folha | Conteúdo |
|---|---|
| DR · Balanço · DFC · KPIs | Demonstrações 2024-2029 |
| FSE | FSE anual por rubrica (14 rubricas) |
| Pessoal | Detalhe contabilístico |
| Produção | Orçamento de produção por produto |
| Pressupostos | Secção / Parâmetro / Valor |
| Hub_Viabilidade | VAL, TIR, Payback, IR, FCF *(hub_on=true)* |
| Hub_Divida | Mapa de serviço da dívida *(hub_on=true)* |
| Info | Metadados (cenário, data, versão) |

---

### 4.11 Configuração

```
GET /api/config/years         → [2024, 2025, 2026, 2027, 2028, 2029]
GET /api/config/fse-rubricas  → rubricas FSE e chaves YAML
```

---

## 5. Dados de entrada (YAML editáveis)

| Ficheiro | Conteúdo | Editável |
|---|---|---|
| `pressupostos/globais.yaml` | Prazos (PMR 45d / **PMP 55d** 2025+), caixa mín/máx, ESG. PMP histórico 2024: 63d (saldo auditado); 55d = objetivo renegociação fornecedores (Diretiva 2011/7/UE). | ✓ |
| `pressupostos/fiscal.yaml` | Taxas IRC / IVA / SS / TSU | ✓ |
| `pressupostos/sazonalidade.yaml` | Perfis mensais por mercado | ✓ |
| `pressupostos/2025/macro.yaml` | Inflação mensal e EUR/USD mensal 2025 | ✓ |
| `pressupostos/2025/vendas.yaml` | Crescimento volume e PVU por produto 2025 | ✓ |
| `pressupostos/2025/custos.yaml` | FSE, pessoal, CMVMC 2025 | ✓ |
| `pressupostos/2025/mix.yaml` | Mix USA/ROW (EXT) e mix canal/produto × mercado — actualizar com vendas reais mensais | ✓ |
| `pressupostos/2026_2029/` | Macro, vendas e custos plurianuais | ✓ |
| `historico/2024/base.yaml` | Balanço, DR e DFC reais 2024 | ✗ |
| `master/smart_objetivos.yaml` | Targets SMART — editar sem tocar em código | ✓ |
| `master/enquadramento_estrategico.yaml` | Regras e limites M6 | ✓ |
| `computed/schedules.yaml` | CAPEX, amortizações, juros, saldos BAU Grestel | ✓ |
| `subsidiarias/hub_logistico/m6_hub_assumptions.yaml` | Todos os pressupostos do Hub M6 | ✓ |
| `subsidiarias/ecogres/ecogres_assumptions.yaml` | Pressupostos Ecogres | ✓ |

---

## 6. Cobertura dos requisitos PEF

| Requisito M3/M6 | Endpoint / Chave | Estado |
|---|---|---|
| Orçamento de vendas mensal | `vendas_mensal_2025` | ✅ |
| Orçamento de produção | `producao_anual` | ✅ |
| Orçamento gastos com pessoal | `pessoal_contab_anual`, `pessoal_depart_anual` | ✅ |
| Orçamento FSE mensal (14 rubricas) | `fse_detalhe_mensal_2025` | ✅ |
| Orçamento CMVMC | `cmvmc_anual` (anual) + `cmvmc_mensal_2025` (mensal) | ✅ |
| Calendarização fiscal (IVA, SS, IRC) | `eoep_mensal_2025` | ✅ |
| Orçamento de tesouraria mensal | `tesouraria_mensal_2025` | ✅ |
| Necessidades de Fundo de Maneio | `nfm_mensal` (rolling forecast) | ✅ |
| DR, DFC, Balanço previsionais (5 anos) | `GET /api/scenarios/all` | ✅ |
| Rolling forecast mensal | `GET /api/rolling-forecast/mensal` | ✅ |
| KPIs mensuráveis | `kpis` em `run_model` | ✅ |
| Análise de cenários (4 cenários) | `GET /api/scenarios/all` | ✅ |
| Análise de sensibilidade | `GET /api/hub/tornado` | ✅ |
| VAL, TIR, Payback Hub M6 | `GET /api/hub/viability` | ✅ |
| Monte Carlo (risco) | `GET /api/hub/monte-carlo` | ✅ |
| Mapa de investimento OE4 | `GET /api/hub/investment-map` | ✅ |
| Mapa serviço da dívida OE4 | `GET /api/hub/debt-service` | ✅ |
| Enquadramento estratégico M6 | `GET /api/enquadramento` | ✅ |
| Subsidiária Ecogres | `GET /api/ecogres` | ✅ |
| Objetivos SMART (M3) | `GET /api/smart/tracker` | ✅ |
| Exportação Excel | `GET /api/export/excel` | ✅ |

---

## 7. Base BAU para M6

Valores de `schedules.yaml` ajustados para reflectir o plano estratégico BAU da gerência antes de activar o Hub:

| Parâmetro | Anterior | BAU M6 | Justificação |
|---|---|---|---|
| CAPEX AFT 2025 | 500k | **900k** | Flagship Madrid + outlet Lisboa + modernização |
| Amortizações 2025 | 7.951k | **5.531k** | Paga só IAPMEI; moratória em BPI/Santander/CGD/Abanca |
| Empréstimos NC fim-2025 | 8.873k | **12.549k** | Dívida comercial mantida (sem amortização) |
| Empréstimos C fim-2025 | 2.043k | **788k** | Apenas Santander + Locações vencíveis em 2026 |
| Juros 2025 | 382k | **419k** | Maior dívida média em circulação |

Gearing estimado fim-2025: **44%** (intervalo alvo 40–65%).

---

## 8. Testes automatizados

```bash
pytest tests/
```

`test_mensais_reconciliacao.py` — **41 testes**, organizados em 3 grupos:

| Grupo | Nº testes | O que verifica |
|---|---|---|
| Estrutura e regressão | 20 | 12 linhas, colunas obrigatórias, sem NaN, 14 salários, sazonalidade de Agosto |
| Reconciliação mensal ↔ anual | 9 | `sum(dr_mensal.vn) ≈ dr[2025].vn` e análogo para CMVMC, FSE, pessoal |
| EOEP fiscal derivado | 12 | IVA Nov+Dez; art.º 105.º CIRC (PPC Jul/Set/Dez); SS desfasado 1 mês |

> O DR mensal é simplificado (sem `outros_rendimentos`), pelo que o EBITDA mensal somado não reconcilia com o EBITDA anual completo — comportamento esperado e documentado nos docstrings.

---

## 9. Verificação rápida

```bash
# Estado do servidor
curl http://localhost:8000/health

# Cenário Base (todos os outputs)
curl "http://localhost:8000/api/scenarios/all"

# Base com Hub + Ecogres
curl "http://localhost:8000/api/scenarios/all?hub_on=true&ecogres_on=true"

# Rolling forecast mensal
curl "http://localhost:8000/api/rolling-forecast/mensal?scenario=Base"

# Viabilidade Hub M6
curl "http://localhost:8000/api/hub/viability"

# Monte Carlo (1 000 simulações)
curl "http://localhost:8000/api/hub/monte-carlo?n=1000"

# Pressupostos efectivos Upside
curl "http://localhost:8000/api/assumptions/effective?cenario=Upside"

# Suite de testes
pytest tests/
```

---

## 10. Notas técnicas

- Servidor na porta **8000**; alterar com `--port XXXX`.
- Modo `--reload` reinicia quando qualquer `.py` ou `.yaml` é alterado.
- Erros retornados em JSON com campos `error`, `detail` e `path`.
- Os spreads reais nos cenários são compostos com a inflação de `macro.yaml` em runtime — alterar a inflação propaga automaticamente a todos os drivers.
- O calendário EOEP mensal é calculado **antes** das demonstrações anuais: os saldos Balanço 2025 derivam dos mensais (bottom-up).

---

*GrestelPy · Engine v0.9.6 · PEF 2025-26 · Grupo G18 · ISCA-UA · actualizado 2026-05-28*
