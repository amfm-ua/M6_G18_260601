# Spec de implementação futura — Coluna analítica "CUP c/ cozedura" na vista de Produção

> **Estado:** por implementar. Este ficheiro é um *prompt auto-contido* — uma sessão futura deve conseguir
> implementar a partir daqui sem o histórico de conversa. Escrito em pt-PT.

## 1. Objetivo

Adicionar à vista **Orçamento de Produção** (tabela "detalhe completo por produto") uma representação
**analítica e ilustrativa** do efeito da **Cozedura de Baixa Temperatura** no custo unitário:

- Uma coluna **`CUP c/ cozedura`** (custo industrial unitário ajustado), e/ou
- Um delta **`Δ energia €/peça`** (poupança de energia de cozedura por unidade).

Deve aparecer **apenas quando o toggle `cozedura_on` está ativo**.

## 2. Porque é que esta coluna é necessária (contexto do modelo — LER PRIMEIRO)

Decisão de modelação já tomada e validada (não alterar sem motivo forte):

- A **energia de cozedura** (Gás + Eletricidade) é contabilizada nas **FSE**, segundo a apresentação **SNC**
  da DR auditada de 2024 — **não** no CMVMC.
- O toggle `cozedura_on` **já desconta** a poupança diretamente das FSE:
  `redução_y = ramp_y × 18% × (Gás×100% + Eletricidade×50%)`
  (ver `src/engine/projetos/cozedura/impacto.py::cozedura_fse_reducao` e a injeção em
  `src/engine/demonstracoes/dr/build.py`). **É aqui que o efeito real no EBITDA acontece.**
- O **CUP** mostrado na tabela de produção = **custo industrial completo** = `MPSC + MOD + GGF`
  (ver docstring em `src/engine/operacional/producao.py:151-156`). É **puramente analítico/absorção total**.
- O **CMVMC da DR usa APENAS a fatia MPSC** (`cup = cips[p] × mp_pct[p] × factor` em
  `src/engine/operacional/cmvmc.py:136`). A energia (dentro do GGF) **não flui** para o CMVMC/EBITDA.

### Conclusão crítica (evitar double counting)

- **NÃO** fazer a coluna alimentar a DR/CMVMC/EBITDA. A poupança de energia já saiu **uma vez** pelas FSE;
  se também saísse pelo custo de produto, seria **double counting**.
- A coluna é **display-only**: vive na `producao_anual` (que é tabela de análise, não entra na DR) ou é
  derivada no frontend. **Nunca** mexer em `cmvmc_anual`, `build.py` da DR, ou no EBITDA.

## 3. Cálculo proposto

Efeito **líquido** por unidade = poupança de energia (−) menos incremento de matéria (volastonite) (+),
para ser honesto (as "duas pernas" do cenário):

```
Δ_energia_unit_p_y   = saving_energia_p_y / qty_produzida_p_y          # negativo no CUP (poupança)
Δ_materia_unit_p_y   = (ramp_y × cmvmc_incremento_pct × MPSC_unit_p_y) # positivo no CUP (volastonite)
CUP_cozedura_p_y     = CUP_p_y − Δ_energia_unit_p_y + Δ_materia_unit_p_y
```

### Alocação da poupança de energia por produto (`saving_energia_p_y`)

Total anual disponível = `cozedura_fse_reducao[y]` (já existe na DR / no módulo impacto).
Distribuir pelos produtos por **intensidade de cozedura**:

```
peso_p = (qty_produzida_p_y × intensidade_energia_p) / Σ_p (qty_produzida_p_y × intensidade_energia_p)
saving_energia_p_y = cozedura_fse_reducao[y] × peso_p
```

- **Opção B (recomendada):** `intensidade_energia_p` lida de `produtos.yaml`
  (`families[p].estrutura_custos.energia_intensidade`, ou proxy = fração GGF, ou = CIP unitário como proxy de massa/complexidade).
- **Opção A (fallback simples):** `intensidade_energia_p = 1` para todos → poupança uniforme €/peça
  = `cozedura_fse_reducao[y] / Σ qty_produzida_y`.

> Documentar claramente a premissa de alocação escolhida (é ilustrativa; a tese reporta 18% por ciclo,
> não por produto). `MPSC_unit_p_y = cips[p] × mp_pct[p] × factor[y]`.

## 4. Ficheiros a alterar

### Backend
1. **`src/engine/operacional/producao.py`** — em `producao_anual(...)`, aceitar a info de cozedura
   (passar `coz` dict + `fse_reducao` por ano, ou recalcular via `projetos.cozedura.impacto`).
   Quando ativo, acrescentar colunas ao DataFrame: `cup_cozedura`, `delta_energia_unit`, `delta_materia_unit`.
   Quando inativo, colunas ausentes ou iguais ao `cup`.
   - Reutilizar `cozedura_fse_reducao(coz, fse_det_by_year)` e `cozedura_cmvmc_incremento` de
     `src/engine/projetos/cozedura/impacto.py`.
   - Garantir invariância: com `cozedura_on=False`, `producao_anual` fica **byte-idêntico** ao atual.
2. **`src/engine/modelo/model.py`** — `run_model` já corre com `cozedura_on`; assegurar que `producao_anual`
   recebe os pressupostos de cozedura quando `cozedura_on=True` (passar `a.raw["cozedura_baixa_temp"]`).
3. **`src/api/routes/scenarios.py`** — `get_producao(...)`: adicionar `cozedura_on: bool = Query(False)` e
   passar a `run_model(..., cozedura_on=cozedura_on)`. (Mesmo padrão já aplicado em `/api/run` e `/api/smart/tracker`.)

### Frontend
4. **`interface/api.js`** — a função que chama `/api/producao` (procurar `producao`/`producaoAnalise`):
   aceitar `cozedura_on` e juntá-lo aos query params (`String(cozedura_on)`).
5. **`interface/views.jsx`** — `ProducaoView`: ler `ctx.cozeduraOn`, passá-lo na chamada à API e adicionar
   dep no `useEffect`/`useMemo`. Renderizar a coluna **`CUP c/ cozedura`** (e opcional `Δ energia €/peça`)
   **só quando `ctx.cozeduraOn`** for `true`. Formatar a €/un. com 2 casas (estilo das colunas PVU/CUP existentes).
   - Rotular a coluna como **ilustrativa** (tooltip: "vista analítica de absorção total; a poupança de energia
     já está refletida nas FSE/EBITDA — não é somada duas vezes").

> Nota: `ctx.cozeduraOn` já existe (foi adicionado no toggle da topbar — `interface/app.jsx`).

## 5. Validações obrigatórias (replicar abordagem anterior)

- **Regressão:** `cozedura_on=False` → `producao_anual` idêntico ao atual (sem colunas novas, ou colunas == cup).
- **Sem double counting:** confirmar que EBITDA/CMVMC/DR **não mudam** ao adicionar as colunas
  (o efeito no EBITDA continua a vir só das FSE). Testar via Python:
  ```python
  from src.engine.modelo.model import run_model
  a = run_model("Base", cozedura_on=True)
  # EBITDA/CMVMC devem ser iguais antes e depois desta feature; só producao_anual ganha colunas.
  ```
- **Coerência de soma:** `Σ_p (saving_energia_p_y × qty?) ` — confirmar que a poupança alocada por produto
  soma ao total `cozedura_fse_reducao[y]` (a alocação é uma repartição, não uma criação de valor).
- **Faseamento:** colunas refletem o `ramp_up` (2027 ⅓ / 2028 ⅔ / 2029 pleno); em 2025-2026 o delta é 0.
- **Browser:** testar em Chrome (servidor com `--reload` no porto 8000; toggle Cozedura BT on/off; ver a
  coluna aparecer/desaparecer e os valores de CUP c/ cozedura < CUP base nos anos 2027-2029).

## 6. Ambiente / como correr (referência)

- Python do venv: `C:\Users\amfmn\AppData\Local\venvs\GrestelPy_G18\Scripts\python.exe`
  (pip/pytest indisponíveis no venv — validar com scripts `python -c "..."`).
- Servidor: já corre com `uvicorn server:app --reload --port 8000` (auto-reload do backend).
- Interface: `http://localhost:8000/interface/` (ficheiros JSX servidos estaticamente; reload do browser chega).
- `interface/api.js` tem `BACKEND_URL = "http://localhost:8000"`.

## 7. Decisão em aberto para o utilizador

Escolher a granularidade da coluna:
- (a) só **`CUP c/ cozedura`** (efeito líquido das duas pernas), ou
- (b) **`CUP c/ cozedura` + `Δ energia €/peça`** (mostra a perna de energia isolada — mais pedagógico), ou
- (c) acrescentar também `Δ volastonite €/peça` (as duas pernas visíveis em separado).

Recomendado: **(b)** — mostra a poupança de energia ao nível do produto (que era a dúvida original) sem
esconder que é líquida da volastonite, e deixa explícito que **não** há double counting com as FSE.
