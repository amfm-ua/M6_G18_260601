# Plano de Restruturação — Frontend da tab *Hub Logístico*

> Documento de *handoff* para o agente que vai reestruturar a interface.
> Âmbito: `interface/views.jsx` (subtabs do Hub) + `interface/api.js` (camada de dados)
> + uma correção de contrato no backend (`src/api/routes/hub.py`).
> Data: 2026-05-30 · Origem: alteração do plano de financiamento no motor M6.

---

## 0. Porquê esta restruturação

O **plano de financiamento foi recomposto no backend** e o motor de viabilidade ganhou
uma **nova camada APV**. A frontend da tab Hub foi escrita contra o plano *antigo* e
tem dezenas de valores *hardcoded* que agora estão **factualmente errados** (sobretudo
o PT2030 como subsídio-herói de 45 % do CAPEX, que passou a **€0**). Há ainda um
**buraco no contrato de dados**: o motor produz campos novos que a rota e a API não
propagam, pelo que a nova camada *nunca* aparece no ecrã.

A tab são 5 subtabs montadas numa única função `HubView` dentro de um ficheiro de
**4570 linhas** (`views.jsx`). A restruturação tem dois objetivos:

1. **Correção factual** — alinhar a UI com o novo plano de financiamento e a nova
   decomposição APV (prioridade alta, é o que está errado no ecrã).
2. **Restruturação técnica** — modularizar a tab, eliminar *fallbacks hardcoded* e
   deixar a UI *data-driven* (a partir do backend), para que futuras mudanças de
   pressupostos não voltem a exigir edição de JSX.

---

## 1. O que mudou no backend (factos de referência)

### 1.1 Plano de financiamento (YAML `m6_hub_assumptions.yaml`, bloco `financiamento`)

| Antes (assumido pela UI) | Agora (motor) |
|---|---|
| 2 tranches de dívida (~€4,5 M, ex. "Banco_Hub" + "Linha_BEI") | **3 tranches** (€4,5 M total) |
| PT2030 = subsídio fundo perdido ~€2,7 M (**45 % CAPEX**) | **PT2030 `montante: 0`** — Grestel é **grande empresa**, sem acesso a SI Inovação PME |
| Carência "desembolso–2027" igual p/ todas | Desembolsos **distintos** (2025 / 2026) por tranche |
| RFAI "€600 000" mencionado de passagem | **RFAI é o apoio regional principal** (teto regional 30 % CAPEX, CFI art. 43.º) |

As 3 tranches atuais (ver YAML `financiamento`):

| Tranche | Montante | Taxa | Amort./ano | Desembolso | Início amort. |
|---|---|---|---|---|---|
| `Linha_BEI` | 1 800 000 | 3,70 % | 180 000 | 2026 | 2028 |
| `Linha_Fomento_GM` | 1 700 000 | 3,85 % | 170 000 | 2025 | 2028 |
| `Banco_Comercial` | 1 000 000 | 4,15 % | 100 000 | 2025 | 2028 |

> Regra de ouro: **a UI nunca deve assumir o número de tranches, os nomes, as taxas
> ou os anos de desembolso.** Tudo isto vem em `investment-map → emprestimos[]`.

### 1.2 Nova camada APV — "Subsídio implícito (taxa bonificada)" / *soft loan*

`src/engine/projetos/hub_logistico/viabilidade.py::vala_hub` ganhou uma **5.ª camada**:

```
VALA = VAL_base(Ku) + Escudo Fiscal + PT2030 líquido + RFAI + Subsídio implícito(soft loan)
```

- Captura o *grant-equivalent* das linhas bonificadas (BEI/Garantia Mútua) — a poupança
  de juros face a uma `taxa_mercado_ref`, descontada a `rf`.
- **Gated**: só é > 0 se `financiamento.taxa_mercado_ref` existir e for > 0. **Hoje o YAML
  não define `taxa_mercado_ref`**, logo a camada é **€0 (inativa)** — mas a UI tem de a
  saber renderizar (linha extra no waterfall/tabela) para quando for ativada, e tem de
  mostrar o estado "camada inativa" de forma legível.
- Campos novos no retorno de `vala_hub`: `pv_soft_loan`, `soft_loan_por_tranche`,
  `decomposicao` passa a ter **5 entradas**, `parametros.taxa_mercado_ref`.

### 1.3 Hub agora é *scenario-aware* via `drivers.py`

`aplicar_drivers_derivados_hub` liga poupanças de pessoal/quebras à mesma base de
atividade do modelo consolidado, por cenário (Base/Upside/Downside/Stress). A UI já
passa `ctx.scenario`/`ctx.ircTaxaEfetiva` na maioria dos *fetches* — confirmar que
**todos** os subtabs reagem ao seletor de cenário (ver §5.4).

### 1.4 PT2030 recalibrado — *driver* de Monte Carlo apenas, não pilar

O PT2030 é **subsídio a fundo perdido** (não reembolsável; NCRF 22). No **caso-base
vale €0** (grande empresa sem acesso ao SI PME). O mecanismo continua cablado em
DR/DFC/balanço/VALA, mas só toma valor onde é **re-injetado** — e o único sítio que o
faz, de forma coerente, é o **Monte Carlo** (`monte_carlo_hub.py`). Parâmetros
recalibrados à realidade de grande empresa:

| Parâmetro | Antes | Agora |
|---|---|---|
| `pt2030_approved` | Bernoulli(p=0,75) | **Bernoulli(p=0,15)** — aprovação rara |
| `pt2030_taxa` (intensidade s/ CAPEX) | Triangular(30/45/60 %) | **Triangular(0/4/7,5 %)** — subsídio residual |
| Teto de auxílio regional | inexistente | **RFAI + subsídio ≤ 30 % CAPEX** (CFI art. 43.º) clampado em `_apply_sample` |

Efeito (MC-VALA): o subsídio passa de *driver dominante* a **cauda de upside raro**
(PV PT2030 média ~€22 k, p95 ~€196 k). A viabilidade **deixa de depender dele**:
`P(VALA>0)` ≈ 0,97 com PT2030 vs. ≈ 0,965 sem. **Implicação para a UI**: o PT2030 **não
é pilar de financiamento** — é uma **nota explicativa** (caso-base) + **um dos eixos de
incerteza** no Monte Carlo. Nunca renderizar como subsídio confirmado de 45 %.

---

## 2. BLOQUEADOR — contrato de dados (fazer primeiro)

A nova camada *soft loan* **não chega à frontend** porque a rota filtra os campos:

- **`src/api/routes/hub.py::get_hub_vala`** (≈ linha 360) devolve um dict fixo que
  **não inclui** `pv_soft_loan` nem `soft_loan_por_tranche`. → **Adicionar** ambos ao
  retorno (e `parametros` já inclui `taxa_mercado_ref` via `result["parametros"]`).
- **`interface/api.js::hubVala`** (linha 523) faz `return await r.json()` — passa tudo
  em bruto, por isso **não precisa de alteração** assim que a rota expuser os campos.
  (Confirmar que nenhum `normalize*` está a podar o objeto — não está.)
- A `decomposicao` já é devolvida inteira pela rota, por isso a **tabela** do waterfall
  (que itera `vala.decomposicao`) já mostrará a 5.ª linha automaticamente; o que falha é
  o **array `wfItems` hardcoded** do gráfico (ver §5.2).

> ⚠️ Sem este passo, qualquer trabalho de UI sobre o *soft loan* é invisível. Validar
> com `GET /api/hub/vala?cenario=Base` e confirmar `pv_soft_loan` no JSON antes de tocar no JSX.

---

## 3. Inventário de valores *hardcoded* / desatualizados a remover

Localização: `interface/views.jsx`. (linhas aproximadas — confirmar no ficheiro)

### `HubOE4View` (Plano de Financiamento, ~L1766–2134) — **a mais afetada**
- L1787 `emprestimo ?? 4_500_000` e L1789 `capProprio ?? 1_500_000` — *fallbacks*
  numéricos. Substituir por valores do backend; se ausentes, mostrar estado vazio, não inventar.
- L1831 `pt2030_pct_capex ?? 0.45` e KPI "Subsídio PT2030" com `tone="pos"` — **com PT2030=0
  isto mostra um subsídio de 45 % inexistente**. Reformular para refletir €0 e promover o
  **RFAI** como apoio regional.
- L1905–1909 banner verde "PT2030 · Subsídio a fundo perdido €X" — falso com €0.
- L1927–1938 `FundingCard` "Subsídio PT2030 / 45 % do CAPEX" — reescrever.
- L1948 `RFAI gerado €600 000` **hardcoded** — puxar do backend (RFAI/`rfai` no YAML).
- L1890 sub "**2 tranches** de capital alheio" — texto fixo; agora são 3 → derivar de
  `emprestimos.length`.
- L1892–1901 e L1911–1926 `StackedBar`/`FundingCard` com cores por `i===0 ? … : …`
  (binário, 2 tranches) — generalizar para **N tranches** (paleta indexada, como `poolColors`).
- L1921 `["Carência", t.desembolso + "–2027 (só juros)"]` — assume janela igual; cada
  tranche tem `desembolso` próprio (2025/2026) e `inicio_amortizacao`. Derivar a string.
- L1792 `dscrMin = 1.20` — manter (é covenant alvo), mas idealmente vindo de config.

### `HubVALAView` (VALA/APV, ~L2158–2453)
- L2191–2197 `wfItems` **hardcoded com 4 camadas** — falta a 5.ª (`pv_soft_loan`).
  Reconstruir a partir de `vala.decomposicao` (data-driven) em vez de lista manual.
- L2251 KPI "PT2030 + RFAI" — com PT2030=0 fica só RFAI; rever rótulo/sub.
- L2205/L2208 `sensList` labels "PT2030=45%", "Sem PT2030 nem RFAI" — texto fixo
  desalinhado; os labels já vêm em `cenarios[key].label` do backend → usar esses.
- L2216–2231 `semaforoItems` "PT2030 confirmado (45% CAPEX)" — narrativa obsoleta;
  reformular em torno de RFAI + escudo fiscal + soft loan.
- L2443–2449 bloco "Conclusão" — texto PT2030-cêntrico; reescrever para a nova tese
  (valor sustentado por operações + RFAI; PT2030 = upside €0 na base).
- L2257 sub do Panel "VALA = VAL base + Escudo + PT2030 + RFAI" — falta "+ Subsídio implícito".

### `HubViabilidadeView` (~L755–1160)
- L811/L1348 `wacc || 0.073` *fallback* — tolerável, mas preferir sempre backend.
- L962 `dmi_reducao_dias || 20` *fallback* "20 dias" — confirmar contra YAML.
- Painel de decomposição (operacional/comercial/fiscal): a camada **fiscal** passa a
  incluir o soft loan — garantir reconciliação com a soma da subtab VALA.

### `HubMonteCarloView` (~L1432) e `HubContingenciaView` (~L2456)
- Auditar por strings "PT2030 45%", "€2,7M", "4,5M", "2 tranches", taxas de juro fixas.
  (Menos afetadas, mas confirmar que não repetem a narrativa antiga.)

> Tática de varredura: `grep -nE "4[._ ]?500[._ ]?000|1[._ ]?500[._ ]?000|0\.45|45 ?%|2 tranches|600[._ ]?000|PT2030"`
> sobre `interface/views.jsx` e tratar cada *hit*.

---

## 4. Restruturação técnica (arquitetura-alvo)

`views.jsx` (4570 linhas) mistura todas as views do dashboard. Para o Hub, extrair para
um módulo dedicado mantendo o estilo e os componentes partilhados existentes
(`Panel`, `KPI`, `StackedBar`, `BarChart`, `WaterfallChart`, `FundingCard`, `KV`, `fmt`).

**Loader confirmado** (`index.html` L583–593): **Babel-standalone no browser**, sem
*build step*. Os ficheiros carregam via `<script type="text/babel" src="ficheiro.jsx?v=8">`
e **partilham escopo global** (não há ESM/`import`). Implicações:
- Criar `interface/hub_views.jsx` é trivial: definir as funções no escopo global e
  adicionar `<script type="text/babel" src="hub_views.jsx?v=9"></script>` **antes** de
  `app.jsx` e **depois** de `charts.jsx`/`views.jsx` (precisa de `Panel`, `KPI`, `fmt`, etc.).
- **Cache-busting obrigatório**: qualquer edição a `views.jsx`/`api.js`/novo ficheiro
  exige bumpar `?v=8 → ?v=9` em `index.html`, senão o browser serve a versão em cache
  e parecerá que nada mudou. Bumpar **todos** os `?v=` em conjunto para simplicidade.

Estrutura lógica (independente de quantos ficheiros):

```
HubView (wrapper de subtabs)                 ← sem mudança estrutural
├─ HubOE4View          (Plano de Financiamento)
├─ HubViabilidadeView  (Viabilidade)
├─ HubVALAView         (VALA / APV)
├─ HubContingenciaView (Plano de Contingência)
├─ HubMonteCarloView   (Monte Carlo)
└─ helpers partilhados do Hub:
     - useHubData(...)        ← hook que encapsula o padrão Promise.all + cancelled
     - TRANCHE_PALETTE        ← paleta indexada p/ N tranches (substitui i===0?:)
     - buildWaterfallFromDecomposicao(vala)  ← gera wfItems a partir do backend
     - fmtCarencia(tranche)   ← deriva "desembolso–(início-1) (só juros)"
     - <SoftLoanBadge active=.../>  ← renderiza camada inativa vs. valor
```

Princípios:
1. **Zero números mágicos de financiamento no JSX.** Tudo de `investment-map`/`vala`.
2. **Listas em vez de pares.** Render de tranches por `.map` sobre `emprestimos[]`,
   nunca por índice fixo.
3. **Estados explícitos:** "camada inativa" (`taxa_mercado_ref` ausente) e "subsídio €0"
   são estados de primeira classe com texto próprio — não buracos nem `tone="pos"`.
4. **Reaproveitar o padrão de `useEffect`+`cancelled`** já presente; opcionalmente
   fatorar num hook `useHubData` para reduzir repetição entre subtabs.

---

## 5. Plano de trabalho por subtab

### 5.1 `HubOE4View` — Plano de Financiamento (maior esforço)
1. Remover *fallbacks* `4_500_000` / `1_500_000` / `0.45` / `600_000`.
2. KPIs: "Capital alheio" já itera `emprestimos` (ok); "Subsídio PT2030" → renderizar
   €0 com tom neutro + nota "grande empresa, sem SI PME"; adicionar/realçar KPI **RFAI**.
3. Banner PT2030 → condicional: se `pt2030_montante === 0`, mostrar mensagem de "apoio
   regional via RFAI" em vez de subsídio fundo perdido.
4. `StackedBar` + `FundingCard` de financiamento → `TRANCHE_PALETTE[i]` p/ N tranches;
   `fmtCarencia(t)` para a janela de carência por tranche.
5. Sub "2 tranches" → `${emprestimos.length} tranches`.
6. Mapa de serviço da dívida (tabela + por-tranche) já é data-driven (`ds.rows`,
   `ds.rows_por_tranche`) — **validar** que renderiza 3 blocos e cores corretas.
7. `FundingCard` PT2030/RFAI: meta-dados a partir do backend (RFAI montante, teto 30 %).

### 5.2 `HubVALAView` — VALA / APV
1. Substituir `wfItems` hardcoded por `buildWaterfallFromDecomposicao(vala)`:
   primeira entrada = `val_base_ke` (total), entradas intermédias = cada `decomposicao`
   que não seja o VAL base, última = VALA (total). Assim a 5.ª camada entra sozinha.
2. KPI "PT2030 + RFAI": separar ou renomear; com PT2030=0 mostrar RFAI + nota.
3. `sensList`/labels: usar `cenarios[key].label` do backend; eliminar strings "45%".
4. `semaforoItems` + "Conclusão": reescrever narrativa (ver §6).
5. Sub do Panel waterfall: "+ Subsídio implícito (taxa bonificada)".
6. Renderizar `<SoftLoanBadge active={params.taxa_mercado_ref>0} valor={pv_soft_loan}/>`.

### 5.3 `HubViabilidadeView`
1. Confirmar reconciliação da camada fiscal (decomposição) com a soma VALA (agora 5 camadas).
2. Remover *fallbacks* `0.073` e `20 dias` onde o backend já fornece.

### 5.4 `HubMonteCarloView` + `HubContingenciaView`
1. Varredura de strings antigas (§3).
2. Confirmar reatividade a `ctx.scenario` / `ctx.ircTaxaEfetiva` (Monte Carlo já recebe;
   Contingência — verificar).
3. **PT2030 como eixo de incerteza** (ver §1.4): no Monte Carlo, apresentar o PT2030
   como *driver* recalibrado — aprovação rara (Bernoulli 0,15), intensidade residual
   (≤ 7,5 % CAPEX) e plafonado pelo teto regional. Rótulos a evitar: "PT2030=45 %",
   "subsídio confirmado". O painel deve deixar claro que o PV PT2030 é **upside de
   cauda** (média ~€22 k) e que `P(VALA>0)` quase não muda sem ele (~0,965 vs ~0,97).

---

## 6. Nova narrativa (texto a aplicar)

A tese mudou de *"projeto viável graças ao PT2030"* para:

> **A Grestel é grande empresa**: sem subsídio PT2030 a fundo perdido (€0 na base, é
> upside). O Hub é viável pelas **operações** (VAL base unlevered > 0) e é **reforçado**
> por apoios sólidos para grande empresa: **RFAI** (apoio regional, teto 30 % CAPEX),
> **escudo fiscal da dívida** e o **subsídio implícito** das linhas bonificadas
> (BEI Clima/Digital, Garantia Mútua) — quando `taxa_mercado_ref` for parametrizada.

Aplicar este enquadramento aos blocos de "Conclusão" (VALA) e semáforo, e às notas dos
`FundingCard`. Coerente com a memória [[financiamento-correcao-conformidade]].

**Nota PT2030 (caso-base, para `FundingCard`/nota explicativa):**

> A Grestel, enquanto **grande empresa**, não tem acesso ao **SI Inovação Produtiva**
> (PT2030, exclusivo de PME). O apoio com finalidade regional é assegurado pelo **RFAI**
> (CFI art. 43.º). Um eventual subsídio a fundo perdido seria *upside*, sempre **≤ teto de
> 30 % do CAPEX** somado ao RFAI. Por prudência, o caso-base assume **subsídio = €0**; a
> sua incerteza é modelada **apenas no Monte Carlo** (ver §1.4).

Alternativas de financiamento a referir na nota: **BEI** (linha Clima/Digital, 3,70 %),
**Banco de Fomento c/ Garantia Mútua** (3,85 %), **crédito comercial** residual (4,15 %).

---

## 7. Verificação (obrigatória antes de fechar)

Workflow de preview (servidor já existente — usar `preview_*`, não Bash):
1. Garantir backend a correr e `GET /api/hub/vala` a devolver `pv_soft_loan`.
2. Abrir a tab Hub, percorrer **os 5 subtabs** sem erros de consola (`preview_console_logs`).
3. **Plano de Financiamento**: confirmar 3 tranches na barra/cards, carências corretas
   por tranche, PT2030 a €0 com narrativa nova, RFAI visível.
4. **VALA**: waterfall com 5 camadas (a 5.ª a €0/"inativa"), tabela reconcilia com KPI VALA.
5. Trocar o **seletor de cenário** (Base→Upside→Downside→Stress) e confirmar que todos os
   números reagem (`preview_click` + `preview_snapshot`).
6. Teste de ativação do soft loan: definir `taxa_mercado_ref` no YAML (ex. 0,06) e confirmar
   que a 5.ª camada passa a > 0 e que o waterfall/tabela somam ao VALA. Reverter depois.
7. `preview_screenshot` dos subtabs OE4 e VALA como prova final.

Regra de aceitação: **a soma das camadas no waterfall = VALA** em todos os cenários, e
**nenhum valor de financiamento hardcoded** sobrevive (re-correr o grep de §3).

---

## 8. Sequenciamento (fases)

| Fase | Conteúdo | Depende de |
|---|---|---|
| **F0** | Backend: expor `pv_soft_loan`/`soft_loan_por_tranche` em `get_hub_vala`; validar JSON | — |
| **F1** | Helpers partilhados (`TRANCHE_PALETTE`, `buildWaterfallFromDecomposicao`, `fmtCarencia`, `SoftLoanBadge`) | F0 |
| **F2** | `HubOE4View` — remover hardcodes, N tranches, PT2030=0, RFAI | F1 |
| **F3** | `HubVALAView` — waterfall data-driven, soft loan, narrativa | F1 |
| **F4** | `HubViabilidadeView` + reconciliação fiscal | F1 |
| **F5** | Monte Carlo + Contingência — varredura de strings + reatividade cenário | F1 |
| **F6** | (Opcional) extrair Hub para `hub_views.jsx` se o *loader* permitir | F2–F5 |
| **F7** | Verificação preview + screenshots + grep final | tudo |

F1–F5 podem ser commits independentes. F0 é bloqueador absoluto.

---

## 9. Riscos / armadilhas

- **Cache `?v=`**: esquecer de bumpar o `?v=` em `index.html` é a armadilha nº1 — as
  alterações não aparecem no preview e perde-se tempo a depurar código que já está certo.
- **`decomposicao` ordem/rótulos**: o waterfall data-driven depende dos `componente`
  exatos do backend ("Subsídio implícito (taxa bonificada)"). Não fazer *match* por string
  frágil — distinguir o VAL base por ser `type:"total"`/primeira entrada, somar o resto.
- **Camada inativa ≠ erro**: `pv_soft_loan === 0` com `taxa_mercado_ref` ausente é o estado
  normal hoje. Renderizar como "inativa", não esconder nem alarmar.
- **Reconciliação numérica**: após mexer, validar VALA = Σ camadas (arredondamentos do
  backend já vêm a 2 casas).
- **Não tocar no motor** (`viabilidade.py`) — está correto; o trabalho é UI + a ponte da rota.
- **Cenário Stress** pode dar VAL base negativo — garantir que `tone`/cores reagem ao sinal.

---

### Ficheiros-chave
- `interface/views.jsx` — `HubView` e subtabs (L709+)
- `interface/api.js` — `hubVala`/`hubDebtService`/`hubInvestmentMap` (L411–561)
- `interface/index.html` — verificar *loader* JSX (566 linhas)
- `src/api/routes/hub.py` — `get_hub_vala` (L337), `get_hub_investment_map` (L136)
- `src/engine/projetos/hub_logistico/viabilidade.py` — `vala_hub` (camada soft loan)
- `src/engine/data/subsidiarias/hub_logistico/m6_hub_assumptions.yaml` — bloco `financiamento`
