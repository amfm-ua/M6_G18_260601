# Plano de Contingência — Rejeição do PT2030 (Hub Logístico)

**Módulo:** `src/engine/projetos/contingencia_hub.py`  
**Parâmetros:** `pressupostos/subsidiarias/hub_logistico/m6_hub_assumptions.yaml`  
**Relacionado:** [plano_financiamento_hub.md](plano_financiamento_hub.md) · [fcf_modelacao_hub.md](fcf_modelacao_hub.md) · [dmi_modelacao_inventario.md](dmi_modelacao_inventario.md)

---

## 1. Enquadramento

A avaliação M6 colocou a seguinte questão estratégica:

> *«O Hub não é viável sem apoios fiscais. Se o PT2030 for rejeitado, é necessário um plano de financiamento alternativo. A sugestão é entrada de capitais próprios dos donos (Grestel). Analisar e quantificar.»*

O PT2030 (€2.700k, recebido em 2027) **não financia a construção**: o CAPEX de €6.000k está integralmente coberto por dívida (€4.500k) + capital próprio (€1.500k). O subsídio é um *reembolso a fundo perdido* posterior à obra. Logo:

- A entrada de capital próprio **não é necessária** para construir nem (dado o DSCR operacional ≥ 1,5×) para servir a dívida.
- É necessária para (i) substituir o **colateral** que o banco perde sem a cessão do subsídio (§6.1.2 do plano de financiamento) e (ii) para o banco aceitar manter a alavancagem sem subir o spread.
- Recapitalizar baixa o Ke mas **sobe o WACC** (perde-se o escudo fiscal da dívida barata) → não restaura o valor económico.
- O único mecanismo que **efetivamente restaura o valor** é redimensionar o CAPEX (faseamento de âmbito).

---

## 2. Correção Metodológica APV

### 2.1 O problema (antes da correção)

O módulo original usava o Ke alavancado (calculado para a estrutura de capital específica de cada cenário) para descontar o FCFF base. Esta abordagem viola o teorema de Modigliani-Miller: reduzir a dívida baixa o Ke → o mesmo cash flow descontado a uma taxa menor inflaciona artificialmente o VAL_base, criando a ilusão de que recapitalizar *cria* valor.

### 2.2 APV correto — Myers (1974)

No **APV (Adjusted Present Value)**, o valor total do projeto decompõe-se em:

```
VALA = VAL_base + PV(Escudo Fiscal) + PV(PT2030, líquido) + PV(RFAI)
```

Onde:
- **VAL_base** — FCFF descontado ao **Ku** (custo do capital *desalavancado*, constante e independente da estrutura de capital)
- **PV(Escudo Fiscal)** — valor presente dos juros × t, que *varia* com o montante de dívida
- **PV(PT2030)** e **PV(RFAI)** — subsídios tratados como fluxos separados ao Ku

O Ke alavancado e o WACC são calculados mas **apenas para reporte** (perfil de risco do acionista, taxa de desconto do FCFE); não afetam o VAL_base.

### 2.3 Parâmetros base

| Parâmetro | Valor | Fonte |
|-----------|-------|-------|
| β_u (desalavancado) | 0,71 | Damodaran, Ceramics Europe (2024) |
| r_f (OT10 PT) | 3,10% | Banco de Portugal, mai-2025 |
| ERP (Damodaran PT) | 5,78% | Damodaran, jan-2025 |
| **Ku = r_f + β_u × ERP** | **7,20%** | Calculado |
| Kd ponderado | 4,02% | Média das duas tranches |
| t (IRC efetivo) | 23,5% | Inclui derrama municipal |

O **Ku = 7,20%** é constante em todos os cenários. Quando a coluna "Ku" da tabela de resultados (§4) mostra o mesmo valor em todas as linhas, isso é a prova visual de que o APV é consistente com MM: a estrutura de capital não afeta o desconto dos cash flows operacionais.

---

## 3. Cenários Analisados

Todos os cenários excluem o PT2030 (RFAI mantido — regime autónomo, CFI art.º 22.º), exceto o cenário de referência.

| Código | Label | Equity (k€) | Dívida (k€) | D/E | CAPEX (k€) |
|--------|-------|-------------|-------------|-----|------------|
| `base` | Referência — com PT2030 + RFAI | 1.500 | 4.500 | 3,00 | 6.000 |
| `sem_apoios_atual` | Sem PT2030 — estrutura inalterada (RFAI mantido) | 1.500 | 4.500 | 3,00 | 6.000 |
| `recap_substituicao` | Recap (a) substituição integral | 4.200 | 1.800 | 0,43 | 6.000 |
| `recap_standby` | Recap (b) standby parcial | 2.250 | 3.750 | 1,67 | 6.000 |
| `recap_garantia` | Recap (c) só garantia da mãe | 1.500 | 4.500 | 3,00 | 6.000 |
| `capex_faseado` | CAPEX faseado Fase 1 — equity inalterado | 1.500 | 3.700 | 2,47 | 5.200 |
| `capex_faseado_standby` | CAPEX faseado + standby parcial | 2.250 | 2.950 | 1,31 | 5.200 |

### 3.1 Faseamento de âmbito — Fase 1 (CAPEX €5.200k)

O faseamento difere os componentes premium/expansão cujo retorno é mais incerto e que dependiam da folga de caixa do subsídio:

| Pool | Fase 1 (k€) | Base (k€) | Motivo do diferimento |
|------|-------------|-----------|----------------------|
| `robotica_amr` | 375 | 625 | Difere 2 de 5 AMRs — capacidade de pico → Fase 2 |
| `wms_software` | 400 | 600 | WMS base sem camada analytics/IA-vision plena |
| `box_on_demand` | 0 | 350 | Diferido integralmente — depende de carteira 3PL |

**Mantido na Fase 1:** construção civil (€2.535k), VLMs (€1.305k), energia solar (€270k), honorários (€120k), software integração (€195k).

> **Nota:** A energia solar é mantida deliberadamente. Cortá-la pouparia €270k de CAPEX mas duplicaria o custo de energia no OPEX (~80.000 kWh/ano sem offset PV), deteriorando o benefício líquido.

**Impacto nos benefícios (Fase 1 vs. base):**

| Benefício | Base (k€/ano) | Fase 1 (k€/ano) | Δ |
|-----------|--------------|-----------------|---|
| Poupança operacional | 440 | 350 | −90 |
| Redução de quebras | 65 | 0 | −65 (Box-on-Demand diferido) |
| OPEX incremental | 225 | 200 | −25 |
| **Benefício líquido** | **280** | **150** | **−130** |
| VN incremental B2C/3PL | base | 70% × base | −30% (haircut premium) |

---

## 4. Resultados

> Valores em k€. Ku = 7,20% (constante). IRC = 23,5%. RFAI mantido em todos os cenários (exceto base que mantém PT2030 adicionalmente).

| Cenário | VALA | VAL_base (Ku) | Escudo | RFAI | VAL(WACC) | TIR | DSCR_min | Ku | Ke_l | WACC |
|---------|-----:|--------------|--------|------|-----------|-----|----------|----|------|------|
| Base — PT2030 + RFAI | +2.490k | … | … | … | … | … | … | 7,20% | 16,6% | 6,46% |
| Sem PT2030, estrutura atual | −676k | … | … | … | … | … | … | 7,20% | 16,6% | 6,46% |
| Recap (a) substituição | −676k | … | … | … | … | … | … | 7,20% | 8,5% | 7,43% |
| Recap (b) standby | −676k | … | … | … | … | … | … | 7,20% | 12,4% | 6,94% |
| Recap (c) garantia | −676k | … | … | … | … | … | … | 7,20% | 16,6% | 6,46% |
| CAPEX faseado Fase 1 | +137k | … | … | … | … | … | … | 7,20% | 14,1% | 6,63% |
| Faseado + standby | +137k | … | … | … | … | … | … | 7,20% | 11,2% | 7,01% |

*Nota: executa `python -m src.engine.projetos.contingencia_hub` para obter todos os campos numéricos em detalhe.*

### 4.1 Leitura da tabela

**Ku constante (7,20%)** — confirma que o VAL_base não muda com a estrutura de capital (APV correto).

**Ke_l variável** — o Ke alavancado aumenta com D/E (Hamada), refletindo o risco acrescido para o acionista, mas não afeta o VALA.

**WACC inversamente proporcional à dívida** — mais dívida → WACC menor (mais escudo fiscal) → VAL(WACC) maior. Mas o VALA APV captura o mesmo efeito diretamente pelo PV(Escudo Fiscal), sem a distorção de misturar o efeito de financiamento na taxa de desconto do ativo.

---

## 5. Conclusões

### 5.1 A recapitalização não restaura o valor

Todos os cenários de recap (a), (b) e (c) produzem o mesmo VALA que "sem apoios, estrutura atual": **−676k**. Porquê?

- O VAL_base é descontado a Ku (constante) → é idêntico em todos os cenários com CAPEX = €6.000k.
- O que muda é apenas o PV(Escudo Fiscal): menos dívida → menos juros dedutíveis → menor escudo → VALA piora marginalmente.
- A recap (a) — substituição integral — é a **pior** das três: perde o maior escudo fiscal (D/E 0,43 vs. 3,00).

Esta conclusão é teoricamente robusta (MM com impostos, 1963) e empiricamente confirmada: a recapitalização serve para satisfazer os requisitos colaterais do banco, **não para criar valor económico**.

### 5.2 O CAPEX faseado é o único mecanismo que cria valor sem PT2030

O faseamento de âmbito (Fase 1, CAPEX €5.200k) produz **VALA > 0** sem PT2030 porque:

1. **Reduz o CAPEX em €800k** → reduz o capital em risco.
2. **Mantém os drivers de valor nuclear** (VLMs, 3 AMRs, energia solar, WMS base) → mantém ~54% do benefício líquido.
3. **Melhora a estrutura D/E** de 3,00 para ~2,47 (a dívida desce com o CAPEX) → mais DSCR headroom.

> A Fase 2 (os componentes diferidos) pode ser executada em 2028–2029, financiada pelos cash flows gerados pela Fase 1, sem necessidade de novo equity nem de PT2030.

### 5.3 Recomendação estratégica

Em caso de rejeição do PT2030:

1. **Primeiro passo (imediato):** reformular o contrato bancário — substituir a cessão do subsídio como colateral por garantia pessoal dos sócios/Grestel (recap c). Custo: zero em termos de valor; apenas exposição contingente dos sócios.
2. **Segundo passo (decisão de investimento):** adotar o faseamento de âmbito (Fase 1) e diferir os €800k de componentes premium para Fase 2, a executar com autofinanciamento.
3. **Não recomendar:** injeção massiva de capital próprio (recap a/b) — destrói valor fiscal sem recuperar o subsídio perdido.

---

## 6. Invariantes e Salvaguardas do Modelo

| Invariante | Verificação |
|-----------|-------------|
| Ku constante (7,20%) independente da estrutura | `via["ke"] = ku` em `_aplicar_estrutura_capital` |
| Escudo fiscal proporcional à dívida | `vala_hub` calcula PV(juros × t) por ano |
| DSCR ≥ 1,0 em todos os anos de amortização | `mapa_servico_divida` verifica por cenário |
| Sem dupla contagem na libertação de DMI | `impacto.py` devolve `clearing` + `estrutural` separados; consolidado usa só `clearing` |
| Faseamento Fase 1 não toca nos parâmetros de DMI | `_aplicar_fase1` altera CAPEX/benefícios; DMI ajusta-se via CMVMC do CAPEX menor |

---

## 7. Referências

- Myers, S. C. (1974). *Interactions of Corporate Financing and Investment Decisions — Implications for Capital Budgeting*. Journal of Finance, 29(1), 1–25.
- Modigliani, F. & Miller, M. H. (1963). *Corporate Income Taxes and the Cost of Capital: A Correction*. American Economic Review, 53(3), 433–443.
- Hamada, R. S. (1972). *The Effect of the Firm's Capital Structure on the Systematic Risk of Common Stocks*. Journal of Finance, 27(2), 435–452.
- Damodaran, A. (2025). *Damodaran Online — Country Risk Premiums and Betas*. Stern School of Business, NYU. [jan-2025]
- Brealey, Myers & Allen (2023). *Principles of Corporate Finance*, 14.ª ed., cap. 19 (APV) e cap. 17 (MM).
- CFI — Código Fiscal do Investimento, art.º 22.º (RFAI — Regime Fiscal de Apoio ao Investimento).
