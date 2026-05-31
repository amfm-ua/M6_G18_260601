# Revisão de dois achados sobre financiamento — enquadramento correcto

> Data: 2026-05-31 · Contexto: revisão pré-entrega M6/OE5.
> Dois achados foram reportados como "bugs críticos de NCRF/legalidade". A revisão
> técnica abaixo **corrige o enquadramento**: um é um erro de dados real (corrigível
> numa linha), o outro **não é um bug** mas uma escolha de modelação, agora explicitada.

---

## Achado #1 — `rec_emprestimos` negativo em 2026

### Enquadramento reportado (incorrecto)
> "Violação da NCRF 2 §33 em `dfc.py:399`; corrigir limitando `rec_emp` a zero."

### Enquadramento correcto
A linha [`dfc.py:399`](../src/engine/demonstracoes/dfc.py) **está correcta**. Faz a
reconstrução-padrão dos desembolsos brutos a partir da variação líquida da dívida e
das amortizações:

```
rec_emp = Δdívida + amortizações       # novo financiamento bruto
```

O valor negativo **não é causado** por esta fórmula — é por ela **revelado**. A causa
real é uma **violação da identidade de roll-forward da dívida** nos *dados de input*
(`schedules.yaml`):

```
D_t = D_{t-1} − Amort_t      ⇒      Amort_t = D_{t-1} − D_t
```

Somando as sete tranches de empréstimo (BPI, Santander, CGD-COVID, CGD-OS, Abanca,
IAPMEI, Locações), a `amortizacoes_capital` registada bate com a redução real da
dívida em **todos os anos excepto 2026**:

| Ano | Σ redução tranches (real) | `amortizacoes_capital` | erro |
|-----|------:|------:|------:|
| 2025 | 5.530.545 | 5.530.545 | 0 ✓ |
| **2026** | **4.463.738** | **2.043.094** | **2.420.645 ✗** |
| 2027 | 1.873.533 | 1.873.533 | 0 ✓ |
| 2028 | 1.723.912 | 1.723.912 | 0 ✓ |
| 2029 | 1.562.907 | 1.562.907 | 0 ✓ |

O valor errado (€2.043.093,62) é a **parcela corrente** `emprestimos_c[2025]` da
classificação de referência (ver [analise_balanco_coerencia.md §2](analise_balanco_coerencia.md)),
copiada por lapso para uma linha de *fluxo*. É um número de **saldo** colocado numa
rubrica de **fluxo**.

### Correcção (uma linha de dados, não de código)

```yaml
# src/engine/data/computed/schedules.yaml
amortizacoes_capital:
  2026: 4463738.28   # era 2043093.62 — repõe D_2025 − D_2026
```

**Porque é segura e correcta:**
- `rec_emprestimos[2026]` volta a ≈0 (não houve novo financiamento nesse ano) — o
  artefacto de "influxo negativo" desaparece, que é o que a NCRF 2 (apresentação
  bruta dos fluxos de financiamento) efectivamente exige.
- `pag_emprestimos[2026]` passa a −€4,46 M (o reembolso real).
- O **`fluxo_financiamento` é invariante**: `rec_emp − amort = Δdívida`, independente
  da forma como se reparte. Logo `variação_caixa` e `reconciliacao_ok` não mexem; o
  Balanço (que lê `emprestimos_NC/C` directamente, não esta linha) não muda.

**Porque o "clamp a zero" estava errado:** congelaria `rec_emp` em 0 deixando
`amort` em €2,04 M, partindo o `fluxo_financiamento` em €2,42 M e **falhando** a
reconciliação DFC↔Balanço que dizia proteger — escondendo €2,42 M de redução de
dívida não explicada.

> Estado: **diagnosticado, fix pendente** (ver plano em §Plano abaixo).

---

## Achado #2 — Amortizações = 0 em 2030–2034

### Enquadramento reportado (incorrecto)
> "Congelamento ilegal da dívida; viola o CIRC art. 87.º e covenants."

### Enquadramento correcto
- O **CIRC art. 87.º** define a **taxa de IRC**, não regras de amortização de dívida.
  A citação não se aplica.
- O modelo **não tem módulo de covenants** ([`balanco.py:447-449`](../src/engine/demonstracoes/balanco.py)
  declara explicitamente que a linha de crédito é um *plug* que não verifica
  covenants). Não se pode violar covenants que o modelo não modela.

`amort_total = 0` em 2030–2034 é um **pressuposto deliberado de estado estacionário**:
o período de continuidade assume **estrutura de capital constante** (dívida renovada
na maturidade), mantendo o WACC estável para o valor terminal de Gordon. É convenção
padrão de *terminal value*, não um "congelamento ilegal".

### Crítica legítima (e o que se fez)
A observação válida não é sobre amortização, mas sobre o **pressuposto de
reinvestimento**: com dívida fixa e retenção integral, o excedente acumulava-se em
aplicações financeiras ociosas, diluindo o ROE (21,4 % → 15,2 %). Adoptou-se o
tratamento **constant leverage + cash sweep** (dividendo residual): distribui-se o
FCFE que ficaria ocioso, fixando as aplicações no nível de 2029. ROE e liquidez
estabilizam (ROE → 23,3 %; liquidez ≈ 1,95×). Implementado e testado — ver
[horizonte_10anos_extensao_motor.md §3.1](horizonte_10anos_extensao_motor.md).

> Estado: **implementado** (`distribuicao.terminal_cash_sweep`, default `true`);
> suite de 120 testes verde.

---

## Plano — recomendações remanescentes

| # | Acção | Ficheiro | Esforço | Risco |
|---|-------|----------|---------|-------|
| P1 | Corrigir `amortizacoes_capital[2026]` 2.043.093,62 → 4.463.738,28 | `schedules.yaml` | 1 linha | baixo |
| P2 | Verificar/actualizar testes canónicos da DFC que fixem o split 2026 (`rec_emprestimos`/`pag_emprestimos`) | `tests/test_*dfc*`, `test_invariantes_financeiras` | baixo | médio |
| P3 | Decidir 2025 NC/C: `emprestimos_C[2025]` 787.984 subavalia parcela corrente em €1,26 M vs SNC (€2,04 M) — corrigir ou divulgar | `schedules.yaml` / relatório | baixo | baixo |
| P4 | Reafirmar invariantes na defesa: `Ativo=Passivo+CP`; `caixa_DFC=caixa_Balanço`; `Σamort=D_2024−D_2034`; `rec_emp≥0` ∀ ano (verdadeiro após P1) | — | — | — |

Sequência sugerida para amanhã: **P1 → correr suite → P2 (ajustar canónicos se
partirem) → P3 (decisão) → P4 (checklist na defesa)**.
