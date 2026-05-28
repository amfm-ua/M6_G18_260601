# Hub Logístico — Impacto nas Margens em 2025

## Contexto

O hub logístico entra em construção em 2025 e torna-se operacional em 2026.  
Esta assimetria temporal entre o reconhecimento de **custos** e o reconhecimento de **benefícios** explica a compressão observada nos rácios financeiros de 2025 no cenário com hub.

---

## Mecanismo: o que acontece em 2025

### Custo reconhecido em 2025

O financiamento do hub (4 125 000 €, taxa 4,15 % a.a.) é contratado em 2025 para cobrir a fase de construção. Os juros associados entram imediatamente na Demonstração de Resultados:

```
juros += 171 000 €   (a partir de 2025)
```

`data.js:158` — `if (hubOn && YEARS[i] >= 2025) juros += 171000;`

### Benefícios que ainda não existem em 2025

Todos os efeitos positivos do hub só se materializam a partir de **2026**, quando a infraestrutura fica operacional:

| Efeito | Início | Valor (2026) |
|---|---|---|
| Incremento de VN (novos clientes/canais) | 2026 | +500 000 € |
| Reconhecimento PT2030 (outros rendimentos) | 2026 | +311 456 € |
| Poupança FSE (eficiência operacional) | 2026 | −300 000 € |
| Incremento de depreciação (CAPEX 5 500 k€ × 10%) | 2026 | +550 000 € |
| Elasticidade pessoal reduzida (α: 0,40 → 0,15) | 2026 | — |

`data.js:138–154`

---

## Efeito nos rácios em 2025

Os 171 k€ de juros adicionais afetam **exclusivamente a linha abaixo do EBIT** (RAI → RL), pelo que:

| Rácio | Afetado em 2025? | Porquê |
|---|---|---|
| Margem EBITDA | **Não** | Juros não entram no EBITDA |
| Margem EBIT | **Não** | Juros não entram no EBIT |
| Margem Líquida | **Sim** | RL reduz com juros adicionais |
| ROE | **Sim** | Resultado líquido menor |
| Cobertura de Juros | **Sim** | EBIT/Juros deteriora |

O impacto é propositado: representa o **custo de carry** do financiamento durante o período de construção, antes de qualquer retorno operacional.

---

## Comparação temporal resumida

```
2025:  Juros +171k  |  Benefícios = 0       →  RAI comprimido
2026:  Juros +171k  |  Benefícios = +~1 061k →  RAI expande
2027+: Juros +171k  |  Benefícios crescem    →  Ganho líquido acumulado
```

O payback do investimento é calculado ao nível do VPL no módulo `hubViability()` (`data.js:394`), que integra todos os fluxos diferenciais hub vs. base.

---

## Nota para o relatório

Esta assimetria é **consistente com o tratamento contabilístico** de investimentos em construção (NCRF 7 / IAS 16): os custos de financiamento imputáveis a ativos em construção podem ser capitalizados, mas o modelo opta por reconhecê-los como gasto no período, o que é uma posição conservadora e favorável à robustez da análise.
