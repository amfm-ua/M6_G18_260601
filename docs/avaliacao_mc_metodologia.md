# Avaliação Estocástica por Monte Carlo — Metodologia e Pressupostos

## 1. Enquadramento

A avaliação intrínseca da Grestel assenta num modelo de três métodos — DCF-FCFF, Múltiplos de Mercado e FCFE —, ponderados numa síntese final. Para além do caso base determinístico, implementou-se uma simulação de Monte Carlo que quantifica a incerteza associada aos principais *value drivers* e produz uma distribuição empírica do *equity value*, permitindo análise probabilística dos resultados.

Este documento descreve as opções metodológicas adoptadas, com fundamentação académica, em particular a tratamento diferenciado dos cenários operacionais (Base, *Downside*, *Stress*) nas distribuições dos parâmetros financeiros.

---

## 2. Estrutura do Modelo de Avaliação

### 2.1 Método DCF-FCFF

O valor do capital próprio pelo método dos fluxos de caixa descontados é dado por:

$$E_{DCF} = \sum_{t=1}^{T} \frac{FCFF_t}{(1+WACC)^t} + \frac{FCFF_T \cdot (1+g_n)}{(WACC - g_n)(1+WACC)^T} - D_{líq}$$

onde $FCFF_t = EBIT_t(1-\tau) + DA_t - \Delta NWC_t - Capex_t$, $g_n$ é a taxa de crescimento terminal, $WACC$ o custo médio ponderado do capital, e $D_{líq}$ a dívida líquida.

Os fluxos de caixa projetados ($t = 2025$ a $2029$) são extraídos directamente do motor operacional `run_model(cenário, hub\_on)`, garantindo coerência entre o plano financeiro e a avaliação.

### 2.2 Método dos Múltiplos

O *Enterprise Value* é estimado através de cinco múltiplos sectoriais (EV/EBITDA, EV/EBIT, EV/Vendas, P/E, P/BV), sendo o *equity value* a média simples dos cinco:

$$E_{Mult} = \overline{\left\{M_i \times X_i - D_{líq}\right\}}$$

onde $M_i$ é o múltiplo sectorial e $X_i$ a métrica correspondente da Grestel.

### 2.3 Ponderação Final

$$E_{pond} = \frac{1}{3} E_{DCF} + \frac{1}{3} E_{Mult} + \frac{1}{3} E_{FCFE}$$

Os três métodos têm igual ponderação (1/3), reflectindo incerteza equivalente sobre qual o método mais adequado, prática comum em contextos de avaliação académica e de *fairness opinions* (Damodaran, 2012).

---

## 3. Simulação de Monte Carlo

### 3.1 Drivers estocásticos

A simulação perturba cinco *drivers* em cada iteração $i = 1, \ldots, N$:

| Driver | Distribuição | Parâmetros (cenário Base) |
|---|---|---|
| WACC | Triangular | $[\mu - 1{,}5\%, \mu, \mu + 1{,}5\%]$, $\mu = 6{,}21\%$ |
| $g_n$ (crescimento terminal) | Triangular | cenário-dependente (ver §4) |
| Múltiplo EV/EBITDA | Normal truncada | $\mathcal{N}(15{,}86; 3{,}0^2)$, suporte $[7{,}9; 31{,}7]$ |
| Choque crescimento receita | Normal truncada | $\mathcal{N}(0; 0{,}015^2)$, suporte $[-5\%; +10\%]$ |
| Choque margem EBITDA | Normal truncada | $\mathcal{N}(0; 0{,}015^2)$, suporte $[-5\%; +5\%]$ |

As distribuições triangulares são utilizadas quando a informação disponível é suficiente para estimar mínimo, moda e máximo, mas insuficiente para calibrar uma distribuição paramétrica completa — situação típica em avaliação empresarial (Mun, 2006). As distribuições normais truncadas garantem que os parâmetros se mantêm em intervalos economicamente admissíveis.

### 3.2 Restrições de coerência

Em cada iteração, é verificada a condição fundamental do modelo de Gordon-Growth:

$$WACC_i > g_{n,i}$$

Iterações que violem esta ou outras restrições ($0{,}03 < WACC < 0{,}20$; $-0{,}05 < g_n < 0{,}10$) são descartadas. O rácio de iterações válidas é reportado como indicador de qualidade da simulação.

### 3.3 Correlações de Spearman

A sensibilidade do *equity value* a cada *driver* é medida pelo coeficiente de correlação de postos de Spearman $\rho_S$, estimado sobre os pares $(\text{driver}_i, E_{pond,i})$ das iterações válidas. O uso de correlações de postos é preferível às correlações de Pearson em contexto de Monte Carlo porque é robusto a não-linearidades e a distribuições assimétricas (Iman & Conover, 1982).

---

## 4. Tratamento dos Cenários Operacionais

### 4.1 Separação entre risco operacional e risco financeiro

A análise por cenários (Base, *Downside*, *Stress*) modifica os fluxos de caixa operacionais projetados através do motor financeiro da Grestel. Uma questão metodológica central é: **deverá o WACC variar entre cenários?**

A resposta da teoria financeira moderna é negativa. O WACC reflecte o risco sistemático do negócio — capturado pelo beta de alavancagem e pelo prémio de risco de mercado —, não o resultado operacional de um determinado cenário. Conforme Damodaran (2012, *Investment Valuation*, 3.ª ed., p. 211):

> *"The discount rate should reflect the risk of the cash flows being discounted, not the optimism or pessimism of the analyst about the future."*

Alterar o WACC entre cenários constituiria uma dupla-contagem do risco (*double-counting*): o cenário *Stress* já incorpora o downside operacional através de cash flows mais baixos; penalizar adicionalmente o denominador enviesa a avaliação para baixo de forma injustificada.

### 4.2 O problema do valor terminal em cenários de stress

O pressuposto verdadeiramente sensível entre cenários não é o WACC, mas a **taxa de crescimento terminal** $g_n$. No modelo de Gordon-Growth, o multiplicador do valor terminal é:

$$TV_{mult} = \frac{1+g_n}{WACC - g_n}$$

Com $WACC = 6{,}21\%$ e $g_n = 2\%$, obtém-se $TV_{mult} \approx 24\times$. Este multiplicador amplifica qualquer FCFF residual, podendo produzir *equity values* aparentemente elevados mesmo em cenários de stress, desde que o FCFF seja positivo.

O pressuposto $g_n = 2\%$ implica que a empresa cresce indefinidamente a 2% em termos nominais — pressuposto razoável para o cenário Base (aproximadamente a inflação de longo prazo da zona euro), mas excessivamente optimista para cenários de deterioração estrutural.

### 4.3 Ajuste do crescimento terminal por cenário

Adopta-se a seguinte calibração, consistente com a literatura de avaliação em contextos de dificuldade financeira:

| Cenário | $g_n$ (centro da distribuição) | Interpretação |
|---|---|---|
| **Base** | 2,0% | Crescimento real + inflação moderada |
| **Downside** | 1,0% | Crescimento real próximo de zero; pressão sectorial persistente |
| **Stress** | 0,0% | Crescimento nominal nulo; empresa em estagnação ou perda de quota |

O spread da distribuição triangular mantém-se em $\pm 0{,}5$ p.p. em todos os cenários, assegurando comparabilidade da incerteza relativa.

Esta abordagem é consistente com Koller, Goedhart & Wessels (2015, *Valuation*, 6.ª ed., McKinsey & Company), que recomendam calibrar $g_n$ à taxa de crescimento nominal da economia ou do sector no longo prazo — expectativa essa que se deteriora em cenários adversos.

O WACC mantém-se constante e igual ao cenário Base em todas as simulações, em linha com o princípio acima enunciado.

---

## 5. Pressupostos Financeiros Base

Os pressupostos financeiros utilizados nas simulações foram calibrados com base nos dados do Relatório & Contas 2024 (auditado) e nas projeções do Orçamento de Exercício 2025–2029:

| Parâmetro | Valor | Fonte |
|---|---|---|
| Taxa sem risco ($R_f$) | 3,30% | OT Portugal 10 anos, mai-2026 |
| Prémio de risco de mercado (ERP) | 5,50% | Damodaran, Western Europe, jan-2025 |
| Beta alavancado ($\beta_L$) | 1,10 | Sector cerâmica industrial |
| Custo do capital próprio ($k_e$) | 9,35% | CAPM: $R_f + \beta_L \times ERP$ |
| Custo da dívida líquido ($k_d$) | 2,80% | $k_{d,bruto}(1-\tau) = 3{,}5\% \times 0{,}80$ |
| Estrutura de capital ($D/V$) | 48% | R&C 2024 + projeções IAPMEI 2025 |
| WACC | 6,21% | $k_e \cdot E/V + k_d \cdot D/V$ |
| Taxa de IRC efectiva ($\tau$) | 20,0% | OE2024, art. 87.º CIRC |
| Dívida líquida | 13,3 M€ | Dívida financeira pós IAPMEI, fim 2025E |
| Múltiplo EV/EBITDA sectorial | 15,86× | Damodaran, aplicado ao perfil da Grestel (OE5) |

Os fluxos de caixa projetados (FCFF e FCFE) são extraídos directamente do motor operacional para cada combinação (cenário × hub\_on), garantindo alinhamento total entre o plano financeiro e a avaliação estocástica.

---

## 6. Interpretação dos Resultados

### 6.1 Distribuição do equity value

A simulação produz uma distribuição empírica de $E_{pond}$ com $N$ observações válidas. São reportados:

- **Média e desvio-padrão** — medidas de tendência central e dispersão
- **Percentis P5, P25, P50, P75, P95** — intervalos de confiança assimétricos
- **P(equity > base)** — probabilidade de o equity estocástico superar o caso determinístico

### 6.2 Impacto do Hub Logístico

A simulação comparativa (com vs. sem Hub) permite isolar o contributo estocástico do Hub para o *equity value* da Grestel. O delta médio representa o valor incremental esperado do projeto em condições de incerteza, complementando a análise determinística do VAL e da TIR.

### 6.3 Correlações de Spearman e análise de sensibilidade

O ranking das correlações de Spearman indica quais os *drivers* que mais influenciam o *equity value* em cada cenário, constituindo um mapa de risco para a gestão. Valores de $|\rho_S| > 0{,}5$ indicam drivers dominantes; valores $|\rho_S| < 0{,}2$ indicam drivers de efeito marginal.

---

## 7. Limitações do Modelo

1. **Dominância do valor terminal**: em qualquer modelo de Gordon-Growth com horizonte finito, o valor terminal representa tipicamente 70–85% do valor total. Os resultados são, portanto, mais sensíveis a $g_n$ e ao WACC do que aos FCFF do período explícito.

2. **Independência dos drivers**: a simulação não modela correlações entre drivers (e.g., um cenário macroeconómico adverso que aumente simultaneamente o WACC e reduza $g_n$). A introdução de correlações via cópulas aumentaria o realismo mas exigiria calibração empírica.

3. **Floor do equity em zero**: o modelo não aplica um floor em zero ao *equity value*. Valores negativos são matematicamente possíveis em cenários de stress severo e sinalizam insolvência técnica (dívida > valor do activo). O acionista não está obrigado a absorver estas perdas (responsabilidade limitada), pelo que o *equity value* realístico tem um floor em zero.

4. **Estacionaridade dos pressupostos**: os múltiplos sectoriais e a estrutura de capital são mantidos constantes ao longo das simulações. Em ambiente de stress, a compressão dos múltiplos e a deterioração do rácio D/E poderiam ser modeladas endogenamente.

---

## 8. Referências

- Damodaran, A. (2012). *Investment Valuation: Tools and Techniques for Determining the Value of Any Asset* (3.ª ed.). John Wiley & Sons.
- Koller, T., Goedhart, M., & Wessels, D. (2015). *Valuation: Measuring and Managing the Value of Companies* (6.ª ed.). McKinsey & Company / John Wiley & Sons.
- Brealey, R. A., Myers, S. C., & Allen, F. (2020). *Principles of Corporate Finance* (13.ª ed.). McGraw-Hill.
- Iman, R. L., & Conover, W. J. (1982). A distribution-free approach to inducing rank correlation among input variables. *Communications in Statistics — Simulation and Computation*, 11(3), 311–334.
- Mun, J. (2006). *Modeling Risk: Applying Monte Carlo Simulation, Real Options Analysis, Forecasting, and Optimization Techniques*. John Wiley & Sons.
- Damodaran, A. (2025). *Equity Risk Premiums (ERP): Determinants, Estimation and Implications*. Stern School of Business, NYU. Disponível em: http://pages.stern.nyu.edu/~adamodar/
