# Cenário de Eficiência de Cozedura — *Mini Business Case*

**Aplicação à Grestel das conclusões da dissertação "Diminuição da Temperatura de Cozedura em Pastas de Sanitários" (Junqueira, Universidade de Aveiro / Roca, 2023)**

---

## 1. Enquadramento e motivação

A dissertação demonstra, em ambiente laboratorial e com validação microestrutural, que é possível **reduzir o patamar de cozedura de 1200 ºC para 1140 ºC** através da reformulação da pasta cerâmica — nomeadamente pela incorporação de **~2% de volastonite** e pelo ajuste do rácio de fundentes — mantendo a vitrificação (absorção de água < 0,5%). O ganho reportado é uma **poupança energética de ~18% por ciclo**.

Para a Grestel, esta conclusão é estrategicamente relevante porque ataca diretamente um dos seus maiores desafios atuais: a **instabilidade dos preços da energia** (gás natural e eletricidade). Diferentemente das iniciativas já em curso, esta alavanca atua sobre a **procura** de energia, e não sobre a oferta.

## 2. Complementaridade com as iniciativas atuais (não redundância)

A Grestel já opera na vanguarda da descarbonização cerâmica europeia. As conclusões da tese são **aditivas** — não substituem o que existe:

| Eixo | Iniciativas Grestel (oferta de energia / circularidade) | Tese (procura de energia) |
|---|---|---|
| Combustível | 1.ª cozedura industrial europeia com **50% de hidrogénio**; eletricidade 100% renovável certificada; 1.180 kW fotovoltaico | — |
| Processo | Recuperação de calor dos fornos; isolamento avançado; retoque por **laser** (evita 2.ª cozedura) | **Menos calor necessário** para vitrificar |
| Materiais | **ECOGRES 4.0**: >95% material reciclado; simbioses industriais | Reformulação mineral da pasta |

> **Efeito multiplicador:** queimar com **menos energia** (tese) *e* com **combustível mais limpo** (H₂/renovável) compõe-se. A redução de gás por peça é independente da origem do combustível, pelo que os ganhos da tese somam-se aos do Projeto H₂.

## 3. Validade da transferência: sanitário → grés fino (por analogia)

A tese incide sobre **louça sanitária** (*vitreous china*, peças massivas); a Grestel produz **grés fino de mesa** (Costa Nova, peças finas). A transferência assenta em **três pilares comuns**:

1. **Base mineralógica idêntica** — argilas, caulinos, feldspatos e quartzo; a lógica de introduzir fundentes (volastonite) para baixar a temperatura é universal.
2. **Mesmo critério de qualidade** — absorção de água < 0,5%, padrão exigido em ambos os setores.
3. **Mesmo desafio energético** — ambos intensivos em energia e sob pressão de descarbonização.

Operacionalmente, a louça de mesa tem **ciclos de cozedura mais flexíveis** e a Grestel já possui cultura de I&D em formulação de pastas (Ecogres), o que *facilita* o ensaio. Trata-se, porém, de uma **prova de conceito a validar industrialmente**, não de uma certeza — daí o faseamento (Secção 5).

## 4. Modelação financeira — estrutura de "duas pernas" + investimento

O cenário foi implementado no motor M6 como um **toggle** (`cozedura_on`), à semelhança do Hub Logístico e da Ecogres. Quando ativo, produz três efeitos coerentes a partir de uma única tabela de pressupostos:

| Perna | Rubrica | Mecânica | Sinal no EBITDA |
|---|---|---|---|
| **1. Poupança de energia** | FSE (Gás + Eletricidade) | `ramp × 18% × (Gás×100% + Eletricidade×50%)` | ↑ (principal) |
| **2. Pasta reformulada** | CMVMC | `ramp × 0,3% × CMVMC` (custo da volastonite + moagem mais fina) | ↓ ligeiro |
| **3. Investimento I&D** | Caixa / fiscal | One-off €200k (2027) + crédito SIFIDE II | *appraisal* de viabilidade |
| **Bónus ESG** | gás/peça | alavanca de eficiência extra, soma ao programa H₂ | melhora o objetivo SMART |

**Base de incidência energética (premissa-chave):** os 18% incidem sobre **100% do Gás Natural** (vetor térmico do forno: 4,3 MWh/t cozido) e **~50% da Eletricidade** (parcela de fornos/secagem; exclui iluminação, conformação e administrativo). É uma premissa **conservadora** — ignora ganhos em áreas não térmicas — adotada porque as fontes não desagregam o consumo elétrico por etapa.

## 5. Pressupostos e faseamento

| Parâmetro | Valor | Fundamentação |
|---|---|---|
| Poupança energética por ciclo | **18%** | Tese (1200 → 1140 ºC) |
| Base de gás elegível | 100% | Combustível 100% térmico |
| Base de eletricidade elegível | ~50% | Fornos/secagem; consumo elétrico 0,595 MWh/t |
| Incremento de CMVMC | +0,3% (pleno) | 2% volastonite (mineral técnico) + moagem d50 ~3 µm |
| Investimento I&D (2027) | €200 000 | Referência: €116k em eficiência energética (Grestel, 2024) |
| Crédito SIFIDE II | 32,5% (base) | Art. 35.º CFI; *upside* ~60% (rácio Grestel 2024: 380 795 / 632 304) |
| WACC (*appraisal*) | 7,3% | Alinhado com viabilidade do Hub |

**Curva de adoção (faseamento):** justificada pelo risco de resistência mecânica e pela necessidade de ensaios industriais —

- **2027 — Piloto (~⅓):** validação da resistência mecânica em vagonas de teste.
- **2028 — Escalabilidade (~⅔):** roll-out parcial após otimização.
- **2029 — Pleno (100%):** maturação da poupança de 18%.

## 6. Resultados — impacto recorrente na DR

Efeito **líquido** (Perna 1 − Perna 2) propagado a EBITDA → EBIT → Resultado Líquido:

| Ano | Poupança energia (FSE) | Custo pasta (CMVMC) | **Δ EBITDA** | Δ Result. Líquido | Margem EBITDA |
|---:|---:|---:|---:|---:|---:|
| 2027 | +59 299 € | −18 545 € | **+40 754 €** | +32 769 € | 14,57% → 14,66% (+0,09 pp) |
| 2028 | +124 493 € | −39 363 € | **+85 130 €** | +64 273 € | 14,60% → 14,77% (+0,17 pp) |
| 2029 | +195 979 € | −62 651 € | **+133 327 €** | +100 662 € | 13,67% → 13,92% (+0,25 pp) |

> A poupança de energia é, no regime de cruzeiro, **~3,1×** o custo incremental da pasta — o efeito líquido é claramente positivo e **protege a margem operacional contra a volatilidade futura do preço do gás**.

### 6.1 Objetivo SMART — Gás Natural por peça

O cenário **ultrapassa largamente** o objetivo SMART ESG (Tabela 8, Obj. 7: reduzir −10% o gás/peça até 2026):

| Ano | Base (só H₂) | **Com cozedura baixa temp** | Alvo SMART |
|---:|---:|---:|---:|
| 2026 | −5,9% | −5,9% | −10% |
| 2027 | −8,7% | **−14,4%** | — |
| 2028 | −11,5% | **−22,1%** | — |
| 2029 | −14,1% | **−29,1%** | — |

Já em **2027** (ano-piloto) o objetivo de −10% é cumprido, atingindo **−29,1% em 2029** — reforçando o alinhamento com a **Taxonomia UE** (Reg. 2020/852, art. 10.º, *manufacturing with GHG reduction*) e com a certificação **ISO 14001:2015**.

## 7. *Business case* — investimento, payback e VAL

Tratado como projeto autónomo de baixo *capex* (inovação de processo), à semelhança da análise de viabilidade do Hub:

| Métrica | Valor |
|---|---|
| Investimento bruto (2027) | €200 000 |
| Crédito SIFIDE II (32,5%) | €65 000 |
| **Investimento líquido** | **€135 000** |
| Ganho EBITDA em regime de cruzeiro (2029) | €133 327/ano |
| **Payback (faseado, desde 2027)** | **~2,3 anos** |
| **Payback (regime de cruzeiro)** | **~1,3 anos** |
| VAL do projeto (5 anos, WACC 7,3%, s/ valor terminal) | +€53 716 |

*Upside* fiscal: a uma taxa SIFIDE de ~60% (observada na Grestel em 2024), o investimento líquido cai para ~€80k e o payback aproxima-se de 1 ano.

## 8. Impacto na avaliação intrínseca (DCF/FCFF)

Capitalizando o ganho líquido estrutural (€133k/ano no pleno) como melhoria **permanente** de custos (perpetuidade, WACC 6,21%, *g* 2%, t 21%) e descontando o investimento líquido:

| Componente | Valor (€ mil) |
|---|---:|
| VP do NOPAT incremental 2025-2029 | +159,7 |
| VP do valor terminal | +1 912,1 |
| (−) VP do investimento líquido | −112,7 |
| **Δ Equity (estimativa)** | **≈ +1 959** |

Acréscimo de **~€2,0 M** ao valor do capital próprio — material (≈ +4% sobre a média ponderada de €47,2 M da OE5), mas não dominante, e fortemente assente na hipótese de **permanência** da poupança. Recomenda-se reportar como **cenário de sensibilidade positivo**, não como caso base.

## 9. Riscos e o que pode correr mal (análise crítica)

1. **Défice de resistência mecânica** *(risco técnico principal)* — a composição W3 atingiu apenas **31,7 MPa @1140 ºC** (e 40,3 MPa @1200 ºC) contra **56,8 MPa** da referência @1200 ºC, abaixo do mínimo industrial (>550 kg/cm²). Em louça fina (Costa Nova), pode elevar **quebras/caco**, anulando a poupança. → mitigado pelo piloto 2027 e por ciclos de patamar mais curtos.
2. **Incremento de matéria-prima** — volastonite é mineral de maior valor; alternativas (nefelina) são "muito dispendiosas". Modelado na Perna 2.
3. **Incerteza de transferência tecnológica** — resultados obtidos em **fornos elétricos de laboratório**; o forno de túnel industrial (atmosfera, pressão, ciclos longos) pode gerar defeitos; vidrados específicos da Grestel não validados.
4. **Deformação piroplástica e moagem** — fase vítrea demasiado fluida → empenamento; partículas finas (d50 ~3 µm) exigem moagem mais longa, aumentando o **consumo elétrico na preparação** (parcialmente contra-cíclico ao ganho).
5. **Fatores financeiros/operacionais Grestel** — covenant **Dívida Líquida/EBITDA ≤ 3,5×**: um insucesso do I&D pressionaria a liquidez num ano desafiante; a introdução da nova pasta exige formação técnica, num contexto de dificuldade de **retenção de mão-de-obra qualificada**.

## 10. Conclusão

A reformulação de pasta para baixa temperatura constitui uma alavanca de **baixo investimento e alto retorno** (payback de regime ~1,3 anos), **complementar** — e não redundante — face ao portefólio ESG da Grestel. Demonstra que a empresa não está apenas a **expandir** (Hub Logístico, investimento em ativos tangíveis), mas também a **otimizar a estrutura de custos** (eficiência térmica, ativo intangível/I&D), protegendo a rentabilidade contra a volatilidade do gás e acelerando o cumprimento das suas metas de descarbonização. A prudência impõe, contudo, que seja apresentada como **cenário de sensibilidade positivo, condicionado à validação industrial da resistência mecânica**.

---

### Nota técnica — reprodutibilidade

```python
from src.engine.modelo.model import run_model
dfs = run_model(cenario="Base", cozedura_on=True)
dfs["dr"]                 # colunas: cozedura_fse_reducao, cozedura_cmvmc_incremento
dfs["cozedura_appraisal"] # FCF do projeto (investimento, SIFIDE, desconto)
dfs["cozedura_resumo"]    # VAL, payback (faseado e de regime), investimento líquido
```

Pressupostos editáveis em `src/engine/data/master/cozedura_baixa_temp.yaml`.
O toggle desativado (`cozedura_on=False`) reproduz exatamente o cenário Base (verificado: DR/Balanço/DFC idênticos).
