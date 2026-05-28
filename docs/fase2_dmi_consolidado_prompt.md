# Fase 2 — Propagar o driver de DMI ao Monte Carlo consolidado

> **Tipo:** prompt de implementação (executável por um agente Claude Code).
> **Pré-requisito:** Fase 1 concluída e validada (driver físico de dias de DMI já vivo no
> hub VAL, tornado e MC do hub). Ver [dmi_modelacao_inventario.md](dmi_modelacao_inventario.md) §5.1.
> **Estado:** pendente. A Fase 2 só arranca depois da Fase 1 validada (já está).

---

## 1. Contexto para o agente (ler antes de tocar em código)

O Monte Carlo **consolidado** corre em
[`src/engine/valuation/monte_carlo.py`](../src/engine/valuation/monte_carlo.py) sobre uma
instância de [`GrestelModel`](../src/engine/valuation/model.py). Ao contrário do MC do hub,
este modelo **não re-executa** o pipeline operacional
([`inventarios.py`](../src/engine/operacional/inventarios.py) → balanço → FCFE). Recebe séries
de fluxos **já sintetizadas** e só perturba 5 drivers:

| Driver atual | Onde entra |
|---|---|
| `WACC` | desconto FCFF (`_equity_dcf`) |
| `g_terminal` | valor terminal Gordon (DCF e FCFE) |
| `EV_EBITDA_mult` | múltiplos (`_equity_multiples`) |
| `g_revenue_shock` | choque aditivo composto sobre FCFF (`_get_fcffs`) |
| `EBITDA_margin_shock` | choque sobre margem (`_get_fcffs`) |

`GrestelModel` guarda os fluxos em dois dicts ano→€:
- `p["projected_FCFF"]` — consumido por `_get_fcffs` (DCF-FCFF).
- `p["projected_FCFE"]` — consumido por `_equity_fcfe`.

`inventarios.py` **já lê** `dmi_reducao_hub` (`DMI_PA_reducao_dias` / `DMI_MP_reducao_dias`)
para o balanço determinístico — isso **não muda**. O que falta é propagar a *incerteza* de DMI
ao MC consolidado, sem reconstruir o pipeline operacional.

**Por que não basta o que existe:** hoje a variação de DMI não altera nem `projected_FCFF` nem
`projected_FCFE`, logo no MC consolidado o DMI tem correlação 0 com o equity value — o mesmo
"driver morto" que corrigimos no hub, mas a nível consolidado.

---

## 2. Abordagem aprovada (P2a — ajuste de fundo de maneio, leve)

Adicionar um driver `dmi_reducao_dias` (total de dias estruturais PA+MP) que, por ano, gera um
**ajuste de caixa de fundo de maneio** e o soma aos fluxos antes do desconto:

```
ajuste_wc[y] = Δd/365 × CMVMC_prod[y]
```

onde `Δd` é a diferença entre os dias amostrados e os dias base (`DMI_PA_reducao_dias +
DMI_MP_reducao_dias` da Fase 1, p.ex. 12+8 = 20). Sinal: **mais dias de redução ⇒ menos stock ⇒
entrada de caixa positiva**. O efeito é o *step-down* no primeiro ano + o *recorrente* sobre o
incremento de CMVMC_prod nos anos seguintes — exatamente a mesma cadeia
`dias → CMVMC_prod → €` de [`impacto.py:hub_inventario_release`](../src/engine/projetos/hub_logistico/impacto.py),
para manter coerência metodológica entre hub e consolidado.

Isto é consistente com a forma como o MC já aplica choques aditivos (`g_revenue_shock`,
`EBITDA_margin_shock`) sobre os fluxos — não introduz uma arquitetura nova.

> **Alternativa P2b (NÃO usar):** reconstruir o modelo operacional por iteração
> (inventarios → balanço → FCFE) dentro do loop MC. Lento, e arquiteturalmente alheio ao MC
> atual. Rejeitada no plano.

---

## 3. Prompt de implementação

> Cola o bloco abaixo a um agente Claude Code com a working directory na raiz do projeto.

```
Implementa a Fase 2 do driver de DMI: propagar a incerteza dos dias de inventário ao Monte
Carlo CONSOLIDADO (src/engine/valuation/monte_carlo.py + src/engine/valuation/model.py),
sem reconstruir o pipeline operacional. Abordagem P2a (ajuste de fundo de maneio aditivo).
Lê primeiro docs/fase2_dmi_consolidado_prompt.md e docs/dmi_modelacao_inventario.md §5.1.

PASSO 1 — model.py: aceitar e aplicar o ajuste de WC.
  • Em GrestelModel, suportar um novo parâmetro opcional p["wc_cash_adjustment"]: dict ano→€
    (entrada de caixa positiva = libertação de stock).
  • Em _get_fcffs(p): depois de calcular a lista base de FCFFs (já com rev/margin shocks),
    somar wc_cash_adjustment[ano] ao fluxo do ano correspondente, alinhado por índice de ano
    (usar a mesma ordenação `years = sorted(raw.keys())`). Se o dict estiver vazio/None, no-op.
  • Em _equity_fcfe(p): aplicar o MESMO ajuste à série FCFE (quando projected_FCFE existe;
    caso contrário, o ajuste já flui via _get_fcffs na aproximação FCFF−juro). Não duplicar.
  • set_params já faz update genérico — confirmar que "wc_cash_adjustment" sobrevive e que é
    limpo no restauro do estado base (ver PASSO 3).

PASSO 2 — monte_carlo.py: novo driver dmi_reducao_dias.
  • DEFAULT_DISTRIBUTIONS: adicionar
      "dmi_reducao_dias": {"type": "triangular", "min": 14, "mode": 20, "max": 27}
    (PA 8–15 + MP 8–12, janela VDMA combinada; mode 20 = 12+8 da base Fase 1).
  • Resolver CMVMC_prod base: ler o snapshot inventario_dmi.cmvmc_prod_base do hub
    (m6_hub_assumptions.yaml) via o loader já usado para construir o modelo; passá-lo para
    monte_carlo_valuation como parte dos params base ou via argumento. NÃO hardcodes os euros —
    reutiliza o mesmo snapshot da Fase 1 para o hub e o consolidado coincidirem.
  • dias base = DMI_PA_reducao_dias + DMI_MP_reducao_dias do dmi_reducao_hub (= 20).
  • No loop de iterações, por cada amostra construir:
      delta = s["dmi_reducao_dias"] - dias_base
      wc_adj[y] = delta/365 * cmvmc_prod[y]            # step-down no 1.º ano
      wc_adj[y>1] usa (cmvmc_prod[y]-cmvmc_prod[y-1])  # componente recorrente
    (replicar a lógica de impacto.py:hub_inventario_release para o sinal e o step-down).
  • model.set_params({... , "wc_cash_adjustment": wc_adj}).
  • Acrescentar "dmi_reducao_dias" a DRIVERS e às correlacoes_spearman de saída.

PASSO 3 — limpeza de estado.
  • Após o loop, no restauro de params base, juntar "wc_cash_adjustment" às chaves removidas
    com model._params.pop(...) (mesma lista onde já se removem EV_EBITDA_mult, g_revenue_shock,
    EBITDA_margin_shock), para não contaminar chamadas determinísticas seguintes.

PASSO 4 — testes (tests/test_consolidado_dmi_mc.py, NOVO).
  • dmi_reducao_dias=20 (=base) ⇒ wc_adj≈0 ⇒ weighted_equity ≈ caso determinístico (tolerância).
  • Aumentar os dias amostrados ⇒ FCFF/FCFE sobem ⇒ weighted_equity sobe (anti-driver-morto).
  • correlacoes_spearman["dmi_reducao_dias"] != 0 com seed fixa.
  • Sinal correto: mais dias de redução ⇒ equity maior.

PASSO 5 — frontend + docs.
  • interface/views.jsx e interface/data.js: o label "Redução de DMI (dias)" já existe da Fase 1;
    garantir que o MC consolidado o mostra nas correlações (mock em data.js se aplicável).
  • Atualizar docs/monte_carlo_distribuicoes.md (tabela de drivers do MC consolidado) e a
    secção "Fase 2" deste ficheiro a marcar como concluída.

VERIFICAÇÃO FINAL.
  • pytest tests/ — toda a suite verde (exceto a falha pré-existente Stress_Volume já sinalizada).
  • Conferir que o balanço/DMI determinístico (inventarios.py) NÃO mudou — Fase 2 só toca no MC.
  • Conferir que os euros libertados no consolidado batem com a ordem de grandeza do hub
    (≈ €776 k de step-down estrutural em 2026 para Δd=20), sinal de coerência das duas vias.
```

---

## 4. Checklist de validação (resumo)

1. **Anti-driver-morto:** variar `dmi_reducao_dias` move `weighted_equity` no MC consolidado.
2. **Neutralidade no base:** `dmi_reducao_dias = 20` (= dias base) ⇒ ajuste ≈ 0 ⇒ equity ≈ determinístico.
3. **Sinal:** mais dias de redução ⇒ mais caixa ⇒ maior equity.
4. **Correlação viva:** `correlacoes_spearman["dmi_reducao_dias"]` ≠ 0.
5. **Coerência hub↔consolidado:** mesmo snapshot `cmvmc_prod_base`; euros da mesma ordem.
6. **Sem regressões:** `pytest tests/` verde; `inventarios.py` intacto; estado base limpo.

## 5. Notas e armadilhas

- **Não duplicar o ajuste** entre `_get_fcffs` e `_equity_fcfe`. O FCFE só recebe o ajuste
  diretamente quando tem `projected_FCFE` próprio; na via de aproximação (FCFE = FCFF − juro)
  o ajuste já vem embutido via `_get_fcffs`.
- **Alinhamento de anos:** os dicts são keyed por ano e ordenados com `sorted(...)`. O ajuste
  tem de casar o ano, não o índice posicional cego — confirmar que `projected_FCFF` cobre os
  mesmos anos de `cmvmc_prod_base` (2026–2034).
- **Snapshot único:** reutilizar `inventario_dmi.cmvmc_prod_base` da Fase 1. Se o consolidado
  usar outro vetor de CMVMC_prod, os euros divergem do hub e perde-se a coerência.
- **Dependências:** manter numpy puro, sem scipy (restrição do módulo).
