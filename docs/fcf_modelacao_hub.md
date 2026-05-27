# Modelação de FCF no Hub Logístico

## 1. FCFF vs FCFE — Definições

**FCFF (Free Cash Flow to the Firm / Fluxo de Caixa Livre da Empresa)**
Representa o dinheiro disponível para todos os provedores de capital (acionistas e credores), antes de qualquer despesa financeira ou serviço de dívida.

**FCFE (Free Cash Flow to Equity / Fluxo de Caixa Livre para o Acionista)**
Representa o dinheiro que sobra exclusivamente para os sócios, após o pagamento de juros e amortizações de dívida.

---

## 2. Implementação no Modelo

### 2.1 FCFF — Métrica Principal

O modelo utiliza **FCFF descontado ao WACC** como métrica central de avaliação.

**Fórmula implementada** (`src/engine/projetos/hub_logistico/impacto.py`, função `hub_fcf()`):

```
FCF = NOPAT + D&A − CAPEX − ΔNFM ± Variações pontuais

onde:
  NOPAT = EBIT × (1 − t)
  D&A   = Depreciações e amortizações (adicionadas de volta por serem não-caixa)
  CAPEX = Investimento em capital fixo
  ΔNFM  = Variação das Necessidades de Fundo de Maneio
```

**Componentes incluídos no FCFF:**

| Componente | Descrição |
|---|---|
| `nopat` | EBIT após IRC |
| `depreciacao` | D&A (pools + juros capitalizados, NCRF 10) |
| `capex` | Investimento em ativo fixo |
| `delta_nfm` | Variação anual do fundo de maneio |
| `inventario_libertado` | Libertação pontual de inventário (2026) |
| `terreno_oportunidade` | Custo de oportunidade do terreno |
| `fcf_livre` | FCF desalavancado final |

**Exclusões do FCFF** (convenção Brealey, Myers & Allen):
- Juros de financiamento — incorporados no WACC
- Amortizações e drawdowns de empréstimos — fluxos de financiamento
- Crédito RFAI — tratado separadamente no modelo APV/VALA
- Subsídio PT2030 em caixa — componente autónomo no APV

### 2.2 FCFE — Opção via Parâmetro

O FCFE está disponível como ajuste ao valor terminal, controlado pelo parâmetro `incluir_liquidacao_divida` em `viabilidade.py`:

```python
# Valor terminal ajustado para perspetiva do acionista:
vt = (valor_realizacao - imposto_mais_valia) + nfm_recovery - capital_vivo_t10
```

A função `_capital_vivo()` calcula o capital em dívida remanescente no horizonte final, agregando todas as tranches (`Banco_Hub`, `Linha_BEI`).

**Por defeito, o modelo usa FCFF** (`incluir_liquidacao_divida=False`).

### 2.3 Parâmetros de Avaliação (YAML)

Definidos em `src/engine/data/subsidiarias/hub_logistico/m6_hub_assumptions.yaml`:

| Parâmetro | Valor |
|---|---|
| WACC | 6,3% |
| IRC (taxa efetiva) | 24,5% |
| Ke (custo do capital próprio) | 16,18% |
| Kd (custo da dívida) | 4,02% |
| Horizonte | 10 anos (2025–2034) |
| CAPEX base | 6 000 k€ |

---

## 3. Horizonte do Modelo e Extrapolação 2030–2034

### 3.1 Estrutura dos 10 Anos de FCF

O Hub tem **10 anos de FCFs calculados (2025–2034)**. O motor core Grestel projeta até 2029; os anos 2030–2034 são obtidos por extrapolação no loop de extensão (`viabilidade.py`, linhas 387–438):

```python
ebitda_ext = ebitda_prev * (1 + g)   # EBITDA cresce à taxa g
"capex": 0.0                          # Sem reinvestimento
"delta_nfm": 0.0                      # Fundo de maneio congelado
```

Onde `g = 3,5%/ano` (`crescimento_anual` no YAML), justificado como 2% inflação + 1,5% crescimento real.

### 3.2 Valor Terminal em 2035

Definido em `m6_hub_assumptions.yaml` (linhas 391–402):

| Premissa | Valor |
|---|---|
| `mais_valia_estimada` | 0 — ativos vendidos ao valor contabilístico exato |
| `taxa_realizacao_ativos` | 1,0 — sem prémio de mercado |
| NFM terminal | Reverte integralmente a cash (`calcular_engine: true`) |

O VLC é calculado deterministicamente pelas depreciações acumuladas (não é uma premissa, é contabilístico). A premissa relevante é **mais-valia = 0**: assume-se que em 2035 os ativos valem exatamente o seu valor líquido contabilístico (≈ 1 878 k€).

### 3.3 Comparação: Extrapolação Atual vs. Motor Completo a 2034

| Premissa | Extrapolação atual | Com motor a 2034 |
|---|---|---|
| EBITDA 2030–2034 | EBITDA₂₀₂₉ × (1,035)^k | Calculado com inflação real + crescimento de vendas Grestel |
| CAPEX | 0 (sem reinvestimento) | CAPEX BAU da Grestel nos anos correspondentes |
| ΔNFM | 0 (fundo de maneio fixo) | NFM com clientes/fornecedores/inventário reais |

O valor terminal em 2035 (VLC + NFM) mantém-se igual em ambos os cenários.

**Conclusão:** O ganho de rigor com a extensão do motor é real mas marginal — os 3,5% anuais são uma assunção razoável e conservadora. Para o entregável académico, a extrapolação é defensável.

---

## 4. Possível Melhoria: CAPEX e NFM na Extrapolação

### 4.1 Limitação Atual

Os anos 2030–2034 assumem CAPEX = 0 e ΔNFM = 0, o que subestima ligeiramente o investimento de manutenção necessário e ignora o crescimento natural do fundo de maneio.

### 4.2 Parametrização Alternativa

**No YAML — definir os parâmetros:**

```yaml
extensao_2030_2034:
  capex_manutencao_pct_ativo: 0.02   # 2% do valor bruto dos ativos/ano
  nfm_crescimento_par_ebitda: true    # ΔNFM acompanha crescimento do EBITDA à taxa g
```

**No loop de extensão (`viabilidade.py:387`) — em vez de zeros fixos:**

```python
# CAPEX de manutenção: % do valor bruto dos ativos
capex_manut = capex_base_ext * pct_manut   # 6 000 k€ × 2% = 120 k€/ano

# ΔNFM proporcional ao crescimento do EBITDA
delta_nfm_ext = nfm_ultimo_ano * g         # cresce à mesma taxa g = 3,5%

fcf_ext = nopat_ext + dep_total_ext - capex_manut - delta_nfm_ext
```

**Efeito prático:** FCFs ligeiramente menores nos anos de extensão → VAL mais conservador. Ordem de grandeza estimada: ~120 k€/ano de CAPEX e ~15–20 k€/ano de ΔNFM, face a FCFs de ~700–900 k€ — impacto pequeno mas metodologicamente mais rigoroso.

### 4.3 Questão para Validação Académica

> "No Hub, os anos 2030–2034 são extrapolados com CAPEX=0 e ΔNFM=0. Do ponto de vista académico, esta simplificação é defensável ou devemos modelar um CAPEX de manutenção e variações de fundo de maneio proporcionais ao crescimento do EBITDA nesse período?"

**Resposta técnica:** É possível e seria correto parametrizar ambos. A simplificação atual é conservadora (subestima o FCF ao ignorar reinvestimento e NFM crescente), não metodologicamente errada. Para o relatório, basta reconhecer a limitação e justificar a assunção.
