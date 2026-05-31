# Prompt de implementação — Serviço de Dívida, Covenants e Imposto do Selo (motor M6 Grestel)

> Documento-prompt autossuficiente para entregar ao Sonnet. Cobre as 5 lacunas
> identificadas na revisão do financiamento: (1) limiares + validação de covenants,
> (2) gearing (Dívida Líq./Capital Total), (3) Imposto do Selo, (4) run-off por
> instrumento 2030–34, (5) dívida dirigida ao gearing-alvo / risco de taxa variável.

## Contexto do repositório

Motor financeiro Python em `src/engine/`. Horizonte: `ANO_BASE=2024`, projeção
`2025–2034` (`src/engine/config.py`). `ALL_YEARS=[2024..2034]`, `YEARS=[2025..2034]`
(`src/engine/inputs/constants.py`).

Fluxo de orquestração (`src/engine/modelo/model.py`):
`financiamento.financiamento_anual(sched, a)` (linha ~122) →
`statements.build_statements(...)` →
`dfs["kpis"] = kpis_mod.build_kpis(dfs["dr"], dfs["balanco"], dfs["dfc"], a)` (linha ~128).

Dados de dívida em `src/engine/data/computed/schedules.yaml` bloco `financiamento:`
— **só preenchido 2024–2029**, por instrumento (`BPI_capital_fim_ano`,
`Santander_…`, `CGD_COVID_…`, `CGD_OS_…`, `Abanca_…`, `IAPMEI_…`, `Locacoes_…`)
+ agregados (`juros_total`, `capital_divida_total_fim_ano`, `amortizacoes_capital`,
`emprestimos_NC`, `emprestimos_C`).

Dívida do Hub (novo investimento) é dinâmica:
`src/engine/projetos/hub_logistico/financiamento.py` `hub_financing(hub)`, tranches
em `src/engine/data/subsidiarias/hub_logistico/m6_hub_assumptions.yaml`
(`projeto_hub.financiamento`), com carência (`inicio_amortizacao`) e juros
capitalizados NCRF 10.

Período terminal 2030–2034: `src/engine/demonstracoes/extensao_maturidade.py` —
atualmente **congela a dívida ao nível de 2029** (`amort_total = 0.0`, linha ~361)
→ constant leverage.

KPIs já calculados em `src/engine/modelo/kpis.py` `build_kpis()` (itera sobre os
anos presentes em `df_dr`, não hardcode): `autonomia_financeira`,
`nd_ebitda`/`debt_ebitda`, `divida_liquida`, `cobertura_juros`, `dscr` (EBITDA puro),
`endividamento`, `debt_equity`, `divida_financeira = emprestimos_nc + emprestimos_c`.

**Regras gerais:** PT-PT em código/docstrings/comentários. Suite atual:
120 passed, 5 skipped — manter verde. Não inventar números: tudo parametrizado em
YAML. Cada tarefa é incremental e testável isoladamente. Correr `pytest` após cada
tarefa.

## DECISÕES CONFIRMADAS PELO UTILIZADOR (validadas contra R&C 2022/2023/2024)

- **Imposto do Selo (T3):** taxa sobre juros = **4%** (Verba 17.3.1), **confirmada
  nos R&C**: na análise de sensibilidade de 2024, um acréscimo de juros de
  42.978,56 € gera selo de 1.719,14 € (= 4,00%). A taxa sobre **utilização de
  crédito** (Verba 17.1) **não consta dos R&C** → parametrizar com taxas legais
  padrão (0,60% LP ≥5 anos; 0,04%/mês CP) mas marcar como estimativa, com toggle
  próprio para isolar do selo sobre juros.
- **DSCR (T2):** **NÃO é covenant** da Grestel — os R&C não o listam. Os covenants
  bancários reais e únicos são **ND/EBITDA ≤ 3,5x** (desde 2023) e **Autonomia
  Financeira Ajustada ≥ 30%** (desde 2024). → Calcular DSCR como métrica
  **informativa**, fora do `covenants_todos_ok`.
- **Autonomia financeira:** **≥30% = covenant contratual** (limiar crítico, entra no
  `covenants_todos_ok`). **≥35% = meta de gestão / buffer** (flag *soft*, não breach).
  Modelar os dois em separado.
- **Gearing 40–65%:** é **política/estratégia de gestão**, não covenant bancário. O
  teto 65% e o piso 40% entram como flags estratégicas (`gearing_abaixo_banda` /
  `gearing_acima_banda`), não como breach contratual.
- **Run-off 2030–34 (T4):** o run-off contratual é **mais fiel ao reporte de 2024**
  (dívida bancária concentrada no escalão 2–5 anos, a liquidar antes de 2034).
  **Interação crítica detetada:** combinar run-off com o cash sweep agressivo
  (Finding #2) pode **empurrar o gearing abaixo do piso estratégico de 40%** —
  desalavancagem excessiva face à política da empresa. → Implementar run-off
  **atrás de toggle**, e usar a validação de covenants (T2) como guarda para
  sinalizar quando a estrutura cai abaixo de 40%. Mostrar before/after antes de
  decidir o default.

---

## TAREFA 1 — Gearing (pré-requisito de tudo o resto)

**Objetivo:** adicionar o rácio de *gearing* na definição da política Grestel:
**Gearing = Dívida Líquida / (Dívida Líquida + Capital Próprio)**.

- Em `src/engine/modelo/kpis.py`, no loop de `build_kpis` (após `divida_liquida`
  na linha ~214), calcular:
  ```python
  capital_total = divida_liquida + cp
  gearing = divida_liquida / capital_total if capital_total > 0 else 0.0
  ```
- Adicionar `"gearing": gearing` ao dict de `rows.append({...})` (junto a
  `nd_ebitda`, ~linha 296).
- **Edge case:** se `divida_liquida < 0` (caixa > dívida, provável nos anos
  terminais com cash sweep), `gearing` fica negativo — manter o valor real (não
  truncar) mas documentar em comentário que gearing<0 = posição de caixa líquida.
- Teste em `tests/test_kpis_contract.py`: confirmar coluna `gearing` presente e que
  em 2024 ≈ Dívida Líquida/(DL+CP) com os valores de `schedules.yaml`
  `reference_balanco`.

## TAREFA 2 — Limiares + validação de covenants

**Objetivo:** parametrizar os alvos da política financeira e gerar, por ano, o
estado de cumprimento (sem rebentar o modelo — é diagnóstico, não exceção).

1. **YAML** — adicionar em `src/engine/data/pressupostos/globais.yaml` um bloco novo.
   Distinguir **covenants bancários** (vinculativos) de **política de gestão**:
   ```yaml
   covenants:
     # --- Covenants bancários contratuais (R&C 2024) → entram em covenants_todos_ok ---
     nd_ebitda_max: 3.5                  # desde 2023
     autonomia_financeira_min: 0.30      # ajustada, desde 2024
     # --- Política / estratégia de gestão → flags, NÃO breach contratual ---
     gearing_min: 0.40                   # piso estratégico (desalavancagem excessiva)
     gearing_max: 0.65                   # teto estratégico
     autonomia_financeira_meta: 0.35     # buffer interno (soft)
     # --- Métricas informativas (calcular, NÃO vinculativas) ---
     dscr_min: null                      # Grestel não tem DSCR contratual
     cobertura_juros_min: 2.0            # referência analítica
   ```
   Expor via `Assumptions` (replicar o padrão de `a.raw.get("covenants", {})`).

2. **Novo módulo** `src/engine/modelo/covenants.py` com:
   ```python
   def avaliar_covenants(df_kpis: pd.DataFrame, a) -> pd.DataFrame:
       """Por ano: valor de cada métrica, limiar e estado.
       Colunas: ano,
         nd_ebitda, nd_ebitda_ok, autonomia, autonomia_ok,   # covenants bancários
         covenants_todos_ok, n_breaches,                       # só os 2 acima
         gearing, gearing_abaixo_banda, gearing_acima_banda,   # política (flags)
         autonomia_meta_ok,                                    # buffer 35% (soft)
         dscr, cobertura_juros."""                             # informativas
   ```
   - **`covenants_todos_ok` = `nd_ebitda_ok AND autonomia_ok`** apenas (os dois
     covenants bancários reais). `nd_ebitda_ok = nd_ebitda <= nd_ebitda_max`;
     `autonomia_ok = autonomia >= autonomia_financeira_min`.
   - **Flags estratégicas (não breach):** `gearing_abaixo_banda = gearing < gearing_min`,
     `gearing_acima_banda = gearing > gearing_max`, `autonomia_meta_ok = autonomia >= 0.35`.
   - DSCR/cobertura só reportados; `dscr_min: null` ⇒ não avaliado.
   - `n_breaches` conta apenas os covenants bancários.

3. **Integração** em `src/engine/modelo/model.py`: após `dfs["kpis"] = ...`
   (linha ~133), adicionar:
   ```python
   dfs["covenants"] = covenants_mod.avaliar_covenants(dfs["kpis"], a)
   ```

4. **Teste** novo `tests/test_covenants.py`: cenário Base → listar explicitamente os
   anos OK / breach esperados e justificar. Validar que limiares vêm do YAML
   (alterar YAML muda resultado).

## TAREFA 3 — Imposto do Selo sobre financiamento

**Objetivo:** modelar o Imposto do Selo, hoje ausente (grep `selo` em `src/engine`
= 0 resultados).

**Âmbito (taxas confirmadas na secção de decisões):**
- **Verba 17.3.1 (juros):** % sobre os juros de financiamento (gasto do período).
- **Verba 17.1 (utilização de crédito):** selo sobre o crédito utilizado, em função
  do prazo. Aplica-se sobretudo à linha CP rotativa e a novos drawdowns.

**Implementação:**
1. **YAML** em `src/engine/data/pressupostos/globais.yaml`:
   ```yaml
   imposto_selo:
     taxa_juros: 0.04                      # Verba 17.3.1 — CONFIRMADO R&C 2024
                                           # (1.719,14 € / 42.978,56 € = 4,00%)
     aplicar_juros: true                   # toggle principal
     # Utilização de crédito (Verba 17.1): NÃO consta dos R&C → estimativa
     taxa_utilizacao_credito_longo: 0.006  # ≥5 anos
     taxa_utilizacao_credito_curto: 0.0004 # 0,04%/mês CP (linha rotativa)
     aplicar_utilizacao: false             # default OFF (não suportado por R&C)
   ```
   **Validação de ancoragem:** o teste deve replicar o ponto dos R&C — selo sobre um
   incremento de juros de 42.978,56 € = 1.719,14 €.
2. **Cálculo** — função em `src/engine/financiamento/financiamento.py`,
   `imposto_selo_anual(df_fin, a) -> pd.DataFrame` (colunas: `ano`, `selo_juros`,
   `selo_credito`, `selo_total`), usando `juros_total` de `df_fin` e os novos
   drawdowns (base + Hub `desembolso`).
3. **Integração na DR** — somar o selo sobre juros aos gastos financeiros (junto a
   `juros`) em `src/engine/demonstracoes/dr/build.py` (ETAPA 5), não ao FSE, para
   coerência com a natureza do encargo. Garantir que reduz o RAI e flui para a DFC.
4. **Reconciliação:** o selo é saída de caixa real → confirmar `reconciliacao_ok=True`
   e `controlo≈0` em todos os anos.
5. **Teste:** `tests/test_imposto_selo.py` — `selo_juros[2024] ≈ taxa * juros_total[2024]`;
   toggle `aplicar: false` → selo=0 e DR volta ao baseline.

## TAREFA 4 — Run-off por instrumento 2030–2034 (substituir o congelamento)

**Objetivo:** em vez de congelar a dívida em 2029, deixar correr a amortização
contratual de cada instrumento até liquidação (dívida histórica liquida antes/perto
de 2034; Hub amortiza 2028→2037).

**Problema atual:** `schedules.yaml` `financiamento:` só vai a 2029;
`extensao_maturidade.py:361` faz `amort_total = 0.0` e mantém `emprestimos_nc/c`
do ano anterior.

**Abordagem (escolher a menos invasiva que feche reconciliação):**
1. **Estender os schedules por instrumento até 2034.** Continuar o plano de
   amortização contratual de cada `*_capital_fim_ano` (BPI 10 anos desde 2022 c/ 2
   anos carência → liquida ~2032; restantes já a 0 em 2029). Preencher 2030–2034 em
   `schedules.yaml` (ou via tool de build em `tools/` se existir). Recalcular
   agregados `capital_divida_total_fim_ano`, `juros_total` (saldo×taxa),
   `amortizacoes_capital`, `emprestimos_NC/C` para 2030–2034.
2. **Hub:** `hub_financing` já itera `YEARS` (até 2034) → confirmar amortização
   correta e soma em `financiamento_anual` (via `_hub_fin`).
3. **extensao_maturidade.py:** deixar de congelar a dívida. Consumir valores reais
   de `df_fin`/schedules para 2030–2034 (`amort_total`, `emprestimos_nc/c`, `juros`
   decrescente) e recalcular `rec_emp`, `fluxo_fin`, `pag_emprestimos` (linhas
   ~361–410). **Atenção:** altera a hipótese de "constant leverage" que sustentava a
   perpetuidade de Gordon limpa — avaliar impacto no WACC/valuation terminal.
4. **Toggle:** adicionar `financiamento.terminal_debt_runoff` (default **off** —
   preserva valuation terminal atual; run-off como cenário comparativo). Cash sweep
   `distribuicao.terminal_cash_sweep` já existe.
   **⚠️ Interação crítica a expor:** run-off (dívida ↓) + cash sweep (caixa ↑/dívida
   ↓) em simultâneo desalavancam fortemente → o `gearing` pode cair **abaixo do piso
   estratégico de 40%** (ver T2 `gearing_abaixo_banda`). No before/after, reportar o
   `gearing` 2030–34 nas 4 combinações de toggles e assinalar quando < 40%. Isto é a
   evidência de que desalavancagem total não está alinhada com a política 40–65%.
5. **Reconciliação:** `Ativo = Passivo + CP`, `caixa_DFC = caixa_Balanço`,
   `reconciliacao_ok=True` em 2030–2034.
6. **Testes:** atualizar fixtures canónicas de DFC/balanço que assumam dívida flat
   2030–34; adicionar teste de que `capital_divida_total_fim[2034]` reflete só o
   resíduo Hub e `Σ amortizações 2030-34` = redução de saldo correspondente.

> ⚠️ Toca a fonte-de-verdade e o valuation terminal. Implementar atrás de toggle e
> mostrar before/after (saldo dívida, juros, ROE, gearing, WACC, VAL) antes de
> tornar default.

## TAREFA 5 — Dívida dirigida ao gearing-alvo + risco de taxa variável

**Objetivo:** (a) sensibilidade a taxa variável (Euribor); (b) verificação face à
banda de gearing 40–65%. Fazer por último, em duas fases conservadoras.

**Fase 5a — Risco de taxa variável (cenário, não endógeno):**
- YAML: `risco_taxa: { euribor_choque_bps: 0, aplica_a_taxa_variavel: true }`.
- Ajustar as taxas das tranches variáveis (base + Hub) por um choque de Euribor em
  bps, propagado a `juros_total`. Ligar aos cenários existentes (Stress/Downside) —
  ver `src/engine/inputs/custom_scenarios.py` e `src/engine/modelo/sensitivity.py`.
- Teste: choque +200bps aumenta `juros_total` proporcionalmente ao saldo de dívida
  variável e reduz RAI/DSCR.

**Fase 5b — Verificação de gearing-alvo (NÃO sizing endógeno automático):**
- Não transformar financiamento exógeno em endógeno (risco de circularidade
  juros↔dívida↔caixa e quebra de reconciliação). Em vez disso:
- Usar `df["gearing"]` (T1) + `covenants` (T2) para sinalizar anos fora da banda e
  produzir "headroom de dívida".
- Função em `covenants.py`: `headroom_divida(df_kpis, a) -> pd.DataFrame`
  (colunas: `ano`, `gearing`, `divida_max_para_teto`, `headroom_eur`).
- Documentar que sizing dinâmico ao alvo fica como trabalho futuro (requer solver
  iterativo).

---

## Ordem de execução recomendada
1. **T1 (gearing)** → base para tudo.
2. **T2 (covenants)** → depende de T1.
3. **T3 (imposto selo)** → independente, baixo risco.
4. **T4 (run-off 2030–34)** → atrás de toggle, com before/after; toca valuation.
5. **T5 (taxa variável + headroom)** → por último.

## Critérios de aceitação globais
- `pytest` verde após **cada** tarefa (baseline 120 passed, 5 skipped).
- `reconciliacao_ok=True` e `controlo≈0` em todos os anos, todos os cenários, após
  T3 e T4.
- Todos os parâmetros novos em YAML (zero hardcode); toggles para T3, T4, T5.
- Documentar cada tarefa numa secção de `docs/` (seguir convenção de nomes existente).
