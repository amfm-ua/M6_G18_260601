# 9. Cash-flows e Viabilidade do Projeto

A viabilidade do Hub Logístico 4.0 é aferida sobre os *cash-flows* incrementais do projeto (diferença entre os cenários com e sem Hub), num horizonte de **10 anos (2025–2034)**, complementada por uma avaliação por APV (*Adjusted Present Value*), análise de sensibilidade (Tornado), análise de cenários e simulação de Monte Carlo.

---

## 9.1. Cálculo dos cash-flows

*Cash-flows* livres incrementais do projeto (FCFF), em €. A taxa de desconto é o WACC de 6,46% (Cap. 6); o valor terminal de 2034 corresponde ao valor residual dos ativos não correntes (VLC) acrescido da recuperação das necessidades de fundo de maneio, **sem perpetuidade** (critério conservador).

| Ano | EBITDA incremental | NOPAT | (+) Depreciações | (−) CAPEX | (±) FM + inventário | **(=) FCFF** | **CF p/ VAL** |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2025 | (105.000) | (105.000) | — | (2.850.000) | (150.000) | **(3.105.000)** | (3.105.000) |
| 2026 | 749.271 | 33.841 | 705.035 | (3.150.000) | 1.683.656 | **(727.468)** | (727.468) |
| 2027 | 894.071 | 144.613 | 705.035 | — | 47.452 | **897.100** | 897.100 |
| 2028 | 994.214 | 221.222 | 705.035 | — | 12.853 | **939.110** | 939.110 |
| 2029 | 1.020.462 | 291.027 | 640.035 | — | 44.058 | **975.120** | 975.120 |
| 2030 | 978.790 | 431.326 | 490.035 | — | — | **921.361** | 921.361 |
| 2031 | 917.772 | 549.565 | 295.035 | — | — | **844.600** | 844.600 |
| 2032 | 945.439 | 573.982 | 295.035 | — | — | **869.017** | 869.017 |
| 2033 | 974.075 | 599.253 | 295.035 | — | — | **894.288** | 894.288 |
| 2034 | 930.307 | 672.198 | 131.910 | — | — | **804.108** | 3.087.543 |

> O *cash-flow* de 2034 inclui o **valor terminal de €2.283.435** (valor residual líquido dos ativos €2.193.060 + recuperação de NFM €90.375). A libertação de inventário de €1,73 M em 2026 (redução do DMI) é o principal contributo do fundo de maneio. O subsídio PT2030 e o crédito RFAI são tratados explicitamente na avaliação por APV (9.2).

---

## 9.2. Indicadores de viabilidade

| Indicador | Valor | Interpretação |
|---|---:|---|
| **VAL** (FCFF @ WACC 6,46%) | **€2.493.769** | Positivo → o projeto cria valor |
| **TIR** | **17,49%** | Muito superior ao WACC (6,46%) |
| Payback simples | 6,12 anos | Inferior ao horizonte de 10 anos |
| Payback atualizado | 7,37 anos | Inferior ao horizonte de 10 anos |
| Índice de rendibilidade | 1,42 | > 1 → cada € investido gera €1,42 atualizados |
| WACC | 6,46% | Taxa de desconto (cenário base) |
| **TIR > WACC?** | **Sim** (17,49% > 6,46%) | Folga de ~11 p.p. |
| VAL @ WACC dinâmico (Miles-Ezzell) | €1.638.783 | Permanece positivo mesmo penalizando os fluxos tardios |

**Avaliação complementar por APV (VALA).** O método do valor atual ajustado separa o valor das operações do valor dos efeitos de financiamento, descontando as operações ao custo do capital próprio do projeto (Ke ≈ 16,62%) e adicionando os componentes de financiamento ao seu próprio risco:

| Componente | Valor (€) | Metodologia |
|---|---:|---|
| VAL base das operações (@ Ke 16,62%) | (591.546) | FCFF operacional descontado ao custo de capital próprio do projeto |
| (+) Escudo fiscal da dívida | 199.700 | Miles-Ezzell, por tranche |
| (+) PT2030 líquido | 2.084.376 | NCRF 22, descontado à taxa sem risco (rf ≈ 3,1%) |
| (+) RFAI | 224.734 | Crédito fiscal, descontado a rf |
| **VALA (APV)** | **1.917.263** | Myers (1974); Miles-Ezzell (1980) |

Os dois métodos confirmam a viabilidade: o VAL por FCFF (€2,49 M) e o VALA (€1,92 M) são ambos claramente positivos. O VALA é mais conservador porque desconta as operações ao elevado custo de capital próprio do projeto (16,62%, reflexo da alavancagem de 75%) antes de adicionar os benefícios de financiamento — evidenciando, de forma transparente, que **o subsídio PT2030 (€2,08 M atualizados) é o principal criador de valor**, seguido do escudo fiscal e do RFAI.

**Conclusão:** o projeto é **economicamente viável** — VAL positivo, TIR (17,49%) muito acima do WACC (6,46%), índice de rendibilidade de 1,42 e *payback* atualizado (7,37 anos) confortavelmente dentro do horizonte de 10 anos.

---

## 9.3. Análise de sensibilidade

Análise de sensibilidade univariada (diagrama de Tornado) sobre o VAL base de €2.493.769, ordenada por amplitude de impacto:

| Variável | Variação testada | VAL pessimista (€) | VAL otimista (€) | Amplitude (€) |
|---|---|---:|---:|---:|
| **CAPEX** | +15% / −15% (€6,9 M / €5,1 M) | 1.547.581 | 3.473.942 | 1.926.360 |
| Crescimento B2C/*e-commerce* | ×0,5 / ×1,5 | 1.490.323 | 3.388.537 | 1.898.213 |
| Poupança operacional | €200k / €500k por ano | 1.047.913 | 2.807.354 | 1.759.441 |
| WACC | 10% / 6% | 1.425.508 | 2.658.920 | 1.233.412 |
| Redução de DMI | 10 / 28 dias | 2.092.518 | 2.814.770 | 722.252 |
| PT2030 | 20% / 45% do CAPEX | 1.866.536 | 2.493.769 | 627.233 |

A variável de **maior elasticidade é o CAPEX** (risco de execução/derrapagem da obra), seguida do crescimento dos canais B2C/*e-commerce* e da poupança operacional recorrente. **Em todos os cenários testados o VAL permanece positivo**, o que evidencia a robustez do projeto: mesmo com uma derrapagem do CAPEX de +15% e simultaneamente um WACC de 10%, o VAL não se anula. Esta conclusão fundamenta a priorização do risco de execução no Plano de Contingência (Cap. 12).

---

## 9.4. Análise de cenários

A análise de cenários combina os pressupostos numa simulação de **Monte Carlo** (N = 2.000 iterações, *seed* 42), que amostra simultaneamente nove fatores de risco a partir de distribuições calibradas (triangulares para os *drivers* operacionais; log-normais para câmbio EUR/USD e preço da energia). Os percentis P5 e P95 da distribuição definem os cenários pessimista e otimista:

| Cenário | Pressupostos principais | VAL (€) | TIR (%) |
|---|---|---:|---:|
| Pessimista (P5) | Combinação adversa de CAPEX, B2C, pessoal e WACC | 1.368.586 | 12,6 |
| **Base** | Pressupostos centrais do plano | **2.493.769** | **17,49** |
| Otimista (P95) | Combinação favorável dos *drivers* | 3.743.315 | 23,7 |
| **VAL esperado (média MC)** | 9 *drivers* estocásticos | **2.585.064** | 17,96 |

**Resultados-chave da simulação:** VAL médio de €2,59 M (desvio-padrão €726k); intervalo de confiança a 90% de **€1,37 M a €3,74 M**; **P(VAL > 0) = 99,95%** e **P(TIR > WACC) = 99,95%**. Os *drivers* com maior correlação de Pearson com o VAL são o crescimento B2C (+0,55), o CAPEX (−0,49), a poupança com pessoal (+0,43) e o WACC (−0,41) — perfeitamente consistente com o diagrama de Tornado. 

A simulação assume independência entre *drivers* (não modela correlações entre, p. ex., câmbio e energia). Ainda assim, o resultado é inequívoco: **o projeto é viável com probabilidade praticamente certa**, e o VAL mantém-se positivo mesmo no extremo inferior da distribuição (P5 ≈ €1,37 M). A robustez confirma-se igualmente perante o WACC dinâmico (Miles-Ezzell), que preserva um VAL de €1,64 M.

---

*Ficheiro de trabalho — M6 · Grupo 18 · 2026-06-01*
