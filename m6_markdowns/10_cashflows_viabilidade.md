# 9. Cash-flows e Viabilidade do Projeto

A viabilidade do Hub Logístico 4.0 é aferida sobre os *cash-flows* incrementais do projeto (diferença entre os cenários com e sem Hub), num horizonte de **10 anos (2025–2034)**, complementada por uma avaliação por APV (*Adjusted Present Value*), análise de sensibilidade (Tornado), análise de cenários e simulação de Monte Carlo.

---

## 9.1. Cálculo dos cash-flows

*Cash-flows* livres incrementais do projeto (FCFF), em €. A taxa de desconto é o WACC de 6,37% (Cap. 6); o valor terminal de 2034 corresponde ao valor residual dos ativos não correntes (VLC) acrescido da recuperação das necessidades de fundo de maneio e da **perpetuidade 3PL** (Gordon Growth: contrib_3pl_2034 / (WACC − g), g = 5% anuais).

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

> O *cash-flow* de 2034 inclui o **valor terminal de ~€2,80 M** (valor residual líquido dos ativos + recuperação de NFM + perpetuidade 3PL). A libertação de inventário de ~€1,73 M em 2026 (redução do DMI) é o principal contributo do fundo de maneio. O subsídio PT2030 não é aplicável a grande empresa (sem elegibilidade a fundo perdido); o crédito RFAI (€0,6 M) é tratado explicitamente.

---

## 9.2. Indicadores de viabilidade

| Indicador | Valor | Interpretação |
|---|---:|---|
| **VAL** (FCFF @ WACC 6,37%) | **€2.031.233** | Positivo → o projeto cria valor |
| **TIR** | **13,99%** | Superior ao WACC (6,37%), folga de ~7,6 p.p. |
| Payback simples | 7,8 anos | Inferior ao horizonte de 10 anos |
| Payback atualizado | 8,80 anos | Inferior ao horizonte de 10 anos |
| Índice de rendibilidade | 1,34 | > 1 → cada € investido gera €1,34 atualizados |
| WACC | 6,37% | Taxa de desconto (cenário base) |
| **TIR > WACC?** | **Sim** (13,99% > 6,37%) | Folga de ~7,6 p.p. |

---

## 9.3. Análise de sensibilidade

Análise de sensibilidade univariada (diagrama de Tornado) sobre o VAL base de €2.031.233, ordenada por amplitude de impacto:

| Variável | Variação testada | VAL pessimista (€) | VAL otimista (€) | Amplitude (€) |
|---|---|---:|---:|---:|
| **CAPEX** | +15% / −15% (€6,9 M / €5,1 M) | ~€1,55 M | ~€3,47 M | ~€1,93 M |
| Crescimento B2C/*e-commerce* | ×0,5 / ×1,5 | ~€1,49 M | ~€3,39 M | ~€1,90 M |
| Poupança operacional | €200k / €500k por ano | ~€1,05 M | ~€2,81 M | ~€1,76 M |
| WACC | 10% / 6% | ~€1,43 M | ~€2,66 M | ~€1,23 M |
| Redução de DMI | 10 / 28 dias | ~€2,09 M | ~€2,81 M | ~€0,72 M |

A variável de **maior elasticidade é o CAPEX** (risco de execução/derrapagem da obra), seguida do crescimento dos canais B2C/*e-commerce* e da poupança operacional recorrente. **Em todos os cenários testados o VAL permanece positivo**, o que evidencia a robustez do projeto: mesmo com uma derrapagem do CAPEX de +15% e simultaneamente um WACC de 10%, o VAL não se anula. Esta conclusão fundamenta a priorização do risco de execução no Plano de Contingência (Cap. 12).

---

## 9.4. Análise de cenários

A análise de cenários combina os pressupostos numa simulação de **Monte Carlo** (N = 2.000 iterações, *seed* 42), que amostra simultaneamente nove fatores de risco a partir de distribuições calibradas (triangulares para os *drivers* operacionais; log-normais para câmbio EUR/USD e preço da energia). Os percentis P5 e P95 da distribuição definem os cenários pessimista e otimista:

| Cenário | VAL (€) | TIR (%) | Índice rendibilidade |
|---|---|---:|---:|---:|
| **Base** | **€2.031.233** | **13,99%** | **1,34** |
| Upside | €3.868.078 | 22,01% | 1,64 |
| Downside | €−796.362 | 4,88% | 0,87 |
| Stress | €−2.370.177 | −0,47% | 0,60 |

**Resultados-chave da simulação:** VAL médio de ~€2,6 M; **P(VAL > 0) = 99,95%** e **P(TIR > WACC) = 99,95%**. Os *drivers* com maior correlação com o VAL são o crescimento B2C, o CAPEX, a poupança com pessoal e o WACC — perfeitamente consistente com o diagrama de Tornado. 

A simulação assume independência entre *drivers* (não modela correlações entre, p. ex., câmbio e energia). Ainda assim, o resultado é inequívoco: **o projeto é viável com probabilidade praticamente certa**, e o VAL mantém-se positivo mesmo no extremo inferior da distribuição (P5 ≈ €1,37 M). A robustez confirma-se igualmente perante o WACC dinâmico (Miles-Ezzell), que preserva um VAL positivo.

---

*Ficheiro de trabalho — M6 · Grupo 18 · 2026-06-01*
