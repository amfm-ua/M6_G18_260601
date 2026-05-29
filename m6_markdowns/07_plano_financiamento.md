# 6. Plano de Financiamento

O financiamento do Hub Logístico 4.0 combina **duas fontes de capitais alheios** (€4.500.000), capitais próprios da Grestel (€1.500.000), um **subsídio a fundo perdido PT2030** (€2.700.000) e um **crédito fiscal RFAI** (€600.000). As duas tranches de dívida bancária satisfazem o requisito de, pelo menos, duas fontes de capitais alheios distintas. O subsídio PT2030 e o crédito RFAI não constituem dívida — são tratados, respetivamente, pelo método da dedução à depreciação (NCRF 22) e como crédito fiscal por dedução à coleta (CFI).

> **Nota de coerência:** o financiamento do Hub é autónomo do empréstimo histórico do Grupo junto do BPI (€10,7 M, Nota 21 do R&C 2024), que respeita a operações anteriores e não a este projeto.

---

## 6.1. Fontes de capitais alheios

| Fonte | Montante (€) | Taxa (%) | Prazo (anos) | Carência | Garantias |
|---|---:|:---:|:---:|:---:|---|
| Tranche bancária CGD | 3.000.000 | 4,15% fixa | 10 | 2025–2027 | Penhor de equipamentos VLM/AMR + hipoteca do imóvel G1 |
| Linha BEI/PME (via IFD) | 1.500.000 | 3,75% fixa | 10 | 2025–2027 | Garantia mútua; elegibilidade verde/digital BEI |
| **TOTAL capitais alheios** | **4.500.000** | **4,02%** *(médio)* | | | |

A tranche **CGD** (€3.000k @ 4,15%) reflete uma Euribor 6M de referência (~3,5%) acrescida de um *spread* de ~65 bp, com colateral imobiliário e cessão parcial do subsídio PT2030. A **Linha BEI/PME** (€1.500k @ 3,75%), intermediada pelo IFD, beneficia de bonificação de ~40 bp por elegibilidade nos pilares Clima e Social do BEI (energia solar, robótica AMR, *software* de analítica). Ambas têm carência de capital de 3 anos (2025–2027), sincronizada com o investimento e o *ramp-up*, e amortização constante entre 2028 e 2037.

**Custo médio ponderado da dívida (Kd):**

$$K_d = \frac{3.000 \times 4{,}15\% + 1.500 \times 3{,}75\%}{4.500} = 4{,}02\% \quad\Rightarrow\quad K_d^{\text{after-tax}} = 4{,}02\% \times (1 - 0{,}235) \approx 3{,}08\%$$

**Apoios públicos complementares (não constituem capital alheio):**

- **Subsídio PT2030 — FEDER (€2.700.000):** 45% do CAPEX elegível de €6.000k, ao abrigo do Sistema de Incentivos à Qualificação das PME (região assistida Centro/Aveiro). Reconhecido pela NCRF 22 (dedução à depreciação), com entrada de caixa esperada em **2027**.
- **Crédito fiscal RFAI (€600.000):** 10% do CAPEX elegível (CFI, região assistida), dedutível até 50% da coleta de IRC por ano, com *carry-forward* de 10 anos a partir de 2028.

---

## 6.2. Capitais próprios

O capital próprio do projeto é integralmente fornecido pela Grestel (empresa-mãe), sem recurso a investidores externos, suportado pela capacidade de autofinanciamento (resultado líquido retido e reservas). A estrutura de financiamento do CAPEX é de **75% dívida / 25% capital próprio** (D/E = 3,0).

| Componente | Montante (€) | % do CAPEX |
|---|---:|:---:|
| Capital próprio (*equity* Grestel) | 1.500.000 | 25% |
| Dívida bancária (CGD + BEI) | 4.500.000 | 75% |
| **TOTAL financiamento (CAPEX)** | **6.000.000** | **100%** |

**Custo do capital próprio (Ke) e WACC.** O custo do capital próprio do projeto foi estimado pelo CAPM, com *beta* realavancado para a estrutura de 75% de dívida (Rf ≈ 3,1%; prémio de risco de mercado ≈ 5,78%; βL ≈ 2,34), resultando num **Ke ≈ 16,6%**. Combinando Ke (25%) e Kd *after-tax* ≈ 3,1% (75%), obtém-se um **WACC ≈ 6,46%**, taxa de desconto aplicada aos *cash-flows* do Hub no cenário base. O modelo utiliza ainda um **WACC dinâmico (Miles-Ezzell)**, crescente à medida que a dívida é amortizada e o peso do capital próprio aumenta, penalizando os fluxos mais tardios (ver Cap. 9).

### 6.2.1. Glossário de nomenclaturas (notação internacional ↔ PI/ISCA-UA)

O relatório adota a **notação internacional de finanças empresariais** (Damodaran; *corporate finance*), por ser a convenção dos instrumentos de cálculo e da literatura de referência. A tabela seguinte estabelece a equivalência com a **nomenclatura dos conteúdos de Projetos de Investimento (PI) da ISCA-UA**, para leitura sem ambiguidade.

| Notação no relatório | Designação | Equivalente nos conteúdos de PI |
|---|---|---|
| **WACC** | Custo médio ponderado do capital | **CMPC** |
| **Ke** | Custo do capital próprio | **rCP** |
| **Kd** | Custo do capital alheio (dívida) | **rCA** |
| **Ku** | Custo do capital **desalavancado** (só risco do negócio) | rCP do projeto *unlevered* (rCP sem efeito da dívida) |
| **FCFF** | *Free Cash Flow to Firm* — fluxo livre da empresa (*unlevered*) | **FCF** / cash-flow líquido do projeto (sem juros) |
| **FCFE** | *Free Cash Flow to Equity* (*levered*) | Cash-flow do acionista |
| **NOPAT** | Resultado operacional após imposto | RO × (1 − T) |
| **APV / VALA** | Valor Atual Líquido Ajustado (Myers, 1974) | **VALA** |
| **Valor terminal** | Valor dos ativos no fim do horizonte | **Valor residual** (VR = VRANC + VRFM) |
| **β_u / βL** | Beta desalavancado / realavancado | β não alavancado / β alavancado |
| **ERP** | *Equity Risk Premium* | Prémio de risco de mercado (rm − rf) |
| **DSCR** | *Debt Service Coverage Ratio* | Rácio de cobertura do serviço da dívida |
| **NFM** | Necessidades de fundo de maneio | NFM (igual) |
| **VAL / TIR / IR / Payback** | Critérios de avaliação | VAL / TIR / IR / PR (iguais) |

> **Regra de não-duplicação (PI):** o relatório nunca mistura os dois métodos no mesmo cálculo — quando desconta ao **WACC (CMPC)** usa fluxos *unlevered* sem juros; quando aplica **VALA (APV)** desconta as operações ao **Ku** e adiciona à parte os benefícios de financiamento (escudo fiscal, PT2030, RFAI), cada um ao seu próprio risco.

---

## 6.3. Mapa de serviço da dívida

Mapa consolidado das duas tranches para o horizonte de projeção (valores em €; detalhe completo 2025–2037 no Anexo III):

| Ano | Capital em dívida (€) | Amortização (€) | Juros (€) | Prestação total (€) |
|---|---:|---:|---:|---:|
| 2025 | 4.500.000 | — | 180.750 | 180.750 |
| 2026 | 4.500.000 | — | 180.750 | 180.750 |
| 2027 | 4.500.000 | — | 180.750 | 180.750 |
| 2028 | 4.500.000 | 450.000 | 180.750 | 630.750 |
| 2029 | 4.050.000 | 450.000 | 162.700 | 612.700 |

Durante a carência (2025–2027), o serviço limita-se aos juros (€180.750/ano). O **pico do serviço da dívida ocorre em 2028** (€630.750), primeiro ano de amortização de capital, decrescendo progressivamente. A dívida extingue-se em 2037, três anos após o horizonte de avaliação.

**Rácios de cobertura (cenário base).** A capacidade de servir a dívida é confortável em todos os anos de exploração:

| Ano | EBITDA incremental Hub (€) | DSCR (EBITDA / serviço) | ICR (EBITDA / juros) |
|---|---:|:---:|:---:|
| 2026 | 749.271 | 4,15× | 4,15× |
| 2027 | 894.071 | 4,95× | 4,95× |
| 2028 | 994.214 | **1,58×** | 5,50× |
| 2029 | 1.020.462 | 1,67× | 6,27× |

O **DSCR mínimo é de 1,58×** (2028, primeiro ano de amortização de capital) — acima do limiar bancário típico de 1,2× e mesmo do limiar robusto de 1,5× preferido em *project finance*. O **rácio de cobertura de juros (ICR)** mantém-se muito elevado (≥ 4,1× em base EBITDA); mesmo numa base mais exigente de EBIT, o ICR situa-se em 1,60× (2028) e 2,34× (2029), acima do mínimo de referência de 1,5×. O ano de 2025 é de *ramp-up* (EBITDA incremental negativo, serviço limitado a juros): o défice pontual é coberto pela tesouraria central da Grestel e pela entrada de caixa do subsídio PT2030 em 2027 — um **risco de liquidez circunscrito ao arranque, não de solvência** do projeto.

Esta folga só se estreita no **cenário de stress sem apoios públicos** (rejeição do PT2030/RFAI), em que o DSCR mínimo desce para ≈ 1,08× — ainda acima de 1,0×, mas suficientemente apertado para justificar o plano de contingência (Cap. 13). Os rácios de cobertura são coerentes com os *cash-flows* operacionais projetados no Cap. 7 (fluxo operacional de €4,97 M em 2025, crescente para €6,67 M em 2029) e com a desalavancagem do rácio Dívida Líquida/EBITDA de 4× (2024) para 1× (2029).

---

*Ficheiro de trabalho — M6 · Grupo 18 · 2026-06-01*
