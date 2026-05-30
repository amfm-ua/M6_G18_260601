# Correção do Plano de Financiamento — Conformidade Legal (PT2030 / RFAI / RGIC)

> **Estado:** motor (YAML) e testes já corrigidos e verdes; **Cap. 6** do relatório
> reescrito. Restante relatório / OE5 / âncoras de memória **por propagar** (em pausa
> a pedido). Este documento é a referência única da correção.
> **Data:** 2026-05-30 · M6 · Grupo 18.

---

## 1. Problema detetado

O plano de financiamento original assumia, sobre o mesmo CAPEX elegível de €6,0 M:

- **Subsídio PT2030 a fundo perdido de €2,7 M (45 %)**, enquadrado no *"Sistema de Incentivos à Qualificação das PME"*; e
- **Crédito fiscal RFAI de €0,6 M (10 %)**.

Intensidade de auxílio público combinada = **€3,3 M = 55 % do CAPEX**.

Isto é **legalmente inviável** e levaria à reprovação da candidatura, por três motivos cumulativos — todos confirmados no próprio repositório e em fontes oficiais.

---

## 2. As três restrições legais (com fontes)

### 2.1. A Grestel é grande empresa → sem acesso a fundo perdido PME
O próprio repositório documenta: *"A Grestel é grande empresa (734 trabalhadores em 2024)"*
([correcao_irc_taxa_efetiva.md](correcao_irc_taxa_efetiva.md)). O **SI Inovação Produtiva /
Qualificação das PME do PT2030 é exclusivo de PME** — uma grande empresa não acede a
subsídio não reembolsável neste programa (acesso restrito a I&D / *calls* específicas,
p. ex. projetos STEP até ~40 %). O enquadramento original ("Qualificação das PME") era,
por isso, duplamente impossível.

### 2.2. Teto de intensidade de auxílio regional: 30 % em Aveiro/Centro
Mapa de auxílios com finalidade regional de Portugal 2022-2027: a Região de Aveiro
(NUTS III, Centro) tem intensidade máxima para **grande empresa = 30 % do CAPEX**
(os 40 % só se aplicam a parcelas de território de transição justa, onde Aveiro não
entra). Majorações de +10 pp (média) e +20 pp (micro/pequena) **não** se aplicam à
Grestel.

### 2.3. Regra de cumulação: PT2030 + RFAI somam e ficam capados a 30 %
O somatório de **todos** os auxílios sobre o **mesmo investimento** (subsídio PT2030 +
benefício fiscal RFAI) não pode exceder a intensidade máxima do mapa regional
(RGIC — Reg. (UE) 651/2014, art. 8.º; CFI art. 43.º + Portaria 297/2015, art. 4.º).
Para a Grestel em Aveiro: **30 %**.

**A conta que reprova:** 45 % (subsídio) + 10 % (RFAI) = **55 % > 30 %** → ~€1,5 M
acima do teto legal.

### Fontes
- [Comissão Europeia — mapa de auxílios regionais Portugal 2022-2027 (IP/22/805)](https://ec.europa.eu/commission/presscorner/api/files/document/print/pt/ip_22_805/IP_22_805_PT.pdf)
- [CE — alteração ao mapa 2022-2027 (transição justa, 40 %)](https://portugal.representation.ec.europa.eu/news/auxilios-estatais-comissao-altera-mapa-dos-auxilios-com-finalidade-regional-2022-2027-para-portugal-2023-04-27_pt)
- [PME Incentivos — SI Inovação Produtiva PT2030 (exclusivo PME; taxas Centro)](https://pmeincentivos.pt/biblioteca/inovacao-produtiva-portugal-2030-candidaturas)
- [PME Incentivos — RFAI Guia Completo 2026](https://pmeincentivos.pt/biblioteca/rfai-regime-fiscal-apoio-investimento-guia-completo)
- [OCC — Benefícios fiscais RFAI (taxas e cumulação)](https://www.occ.pt/pt-pt/noticias/beneficios-fiscais-rfai-0)
- [Portal dos Incentivos — RFAI (cumulação, art. 43.º CFI / Portaria 297/2015)](https://portaldosincentivos.pt/index.php/rfai)

---

## 3. Situação financeira da Grestel (condiciona o mix)

Dados auditados 2024 ([base.yaml](../src/engine/data/historico/2024/base.yaml)):

| Indicador | Valor 2024 | Implicação para o financiamento |
|---|---:|---|
| Capital próprio | €12,2 M | Equity adicional limitado |
| Dívida financeira total | €17,7 M | Alavancagem elevada |
| **Dívida Líquida / EBITDA** | **≈ 4,1×** | Minimizar nova dívida comercial |
| Caixa | **€0,54 M** | Liquidez fina → preservar caixa |
| Fluxo operacional 2024 | **−€1,67 M** | Pressão de tesouraria (inventário €13 M) |
| Autonomia financeira | ≈ 30 % | No mínimo de conforto |
| Colateral imobiliário | Onerado (hipotecas BPI) | → Garantia mútua, não colateral real |
| EBITDA | €4,15 M | Cobre o serviço da dívida do Hub com folga |

---

## 4. Plano corrigido (base prudente — subsídio = 0)

**CAPEX €6,0 M.**

### Fontes de capital
| Fonte | Montante | % | Racional |
|---|---:|:---:|---|
| Capitais próprios Grestel | €1,5 M | 25 % | Mínimo RGIC livre de apoio público |
| Linha BEI verde/digital (via BPF) | €1,8 M | 30 % | Bonificação Clima/Digital → 3,70 % |
| Linha Banco de Fomento c/ Garantia Mútua | €1,7 M | 28 % | Sem colateral real; spread −30 bp → 3,85 % |
| Crédito comercial CGD/BPI (residual) | €1,0 M | 17 % | Minimizado → 4,15 % |
| **Total dívida** | **€4,5 M** | **75 %** | Kd médio **3,86 %**; ≥2 fontes ✓ |

### Apoio público (≤ teto 30 %)
| Instrumento | Montante | Conta p/ teto 30 %? |
|---|---:|:---:|
| **RFAI** (22,5 % = 25 % até €5 M + 10 % acima, Centro) | **€1,35 M** | Sim |
| Subsídio fundo perdido | **€0** (upside) | Sim |
| **Intensidade regional total** | **€1,35 M = 22,5 %** | ✅ **legal (folga 7,5 pp)** |

> *Upside fora do teto regional (não modelado):* **SIFIDE** sobre a componente de I&D
> genuína (Digital Twin, visão IA, ML de previsão) — é auxílio à I&D, categoria distinta,
> não consome o teto de 30 %. Disponível a grande empresa.

---

## 5. Impacto na avaliação (números do motor)

| Métrica | Antigo (ilegal, 55 %) | Novo (legal, ≤22,5 %) |
|---|---:|---:|
| **VALA (APV)** | €3.436.510 | **€1.122.378** |
| └ VAL base (Ku, ops+comercial) | €927.700 | €918.966 |
| └ Escudo fiscal da dívida | €199.700 | €193.438 |
| └ PT2030 (subsídio) | €2.084.376 | **€0** |
| └ RFAI (APV, conservador) | €224.734 | €9.975 |
| **VAL (WACC)** | €2.493.770 | **€1.333.787** |
| **TIR** | 17,49 % | **12,01 %** |
| Índice de rendibilidade | 1,42 | **1,22** |
| Payback atualizado | 7,37 a | **9,19 a** |
| WACC / Kd | 6,46 % / 4,02 % | **6,37 % / 3,86 %** |
| DSCR mín. standalone (2028) | 1,58× | **1,09×** |

### Leitura
1. **O projeto continua viável e legal:** VAL **+€1,33 M**, TIR **12,0 %** (>> WACC 6,37 %),
   VALA **+€1,12 M**. Cria valor sem depender de apoio ilegal.
2. **61 % do "valor" anterior era o subsídio impossível** (€2,08 M de €3,44 M).
3. **RFAI subvalorizado no APV:** o modelo absorve o crédito contra o **IRC só do Hub**
   (postura conservadora já documentada). Sem o subsídio a inflar a base tributável, o Hub
   gera pouco IRC e só absorve €316 k dos €1,35 M (resto em *carry-forward* 10 anos).
   Contra o **IRC total da Grestel** (~€127 k–1,5 M/ano) o RFAI seria absorvido depressa e o
   VALA subiria para **~€1,5–1,8 M**. O €1,12 M é, portanto, um **piso ultra-conservador**.
4. **DSCR standalone 1,09× em 2028** (era 1,58× inflacionado pelo accrual NCRF 22 do
   subsídio). Coberto pela geração consolidada da Grestel (~€4,15 M EBITDA); o risco de
   liquidez é circunscrito ao arranque, não de solvência.
5. **Cenários adversos passam a negativos** (Downside −€1,22 M, Stress −€3,10 M) sem a
   almofada do subsídio → reforça o Plano de Contingência (Cap. 13).

### Novos valores canónicos por cenário (motor)
| Cenário | VAL (€) | TIR |
|---|---:|---:|
| Base | 1.333.787 | 12,01 % |
| Upside | 2.716.215 | 19,09 % |
| Downside | −1.217.468 | 2,70 % |
| Stress | −3.104.882 | −5,24 % |

### Novo mapa de serviço da dívida e cobertura
| Ano | Capital em dívida | Amortização | Juros | Prestação | EBITDA inc. | DSCR | ICR |
|---|---:|---:|---:|---:|---:|:---:|:---:|
| 2025 | 2.700.000 | — | 106.950 | 106.950 | — | — | — |
| 2026 | 4.500.000 | — | 173.550 | 173.550 | 437.500 | 2,52× | 2,52× |
| 2027 | 4.500.000 | — | 173.550 | 173.550 | 582.300 | 3,36× | 3,36× |
| 2028 | 4.050.000 | 450.000 | 173.550 | 623.550 | 682.443 | 1,09× | 3,93× |
| 2029 | 3.600.000 | 450.000 | 156.195 | 606.195 | 737.941 | 1,22× | 4,72× |

---

## 6. Alterações já aplicadas (fonte de verdade)

Ficheiros editados e **verificados** (motor corre; 105 testes passam, 5 *skipped*):

- [`m6_hub_assumptions.yaml`](../src/engine/data/subsidiarias/hub_logistico/m6_hub_assumptions.yaml)
  e a cópia [`_defaults`](../src/engine/data/_defaults/subsidiarias/hub_logistico/m6_hub_assumptions.yaml):
  - `financiamento`: 3 tranches (Linha_BEI €1,8M @3,70 %, Linha_Fomento_GM €1,7M @3,85 %,
    Banco_Comercial €1,0M @4,15 %); `PT2030.montante: 0`.
  - `rfai.taxa: 0.225` (era 0.10).
  - `viabilidade.wacc: 0.0637` (era 0.0646), `viabilidade.kd: 0.03857` (era 0.0402).
- [`tests/test_hub_viabilidade_cenarios.py`](../tests/test_hub_viabilidade_cenarios.py):
  valores canónicos VAL/TIR/IR/payback atualizados.
- [`m6_markdowns/07_plano_financiamento.md`](../m6_markdowns/07_plano_financiamento.md):
  Cap. 6 reescrito por completo (nota de conformidade, mix novo, mapa da dívida, DSCR honesto).

---

## 7. Propagação pendente (checklist — POR FAZER)

O motor é a fonte de verdade; estes ficheiros ainda mostram os números antigos e estão
**dessincronizados**. Substituir pelos valores da secção 5:

- [ ] [`01_sumario_executivo.md`](../m6_markdowns/01_sumario_executivo.md) — fontes de
      financiamento (CGD €3M/BEI €1,5M → 3 tranches), subsídio €2,7M → 0, RFAI €0,6M → €1,35M.
- [ ] [`10_cashflows_viabilidade.md`](../m6_markdowns/10_cashflows_viabilidade.md) — VAL/TIR/IR/
      payback, decomposição APV (PT2030 €0), Tornado (rever driver PT2030), tabela de cenários,
      Monte Carlo (regenerar com o motor corrigido).
- [ ] [`12_conclusao.md`](../m6_markdowns/12_conclusao.md) — números-síntese.
- [ ] [`08_projecoes_economicas_financeiras.md`](../m6_markdowns/08_projecoes_economicas_financeiras.md),
      [`09_analise_riscos.md`](../m6_markdowns/09_analise_riscos.md),
      [`13_plano_contingencia.md`](../m6_markdowns/13_plano_contingencia.md),
      [`15_anexos.md`](../m6_markdowns/15_anexos.md) — referências dispersas a 45 %/€2,7M/WACC 6,46 %.
- [ ] [`metodologia_apv_val_sem_beneficios_fiscais.md`](metodologia_apv_val_sem_beneficios_fiscais.md) —
      decomposição APV e cenários "sem PT2030".
- [ ] [`memory/project_m6_anchors.md`](../memory/project_m6_anchors.md) — VALA €1,917M / PT2030 €2.700k
      (desatualizado).
- [ ] **OE5** ([`oe5_markdowns/`](../oe5_markdowns/)) — regenerar a partir do motor corrigido.

> Nota: a memória do projeto regista que *"os números da avaliação OE5 vêm do motor
> (engine/API), não inventados"* — pelo que a regeneração do OE5 deve ler diretamente o
> motor já corrigido, não copiar valores à mão.
