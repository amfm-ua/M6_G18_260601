# Monte Carlo — Distribuições por Driver

> Referência de decisão para evolução do modelo `monte_carlo_hub.py`.  
> Estado actual: Engine v0.9.6 · revisto 2026-05-27

---

## Drivers actuais e distribuições implementadas

| Driver | Distribuição actual | Parâmetros |
|---|---|---|
| `inventario` | Triangular | min=1 000k, mode=2 000k, max=2 500k |
| `pt2030_taxa` | Triangular | min=30%, mode=45%, max=60% |
| `b2c` | Normal truncada | N(1,0; σ=0,20) ∈ [0,3; 2,0] |
| `pessoal` | Triangular | min=200k, mode=380k, max=500k |
| `wacc` | Triangular | min=6%, mode=7,3%, max=10% |
| `capex` | Triangular | ±15% sobre base (runtime) |
| `preco_eletricidade` | Triangular | min=0,08, mode=0,12, max=0,20 €/kWh |
| `eur_usd` | Triangular | min=0,90, mode=1,08, max=1,25 |
| `crescimento_logistico` | Triangular | min=2%, mode=4%, max=7% |
| `pt2030_approved` | Bernoulli | p=0,75 |
| `rfai_utilization` | Triangular | min=50%, mode=100%, max=100% |
| `kd_shock` | Triangular | min=−100bps, mode=0, max=+200bps |

---

## Distribuições alternativas a considerar

### `eur_usd` — substituir Triangular → **Log-normal**

**Justificação teórica:**  
Taxas de câmbio seguem processos multiplicativos (GBM — Geometric Brownian Motion). A distribuição triangular corta artificialmente as caudas e assume simetria que os dados históricos não suportam. A log-normal preserva positividade e reflecte a distribuição dos retornos cambiais.

**Calibração proposta:**
```
μ = ln(1,08)   ← referência 2024
σ = 0,08       ← volatilidade anualizada EUR/USD histórica 2018-2024 (~8%)
clip: [0,85; 1,30]
```

**Comparação de percentis implícitos:**

| Percentil | Triangular actual | Log-normal proposta |
|---|---|---|
| P5 | 0,93 | 0,94 |
| P25 | 1,01 | 1,01 |
| P50 | 1,08 | 1,08 |
| P75 | 1,15 | 1,15 |
| P95 | 1,22 | 1,23 |
| P99 | — (hard cap 1,25) | 1,27 (cauda aberta) |

**Alternativa mais conservadora:** t-Student (ν ≈ 5) — captura fat tails (choques cambiais como 2015 CHF, 2022 JPY). Requer scipy.stats; não compatível com a dependência-zero actual do módulo.

**Impacto esperado no VAL:** Pequeno. O EUR/USD afecta apenas `usd_fraction` (15%) do `vn_incremental`. A principal diferença vs. triangular é a cauda direita mais longa (EUR muito forte), que é o cenário pessimista para o Hub.

---

### `preco_eletricidade` — substituir Triangular → **Log-normal**

**Justificação teórica:**  
O tecto actual (0,20 €/kWh) é factualmente insuficiente: em 2021-2022 o OMIE médio anual em Portugal atingiu ~0,24-0,28 €/kWh. A distribuição triangular exclui cenários historicamente realizados. Os preços de energia têm assimetria positiva pronunciada (cauda direita longa) e nunca são negativos — características que a log-normal captura por construção.

**Calibração proposta:**
```
μ = ln(0,12)   ← OMIE 2024 referência
σ = 0,25       ← captura volatilidade interanual incluindo choques energéticos
clip: [0,06; 0,40]
```

**Comparação de percentis implícitos:**

| Percentil | Triangular actual | Log-normal proposta |
|---|---|---|
| P5 | 0,083 | 0,074 |
| P25 | 0,097 | 0,096 |
| P50 | 0,113 | 0,120 |
| P75 | 0,144 | 0,152 |
| P95 | 0,183 | 0,192 |
| P99 | — (hard cap 0,20) | 0,218 |

**Nota:** A log-normal aumenta a probabilidade de cenários de crise energética (P > 0,20 €/kWh) de 0% para ~8%, o que é mais coerente com a experiência 2021-2023 na Península Ibérica.

**Alternativa:** Gamma(α, β) também adequada para custos energéticos, mas mais difícil de calibrar com dados públicos OMIE. Log-normal é preferível por parcimónia.

---

### `capex` — considerar **Log-normal assimétrica**

**Justificação:**  
Sobrecustos em projectos de construção/logística são assimétricos — é muito mais comum exceder o orçamento em 40-60% do que ficar 40% abaixo. A triangular simétrica (±15%) subestima o risco de overrun.

**Proposta:**
```
Triangular assimétrica: min=−10%, mode=0%, max=+30%
  ou
Log-normal de overrun: ln_overrun ~ N(0; σ=0,15), factor = exp(ln_overrun), clip=[0,85; 1,50]
```

**Prioridade:** Baixa. O CAPEX é fixo por contrato (fase 1 adjudicada) e o overrun afecta principalmente o calendário, não o montante total previsto no YAML (6 000k€).

---

### `wacc` — considerar **Normal truncada** (já existe no módulo)

**Justificação:**  
O WACC resulta de estimativas de mercado (beta, prémio de risco, spread) que têm distribuição aproximadamente normal em torno do consenso. A triangular assume que os extremos são igualmente improváveis que o centro, o que não reflecte a natureza paramétrica do WACC.

**Proposta:**
```
TruncNorm: N(0,073; σ=0,010) ∈ [0,050; 0,120]
```

**Prioridade:** Média. O WACC é o driver com maior correlação Pearson com o VAL em modelos de infraestrutura logística — refinar a sua distribuição melhora a qualidade das caudas da distribuição do VAL.

---

### `crescimento_logistico` — manter Triangular

**Justificação para manter:**  
O crescimento do mercado logístico nacional (2-7%/a) é um driver de opinião de gestão, não um processo financeiro. A triangular é adequada para elicitação de incerteza com três pontos (pessimista/base/optimista). Não há dados de mercado suficientemente densos para calibrar uma distribuição paramétrica mais sofisticada.

---

### `inventario` — manter Triangular

**Justificação para manter:**  
A libertação de inventário (1 250k€ + 1 250k€) está faseada por contrato e depende de decisões operacionais internas, não de mercado. A triangular com range ±25% reflecte adequadamente a incerteza de timing, não de valor.

---

## Matriz de prioridade de evolução

| Driver | Mudança proposta | Impacto no VAL | Complexidade impl. | Prioridade |
|---|---|---|---|---|
| `preco_eletricidade` | Triangular → Log-normal | Médio (cauda direita nova) | Baixa | **Alta** |
| `eur_usd` | Triangular → Log-normal | Baixo | Baixa | **Alta** |
| `wacc` | Triangular → TruncNorm | Alto | Nula (já existe) | Média |
| `capex` | Triangular simétrica → assimétrica | Médio | Baixa | Baixa |
| restantes | Manter | — | — | Não aplicável |

---

## Restrição de dependências

O módulo `monte_carlo_hub.py` usa **apenas numpy + stdlib**, sem scipy.  
Qualquer nova distribuição deve ser implementável com `numpy.random.Generator` ou rejection sampling.  
Log-normal: `rng.lognormal(mean, sigma, size=n)` — disponível em numpy. ✓  
t-Student: `rng.standard_t(df, size=n)` — disponível em numpy. ✓ (mas requer transformação manual para escala/localização)
