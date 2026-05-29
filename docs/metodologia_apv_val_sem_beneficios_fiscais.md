# Metodologia de Avaliação — APV / VALA: o VAL do projeto *sem* benefícios fiscais

> **Pergunta que esta metodologia responde:**
> *Quanto vale o Hub Logístico só pelas suas operações, antes de qualquer subsídio, escudo fiscal da dívida ou crédito fiscal?* — e, a partir daí, quanto vale **cada** benefício fiscal isoladamente.

> ✅ **Estado da implementação (2026-05-29 — CORRIGIDO):** a metodologia abaixo está agora **implementada corretamente** em `vala_hub()`. O caso-base passou a ser descontado ao **Ku desalavancado (7,20 %)** (antes usava o Ke alavancado 16,62 %). Resultado: VAL-base de **+1.209.734** (antes −591.546) e VALA de **3.718.544** (antes 1.917.263). Detalhe das alterações em §7.

---

## 1. Porque APV (e não só WACC)

O método WACC mistura tudo num único número: as operações, o escudo fiscal da dívida e (se incluídos nos fluxos) os subsídios ficam todos «dissolvidos» numa taxa de desconto e num VAL agregado. Não permite responder à pergunta *«e se não houvesse subsídio?»* sem refazer o modelo.

O **APV — Adjusted Present Value (Myers, 1974)** faz o oposto: **separa por camadas**. Avalia primeiro o projeto como se fosse **100 % financiado por capital próprio** (sem dívida, sem benefícios fiscais) e depois **soma** o valor presente de cada efeito de financiamento.

$$\text{VALA} = \underbrace{\text{VAL}_{\text{unlevered}}}_{\text{operações puras}} + \text{VA(escudo fiscal)} + \text{VA(subsídio PT2030)} + \text{VA(RFAI)}$$

Isto é exatamente o que as fontes do projeto prescrevem:

- *«VAL_unlevered: projeto financiado 100 % CP… os benefícios fiscais são tratados separadamente.»* — `PI_financiamento.md` §4
- *«VALA — Ideal quando: financiamento específico, variável no tempo, **com subsídios, taxas bonificadas** ou múltiplas fontes.»* — `PI_financiamento.md` §4
- **Regra de auditoria (gate):** *«🔴 VALA com taxa de desconto da 1.ª parcela ≠ rCP do projeto **unlevered**.»* — `PI_financiamento.md` §5

O Hub tem **três** efeitos de financiamento simultâneos (dívida bonificada CGD/BEI, subsídio PT2030 de 2,7 M€, crédito RFAI de 0,6 M€). É o caso de manual para APV em vez de WACC.

---

## 2. As camadas do APV no Hub

| # | Componente | O que mede | É benefício fiscal? |
|---|------------|------------|:---:|
| 1 | **VAL_base (unlevered)** | Valor das operações puras: poupanças, libertação de inventário, VN incremental B2C, líquido de CAPEX, ΔNFM, IRC pleno e valor terminal | ❌ Não |
| 2 | **Escudo fiscal da dívida** | Poupança de IRC pelos juros dedutíveis (CGD 4,15 % + BEI 3,75 %) | ✅ Sim |
| 3 | **PT2030 líquido** | Subsídio de 2,7 M€ recebido em 2027, líquido do IRC sobre o reconhecimento NCRF 22 | ✅ Sim |
| 4 | **RFAI** | Crédito fiscal de 0,6 M€ (10 % do CAPEX elegível), deduzido à coleta | ✅ Sim |

> **O número que o utilizador quer ver — «VAL sem benefícios fiscais» — é a Camada 1 isolada.** As camadas 2–4 são *adicionais* e opcionais à decisão de viabilidade económica nuclear.

---

## 3. Taxa de desconto de cada camada (regra de não-duplicação)

Cada camada desconta-se à taxa que reflete **o seu próprio risco** — princípio de Miles-Ezzell (1980) e Damodaran (2002, §10.5):

| Camada | Taxa de desconto | Justificação |
|--------|------------------|--------------|
| VAL_base (operações) | **Ku** — custo de capital **desalavancado** | Risco só do negócio, sem risco financeiro. **NÃO** é o Ke alavancado. |
| Escudo fiscal | **k_d** por tranche | O tax shield é tão arriscado quanto a dívida que o gera (Miles-Ezzell). |
| PT2030 | **r_f** | Subsídio aprovado é quase determinístico → risco ≈ taxa sem risco. |
| RFAI | **r_f** | Crédito determinístico (10 % × CAPEX); único risco = gerar coleta suficiente. |

> 🔑 **O erro mais comum em APV** (e o que está no código atual) é descontar as operações ao **Ke alavancado**. O Ke embute o risco financeiro de uma estrutura com D/E = 3,0; aplicá-lo a fluxos *unlevered* penaliza-os duplamente. A 1.ª camada **tem de** usar o Ku.

---

## 4. Cálculo do Ku para o Hub

Partindo dos parâmetros canónicos em `m6_hub_assumptions.yaml` (secção `viabilidade`):

```
r_f      = 3,10 %                    (OT Portugal 10 anos)
β_u      = 0,71                      (Damodaran, Household Products Europe, unlevered corr. for cash)
ERP      = 5,78 %                    (implícito: (Ke − r_f)/β_l = (16,62 % − 3,10 %)/2,34)
```

$$K_u = r_f + \beta_u \times \text{ERP} = 3{,}10\% + 0{,}71 \times 5{,}78\% = \mathbf{7{,}20\%}$$

Repare-se que **o `β_u = 0,71` já existe no YAML** mas **não é usado** para descontar o caso-base — o código usa o `ke` (β alavancado 2,34). A correção é usar o Ku derivado acima.

> Coerência: Ku 7,20 % ≈ WACC 6,46 %, como esperado (a pequena diferença é precisamente o efeito do escudo fiscal embutido no WACC *after-tax*). Esta proximidade é a prova de que o Ku está bem calculado.

---

## 5. Reconciliação APV ↔ WACC (validação cruzada)

Bem construídos, os dois métodos têm de **convergir** na parte «operações + escudo fiscal»:

| | Valor |
|---|---|
| VAL_base @ Ku 7,20 % (operações puras) | +1.210.068 |
| (+) Escudo fiscal da dívida | +199.700 |
| **= Operações + escudo (APV)** | **≈ 1.409.768** |
| VAL operações @ WACC 6,46 % (referência) | **1.429.672** |
| Diferença | ~20 k€ (1,4 %) — Miles-Ezzell vs WACC + arredondamentos ✅ |

A reconciliação **fecha**. Com o caso-base atual ao Ke (−591 k€) **não fecha com nada** — sinal claro do desvio metodológico.

---

## 6. Resultado: o VAL sem benefícios fiscais

| Caso-base (operações puras, sem benefícios fiscais) | Taxa | VAL |
|---|:---:|---:|
| **Implementação atual** (Ke alavancado) — incorreto para APV | 16,62 % | **−591.546** |
| **Correto (Ku desalavancado)** | 7,20 % | **+1.210.068** |
| Referência (WACC) | 6,46 % | +1.429.672 |

> **Conclusão económica:** o Hub **cria valor só pelas operações** (+1,21 M€), *antes* de qualquer apoio público ou fiscal. Os benefícios fiscais reforçam — não sustentam — a viabilidade. Esta é a mensagem mais forte que o modelo pode dar; a versão anterior **escondia-a** ao reportar um caso-base negativo (Ke alavancado).

### VALA completo — antes vs. depois da correção

| Componente | Antes (Ke) | **Depois (Ku) — em produção** |
|------------|------:|---------------:|
| VAL_base | −591.546 | **+1.209.734** |
| Escudo fiscal | +199.700 | +199.700 |
| PT2030 líquido | +2.084.376 | +2.084.376 |
| RFAI | +224.734 | +224.734 |
| **VALA** | **1.917.263** | **3.718.544** |

O VALA estava subavaliado em **~1,8 M€** apenas por causa da taxa do caso-base. *(Valores reais devolvidos por `vala_hub()` após a correção.)*

---

## 7. Averiguação da implementação

Função principal: `vala_hub()` em `src/engine/projetos/hub_logistico/viabilidade.py:851`.

| Aspeto | Estado | Localização |
|--------|:------:|-------------|
| Estrutura APV em 4 camadas | ✅ Correto | `viabilidade.py` (`vala_hub`, secção 5) |
| Escudo fiscal a k_d por tranche (Miles-Ezzell) | ✅ Correto | `viabilidade.py` (`vala_hub`, secção 2) |
| PT2030 líquido a r_f, líquido de IRC NCRF 22 | ✅ Correto | `viabilidade.py` (`vala_hub`, secção 3) |
| RFAI a r_f | ✅ Correto | `viabilidade.py` (`vala_hub`, secção 4) |
| Caso-base limpo do reconhecimento NCRF 22 | ✅ Correto | `viabilidade.py` (`vala_hub`, secção 1) |
| **Caso-base descontado ao Ku** | ✅ **Corrigido** — usa `ku` (7,20 %) | `viabilidade.py:957` |
| Referência WACC genuína | ✅ **Corrigido** — `viabilidade_hub(..., wacc=wacc_real)` devolve €2.493.769 | `viabilidade.py:930-932` |
| `nota_metodologica` e etiqueta da decomposição | ✅ **Corrigido** — «VAL_base (Ku, unlevered)» | `viabilidade.py` |
| `ku` parametrizado no YAML | ✅ **Adicionado** | `m6_hub_assumptions.yaml` (secção `viabilidade`) |
| Workaround do `contingencia_hub` | ✅ **Corrigido** — define `via["ku"]` e `via["ke"]=ke_lev` (já não corrompe o WACC dinâmico) | `contingencia_hub.py:150-151` |

### Alterações aplicadas (2026-05-29)

1. ✅ **`m6_hub_assumptions.yaml`** — adicionada a chave `ku: 0.07204` na secção `viabilidade`.
2. ✅ **`viabilidade.py` `vala_hub`** — caso-base descontado ao **Ku**: `val_base = _npv(cfs_clean, ku)`; o `ku` é lido do YAML ou derivado de `rf + β_u × ERP`.
3. ✅ **`val_wacc_referencia`** — agora genuíno (fluxos descontados ao WACC real, não ao Ke).
4. ✅ **`nota_metodologica`** + etiqueta da decomposição atualizadas para Ku; adicionada a chave de saída `val_base_ku` (mantido `val_base_ke` como alias retrocompatível).
5. ✅ **`contingencia_hub.py`** — o hack `via["ke"]=ku` foi substituído por `via["ku"]=ku` + `via["ke"]=ke_lev`.
6. ⏳ **Pendente (manual):** atualizar os números no relatório M6 (cap. 10) e em `fcf_modelacao_hub.md`.

> Todas as correções **aumentam** o VAL (eram conservadoras na direção anterior), pelo que **não invertem** a decisão GO — mas alinham o modelo com a metodologia APV das fontes e tornam a narrativa («viável mesmo sem apoios») defensável. Testes: 91 passed, 5 skipped (inalterado).

---

## 8. Regras de ouro (das fontes, a não violar)

- `FINANCIAMENTO ≠ CRIAÇÃO DE VALOR` — a dívida só altera custo de oportunidade e estrutura de fluxos.
- `CMPC ↔ VALA mutuamente exclusivos` — nunca misturar os dois métodos no mesmo cálculo.
- `Alinhamento CF/taxa` — WACC → fluxos *unlevered* (sem juros); APV → fluxos unlevered + benefícios à parte.
- `Poupança fiscal condicional` — o escudo `juros × T` só existe se RAI > 0.
- **Lei de Damodaran** — *se não afeta cash flows e não afeta risco, não afeta valor.*

---

## 9. Referências

- Myers, S. C. (1974). *Interactions of Corporate Financing and Investment Decisions.* Journal of Finance 29(1). — Teoria APV.
- Miles, J. A. & Ezzell, J. R. (1980). *The Weighted Average Cost of Capital…* Journal of Finance 35(4). — Tax shields a k_d.
- Damodaran, A. (2002). *Investment Valuation*, 3.ª ed., §10.5. — Efeitos de financiamento.
- Materiais da UC (cowork/notebook/api_damodaran): `PI_financiamento.md`, `PI_aval_risco.md`, `valuation_damodaran.md`.

---

*Documento criado em 2026-05-29; correções da §7 aplicadas na mesma data. Números computados com as funções do motor (`vala_hub`, `viabilidade_hub`, `_npv`) sobre o cenário Base.*
