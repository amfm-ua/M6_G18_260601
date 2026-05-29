# 6. Plano de Financiamento — Hub Logístico 4.0

> ⚠️ **Nota de coerência (ver `_INDICE_RELATORIO.md`):** esta secção foi integrada no **Cap. 6** do relatório. A estrutura de financiamento (tranches CGD €3.000k @ 4,15% + BEI €1.500k @ 3,75%, PT2030 €2.700k, RFAI €600k) e o mapa de serviço da dívida mantêm-se válidos. Porém, os parâmetros derivados (WACC 6,3%, Ke 16,18%, IRC 24,5%) estão **desatualizados** — valores canónicos: **WACC 6,46% · Ke 16,62% · IRC 23,5%**.

> Secção pronta a inserir no relatório M6.  
> Valores em k€ (milhares de euros). Horizonte de análise: 2025–2037 (período de reembolso total da dívida).

---

## 6.1. Fontes de Capitais Alheios

O financiamento por capitais alheios do Hub Logístico 4.0 assenta em duas tranches de dívida bancária e num subsídio a fundo perdido no âmbito do programa PT2030, perfazendo uma estrutura de financiamento total de **€7.500k** (incluindo o subsídio).

### 6.1.1. Estrutura de Capitais Alheios

| Fonte | Montante (k€) | Taxa | Tipo | Carência | Início Amort. | Prazo |
|-------|--------------|------|------|---------|--------------|-------|
| Tranche bancária CGD/BPI | 3.000 | 4,15% fixo | Empréstimo a ML prazo | 2025–2027 | 2028 | 10 anos |
| Linha BEI/PME (via IFD) | 1.500 | 3,75% fixo | Linha de crédito bonificada | 2025–2027 | 2028 | 10 anos |
| Subsídio PT2030 (FEDER) | 2.700 | n.a. | Não reembolsável | — | — | — |
| **Total capitais alheios** | **7.200** | — | — | — | — | — |

> **Nota:** O subsídio PT2030 não constitui dívida — é tratado contabilisticamente pelo método da dedução à depreciação (NCRF 22), reduzindo o valor líquido contabilístico dos ativos à medida que as depreciações são reconhecidas. Em termos de caixa, representa uma entrada de €2.700k esperada em 2027 após aprovação formal.

---

### 6.1.2. Tranche Bancária — CGD/BPI (€3.000k @ 4,15%)

A tranche bancária, negociada junto da CGD ou BPI ao abrigo de linha de investimento para PME industriais, tem as seguintes condições:

| Condição | Detalhe |
|---------|--------|
| Montante | €3.000k |
| Taxa de juro | 4,15% fixa (Euribor 6M cap + spread negociado) |
| Regime de juros | Anuais postecipados; pagamento corrente durante carência |
| Carência de capital | 3 anos (2025–2027) — alinhada com o período de investimento e ramp-up operacional |
| Amortização | €300k/ano, regime constante, 2028–2037 |
| Garantias | Penhor sobre equipamentos VLM/AMR + hipoteca sobre o imóvel reabilitado (G1) |
| Colateral PT2030 | Cessão parcial do subsídio como garantia adicional |

**Racional da taxa:** A taxa fixa de 4,15% foi construída com base em Euribor 6M de referência (~3,5% em maio 2025) acrescida de spread de ~65 bp, refletindo o risco PME industrial com colateral imobiliário e garantia RFAI.

---

### 6.1.3. Linha BEI/PME — IFD (€1.500k @ 3,75%)

A linha BEI/PME, intermediada pelo Instituto de Financiamento do Desenvolvimento (IFD) com base nos Fundos de Garantia do BEI para PME, oferece condições bonificadas face à taxa de mercado:

| Condição | Detalhe |
|---------|--------|
| Montante | €1.500k |
| Taxa de juro | 3,75% fixa (bonificação de ~40 bp vs. linha comercial equivalente) |
| Regime de juros | Anuais postecipados; pagamento corrente durante carência |
| Carência de capital | 3 anos (2025–2027) |
| Amortização | €150k/ano, regime constante, 2028–2037 |
| Elegibilidade | Investimento em automação e eficiência energética — alinhado com critérios BEI (Pilar Social e Clima) |
| Condição suspensiva | Submissão da candidatura PT2030 e comprovativo de início de obra |

**Racional da elegibilidade BEI:** Os componentes de energia solar (€270k), robótica AMR (€625k) e software Digital Twin/Analytics (€600k) enquadram-se nos objetivos de transição verde e digital do BEI, justificando o acesso à linha bonificada.

---

### 6.1.4. Subsídio PT2030 — FEDER (€2.700k, 45% do CAPEX)

| Parâmetro | Detalhe |
|---------|--------|
| Programa | Portugal 2030 — FEDER, eixo "Competitividade e Internacionalização" |
| Aviso | Sistema de Incentivos à Qualificação das PME (SI Qualificação) |
| Taxa de apoio | 45% do CAPEX elegível (máximo 60% para região assistida Centro/Aveiro) |
| CAPEX elegível | €6.000k |
| Montante aprovado | €2.700k |
| Aprovação esperada | 2027 (após verificação física dos investimentos de 2025–2026) |
| Reconhecimento contabilístico | NCRF 22 — método da dedução à depreciação: o subsídio reduz o valor depreciável dos ativos, diminuindo as quotas de amortização ao longo da vida útil |
| Tratamento no FCF | Entrada de caixa de €2.700k em 2027; tratado como componente autónomo no cálculo do VAL por APV (Adjusted Present Value) |
| Enquadramento geográfico | Região assistida Centro/Aveiro (NUTS III Baixo Vouga) — REGIOSTARS 2024 |

**CAPEX líquido após subsídio:**

| | k€ |
|-|---|
| CAPEX total capitalizável | 6.000 |
| Subsídio PT2030 (dedução ao ativo) | (2.700) |
| **CAPEX líquido efetivo** | **3.300** |

---

### 6.1.5. Custo Médio Ponderado da Dívida (Kd)

$$K_d = \frac{3.000 \times 4{,}15\% + 1.500 \times 3{,}75\%}{3.000 + 1.500} = \frac{124{,}5 + 56{,}25}{4.500} = \mathbf{4{,}02\%}$$

Após escudo fiscal de IRC (taxa Hub: 24,5%):

$$K_d^{\text{after-tax}} = 4{,}02\% \times (1 - 0{,}245) = \mathbf{3{,}04\%}$$

---

### 6.1.6. Crédito Fiscal RFAI — Incentivo Complementar

O Regime Fiscal de Apoio ao Investimento (RFAI) constitui um incentivo complementar ao financiamento, reduzindo a carga fiscal e melhorando o cash flow líquido do projeto:

| Parâmetro | Valor |
|---------|-------|
| Taxa RFAI | 10% do CAPEX elegível (região assistida — CFI art. 23) |
| CAPEX elegível | €6.000k |
| Crédito fiscal total | €600k |
| Limite anual de utilização | 50% do IRC liquidado |
| Carry-forward | 10 anos |
| Início de utilização | 2028 (primeiro ano com IRC Hub positivo relevante) |

O crédito RFAI de €600k equivale a uma redução efetiva do custo de financiamento por capitais próprios, sendo tratado como componente do VALA no modelo de avaliação.

---

## 6.2. Capitais Próprios

### 6.2.1. Estrutura e Montante

Os capitais próprios do Hub Logístico 4.0 são inteiramente fornecidos pela Grestel, empresa-mãe, sem recurso a investidores externos. A injeção de capital de €1.500k enquadra-se na capacidade de autofinanciamento da Grestel (resultado líquido retido 2024 e reservas disponíveis).

| Componente | k€ | % do CAPEX |
|-----------|-----|-----------|
| Capital próprio (equity Grestel) | 1.500 | 25% |
| Dívida bancária (CGD/BPI + BEI) | 4.500 | 75% |
| **Total financiamento** | **6.000** | **100%** |

A estrutura de capital D/E = 3,0 (75% dívida / 25% capital próprio) reflete uma alavancagem elevada, típica em projetos de infraestrutura industrial com ativos físicos como colateral. A carência de 3 anos permite que os FCFs operacionais do Hub cubram o serviço da dívida a partir de 2028, quando o projeto já opera em plena capacidade.

---

### 6.2.2. Custo do Capital Próprio (Ke) — Modelo CAPM

O custo do capital próprio foi estimado pelo modelo CAPM, com beta reavalancado para a estrutura financeira do Hub:

| Parâmetro | Valor | Fonte/Método |
|---------|-------|-------------|
| Taxa sem risco (Rf) | 3,25% | OT Portugal 10 anos, maio 2025 |
| Prémio de risco de mercado (ERP) | 5,5% | Damodaran, Europa 2025 |
| Beta desalavancado (βu) | 0,72 | Damodaran, Household Products (Europa) |
| Rácio D/E Hub | 3,0 | 75% dívida / 25% capital |
| Taxa IRC | 24,5% | IRC 21% + derramas Vagos |
| **Beta alavancado (βL)** | **2,35** | βu × [1 + (1 − t) × D/E] = 0,72 × [1 + 0,755 × 3,0] |
| **Ke (custo do capital próprio)** | **16,18%** | Rf + βL × ERP = 3,25% + 2,35 × 5,5% |

O beta alavancado elevado (2,35) reflete o risco acrescido para o acionista resultante da alavancagem financeira de 75% — em caso de dificuldade, os credores têm prioridade sobre os ativos. A rentabilidade exigida de 16,18% é o retorno mínimo que o capital próprio investido deve gerar para remunerar adequadamente o risco assumido pela Grestel.

---

### 6.2.3. WACC — Custo Médio Ponderado do Capital

| Componente | Peso | Taxa | Contribuição |
|-----------|------|------|-------------|
| Capital próprio (Ke) | 25% | 16,18% | 4,045% |
| Dívida líquida de IRC (Kd after-tax) | 75% | 3,04% | 2,280% |
| **WACC (estático, cenário Base)** | **100%** | — | **6,32% ≈ 6,3%** |

O WACC de 6,3% é a taxa de desconto aplicada aos FCFFs do Hub no cenário base. O modelo utiliza também um **WACC dinâmico (Miles-Ezzell)**, que aumenta progressivamente à medida que a dívida é amortizada e o peso do capital próprio cresce, penalizando os cash flows mais tardios conforme a estrutura de capital evolui.

| Cenário | WACC | Δ vs. Base | Fundamentação |
|---------|------|-----------|--------------|
| Base | 6,3% | — | Estrutura central |
| Upside | 6,9% | +0,6pp | Maior CAPEX efetivo, menor alavancagem relativa |
| Downside | 8,1% | +1,8pp | Risco de crédito acrescido; spread bancário mais elevado |
| Stress | 9,1% | +2,8pp | Colapso de confiança; potencial restrição de crédito |

---

### 6.2.4. Efeito do PT2030 na Estrutura de Capital Efetiva

Após receção do subsídio PT2030 em 2027 (€2.700k), a estrutura de capital efetiva do Hub melhora substancialmente:

| | Antes PT2030 | Após PT2030 |
|-|-------------|------------|
| Total investimento (k€) | 6.000 | 6.000 |
| Subsídio recebido (k€) | — | (2.700) |
| Investimento líquido efetivo (k€) | 6.000 | **3.300** |
| Capital em risco para acionista (k€) | 1.500 | 1.500 |
| Dívida remanescente (k€) | 4.500 | 4.500 |
| Retorno sobre capital em risco | — | Significativamente melhorado |

O subsídio PT2030 não altera o serviço da dívida (a dívida mantém-se para preservar o escudo fiscal dos juros), mas reduz o investimento líquido do acionista de €6.000k para €3.300k, melhorando a rentabilidade do capital próprio e o perfil de risco percebido.

---

## 6.3. Mapa de Serviço da Dívida

### 6.3.1. Tranche CGD/BPI — €3.000k @ 4,15%

*(valores em k€; amortização anual constante de €300k; carência 2025–2027)*

| Ano | Saldo Inicial | Amortização | Juros (4,15%) | Serviço Total | Saldo Final |
|-----|:------------:|:-----------:|:-------------:|:------------:|:-----------:|
| 2025 | 3.000,0 | — | 124,5 | 124,5 | 3.000,0 |
| 2026 | 3.000,0 | — | 124,5 | 124,5 | 3.000,0 |
| 2027 | 3.000,0 | — | 124,5 | 124,5 | 3.000,0 |
| 2028 | 3.000,0 | 300,0 | 124,5 | 424,5 | 2.700,0 |
| 2029 | 2.700,0 | 300,0 | 112,1 | 412,1 | 2.400,0 |
| 2030 | 2.400,0 | 300,0 | 99,6 | 399,6 | 2.100,0 |
| 2031 | 2.100,0 | 300,0 | 87,2 | 387,2 | 1.800,0 |
| 2032 | 1.800,0 | 300,0 | 74,7 | 374,7 | 1.500,0 |
| 2033 | 1.500,0 | 300,0 | 62,3 | 362,3 | 1.200,0 |
| 2034 | 1.200,0 | 300,0 | 49,8 | 349,8 | 900,0 |
| 2035 | 900,0 | 300,0 | 37,4 | 337,4 | 600,0 |
| 2036 | 600,0 | 300,0 | 24,9 | 324,9 | 300,0 |
| 2037 | 300,0 | 300,0 | 12,5 | 312,5 | — |
| **Total** | — | **3.000,0** | **1.058,3** | **4.058,3** | — |

---

### 6.3.2. Linha BEI/PME — €1.500k @ 3,75%

*(valores em k€; amortização anual constante de €150k; carência 2025–2027)*

| Ano | Saldo Inicial | Amortização | Juros (3,75%) | Serviço Total | Saldo Final |
|-----|:------------:|:-----------:|:-------------:|:------------:|:-----------:|
| 2025 | 1.500,0 | — | 56,3 | 56,3 | 1.500,0 |
| 2026 | 1.500,0 | — | 56,3 | 56,3 | 1.500,0 |
| 2027 | 1.500,0 | — | 56,3 | 56,3 | 1.500,0 |
| 2028 | 1.500,0 | 150,0 | 56,3 | 206,3 | 1.350,0 |
| 2029 | 1.350,0 | 150,0 | 50,6 | 200,6 | 1.200,0 |
| 2030 | 1.200,0 | 150,0 | 45,0 | 195,0 | 1.050,0 |
| 2031 | 1.050,0 | 150,0 | 39,4 | 189,4 | 900,0 |
| 2032 | 900,0 | 150,0 | 33,8 | 183,8 | 750,0 |
| 2033 | 750,0 | 150,0 | 28,1 | 178,1 | 600,0 |
| 2034 | 600,0 | 150,0 | 22,5 | 172,5 | 450,0 |
| 2035 | 450,0 | 150,0 | 16,9 | 166,9 | 300,0 |
| 2036 | 300,0 | 150,0 | 11,3 | 161,3 | 150,0 |
| 2037 | 150,0 | 150,0 | 5,6 | 155,6 | — |
| **Total** | — | **1.500,0** | **478,2** | **1.978,2** | — |

---

### 6.3.3. Mapa Consolidado do Serviço da Dívida

*(valores em k€; agregação das duas tranches)*

| Ano | Amort. CGD/BPI | Amort. BEI/PME | **Amort. Total** | Juros CGD/BPI | Juros BEI/PME | **Juros Total** | **Serviço Total** | **Saldo Dívida** |
|-----|:--------------:|:--------------:|:----------------:|:-------------:|:-------------:|:---------------:|:-----------------:|:----------------:|
| 2025 | — | — | **—** | 124,5 | 56,3 | **180,8** | **180,8** | 4.500,0 |
| 2026 | — | — | **—** | 124,5 | 56,3 | **180,8** | **180,8** | 4.500,0 |
| 2027 | — | — | **—** | 124,5 | 56,3 | **180,8** | **180,8** | 4.500,0 |
| 2028 | 300,0 | 150,0 | **450,0** | 124,5 | 56,3 | **180,8** | **630,8** | 4.050,0 |
| 2029 | 300,0 | 150,0 | **450,0** | 112,1 | 50,6 | **162,7** | **612,7** | 3.600,0 |
| 2030 | 300,0 | 150,0 | **450,0** | 99,6 | 45,0 | **144,6** | **594,6** | 3.150,0 |
| 2031 | 300,0 | 150,0 | **450,0** | 87,2 | 39,4 | **126,6** | **576,6** | 2.700,0 |
| 2032 | 300,0 | 150,0 | **450,0** | 74,7 | 33,8 | **108,5** | **558,5** | 2.250,0 |
| 2033 | 300,0 | 150,0 | **450,0** | 62,3 | 28,1 | **90,4** | **540,4** | 1.800,0 |
| 2034 | 300,0 | 150,0 | **450,0** | 49,8 | 22,5 | **72,3** | **522,3** | 1.350,0 |
| 2035 | 300,0 | 150,0 | **450,0** | 37,4 | 16,9 | **54,3** | **504,3** | 900,0 |
| 2036 | 300,0 | 150,0 | **450,0** | 24,9 | 11,3 | **36,2** | **486,2** | 450,0 |
| 2037 | 300,0 | 150,0 | **450,0** | 12,5 | 5,6 | **18,1** | **468,1** | — |
| **Total** | **3.000,0** | **1.500,0** | **4.500,0** | **1.058,3** | **478,2** | **1.536,5** | **6.036,5** | — |

**Leitura-chave:**
- **Período de carência (2025–2027):** serviço limitado a juros — €180,8k/ano — permite que o Hub arranque e gere retorno antes de iniciar a amortização de capital.
- **Pico de serviço (2028):** €630,8k no primeiro ano de amortização; progressivamente decrescente à medida que o capital em dívida reduz.
- **Extinção total da dívida:** 2037, 12 anos após o início do projeto, 3 anos além do horizonte de avaliação de 10 anos.
- **Encargo total de juros:** €1.536,5k ao longo de 13 anos (2025–2037), representando um custo financeiro total equivalente a 25,6% do CAPEX original.

---

### 6.3.4. Cobertura do Serviço da Dívida (DSCR Indicativo)

O Debt Service Coverage Ratio (DSCR) mede a capacidade do Hub para gerar caixa suficiente para cumprir o serviço da dívida em cada ano. O EBITDA hub é estimado como a soma do benefício líquido operacional e da margem sobre as receitas incrementais B2C/3PL:

| Ano | EBITDA Hub Est. (k€) | Serviço Dívida (k€) | **DSCR** | Avaliação |
|-----|:-------------------:|:-------------------:|:--------:|---------|
| 2025 | n.a. (investimento) | 180,8 | — | Carência |
| 2026 | 630,0 ¹ | 180,8 | **3,49×** | Carência — excesso financia ramp-up |
| 2027 | 930,0 ² | 180,8 | **5,15×** | Carência — acumulação de caixa |
| 2028 | 682,5 ³ | 630,8 | **1,08×** | Coberto (nível mínimo aceitável) |
| 2029 | 738,5 ⁴ | 612,7 | **1,21×** | Coberto com margem crescente |
| 2030+ | Crescente | Decrescente | **>1,3×** | Cobertura confortável |

> ¹ 2026: benefício operacional €280k + inventários libertados €950k (one-off) + margem incremental €350k × 45% = ~€630k  
> ² 2027: benefício €290k + inventários €950k (2.ª tranche) + receitas €650k × 45% = ~€930k  
> ³ 2028: benefício €300k + receitas €850k × 45% = ~€682k (sem libertação de inventários)  
> ⁴ 2029: benefício €311k + receitas €950k × 45% = ~€738k  

O DSCR cai abaixo de 1,5× em 2028 (primeiro ano de amortização), o que é mitigado por: (i) o PT2030 de €2.700k recebido em 2027 disponibiliza reserva de caixa; (ii) o crédito RFAI de €600k reduz o IRC a pagar nos anos seguintes, libertando fluxo de caixa fiscal; (iii) a dívida decrescente melhora progressivamente o DSCR a partir de 2029.

---

### 6.3.5. Síntese do Plano de Financiamento

| Fonte | Montante (k€) | % Total | Custo Nominal | Custo After-Tax |
|-------|:------------:|:-------:|:-------------:|:---------------:|
| Tranche CGD/BPI | 3.000 | 37,5% | 4,15% | 3,13% |
| Linha BEI/PME | 1.500 | 18,8% | 3,75% | 2,83% |
| Capital próprio Grestel | 1.500 | 18,8% | 16,18% (Ke) | 16,18% |
| Subsídio PT2030 (FEDER) | 2.700 | 33,8%¹ | 0% | 0% |
| **Total (incl. subsídio)** | **8.700** | — | — | — |
| **Total sem subsídio** | **6.000** | **100%** | **WACC 6,3%** | — |

> ¹ O PT2030 é calculado em % do total fontes incluindo o subsídio (€8.700k), ou seja, 45% do CAPEX de €6.000k.

**Vantagens da estrutura adotada:**
1. **Carência de 3 anos** sincronizada com o período de investimento (2025–2026) e ramp-up operacional, evitando pressão de caixa antes de o Hub gerar retorno.
2. **Dois instrumentos de dívida** com taxas diferentes (4,15% e 3,75%) diversificam o risco de refinanciamento e otimizam o Kd para 4,02%.
3. **Subsídio PT2030 (€2.700k)** reduz o CAPEX líquido efetivo para €3.300k e melhora o VAL do projeto em valor equivalente ao subsídio atualizado.
4. **RFAI (€600k)** adiciona um escudo fiscal que complementa o escudo de juros da dívida, reduzindo o custo efetivo do projeto.
5. **Alavancagem de 75%** maximiza o escudo fiscal dos juros sem comprometer a viabilidade — o DSCR indicativo mantém-se acima de 1,0× mesmo no pior ano (2028 = 1,08×).
