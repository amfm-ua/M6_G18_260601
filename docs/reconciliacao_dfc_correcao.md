# Reconciliação DFC ↔ Balanço — correção do desfasamento estrutural

> Atualizado: 2026-05-28 · Módulos: `src/engine/demonstracoes/balanco.py`,
> `dfc.py`, `extensao_maturidade.py`

## 1. Sintoma

A Demonstração de Fluxos de Caixa (método indirecto) não reconciliava com o
Balanço: `reconciliacao_ok = False` em **todos** os anos 2025–2029. A diferença
entre a `variação_caixa` da DFC e a Δcaixa do Balanço crescia de forma sistemática:

| Ano | Gap (Base, hub-off) |
| --- | ------------------- |
| 2025 | ~27 k€ |
| 2026 | ~178 k€ |
| 2027 | ~199 k€ |
| 2028 | ~217 k€ |
| 2029 | ~246 k€ |

## 2. Diagnóstico

A identidade do método indirecto — `Δcaixa = ΔCapitalPróprio + ΔPassivo −
Δ(ativos não-caixa)` — fecha a `0,0000` por construção da equação do Balanço
(verificado numericamente). Logo o gap só podia vir de **linhas do Balanço não
capturadas nos fluxos da DFC**. A decomposição atribuiu o gap, **ao cêntimo**, a
duas causas (resíduo = 0 em todos os anos, Base e Hub_Ativo):

### Causa 1 — A reserva legal "evaporava-se" do capital próprio

Em `balanco.py`, o rollforward dos resultados transitados fazia
`rt[y] = rt[y-1] + rl_prev − div − res`, subtraindo a apropriação anual da reserva
legal (`res = rl_prev × reserva_legal_pct`) **mas nunca a creditando** em
`reservas_legais` (que ficava constante). A reserva legal saía do equity sem
destino → capital próprio total subavaliado → caixa do *treasury plug*
subavaliada. A DFC, que só vê `rl − dividendos` no equity, não tinha como capturar
esta fuga. Era a maior fatia (149 k€→212 k€/ano).

### Causa 2 — Imparidade dupla-contada na DFC

Em `dfc.py`, `op_pre_nfm` somava o add-back não-caixa `+imp`. Porém o saldo de
`clientes` no Balanço já está **líquido** de imparidades acumuladas (NCRF 27 §41),
pelo que a variação `d_cli` (líquida) já embutia o gasto anual de imparidade.
Somar `+imp` em separado contava-o duas vezes (27 k€→34 k€/ano).

## 3. Correção

| Causa | Ficheiro | Mudança |
| ----- | -------- | ------- |
| Reserva legal | `balanco.py` | `reservas_legais` passou a acumular a apropriação anual (`reservas_leg[y] = reservas + Σres`). Transferência interna ao capital próprio (CSC art. 295.º-296.º): `rt` continua a descontar `res`, mas agora ele reaparece em reservas legais → equity total inalterado pela apropriação. |
| Imparidade | `dfc.py` | Mantém-se o add-back `+imp` em `op_pre_nfm`, mas a variação de clientes em `var_nfm` passa a base **bruta** (`d_cli_bruto = d_cli − imp`), para a imparidade contar uma só vez. |
| Ambas | `extensao_maturidade.py` | As mesmas duas correções replicadas na fase de maturidade (2030–2034). |

> A fórmula de `resultados_transitados` **não** mudou — as regressões
> `tests/test_balanco_rt_regression.py` mantêm-se válidas.

## 4. Resultado

- `reconciliacao_ok = True` em **todos** os anos 2025–2034 (Base e Hub_Ativo).
- `controlo ≈ 0,0000` mantém-se em todos os anos (o Balanço continua a fechar).
- A caixa do Balanço **sobe** pelo montante da reserva legal anteriormente perdida
  (até ~+715 k€ acumulado em 2029, hub-off) — figura agora correcta, não inflada:
  é dinheiro que o leak suprimia. A avaliação (FCFF/FCFE) não depende da caixa,
  pelo que os múltiplos de valor não são afectados por esta reclassificação.
- Suite de testes: 90 passed (a única falha, `test_api_scenarios_structure`, é
  pré-existente e alheia — diz respeito às chaves de cenários, não às demonstrações).
