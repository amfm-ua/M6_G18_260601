# Benefícios Comerciais do Hub — fundamentação, incrementalidade e defesa

> **Pergunta que este documento responde:**
> *Os €0,35–0,95 M/ano de Volume de Negócios (VN) incremental atribuídos ao Hub devem entrar na avaliação do projeto? Não é dupla contagem, dado que os canais B2C e Horeca já existem?*

> ✅ **Conclusão (defensável):** Sim, devem entrar. São **incrementais** (acréscimo causado pelo Hub *acima* do crescimento orgânico), **não há dupla contagem** (o baseline do modelo core não embute qualquer efeito do Hub), e a **magnitude é modesta** (+1,7 % a +4,0 % sobre canais existentes). O projeto é robusto: a receita comercial pode cair **57 %** e o VALA *sem apoios fiscais* mantém-se positivo.

> 📅 Apuramento: 2026-05-29 · cenário Base · modelo core (`run_model(hub_on=False)`) · `vala_hub()`.

---

## 1. O ponto de partida: os canais já existem

A objeção mais forte do júri seria *«estão a inventar vendas novas para salvar o projeto»*. Os dados do próprio modelo core respondem a isto: os canais diretos **já existem e já são metade do negócio** da Grestel, muito antes do Hub.

Apuramento `vendas_anuais() × mix_canal_produto` (cenário Base, **sem** Hub):

| Canal | VN 2024 | VN 2026 | VN 2029 | % do VN produtos |
|---|---:|---:|---:|---:|
| **E-Commerce (B2C)** | €5,9 M | €6,96 M | €8,27 M | 17 % |
| **Hotelaria (Horeca)** | €11,2 M | €13,18 M | €15,65 M | 33 % |
| Private Label | €7,5 M | €8,87 M | €10,54 M | 22 % |
| Retalho | €9,5 M | €11,22 M | €13,33 M | 28 % |
| **Total VN produtos** | **€34,1 M** | **€40,2 M** | **€47,8 M** | 100 % |

> O B2C + Horeca somam **~€17 M (2024) → ~€24 M (2029)**. O Hub **não cria** estes canais — **destrava-os**.

Fontes no código: `src/engine/operacional/vendas.py` (cálculo de VN) e `src/engine/data/pressupostos/2025/mix.yaml` (mix de canais: E-Commerce 10–20 %, Hotelaria 25–40 % por mercado).

---

## 2. Princípio incremental: «com vs. sem projeto»

A regra de avaliação de projetos (Brealey, Myers & Allen, *Principles of Corporate Finance*, Cap. 6) é contar apenas os **fluxos incrementais**:

$$\text{benefício}_t = \text{VN}^{\text{COM Hub}}_t - \text{VN}^{\text{SEM Hub}}_t$$

O `vn_incremental` (€0,35→0,95 M) representa **só o acréscimo** que o Hub gera *acima* da trajetória que os canais já teriam sem ele. O baseline (a trajetória «sem Hub») não é zero — é a tabela da §1.

---

## 3. Porque NÃO há dupla contagem (prova)

Esta é a verificação crítica. Se o crescimento orgânico dos canais no modelo core já incluísse o efeito do Hub, somar o `vn_incremental` seria contar duas vezes. **Não é o caso**, e isto é verificável:

Em `src/engine/data/pressupostos/2025/vendas.yaml`:

```yaml
crescimento_volume_por_canal:
  Private_Label: 0.00
  Hotelaria:     0.00
  Retalho:       0.00
  E_Commerce:    0.00
crescimento_pvu_por_canal:
  Private_Label: 0.00
  Hotelaria:     0.00
  Retalho:       0.00
  E_Commerce:    0.00
```

Os canais crescem **apenas ao ritmo global do cenário (~2 %/ano de volume + spread de preço)** — não há nenhum *boost* específico de B2C ou Horeca atribuível ao Hub embutido no baseline. Logo, o `vn_incremental` do Hub é, **por construção, somado por cima** de uma base que o ignora. Não há sobreposição.

Adicionalmente, a avaliação do Hub (`vala_hub`) usa o seu próprio `vn_incremental` de forma isolada; não importa o VN do core. A separação é total.

---

## 4. Magnitude: um pedido modesto, não uma aposta

O `vn_incremental` representa, sobre o VN combinado dos dois canais que o Hub visa (B2C + Horeca):

| Ano | vn_incremental | VN B2C+Horeca (base) | Uplift implícito |
|---|---:|---:|---:|
| 2026 | €0,35 M | €20,14 M | **+1,7 %** |
| 2027 | €0,65 M | €21,29 M | +3,1 % |
| 2028 | €0,85 M | €22,63 M | +3,8 % |
| 2029 | €0,95 M | €23,92 M | **+4,0 %** |

> Estamos a afirmar que o Hub faz crescer canais existentes **2 a 4 %** acima do orgânico. É uma captura de quota conservadora — não a criação de um mercado novo. (Nota: parte do incremento de 2028-2029 é serviço logístico a terceiros, ~€0,2 M, pelo que o uplift *puramente* comercial é ainda menor — o quadro acima é conservador por atribuir tudo aos dois canais.)

---

## 5. Mecanismo causal: o Hub levanta um teto imposto pelo DMI

A incrementalidade é **causal**, não otimista: os canais diretos estão hoje **estrangulados** e o Hub remove o estrangulamento.

| Estrangulamento atual | Como o Hub o remove | Efeito comercial |
|---|---|---|
| Lead time 3-5 dias (DMI elevado) | Fulfillment 24-48h (VLMs + WMS) | Recupera encomendas B2C/Horeca hoje perdidas por prazo |
| Capacidade de SKUs limitada | +200 % SKUs geridos (6 VLMs) | Amplitude de coleções sem +headcount |
| Embalagem padrão | Box-on-Demand (gift premium) | +18 pp de margem no canal direto |
| Stock-outs por previsão fraca | Digital Twin + MES (previsão ML) | Menos ruturas → menos vendas perdidas |
| — | Capacidade logística ociosa (Fase 2) | Novo serviço B2B a cerâmicas da região |

> Este é o **mesmo** fenómeno (DMI alto) que justifica a libertação de inventário — só que do lado da receita: o inventário mal gerido não só prende capital, como **faz perder vendas**. Um problema, dois benefícios.

---

## 6. Robustez: análise de sensibilidade (defesa contra «e se as vendas não aparecerem?»)

Teste de stress sobre o cenário **sem apoios fiscais** (PT2030 = 0, RFAI desligado), escalando o `vn_incremental`:

| Escala do vn_incremental | VALA (sem apoios) |
|---:|---:|
| 100 % | +1 127 k€ |
| 75 % | +642 k€ |
| 60 % | +341 k€ |
| 50 % | +140 k€ |
| **43 % (break-even)** | **≈ 0** |
| 25 % | −370 k€ |
| 0 % | −889 k€ |

> **A receita comercial pode falhar 57 % e o projeto continua viável mesmo sem qualquer apoio fiscal.** Esta é a margem de segurança que torna o benefício comercial credível como plano de contingência aos subsídios.

---

## 7. Posição estrutural na avaliação (onde encaixa)

Decomposição do VALA (APV — ver `metodologia_apv_val_sem_beneficios_fiscais.md`):

| Camada | Contributo (VALA) | Natureza |
|---|---:|---|
| Núcleo operacional puro (poupanças − OPEX) | **−2 506 k€** | quase certo |
| (+) Libertação de inventário (DMI) | +1 617 k€ | quase certo |
| (+) **Receita comercial (B2C/Horeca)** | **+1 388 k€** | incremental, +2-4 % |
| = Subtotal económico (sem apoios) | **≈ +1 127 k€** | — |
| (+) Apoios fiscais (PT2030 + RFAI + escudo) | +2 591 k€ | dependente de aprovação |
| = **VALA total** | **+3 719 k€** | — |

> Leitura para a defesa: o projeto **não** depende dos apoios fiscais para ser viável — depende de **destravar canais que já existem**. Os apoios majoram o retorno; não o salvam.

---

## 8. Scripts de defesa

**Relatório (texto sugerido):**
> «Os benefícios comerciais do Hub não representam vendas novas especulativas: os canais B2C (€5,9 M) e Horeca (€11,2 M) já constituem 50 % do volume de negócios da Grestel. O Hub atua sobre um estrangulamento operacional concreto — lead times de 3-5 dias e ruturas de stock decorrentes do DMI elevado — que hoje limita estes canais. O `vn_incremental` modelado (€0,35–0,95 M/ano) corresponde a uma aceleração de apenas 1,7 % a 4,0 % sobre a base existente, somada acima de um baseline que não incorpora qualquer efeito do Hub (crescimento por canal = 0 no modelo core), pelo que não há dupla contagem. A análise de sensibilidade demonstra robustez: uma quebra de até 57 % nesta receita mantém o VALA positivo mesmo na ausência de apoios fiscais.»

**Pergunta provável do júri e resposta:**
> *«Esses €0,95 M não são vendas que já têm?»*
> «Não. O modelo core já projeta o crescimento orgânico desses canais (€5,9 M → €8,3 M no B2C) ao ritmo global de ~2 %. O `vn_incremental` é o acréscimo *adicional* que só o Hub viabiliza, somado por cima dessa trajetória — verificável no facto de o crescimento específico por canal estar a zero no baseline.»

> *«E se a receita comercial não se materializar?»*
> «Mesmo com uma quebra de 57 % e sem qualquer apoio fiscal, o VALA permanece positivo. É o nosso piso de stress. Abaixo disso, o plano de contingência de financiamento (reforço de capitais próprios) entra em ação — ver `13_plano_contingencia.md`.»

---

## 9. Reprodutibilidade

```python
# Baseline de canais (modelo core, sem Hub)
from src.engine.modelo.model import load
from src.engine.operacional import vendas as v
a, base, sched = load(cenario="Base")
df_prod = v.vendas_anuais(a, base, sched)        # VN por produto × mercado × ano
# aplicar a.mix_canal_produto para repartir por canal (E_Commerce, Hotelaria, …)

# Robustez do benefício comercial (sem apoios)
from src.engine.projetos.hub_logistico import vala_hub, load as load_hub
import copy
hub = load_hub()
h = copy.deepcopy(hub); p = h["projeto_hub"]
p["financiamento"]["PT2030"]["montante"] = 0.0
p["rfai"]["aplicar"] = False
for y in p["beneficios_comerciais"]["vn_incremental"]:
    p["beneficios_comerciais"]["vn_incremental"][y] *= 0.43   # break-even
print(vala_hub(h)["vala"])   # ≈ 0
```

---

## 10. Referências

- **Brealey, R., Myers, S. & Allen, F.** — *Principles of Corporate Finance*, Cap. 6 (fluxos de caixa incrementais; regra «com vs. sem projeto»).
- **Damodaran, A.** (2002) — *Investment Valuation*, 2.ª ed. (incrementalidade e atribuição de receitas a projetos).
- Documentação relacionada do projeto:
  - `docs/metodologia_apv_val_sem_beneficios_fiscais.md` — decomposição APV / VALA.
  - `docs/dmi_modelacao_inventario.md` — libertação de inventário (o outro benefício do DMI).
  - `m6_markdowns/13_plano_contingencia.md` — plano de contingência de financiamento.
- Ficheiros de pressupostos:
  - `src/engine/data/subsidiarias/hub_logistico/m6_hub_assumptions.yaml` → `beneficios_comerciais`.
  - `src/engine/data/pressupostos/2025/vendas.yaml` → `crescimento_*_por_canal` (= 0).
  - `src/engine/data/pressupostos/2025/mix.yaml` → `mix_canal_produto`.
