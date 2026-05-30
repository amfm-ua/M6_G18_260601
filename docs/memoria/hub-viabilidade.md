# Hub Logístico M6 — racional de viabilidade

> Documento de decisões analíticas. Última atualização: 2026-05-30.
> Exportado a partir das notas de trabalho; serve como registo do *porquê* das opções de modelação, não como manual técnico do código.

## Tese central

A viabilidade do Hub depende de **duas alavancas** — apoios fiscais **OU** receita comercial nova. O **núcleo operacional puro é negativo**, mas o projeto torna-se viável se ≥ 1 das duas alavancas se concretizar.

A premissa antiga ("VALA negativo sem apoios") já **não** se verifica no modelo corrente, por duas mudanças face à observação inicial da professora:

1. O caso-base APV passou a descontar ao **Ku desalavancado (7,2 %)** em vez do Ke (16,6 %) — correção metodológica que, por si só, vira o sinal.
2. Foram adicionados **benefícios comerciais** (`beneficios_comerciais.vn_incremental`, €0,35 → 0,95 M/ano B2C/Horeca).

## Quadro VALA (APV) — corrigido 2026-05-30

Valores após a correção da dupla contagem do RFAI (ver secção abaixo):

| Cenário | VALA |
|---|---|
| Com tudo | **+3 437 k€** (era +3 719 k€ antes da correção) |
| Operacional + comercial (sem apoios fiscais) | **+928 k€** (positivo) |
| Núcleo operacional puro (sem comercial **e** sem apoios, a Ku) | **−1 089 k€** (continua negativo) |
| Camada fiscal | +2 509 k€ (PT2030 +2 084 k€ · RFAI +225 k€ · escudo dívida +200 k€) |

A dependência não desapareceu, **migrou**: de "subsídios" para "subsídios **OU** receita comercial nova". PT2030 sozinho vale ~+2 084 k€; escudo fiscal da dívida ~+200 k€.

**Porquê isto importa:** a professora pediu plano de contingência por causa da dependência de apoios; a vulnerabilidade real agora é a assunção de ~1 M€/ano de receita comercial que ainda não existe.

**Como aplicar:** posicionar a receita comercial B2C/Horeca como o plano de contingência genuíno aos subsídios (em vez de a esconder), e apresentar o cenário "sem apoios + sem comercial" (−889 k€) como piso de stress.

## A receita comercial é defensável (sem dupla contagem)

A receita comercial do Hub (`beneficios_comerciais.vn_incremental`, €0,35 → 0,95 M/ano) é **defensável** e **não** há dupla contagem:

- O modelo core (cenário Base, sem Hub) já tem os canais **E-Commerce (B2C**, ~€5,9 M em 2024 → €8,3 M em 2029, 17 % do VN produtos) e **Hotelaria (Horeca**, ~€11,2 M → €15,6 M, 33 %).
- Mas com `crescimento_volume_por_canal` / `crescimento_pvu_por_canal` = 0 (`data/pressupostos/2025/vendas.yaml:79-101`) — ou seja, o baseline **não** embute efeito do Hub, logo o `vn_incremental` é somado por cima.
- Magnitude: +1,7 % (2026) a +4,0 % (2029) sobre B2C+Horeca — modesto e credível.

**Correção de narrativa pendente** no YAML do hub (linhas ~297-309): o texto fala em "canal B2C de raiz / habilitado pelo Hub", mas os canais **já existem** (€17 M/ano). Reframe correto: *"canais existentes limitados por capacidade/fulfillment (DMI alto, lead time 3-5 d); o Hub levanta o teto"* — liga ao argumento do DMI e satisfaz a regra incremental (com vs. sem projeto).

## Painel ao vivo (2026-05-30)

A sub-tab **Viabilidade** tem agora *"Origem do valor · Operacional vs. Comercial vs. Fiscal"* — gráfico de cascata + tabela. Endpoint `/api/hub/decomposicao-beneficios` (`decomposicao_beneficios_hub` em `viabilidade.py`). Decompõe o VALA em 3 camadas que somam ao total:

- **Operacional** = `val_base_ku` sem receita comercial (−1 089 k€)
- **Comercial** = acréscimo ao reativar `vn_incremental` (+2 016 k€)
- **Fiscal** = escudo + PT2030 + RFAI (+2 509 k€)

## Bug corrigido 2026-05-30 — dupla contagem do RFAI no `vala_hub`

O caso-base APV (`val_base`) partia do `fcf_livre` do `viabilidade_hub`, que **já** embute o crédito RFAI (reduz o IRC) e o reconhecimento NCRF 22 do PT2030. O ajuste-por-fórmula antigo (`cfs_clean = fcf − accrual_pt2030·(1−t)`) limpava só o PT2030 e, mesmo esse, falhava quando o EBIT do ano era ≤ 0.

**Resultado do bug:** o RFAI era contado 2× (no `val_base` **e** na camada `pv_rfai`), inflando o VALA oficial em ~282 k€ e mascarando o núcleo operacional negativo (mostrava −46 k€ em vez de −1 089 k€).

**Correção:** o `val_base` passa a re-correr `viabilidade_hub` com PT2030 = 0 e RFAI desligado (FCFF genuinamente unlevered e sem apoios); os apoios entram só pelas camadas dedicadas. Verificado: desligar RFAI baixa o VALA exatamente `pv_rfai` e `val_base` não se move. Afetou sub-tab VALA e Monte Carlo VALA (atualizam automaticamente, sem hard-codes). 105 testes passam.

## Cuidado com docs de argumentação externos

O doc "argumentação diplomática" (Qwen HTML): a história de "anos 6-10 a preços constantes/cruzeiro" **contradiz** o código — a extensão 2030-2034 cresce a 3,5 % nominal (`viabilidade.py:401`) com depreciação a custo histórico; é um modelo nominal coerente nos 10 anos (sem inconsistência real/nominal — é **força**, não defender o contrário).

## Ficheiros-chave

- `src/engine/data/subsidiarias/hub_logistico/m6_hub_assumptions.yaml`
- `src/engine/operacional/vendas.py`
- `src/engine/projetos/hub_logistico/viabilidade.py` (`decomposicao_beneficios_hub`, extensão 2030-2034 na linha ~401)
- `data/pressupostos/2025/vendas.yaml:79-101` (canais com crescimento = 0 no baseline)
