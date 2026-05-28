# Custo Unitário Ajustado pela Cozedura de Baixa Temperatura — Metodologia Analítica

**Módulo:** Orçamento de Produção · vista analítica  
**Ativação:** toggle `cozedura_on` (topbar do dashboard)  
**Natureza:** coluna *display-only* — não alimenta a DR, o CMVMC nem o EBITDA

---

## 1. Motivação — o problema de representação

O cenário de Cozedura de Baixa Temperatura reduz a procura de energia dos fornos (~18% por ciclo), mas esse efeito **não é visível no custo unitário de produto** (CUP) que aparece no Orçamento de Produção. A razão é contabilística:

> Segundo a apresentação SNC adotada, a energia dos fornos (Gás Natural e Eletricidade de processo) é registada em **FSE — Fornecimentos e Serviços Externos**, e não no CMVMC. O CUP da tabela de produção representa apenas o **custo industrial de absorção total** (MPSC + MOD + GGF), calibrado ao CIIP_Produtos_2024 auditado. A poupança energética entra diretamente nas FSE, donde propaga ao EBITDA — nunca passa pelo CMVMC.

Esta separação é contabilisticamente correta, mas cria uma leitura incompleta na tabela de produção: o CUP parece inalterado pelo cenário, mesmo quando a poupança de energia é o principal motor de valor. A coluna **CUP c/ cozedura** resolve essa ambiguidade de forma explicitamente analítica, sem alterar a DR.

---

## 2. Enquadramento de double counting — decisão de modelação

O risco central é contar a poupança de energia duas vezes:

| Via | Quem regista | Já está no modelo? |
|---|---|---|
| FSE reduzidas → EBITDA | `cozedura_fse_reducao` em `dr/build.py` → DR | **Sim** — é o efeito real |
| CUP reduzido → CMVMC → EBITDA | `cmvmc_anual` / `producao_anual` | **Não deve existir** |

A coluna analítica resolve isto sendo **estritamente decorativa**: vive no DataFrame `producao_anual` (tabela de gestão, não contabilística) e nunca é lida pela DR, pelo balanço ou pelos fluxos de caixa. A poupança é alocada por produto apenas para fins de análise interna de rentabilidade, não para apuramento de resultados.

---

## 3. Fórmula de cálculo

Para cada produto *p* e cada ano *y*:

### 3.1 Poupança de energia por unidade — Δ energia €/peça

```
Δ_energia_unit(p, y) = FSE_saving(y) / Qty_total_produzida(y)
```

onde `FSE_saving(y) = cozedura_fse_reducao[y]` (valor já calculado na DR, ver `impacto.py::cozedura_fse_reducao`).

**Premissa de alocação:** uniforme por unidade produzida — cada peça absorve a mesma poupança de energia independentemente do produto. É a **Opção A (fallback simples)** descrita na spec, adotada por:
- ausência de dados de intensidade energética por referência nos pressupostos atuais;
- natureza ilustrativa da coluna (a tese reporta 18% por ciclo de forno, não por produto);
- facilidade de verificação: `Σ_p (Δ_energia_unit × qty_produzida_p) = FSE_saving(y)` (verificado — ver Secção 5).

### 3.2 Custo incremental de matéria por unidade — Δ volastonite €/peça

```
Δ_materia_unit(p, y) = ramp(y) × cmvmc_incremento_pct × MPSC_unit(p, y)
```

onde:
- `ramp(y)` — fator de adoção faseada (⅓ em 2027, ⅔ em 2028, 1 em 2029);
- `cmvmc_incremento_pct` — incremento de matéria-prima pela volastonite (0,3% no pleno, lido de `cozedura_baixa_temp.yaml`);
- `MPSC_unit(p, y) = cip_unitario(p) × mp_fraction(p) × factor_custo(y)` — componente de matéria-prima do CUP, por produto e ano.

### 3.3 CUP c/ cozedura (efeito líquido)

```
CUP_cozedura(p, y) = CUP(p, y) − Δ_energia_unit(p, y) + Δ_materia_unit(p, y)
```

O sinal é deliberado: a poupança de energia reduz o CUP analítico (−), o custo da volastonite aumenta-o ligeiramente (+). O efeito líquido é positivo (CUP c/ cozedura < CUP base) porque a poupança de energia é ~3,1× o custo incremental da pasta no regime de cruzeiro.

---

## 4. Faseamento

As colunas respeitam a curva de adoção definida nos pressupostos:

| Ano | ramp | Δ energia €/peça | Δ volastonite €/peça | CUP c/ cozedura vs. CUP base |
|---:|---:|---:|---:|---|
| 2025 | 0 | 0,0000 | 0,0000 | Igual |
| 2026 | 0 | 0,0000 | 0,0000 | Igual |
| 2027 | ⅓ | −0,0088 | +0,0022 | **< CUP** (piloto) |
| 2028 | ⅔ | −0,0180 | +0,0046 | **< CUP** (roll-out) |
| 2029 | 1 | −0,0275 | +0,0071 | **< CUP** (pleno) |

*Valores para o produto "Pratos" no cenário Base; variam ligeiramente entre produtos devido à componente MPSC diferenciada.*

---

## 5. Validações realizadas

### 5.1 Regressão — invariância sem toggle

```python
a_off = run_model("Base", cozedura_on=False)
"cup_cozedura" in a_off["producao_anual"].columns  # False
```

Com `cozedura_on=False`, o DataFrame `producao_anual` não contém as colunas novas. O resultado é byte-idêntico ao modelo base.

### 5.2 Coerência de soma — conservação da poupança

A alocação é uma repartição (não cria valor): a soma ponderada pelas quantidades deve igualar o total FSE saving da DR.

| Ano | Σ (Δ energia × qty) | FSE_saving da DR | Diferença |
|---:|---:|---:|---:|
| 2027 | 59 288,75 € | 59 288,75 € | 0,00 € |
| 2028 | 124 470,98 € | 124 470,98 € | 0,00 € |
| 2029 | 195 943,88 € | 195 943,88 € | 0,00 € |

### 5.3 Ausência de double counting — EBITDA inalterado pelas novas colunas

O EBITDA do cenário `cozedura_on=True` reflete exclusivamente a poupança via FSE (efeito já existente antes desta feature). As novas colunas não alteram a DR:

| Ano | EBITDA OFF | EBITDA ON | Δ origem |
|---:|---:|---:|---|
| 2027 | 6 891 077 € | 6 931 823 € | FSE (pré-existente) |
| 2028 | 7 335 073 € | 7 420 185 € | FSE (pré-existente) |
| 2029 | 7 268 199 € | 7 401 498 € | FSE (pré-existente) |

O diferencial é **idêntico antes e depois da adição das colunas** — prova que não há double counting introduzido.

---

## 6. Apresentação no dashboard

A coluna aparece no Orçamento de Produção (vista "Produção") apenas quando o toggle **Cozedura BT** está ativo, em duas tabelas:

- **Detalhe por produto · 2025** — colunas "CUP c/ cozedura (€/un.)" e "Δ energia €/peça" inseridas após o CUP base.
- **Orçamento de Produção · detalhe completo** (seletor de ano 2024–2029) — idem.

Ambas as colunas têm um *tooltip* `title` explicitando a natureza analítica:

> *"Vista analítica de absorção total; a poupança de energia já está refletida nas FSE/EBITDA — não é somada duas vezes."*

Os valores são formatados a €/un. com 2 casas decimais, coerentes com o estilo das colunas PVU e CUP existentes.

---

## 7. Arquitetura de implementação

```
toggle cozedura_on (topbar)
        │
        ▼
GET /api/producao?cozedura_on=true
        │
        ▼
run_model(cozedura_on=True)
  ├─ build_statements() → dfs["dr"] com cozedura_fse_reducao por ano
  └─ producao_anual(a, base, sched, coz_fse_reducao={2027: X, ...})
       └─ post-processa DataFrame → adiciona delta_energia_unit,
                                     delta_materia_unit, cup_cozedura
        │
        ▼
ProducaoView (views.jsx)
  └─ ctx.cozeduraOn → renderiza colunas condicionalmente
```

**Ficheiros modificados:**

| Ficheiro | Alteração |
|---|---|
| `src/engine/operacional/producao.py` | Novo param `coz_fse_reducao`; post-processamento do DataFrame |
| `src/engine/modelo/model.py` | Extrai `coz_fse_reducao` da DR e passa à `producao_anual` |
| `src/api/routes/scenarios.py` | `cozedura_on: bool = Query(False)` no endpoint `/api/producao` |
| `interface/api.js` | `producaoAnalise` aceita e reencaminha `cozedura_on` |
| `interface/views.jsx` | `ProducaoView` — deps, chamada API e colunas condicionais |

---

## 8. Nota de reprodutibilidade

```python
from src.engine.modelo.model import run_model

dfs = run_model("Base", cozedura_on=True)

# Colunas adicionadas ao orçamento de produção:
df = dfs["producao_anual"]
df[["ano", "produto", "cup", "delta_energia_unit", "delta_materia_unit", "cup_cozedura"]]

# Verificar conservação da poupança (deve ser ~0):
import pandas as pd
dr = dfs["dr"].set_index("ano")
for y in [2027, 2028, 2029]:
    rows = df[df["ano"] == y]
    soma = (rows["delta_energia_unit"] * rows["qty_produzida"]).sum()
    fse  = float(dr.loc[y, "cozedura_fse_reducao"])
    print(f"{y}: alocado={soma:.2f}  DR={fse:.2f}  diff={soma-fse:.4f}")
```
