# Índice docs/ ↔ Relatório M6 (mapa de coerência)

> **Propósito:** mapear os documentos de `docs/` ao relatório final em `m6_markdowns/` e separar o que é **metodologia viva** do que são **snapshots já refletidos no relatório**. O relatório é a fonte canónica dos números; os `docs/` da raiz retêm a derivação técnica e a metodologia de engenharia que não cabem no corpo do relatório.

## ⚠️ Valores canónicos (modelo atual — sujeitos a recálculo)

Extraídos do modelo em execução (`viabilidade_hub`, `vala_hub`, `monte_carlo_hub`). Prevalecem sobre quaisquer valores divergentes nos documentos. **Quando o modelo for recalculado, atualizar esta tabela e as tabelas numéricas do relatório (Cap. 7–10, Anexos); os documentos de metodologia não precisam de alteração.**

| Parâmetro | Valor canónico | Docs antigos (arquivados) |
|---|---|---|
| WACC (base) | **6,46%** | 6,3% |
| Ke (APV) | **16,62%** | 16,18% |
| IRC (marginal do projeto) | **23,5%** | 24,5% (ver `correcao_irc_taxa_efetiva.md` — questão em aberto) |
| VAL (FCFF @ WACC) | **€2.493.769** | €2.110k |
| TIR | **17,49%** | 14,6% |
| Payback atualizado | **7,37 anos** | ~8,4 anos |
| Índice de rendibilidade | **1,42** | 1,35 |
| VALA (APV, VAL_base @ Ku) | **€3.718.544** | — |
| Monte Carlo P(VAL>0) | **99,95%** | N=2.000, seed 42 |

---

## 🟢 Raiz `docs/` — manter (metodologia / motor, válida apesar de mudanças de valores)

| Documento | Conteúdo |
|---|---|
| `_INDICE_RELATORIO.md` | Este mapa de coerência |
| `avaliacao_mc_metodologia.md` | Metodologia da simulação de Monte Carlo |
| `monte_carlo_distribuicoes.md` | Calibração das distribuições dos drivers |
| `fcf_modelacao_hub.md` | Definições FCFF/FCFE e construção do FCF *(banner de coerência)* |
| `dmi_modelacao_inventario.md` | Modelação do DMI e libertação de inventário |
| `horizonte_10anos_extensao_motor.md` | Extensão do motor (flag `horizonte_maturidade`) |
| `extensao_fcf_hub_2030_2034.md` | Extrapolação do FCF 2030–2034 |
| `analise_balanco_coerencia.md` | Testes de coerência do balanço |
| `reconciliacao_dfc_correcao.md` | Reconciliação da DFC |
| `aplicacoes_financeiras_cp.md` | Modelação de aplicações financeiras de CP |
| `correcao_irc_taxa_efetiva.md` | Discussão da taxa de IRC — **questão em aberto** |
| `pressupostos_sinteticos.md` | Referência-mãe de pressupostos *(banner de coerência)* |

## 🟡 `docs/_fora_ambito_m6/` — trabalho válido fora do âmbito do plano Hub

| Documento | Tema |
|---|---|
| `cenario_cozedura_baixa_temp.md` | Cenário ESG cozedura (toggle `cozedura_on`) |
| `cup_cozedura_analitico.md` | Análise de custo da cozedura |
| `spec_cup_cozedura_analitico.md` | Especificação da análise de custo da cozedura |
| `Decodificando o Motor de Valuation Grestel….md` | Análise do motor de valuation (OE5) |

## 🔴 `docs/_arquivo/` — snapshots já integrados no relatório

| Documento | Onde já consta no relatório |
|---|---|
| `plano_financiamento_hub.md` | Cap. 6 + Anexo III |
| `relatorio_m6_monte_carlo_hub.md` | Cap. 9.4 |
| `analise_base_hub_vs_sem_hub.md` | Cap. 7.2 / 7.4 / 11.2 |
| `hub_impacto_margem_2025.md` | Cap. 7.2 |
| `sintese_m6_enquadramento_estrategico.md` | Cap. 1 e 2 |
| `contingencia_hub_pt2030.md` | Cap. 12 / 6.1 |
| `fase2_dmi_consolidado_prompt.md` | Nota de trabalho interna |
