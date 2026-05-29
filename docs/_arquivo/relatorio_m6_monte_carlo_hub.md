# Relatório M6 — Secção Monte Carlo Hub Logístico

> Bloco pronto a inserir no relatório M6.  
> Placeholders assinalados com `[INSERIR …]` — preencher com outputs do endpoint `GET /api/hub/monte-carlo`.

---

### 4.X — Simulação de Monte Carlo: Análise Probabilística de Viabilidade

#### Metodologia

A análise de viabilidade do Hub Logístico 4.0 é complementada por uma simulação de Monte Carlo com N = 1 000 iterações, implementada sobre o mesmo motor de cálculo determinístico. Em vez de dois pontos por variável (pessimista/optimista), como na análise de sensibilidade e no diagrama de Tornado, cada iteração amostra independentemente todos os drivers de risco a partir das respectivas distribuições de probabilidade, correndo o modelo de cash flows completo e registando o VAL e a TIR resultantes.

Esta abordagem produz distribuições empíricas de saída que permitem:

- (i) quantificar a probabilidade de viabilidade — P(VAL > 0);
- (ii) estimar a probabilidade de excesso de retorno — P(TIR > WACC);
- (iii) estabelecer intervalos de confiança para o VAL (P5–P95);
- (iv) ranquear os drivers pelo coeficiente de correlação de Pearson com o VAL, identificando as fontes de risco mais relevantes.

#### Drivers e distribuições

Foram modelados nove drivers de risco operacional e de mercado, com distribuições calibradas a partir de dados históricos e de pressupostos do plano de negócios:

| Driver | Distribuição | Justificação |
|---|---|---|
| Volume de inventário libertado | Triangular(1 000k; 2 000k; 2 500k) € | Incerteza de timing operacional |
| Taxa de subsídio PT2030 | Triangular(30%; 45%; 60%) | Range contratual do aviso |
| Multiplicador canal B2C | Normal truncada N(1,0; σ=0,20) ∈ [0,3; 2,0] | Incerteza de mercado; média = cenário base |
| Custos com pessoal | Triangular(200k; 380k; 500k) € | Negociação colectiva ± 30% |
| WACC | Triangular(6%; 7,3%; 10%) | Sensibilidade a condições de mercado |
| CAPEX total | Triangular(−15%; base; +15%) | Risco de execução de obra |
| Preço da eletricidade | Log-normal ln N(ln 0,12; σ=0,25) ∈ [0,06; 0,40] €/kWh | Assimetria positiva (crises energéticas 2021-22); OMIE Portugal |
| Taxa EUR/USD | Log-normal ln N(ln 1,08; σ=0,08) ∈ [0,85; 1,30] | Processo multiplicativo GBM; volatilidade histórica 8%/a |
| Crescimento logístico anual | Triangular(2%; 4%; 7%) | Mercado nacional de logística |

As distribuições triangulares foram escolhidas para os drivers operacionais porque permitem elicitação directa de três pontos (pessimista/base/optimista) sem exigir dados históricos densos. Para os drivers de mercado financeiro — câmbio e energia — foram adoptadas distribuições log-normais, que são teoricamente mais adequadas: (i) preservam a positividade do preço/taxa; (ii) reflectem a natureza multiplicativa dos processos financeiros; (iii) capturam a assimetria positiva documentada nos mercados energéticos ibéricos.

#### Resultados

[INSERIR OUTPUTS DO ENDPOINT `GET /api/hub/monte-carlo`:
- `val.mean` — VAL médio das simulações
- `val.p5` e `val.p95` — intervalo de confiança 90%
- `val.prob_positivo` — P(VAL > 0)
- `tir.mean` — TIR média
- `tir.prob_supera_wacc` — P(TIR > WACC)
- `correlacoes_val` top-3 — drivers com maior |r| de Pearson]

A Figura X apresenta o histograma da distribuição do VAL obtida nas 1 000 iterações.

[INSERIR FIGURA — histograma `val.histogram` do endpoint]

O coeficiente de correlação de Pearson entre cada driver e o VAL indica que [INSERIR top-3 drivers com maior |r|] são as fontes de risco dominantes, o que é consistente com os resultados da análise de Tornado (secção 4.X−1).

#### Limitações

A simulação assume independência entre drivers, não modelando correlações entre, por exemplo, taxa EUR/USD e preços de energia — ambos sensíveis a choques geopolíticos. Modelos com matrizes de correlação de Cholesky reduziriam esta limitação em fases posteriores de análise.
