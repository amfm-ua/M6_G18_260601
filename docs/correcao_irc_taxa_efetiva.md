# Tratamento do IRC — Taxa Efetiva Única (Correção C-1)

> GrestelPy · Motor financeiro da empresa Grestel · PEF 2025-26 · Grupo 18 · ISCA-UA
> Documento de suporte ao relatório M6 — fundamentação contabilística e fiscal

---

## 1. Problema identificado (C-1)

Durante a auditoria ao código detetou-se que a **mesma taxa de IRC** estava
representada por **quatro valores distintos e hardcoded**, espalhados pela
camada de apresentação (frontend). Cada local aplicava um número diferente:

| Local (ficheiro:linha original) | Valor | Função |
|---|---|---|
| `data.js:114` — `projectDR()` | `0,215` | DR projetada (mock) |
| `data.js:366` — `hubViability()` default | `0,21` | Viabilidade do Hub (mock) |
| `data.js:597` — `ASSUMPTIONS` | `0,20 + 1,5% + 1,35%` = **22,85%** | Pressupostos exibidos |
| `api.js:393` — adaptador mock | `0,245` | Viabilidade do Hub (live adapter) |
| `api.js:483 / 492` — Monte Carlo | `0,245` | Simulação estocástica VAL/TIR |
| `api.js:599` — sensibilidade | `0,215` | Análise de sensibilidade 2025 |

### Porque é crítico

- **Inconsistência interna:** quatro valores (0,20 / 0,21 / 0,215 / 0,245) para
  um único parâmetro fiscal. Nenhum coincidia com os restantes.
- **Enviesamento mock ↔ live:** como o sistema corre em modo *live*
  (`USE_LIVE_API = true`), o valor `0,245` era **enviado ao backend** nos
  endpoints de Monte Carlo e viabilidade do Hub, enquanto a Demonstração de
  Resultados usava a taxa **efetiva real** apurada pelo motor (~8%). Qualquer
  comparação entre cenários ou entre projetos ficava distorcida.
- **Valor não justificado:** o `0,245` (24,5%) nunca foi fundamentado. Hoje sabe-se
  que corresponde à soma nominal do período de projeção: IRC 20% (taxa 2025+ por
  OE2024, Lei 28/2023) + Derrama Municipal 1,5% + Derrama Estadual 3% = 24,5%.

---

## 2. Enquadramento fiscal (R&C 2024 auditado)

### 2.1 Taxas nominais e combinada

| Componente | Taxa | Base legal |
|---|---|---|
| IRC — taxa base | **21,00%** (2024) / 20% (2025+) | Art. 87.º n.º 1 CIRC; OE2024 Lei 28/2023 |
| Derrama Municipal | **1,50%** | Lei das Finanças Locais art. 18.º (Vagos usa taxa máxima) |
| Derrama Estadual (1.º escalão) | **3,00%** | Art. 87.º-A CIRC (lucro tributável €1,5 M – €7,5 M) |
| **Taxa nominal combinada (2024)** | **25,50%** | — |

> A Grestel é **grande empresa** (734 trabalhadores em 2024): a taxa reduzida de
> PME não se aplica (art. 87.º n.º 2 CIRC). A taxa geral incide desde o 1.º euro.

### 2.2 Taxa efetiva vs. taxa nominal

A taxa que realmente impacta o resultado líquido é a **taxa efetiva**, muito
inferior à nominal devido a benefícios fiscais estruturais:

| Exercício | Taxa efetiva | RAI | Coleta |
|---|---|---|---|
| 2023 | **18%** | 5.055.858 € | 3.663.014 € |
| 2024 | **8%** | 1.517.481 € | 370.848 € |

A descida de 18% para 8% explica-se por dois fatores combinados:

1. **Queda do lucro tributável** — o RAI caiu de 5,06 M€ (2023) para 1,52 M€ (2024).
2. **Peso proporcional dos benefícios fiscais** — sobre uma base menor, as
   deduções "abatem" uma percentagem muito maior do imposto:
   - **SIFIDE II** (I&D): dedução à coleta ≈ **380.795,67 €** (despesas elegíveis
     de 632.304,15 € × 32,5%) — art. 35.º CFI.
   - **ICE** — Incentivo à Capitalização das Empresas: ≈ **342.403 €** de
     rendimentos não tributáveis (art. 41.º-A EBF).
   - **Majoração de 20%** nos encargos com eletricidade e gás natural: ≈ 117.283 €.

### 2.3 Tratamento por casos

- **Grestel + subsidiárias (Ecogres):** tributação sob o **RETGS** (Regime
  Especial de Tributação de Grupos de Sociedades). O lucro tributável é apurado
  pela sociedade dominante por soma algébrica dos resultados do grupo. A Ecogres
  mantém, no modelo, a sua própria taxa de subsidiária (distinta da taxa geral).
- **Projetos M6 (plano de negócios):** o M6 exige fundamentação nas vertentes
  contabilística e fiscal. Recomenda-se a **taxa efetiva projetada**, assumindo a
  continuidade dos benefícios de I&D — a inovação (Ecogres 4.0, novos moldes) é
  central para a empresa.

---

## 3. Decisão técnica

Adotou-se uma **taxa de IRC efetiva única de 13%** como fonte de verdade para
todas as projeções (DR, Hub, Monte Carlo, sensibilidade). A taxa nominal
combinada de 25,5% fica apenas como **referência documental** nos pressupostos.

### Justificação dos 13%

- **Ponto médio da banda histórica efetiva** (8% em 2024 ↔ 18% em 2023): mais
  realista para o médio/longo prazo do que qualquer dos extremos.
- **Continuidade de benefícios:** assume que a Grestel continua a captar SIFIDE II
  e ICE, mas de forma menos agressiva que o mínimo de 2024 (que beneficiou de um
  ano de lucros contidos).
- **Prudência vs. viabilidade:** usar a nominal (25,5%) **subestimaria** o
  resultado líquido e a viabilidade dos investimentos (Hub, Ecogres 4.0), uma vez
  que a empresa reduz consistentemente a fatura fiscal via incentivos.

| Uso | Taxa |
|---|---|
| Projeções (fonte de verdade única) | **0,13 (13%)** |
| Referência nominal (documentação) | 0,255 (25,5%) |
| Cenário otimista (sensibilidade) | 0,08 (8%) |
| Cenário pessimista (sensibilidade) | 0,18 (18%) |

> **Nota:** a DR do motor (backend) continua a apurar a taxa efetiva **real ano a
> ano** — RAI − ICE, derramas multi-escalão (art. 87.º-A CIRC), SIFIDE II com
> *carry-forward* de 8 anos, RFAI (limite 25% da coleta, art. 23.º CFI) e
> tributação autónoma. Os 13% aplicam-se às análises que usam uma **taxa plana**
> (viabilidade do Hub, Monte Carlo, sensibilidade), não substituindo o cálculo
> rigoroso da DR.

---

## 4. Solução implementada

Arquitetura: **fonte de verdade única**, exposta pela API e consumida pelo
frontend — o valor deixa de existir hardcoded em qualquer local de apresentação.

```
fiscal/globais.yaml ──► serializers.py ──► GET /api/assumptions/effective
   (0.13 declarado)      (irc_taxa_efetiva)        │
                                                    ▼
                              app.jsx  (ctx.ircTaxaEfetiva)
                                                    │
                       ┌────────────────────────────┴───────────────┐
                       ▼                                             ▼
              views.jsx (Hub, Monte Carlo, VALA, sensibilidade)  fallback offline
              irc_taxa: ctx.ircTaxaEfetiva                  GRESTEL.IRC_TAXA_EFETIVA
```

### 4.1 Backend

- **`globais.yaml`** — novo parâmetro `impostos.IRC_taxa_efetiva_planeamento: 0.13`,
  documentado com a banda histórica e a fundamentação.
- **`serializers.py`** — `GET /api/assumptions/effective` passa a devolver o campo
  `irc_taxa_efetiva` (como **fração**, ex.: `0.13`, para ser passado diretamente
  aos endpoints do Hub).

### 4.2 Frontend

- **`data.js`** — definidas as constantes únicas `IRC_TAXA_EFETIVA = 0.13` e
  `IRC_TAXA_NOMINAL_COMBINADA = 0.255` (exportadas em `GRESTEL`). Substituídos os
  valores `0,215` (`projectDR`) e `0,21` (`hubViability`). Corrigidos os
  `ASSUMPTIONS`: IRC 0,20 → **0,21** e Derrama Estadual 0,0135 → **0,03**;
  acrescentados os campos `IRC_taxa_efetiva` e `IRC_taxa_nominal_combinada`.
- **`api.js`** — nova função `API.assumptions()` que busca a taxa à API (com
  fallback offline). Removidos os defaults `0,245` (`hubMonteCarlo`,
  `hubMonteCarloVala`, adaptador `hubViability`) e `0,215` (sensibilidade),
  todos substituídos por `GRESTEL.IRC_TAXA_EFETIVA`.
- **`app.jsx`** — busca `irc_taxa_efetiva` em paralelo com a projeção e injeta-a
  no contexto global como `ctx.ircTaxaEfetiva`.
- **`views.jsx`** — todas as chamadas do Hub que aceitam `irc_taxa` passam agora
  `ctx.ircTaxaEfetiva` (viabilidade, tornado, consolidado, Monte Carlo,
  VALA, sensibilidade VALA, viabilidade por cenários). Fallback de display
  atualizado.

### 4.3 Resumo das alterações

| Ficheiro | Natureza |
|---|---|
| `src/engine/data/pressupostos/globais.yaml` | Novo parâmetro `IRC_taxa_efetiva_planeamento: 0.13` |
| `src/api/serializers.py` | Expõe `irc_taxa_efetiva` no endpoint de assumptions |
| `interface/data.js` | Constantes únicas + correção dos ASSUMPTIONS nominais |
| `interface/api.js` | `API.assumptions()` + remoção dos defaults divergentes |
| `interface/app.jsx` | Busca a taxa da API e coloca em `ctx.ircTaxaEfetiva` |
| `interface/views.jsx` | Injeta `irc_taxa` em todas as chamadas do Hub |

---

## 5. Impacto e validação

- **Consistência:** existe agora um único valor de IRC em todo o sistema. Em modo
  *live* vem da API; em modo *mock/offline* vem do fallback `GRESTEL.IRC_TAXA_EFETIVA`.
- **Fim do enviesamento mock ↔ live:** o Monte Carlo e a viabilidade do Hub
  recebem a mesma taxa (13%) que a restante análise, em vez de 24,5%.
- **Viabilidade não subestimada:** ao usar a efetiva (13%) e não a nominal
  (25,5%), o VAL e a TIR do Hub e da Ecogres 4.0 refletem a eficiência fiscal
  real da empresa.
- **Validação executada:** sintaxe JS verificada (`node --check`); YAML e
  serializer Python validados; confirmado end-to-end que
  `GET /api/assumptions/effective` devolve `irc_taxa_efetiva = 0.13`.

---

## 6. Notas e recomendações futuras

- **Ecogres (subsidiária):** mantém a sua taxa própria no mock — é uma entidade
  distinta sob RETGS, fora do âmbito da taxa geral tratada em C-1.
- **Motor IRC (backend):** o `IRC_taxa_geral` de 0,20 (2025+) é o modelo fiscal
  legítimo por ano (21% em 2024 via sobreposição), que apura a efetiva real na
  DR. Não foi alterado — fazê-lo mudaria outputs auditados.
- **OE5 / 2025:** monitorizar atualizações do Orçamento do Estado (ex.:
  majoração de encargos com energia). As declarações estão sujeitas a revisão
  pela AT por 4 anos e devem seguir a legislação em vigor no momento.
- **Afinação:** a taxa de planeamento está centralizada num único parâmetro
  (`IRC_taxa_efetiva_planeamento`), pelo que qualquer revisão futura (ex.: para 8%
  ou 18%) é feita num só local.
