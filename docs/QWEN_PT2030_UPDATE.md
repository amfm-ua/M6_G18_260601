# QWEN PT2030 Update — 2025-05-30

## Resumo da Decisão

O subsídio **PT2030 a fundo perdido** foi **removido do modelo** como cenário base.

**Fundamento:** A Grestel é uma grande empresa e, nessa condição, não tem elegibilidade ao fundo perdido do Sistema de Incentivos à Inovação Produtiva (exclusivo de PME). Qualquer apoio residual seria upside (≤ 7,5% CAPEX após RFAI), com custo de oportunidade superior ao benefício líquido.

---

## Ficheiros Alterados

### Backend (Python)

| Ficheiro | Alteração |
|----------|-----------|
| `src/engine/projetos/monte_carlo_hub.py` | Removido `pt2030_taxa` de `DRIVERS`, removido `pt2030_approved` de `VALA_EXTRA_DRIVERS`, removido sampling estocástico de PT2030, removido diagnóstico por PT2030 |
| `src/engine/projetos/hub_logistico/viabilidade.py` | Removido `pt2030_taxa` do tornado (sensibilidade), removido branch de driver |
| `src/engine/projetos/hub_logistico/impacto.py` | Estrutura mantida — `pt2030_reconhecimento()` mantém compatibilidade mas devolve €0 com PT2030.montante=0 |
| `src/engine/projetos/contingencia_hub.py` | Funcionalidade de "_remover_pt2030" mantida por retrocompatibilidade |

### Frontend (JavaScript/React)

| Ficheiro | Alteração |
|----------|-----------|
| `interface/views.jsx` | Removidos KPIs condicionais PT2030, diagnóstico de falhas, coluna PV(PT2030) da tabela de stress, labels de drivers |
| `interface/data.js` | `HUB_PT2030_REC` zerado, cash-flow 2027 limpo, DFC fluxo investimento limpo |
| `interface/api.js` | Removido parâmetro `pt2030_prob` de `hubMonteCarloVala()` |

---

## Alterações Detalhadas

### 1. `monte_carlo_hub.py`

**Driver removido:**
```python
# ANTES:
DRIVERS = [
    "dmi_pa_reducao", "dmi_mp_reducao", "dmi_clearing_dias",
    "pt2030_taxa", "b2c", "pessoal", "wacc", "capex",
    ...
]

# DEPOIS:
DRIVERS = [
    "dmi_pa_reducao", "dmi_mp_reducao", "dmi_clearing_dias",
    "b2c", "pessoal", "wacc", "capex",
    ...
]
```

**Drivers VALA removidos:**
```python
# ANTES:
VALA_EXTRA_DRIVERS = ["pt2030_approved", "rfai_utilization", "kd_shock"]
DEFAULT_VALA_EXTRA_DISTRIBUTIONS = {
    "pt2030_approved": {"type": "bernoulli", "p": 0.15},
    ...
}

# DEPOIS:
VALA_EXTRA_DRIVERS = ["rfai_utilization", "kd_shock"]
# PT2030 REMOVIDO (2025-05-30)
```

**Sampling limpo:**
```python
# ANTES (PT2030 sampled):
subsidio = s["pt2030_taxa"] * capex_amostra
proj["financiamento"]["PT2030"]["montante"] = subsidy

# DEPOIS:
# 3. PT2030 REMOVIDO (2025-05-30): Grande empresa sem elegibilidade a fundo perdido.
# O financiamento do Hub baseia-se exclusivamente em operações + RFAI + dívida bancária.
```

**Diagnóstico simplificado:**
```python
# ANTES:
pct_falhas_por_pt2030 = ...
diagnostico["prob_vala_positivo_dado_pt2030_aprovado"] = ...
diagnostico["prob_vala_positivo_dado_pt2030_rejeitado"] = ...

# DEPOIS:
n_falhas_val_base_neg = int((mask_falha & (val_base_arr < 0)).sum())
pct_falhas_val_base = n_falhas_val_base_neg / n_falhas if n_falhas > 0 else 0.0
diagnostico["pct_falhas_com_val_base_negativo"] = round(pct_falhas_val_base, 4)
```

**Stress fiscais reduzidos de 3 para 2:**
```python
# ANTES:
"pt2030_rejeitado": {"label": "PT2030 rejeitado (montante = 0)", ...}
"rfai_esgotado": {"label": "RFAI carry-forward esgota", ...}
"irc_28pct": {"label": "IRC sobe para 28%", ...}

# DEPOIS:
"rfai_esgotado": {"label": "RFAI carry-forward esgota", ...}
"irc_28pct": {"label": "IRC sobe para 28%", ...}
```

### 2. `viabilidade.py`

**Tornado limpo:**
```python
# ANTES:
"pt2030_taxa": {
    "vals": [0.20, 0.45],
    "label": "Co-financiamento PT2030 (% CAPEX)",
    "desc_low": "20 % (€760 k)",
    "desc_high": "45 % (€1 710 k)",
},

# DEPOIS:
# 2. PT2030 REMOVIDO (2025-05-30): Grande empresa sem elegibilidade a fundo
#    perdido. O cenário base usa PT2030=€0.
```

**Driver敏感性 removido:**
```python
# ANTES:
elif driver == "pt2030_taxa":
    capex_val = float(proj["capex"]["base"])
    proj["financiamento"]["PT2030"]["montante"] = v * capex_val

# DEPOIS:
# PT2030 REMOVIDO (2025-05-30): Grande empresa sem elegibilidade a fundo perdido.
# A sensibilidade ao PT2030 foi removida do tornado. O modelo usa PT2030=€0.
```

### 3. `views.jsx`

**KPI conditionally removed:**
```jsx
// ANTES:
<KPI label="P(VALA>0 | PT2030 ✓)" value={fmt.pct(diag.prob_vala_positivo_dado_pt2030_aprovado, 1)} ... />
<KPI label="P(VALA>0 | PT2030 ✗)" value={fmt.pct(diag.prob_vala_positivo_dado_pt2030_rejeitado, 1)} ... />

// DEPOIS:
{/* PT2030 KPIs REMOVIDO (2025-05-30): Grande empresa sem elegibilidade */}
```

**Diagnóstico updated:**
```jsx
// ANTES:
{fmt.pct(diag.pct_falhas_por_pt2030_rejeitado, 0)} das falhas devem-se à rejeição do PT2030

// DEPOIS:
{fmt.pct(diag.pct_falhas_com_val_base_negativo, 0)} das falhas devem-se a VAL_base negativo (operacional)
```

**Decomposição table sub updated:**
```jsx
// ANTES:
sub="VAL_base(Ku) + Escudo Fiscal + PT2030 líquido + RFAI · P5 / médio / P95"

// DEPOIS:
sub="VAL_base(Ku) + Escudo Fiscal + RFAI · P5 / médio / P95"
```

### 4. `data.js`

**PT2030 recognition zerado:**
```javascript
// ANTES:
const HUB_PT2030_REC = { 2026: 311456, 2027: 311456, 2028: 311456, 2029: 266456 };

// DEPOIS:
const HUB_PT2030_REC = { 2026: 0, 2027: 0, 2028: 0, 2029: 0 };
```

**DFC clean:**
```javascript
// ANTES:
if (hubOn && y === 2027) rec += 2200000; // PT2030

// DEPOIS:
if (hubOn && y === 2027) rec += 0; // PT2030 REMOVIDO (2025-05-30): €0
```

---

## Impacto no VALA

| Componente | Antes | Depois |
|------------|-------|--------|
| PT2030 líquido | Simulado (Bernoulli p=0.15, Triangular 0-7.5%) | **€0 fixo** |
| PV(PT2030) na decomposição | ~€0-450k conforme simulação | **€0** |
| P(VALA>0 | PT2030 ✓) | ~95%+ | **N/A** |
| P(VALA>0 | PT2030 ✗) | ~70% | **= P(VALA>0)** |
| Falhas atribuídas a PT2030 | 100% (das que tinham PT2030=0) | **0%** |

---

## Estabilidade

- A estrutura YAML mantém a chave `PT2030` para integridade de schema
- `pt2030_reconhecimento()` em `impacto.py` continua a funcionar — devolve €0 quando montante=0
- O código de contingência (`contingencia_hub.py`) mantém `_remover_pt2030()` por retrocompatibilidade

---

## NOTA: Energia Solar Avaliada

Durante esta sessão foi avaliada a elegibilidade de energia solar (€270k CAPEX) para PT2030/PRR.

**Conclusão:** Não compensa. O subsídio otimista (30-40%) seria €81k-€108k, insuficiente para cobrir custos de consultoria, auditorias obrigatórias e esforço burocrático para uma Grande Empresa.

**Recomendação:** Manter otimização focada no RFAI para o CAPEX total do Hub.