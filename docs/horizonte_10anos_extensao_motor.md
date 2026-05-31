# Horizonte de 10 anos — Extensão do motor consolidado a 2034

> Atualizado: 2026-05-31 · Módulo: `src/engine/demonstracoes/extensao_maturidade.py`
> Flag: `horizonte_maturidade` (opt-in) em `run_model()` / `build_statements()`
> Continuidade: estrutura de capital constante + cash sweep (ver 3.1)

## 1. Porquê 10 anos (2025–2034)

A avaliação de um **projeto de investimento real** (o Hub Logístico) deve cobrir
toda a sua vida útil. Uma janela de 5 anos (2025–2029) introduz dois erros
metodológicos:

1. **Payback desalinhado** — o payback do projeto ocorre por volta do **ano 7**;
   uma projeção de 5 anos não consegue, por construção, mostrar o momento em que
   o investimento se paga.
2. **Omissão de fluxos relevantes** — os anos 6–10 contêm a maturação do VN do
   hub, o CAPEX de substituição (manutenção) e o valor residual dos activos. Cortar
   em 2029 trunca metade da vida útil e do valor do projeto.

Isto **não contradiz** a cautela de Myers quanto a projeções de longo prazo: essa
cautela aplica-se ao *planeamento estratégico* de uma empresa a 15–20 anos, não à
avaliação de um projeto de investimento delimitado, cuja vida útil é conhecida.

A literatura distingue duas fases:

- **Anos 1–5 (2025–2029) — fase de arranque/crescimento:** modelação detalhada,
  linha-a-linha (o motor existente, intocado).
- **Anos 6–10 (2030–2034) — fase de maturidade/estabilização:** estado
  estacionário com pressupostos macro.

## 2. Abordagem escolhida — B (append isolado)

Foram ponderadas duas vias:

| Via | Descrição | Decisão |
| --- | --------- | ------- |
| **A** | Empurrar `ANO_FIM` 2029→2034 e recriar todas as tabelas pré-computadas (`schedules.yaml`, mapa de dívida, `reference_balanco`) até 2034. | **Rejeitada** — vários dias de trabalho, alto risco de descalibrar o *treasury plug* e as 3 reconciliações. |
| **B** | *Roll-forward* de estado estacionário a partir da última linha detalhada (2029), anexado às demonstrações sem tocar no motor 2024–2029. | **Adotada.** |

A via B preserva a reconciliação ao cêntimo de 2024–2029 e é **opt-in**: com a flag
desligada (default), as demonstrações terminam em 2029 exatamente como antes
(garante zero regressões).

### Descoberta que reduziu o risco

O Balanço anual **fecha por construção** via o *treasury plug* (caixa / aplicações
financeiras CP / linha de crédito CP absorvem o residual). Não depende do
`reference_balanco` do Excel. Por isso, o maior receio da via A ("recalibrar sem a
âncora do Excel") **não se aplica** ao roll-forward: o `controlo ≈ 0` é garantido
em qualquer ano de extensão, seja qual for o detalhe da DR/equity.

## 3. Regras de estado estacionário (2030–2034)

| Rubrica | Regra | Justificação |
| ------- | ----- | ------------ |
| Receitas e custos operacionais | crescem a `g = 2 %`/ano (inflação) | regime de cruzeiro pós-ramp |
| Fundo de maneio (inventários, clientes, EOEP, fornecedores, ...) | cresce a `g` → estabiliza como **% fixa das vendas** | NFM proporcional ao volume |
| Depreciação | mantida ao nível de 2029 | activo fixo em regime estável |
| CAPEX | **= Amortizações** → AFT líquido constante | investimento só de substituição/manutenção |
| Dívida | mantida ao nível de 2029 | manter alavancagem; juros constantes |
| Payout de dividendos | payout dinâmico do motor **+ cash sweep residual** | estrutura de capital constante (ver 3.1) |
| Aplicações financeiras CP | **fixas no nível de 2029** (`aplic_target`) | não acumular excedente ocioso |
| IRC | taxa **efectiva de 2029** aplicada ao RAI | SIFIDE/RFAI já consumidos até 2029 (carry-forward esgotado, `sifide_carryforward[2029]=0`) |

O parâmetro `g` é configurável (`g_maturidade` em `build_statements`; default 2 %).

### 3.1 Cash sweep — política de dividendo residual na continuidade

**Problema (retenção total).** Com dívida fixa e retenção integral do resultado, o
excedente de tesouraria acumulava-se ano após ano em **aplicações financeiras CP**
(€4,8 M em 2029 → €21,6 M em 2034 no cenário Base). A base de capital próprio
inflava com activos financeiros de baixo rendimento e o **ROE diluía-se
artificialmente** (21,4 % → 15,2 %), tal como a liquidez geral (1,95× → 2,84×). Não
é uma deterioração operacional — é um artefacto do pressuposto de reinvestimento.

**Tratamento adoptado — constant leverage + cash sweep.** Mantém-se a dívida no
nível de 2029 (alavancagem fixa → **WACC estável**, requisito de um valor terminal
de Gordon) e **distribui-se o FCFE que de outro modo ficaria ocioso** como dividendo
residual, fixando as aplicações financeiras no nível de 2029. É a hipótese implícita
de uma perpetuidade: a empresa devolve aos accionistas o que não consegue
reinvestir produtivamente.

**Resultado.** ROE e liquidez geral mantêm-se ao nível de 2029 (ROE 21,4 % → 23,3 %;
liquidez ≈ 1,95×), reflectindo a rentabilidade operacional e não a acumulação de
caixa. O valor terminal consolidado quase não se altera (o caixa ocioso tinha VAL
≈ nulo); o que melhora é a **coerência dos rácios** e a defensabilidade.

**Implementação (fechada, sem iteração).** Como o `surplus` do *treasury plug* é
linear no dividendo (−€1 por €1) e a dotação da reserva legal se anula no capital
próprio, o sweep resolve-se em forma fechada:
`div_sweep = max(0, surplus0 − div_base − caixa_max − aplic_target)`. A reconciliação
DFC↔Balanço e o `controlo ≈ 0` mantêm-se por construção.

**Desligável.** `distribuicao.terminal_cash_sweep: false` recupera o comportamento
antigo (retenção total) — usado para análise de sensibilidade e regressão.

## 4. Going concern vs. liquidação do projeto — NOTA PARA A DOCENTE

Há **duas perspetivas de valor terminal** em jogo, e é importante não as confundir:

- **Valor terminal consolidado (Grestel como um todo):** a empresa é um *going
  concern* — continua a operar para além de 2034. O valor terminal da avaliação
  consolidada usa o **modelo de Gordon** (crescimento perpétuo), agora ancorado no
  FCF de **2034** (último ano da janela) em vez de 2029. Não há liquidação da
  empresa.

- **Valor de liquidação (apenas o projeto Hub, standalone):** na avaliação isolada
  do Hub (`viabilidade.py`), o projeto é fechado em 2034/2035 com um **valor de
  liquidação** — venda residual dos activos (terrenos/armazéns) líquida de imposto
  sobre mais-valias + recuperação integral do fundo de maneio. Faz sentido porque
  estamos a avaliar um *projeto delimitado*, não a empresa.

> **Em resumo:** a liquidação aplica-se **só ao VAL standalone do Hub**; o valor
> consolidado da Grestel mantém-se em *going concern* (Gordon). Esta opção foi
> deliberada — assinala-se aqui para esclarecimento.

## 5. Estado da reconciliação na extensão

- **Balanço:** `controlo ≈ 0,0000` em todos os anos 2030–2034, nos cenários Base e
  Hub_Ativo (fecho garantido pelo plug).
- **DFC (método indirecto):** `reconciliacao_ok = True` em **todos** os anos
  2025–2034 (Base e Hub_Ativo). O desfasamento estrutural plug↔DFC que existia no
  motor (~27 k€ em 2025 a ~246 k€ em 2029) foi **eliminado na raiz** — ver
  [reconciliacao_dfc_correcao.md](reconciliacao_dfc_correcao.md). Tinha duas causas:
  (i) a **reserva legal evaporava-se** do capital próprio (saía dos resultados
  transitados sem entrar em reservas legais), subavaliando a caixa do plug; e
  (ii) a **imparidade era dupla-contada** na DFC (add-back `+imp` somado a uma
  variação de clientes já líquida). Corrigidas ambas, a `variação_caixa` da DFC
  iguala a Δcaixa do Balanço ao cêntimo.

## 6. Impacto na avaliação consolidada

`_build_mc_params_from_run` (`src/api/routes/valuation.py`) passou a correr o
modelo com `horizonte_maturidade=True`. As séries `projected_FCFF` /
`projected_FCFE` estendem-se agora a **2025–2034**, e o valor terminal de Gordon
(`_equity_dcf`) ancora automaticamente no **último ano (2034)**.

Efeito ilustrativo (Base, WACC 9 %, g 2 %, FCFF derivado do DR):

| Métrica | 5 anos (2029) | 10 anos (2034) |
| ------- | ------------- | -------------- |
| equity_dcf | ≈ 29,1 M€ | ≈ 31,6 M€ |
| equity_fcfe | ≈ 23,2 M€ | ≈ 25,3 M€ |
| weighted_equity | ≈ 19,2 M€ | ≈ 20,8 M€ |

O aumento reflete os 5 anos adicionais de FCF e o terminal ancorado num FCF de
2034 mais elevado.

## 7. Limitações conhecidas

1. **KPIs não estendidos:** `kpis.py` itera `ALL_YEARS` (2024–2029) e liga-se a
   cronogramas de produção/ESG que terminam em 2029. A tabela de KPIs continua a
   mostrar 2024–2029 mesmo com a extensão ligada. As três demonstrações
   (DR/Balanço/DFC) é que ficam a 10 anos.
2. **IRC simplificado na maturidade:** usa a taxa efectiva de 2029 (não recorre o
   `_irc` com derrama por escalões). Defensável porque os créditos fiscais já estão
   esgotados e a taxa efectiva é estável em regime de cruzeiro.
3. **Subsidiárias em regime estável:** o valor da participação é mantido constante
   (assume-se dividendo recebido ≈ resultado por equivalência patrimonial).

## 8. Como ligar

```python
from engine.modelo.model import run_model
dfs = run_model("Base", hub_on=True, horizonte_maturidade=True)
# dfs["dr"], dfs["balanco"], dfs["dfc"] cobrem agora 2024–2034
```

Para a avaliação consolidada, o horizonte de 10 anos já está ligado por defeito em
`_build_mc_params_from_run`.
