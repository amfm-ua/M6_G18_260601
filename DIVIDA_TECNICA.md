# Dívida Técnica — Motor Financeiro Grestel M6_G18

**Documento de handover** para um desenvolvedor externo que ainda não conhece o projeto.
Data: 2026-05-30 | Entrega académica M6 G18 | Contexto: financiamento, não produto SaaS.

---

## 1. Como ler este documento

O motor **funciona** e produz números corretos para os fins académicos a que se destina.
A prova objetiva está em `tests/test_invariantes_financeiras.py`:

- **Identidade do balanço** (Ativo = Passivo + CP): **7/7 cenários, todos os anos** — PASS.
- **Reconciliação DFC ↔ Balanço**: **7/7 cenários** — PASS (com 7 gaps conhecidos e documentados
  em anos específicos, ver Secção 4).

O código entrega — a dívida é **organizacional** (estrutura, legibilidade, manutenibilidade),
não de correção financeira. Este documento localiza os problemas com ficheiro e zona,
explica *porquê* doem e dá a ordem de ataque pós-entrega. A code review externa
(Grestel code review, 25/100) usou critérios de produto SaaS de produção; as suas
recomendações R1–R8 são válidas mas calibradas para escalabilidade, não para a entrega imediata.

---

## 2. Mapa de pontos confusos (priorizado)

### P1 — Contratos de dados em `dict` crus (`models.py`)

**Ficheiro:** `src/engine/inputs/models.py`

A classe `Assumptions` envolve `raw: dict[str, Any]` com 40+ `@property` e fallbacks `or {}`/`or 0.0`.
Um typo no YAML devolve o valor default em silêncio, sem erro. Exemplo:
```python
@property
def caixa(self) -> dict:
    return self.raw.get("caixa", {})  # key "caxa" retorna {} sem aviso
```

`_flatten_assumptions` em `src/api/schemas.py` (e anteriormente em serializers.py)
espelha manualmente 100+ chaves, criando um segundo ponto de falha silenciosa.

**Porque dói:** regressões invisíveis quando um pressuposto muda de YAML mas o código
usa o default antigo. Difícil de testar sem dados reais.

**Fix pós-entrega:** R1 da review — converter `Assumptions` para modelos Pydantic com
validação de campos obrigatórios. **Nota importante:** o projeto JÁ usa Pydantic v2
(verificado — `ConfigDict`, `Field`, validators modernizados em `validators.py` e na API).
O que falta não é migrar a versão do Pydantic, mas *usar* modelos tipados para os dados
internos do motor.

---

### P2 — Cenários como código hardcoded (`loader.py`)

**Ficheiro:** `src/engine/inputs/loader.py`, linhas 95–412

~300 linhas de overrides por cenário num dict literal `_SCENARIO_OVERRIDES`, mais
`_HUB_SCENARIO_RECALIBRATION` que muta o mesmo dict no import. Para adicionar
um cenário novo é necessário editar Python diretamente.

```python
_SCENARIO_OVERRIDES: dict[str, dict] = {
    "Base": {},
    "Upside": { ... },   # ~40 linhas
    "Stress": { ... },   # ~60 linhas, inclui ramp-up do Hub
    ...
}
# Muta _SCENARIO_OVERRIDES no import:
for _scenario_name, _hub_override in _HUB_SCENARIO_RECALIBRATION.items():
    _SCENARIO_OVERRIDES[_scenario_name] = _deep_update(...)
```

**Porque dói:** um analista financeiro não consegue criar cenários sem tocar em Python.
Manutenção de múltiplos cenários diverge rapidamente. Os cenários 2030-2034 têm lógica
de extensão separada em `extensao_maturidade.py` mas os overrides continuam em código.

**Fix pós-entrega:** R7 — mover overrides para ficheiros YAML em `data/cenarios/`
e carregar com `_yaml_load`. A estrutura `_deep_update` já existe e suporta isso.

---

### P3 — Funções gigantes (build.py, balanco.py, dfc.py)

**Ficheiros:**
- `src/engine/demonstracoes/dr/build.py` — `build_dr()` 200+ linhas
- `src/engine/demonstracoes/balanco.py` — `build_balanco()` 270+ linhas
- `src/engine/demonstracoes/dfc.py` — `build_dfc()` 150+ linhas + helpers
- `src/api/routes/export.py` — `export_excel()` / `export_m3()` 300+ linhas cada

Cada função tem múltiplas responsabilidades misturadas (cálculo, lookup de dados,
transformação, logging de debug). Difícil fazer testes unitários a componentes individuais.

**Porque dói:** qualquer alteração tem risco de efeito colateral não detetado.
A code review classifica como CQ1 + M1.

**Fix pós-entrega:** R3 — extrair subfunções por rubrica (ex: `build_dr_vn()`,
`build_dr_cmvmc()`) e testar cada uma isoladamente.

---

### P4 — Lógica de negócio nas rotas HTTP

**Ficheiros:** `src/api/routes/hub.py`, `src/api/routes/export.py`,
`src/api/routes/valuation.py`

Cálculos financeiros reais (VAL, TIR, rácios de rendibilidade, payback) vivem dentro
dos handlers FastAPI. Exemplo em `hub.py`:

```python
@router.get("/hub/viabilidade")
def get_hub_viability(cenario: str = "Base", ...):
    result = run_model(cenario, hub_on=True, ...)
    # ... 40 linhas de cálculo de VAL/TIR/FCF ...
    return {"val": val, "tir": tir, ...}
```

**Porque dói:** A lógica financeira não é testável sem subir o servidor HTTP.
Também mistura I/O HTTP com regras de negócio (A4 da review).

**Fix pós-entrega:** R3 — extrair para `src/engine/valuation.py` (ou similar),
testar diretamente. As rotas ficam como thin wrappers.

---

### P5 — Saída do motor não tipada (`model.py`)

**Ficheiro:** `src/engine/modelo/model.py`, linha 38

```python
def run_model(...) -> dict[str, pd.DataFrame]:
```

As chaves do dict (`"dr"`, `"balanco"`, `"dfc"`, `"kpis"`, ...) são strings mágicas.
Aceder a uma chave errada devolve `KeyError` em runtime, não em tempo de análise.

**Porque dói:** sem autocompletion, sem type checking, sem documentação automática
das saídas disponíveis (A5 da review).

**Fix pós-entrega:** criar um `dataclass` ou `TypedDict`:
```python
@dataclass
class ModelResult:
    dr: pd.DataFrame
    balanco: pd.DataFrame
    dfc: pd.DataFrame
    kpis: pd.DataFrame | None = None
    ...
```

---

### P6 — Números mágicos dispersos

**Ficheiros:** `src/engine/demonstracoes/balanco.py`, `src/engine/demonstracoes/dr/impostos.py`,
`src/engine/modelo/kpis.py`

Taxas fiscais, percentagens e thresholds hardcoded em múltiplos sítios:
```python
# em balanco.py
taxa_irc_base = float(a.impostos.get("IRC_taxa_geral", 0.20))
# em kpis.py (independente):
irc_rate = a.raw.get("impostos", {}).get("IRC_taxa_geral", 0.21)  # default diferente!
```

**Porque dói:** uma alteração fiscal (ex: OE para 2027) exige alterar múltiplos ficheiros.
O risco de defaults divergentes já existe (0.20 vs 0.21 acima). CQ3 da review.

**Fix pós-entrega:** centralizar todas as taxas num único lugar (já existe `a.impostos`
— garantir que é a única fonte de verdade).

---

### P7 — Tratamento de erros inconsistente + validators mortos

**Ficheiros:**
- `src/engine/inputs/validators.py` — modelos Pydantic definidos mas nunca instanciados
  pelo loader (o loader usa `Assumptions(raw=data)` diretamente)
- `src/engine/modelo/model.py` — 15 blocos `except Exception: logger.warning("falhou"); df = empty`
- API — mistura de `raise HTTPException`, `return None`, e `logger.error` sem padrão

Os `except` em `model.py` cobrem tabelas **auxiliares** (FSE mensal, pessoal detalhe,
produção mensal), não o core DR/Balanço/DFC. **Confirmado que zero warnings "falhou"
aparecem nos logs em execução normal** (verificar com `run_model` antes da entrega).
Mas se aparecerem, a tabela vai vazia para o relatório/UI sem aviso ao utilizador.

**Porque dói:** CQ2 + CQ4 da review. Falhas silenciosas são difíceis de debugar em produção.

**Fix pós-entrega:** R6 — endurecer os `except` de tabelas auxiliares para `raise` em modo
de desenvolvimento; só silenciar em produção com flag explícito. Ligar `validators.py`
ao loader ou remover.

---

### P8 — Gaps de reconciliação DFC ↔ Balanço em anos específicos

**Ficheiros:** `src/engine/demonstracoes/dfc.py`, `src/engine/demonstracoes/balanco.py`

**Causa identificada:** o `dynamic_payout` em `dfc.py` calcula o payout ratio usando
o endividamento do ano **corrente** (`row_y`), enquanto `balanco.py` calcula o RT
com uma fórmula de payout ligeiramente diferente (usa estado do ano anterior em certos
parâmetros). A divergência gera um gap no fluxo de caixa de dividendos:

| Cenário      | Anos com gap | Delta (€)  |
|--------------|-------------|------------|
| Base         | 2026        | ~64 k      |
| Upside       | 2026, 2029  | ~93k, ~90k |
| Downside     | 2026        | ~18 k      |
| OE5          | 2026        | ~63 k      |
| Tarifa_EUA   | 2026        | ~64 k      |
| Hub_Ativo    | 2026        | ~98 k      |
| Stress       | —           | 0 (OK)     |

Stress não é afetado porque o payout_min é constante em ambas as fórmulas sob stress.
O balanço **fecha** em todos os anos (identidade Ativo = Passivo + CP verificada).
O gap afeta apenas a *reconciliação formal* entre DFC e Balanço — os números do
relatório (VAL, TIR, cash flows de avaliação) não são afetados.

**Prova:** `tests/test_invariantes_financeiras.py` — 14/14 PASS com warnings.

**Fix pós-entrega:** unificar a lógica de payout numa única função partilhada entre
`dfc.py` e `balanco.py`, ou fazer a DFC ler o payout_ratio diretamente do RT do Balanço
(eliminar o recalculo).

---

### P9 — Linhas duplicadas 2030-2034 nos DataFrames

**Ficheiro:** `src/engine/demonstracoes/statements.py` + `extensao_maturidade.py`

`build_dfc` e `build_balanco` cobrem `ALL_YEARS = [2024..2034]` (porque `ANO_FIM=2034`
foi alargado de 2029 para 2034). `estender_maturidade` depois **anexa** outra versão
de 2030-2034 (roll-forward de estado estacionário). O resultado são DataFrames com
linhas duplicadas para 2030-2034.

O balanço fecha nos dois conjuntos de linhas (controlo ≈ 0 em ambos), logo o impacto
sobre os cálculos de avaliação é mínimo. A DFC da segunda versão (extensão) reconcilia
correctamente; a primeira não (usa dados do balanço base, não do roll-forward).

O teste `test_invariantes_financeiras.py` deduplica com `drop_duplicates(keep='last')`
para usar a versão canónica.

**Fix pós-entrega:** quando `horizonte_maturidade=True`, a `build_dfc` (e `build_balanco`)
deve cobrir apenas `[2024..2029]` e `estender_maturidade` estende para 2034. Alternativa
mais simples: `estender_maturidade` substitui (não anexa) as linhas 2030-2034.

---

### P10 — Frontend monolítico sem build

**Ficheiro:** `src/frontend/` (JSX via Babel-standalone, sem bundler)

O frontend usa Babel para transpilar JSX no browser em runtime. Sem build step,
sem tree-shaking, sem hot reload. A bundle do Babel-standalone (~900 KB) é carregada
em cada visita. Difícil de escalar ou testar.

**Porque dói:** M2 + R5 da review. Performance em produção, impossibilidade de testes
unitários a componentes React.

**Fix pós-entrega:** R5 — migrar para Vite + React com hot reload. É uma reescrita
do frontend (não do motor), independente dos outros fixes.

---

### P11 — Ficheiro com nome unicode

**Ficheiro:** `src/engine/operacional/produção.py`

O nome do ficheiro contém `ç` (Unicode), o que pode causar problemas em sistemas
Windows com locale não-UTF-8 ou em ferramentas que não suportam Unicode em paths.
CQ5 da review.

**Fix pós-entrega:** renomear para `producao.py` e atualizar todos os imports.

---

## 3. Fora de âmbito da entrega (explicitamente NÃO fazer agora)

- **Segurança** (S1-S4 da review): sem autenticação, sem HTTPS, credenciais em env vars.
  Não relevante para um protótipo académico local.
- **Versionamento de API** (M3): sem `/v1/`, sem deprecation notices.
- **Caching de resultados** (R8): `run_model` é chamado a cada request sem cache.
- **Reescrita do frontend** (R5): JSX funciona para demonstração.
- **CI/CD, Docker, deploy** (M4, M5): fora do âmbito académico.

---

## 4. Roadmap de correção pós-entrega

Ordenado por impacto/esforço. Cada item desbloqueia o seguinte.

| Prioridade | Ref  | Ação                                              | Esforço |
|-----------|------|---------------------------------------------------|---------|
| **P0**    | R1   | Converter `Assumptions` para Pydantic tipado      | 2–3 dias|
| **P1**    | P8   | Unificar lógica de payout DFC ↔ Balanço           | 1 dia   |
| **P1**    | P9   | Corrigir duplicação 2030-2034 nos DataFrames      | 0.5 dia |
| **P2**    | R3   | Extrair lógica financeira das rotas HTTP          | 3–4 dias|
| **P2**    | R6   | Endurecer tratamento de erros + ligar validators  | 1 dia   |
| **P3**    | R7   | Cenários em YAML (não código)                     | 1–2 dias|
| **P4**    | R2   | Refactor funções gigantes em subfunções           | 3 dias  |
| **P5**    | R5   | Migrar frontend para Vite + React                 | 5+ dias |

**Nota:** R1 (P0) é pré-requisito de quase tudo — com modelos Pydantic tipados,
muitos dos outros problemas (P6, P7) ficam automaticamente detetados em CI.

---

## 5. Estado já tratado (para o próximo dev não repetir)

- **Pydantic v2** já instalado e em uso. A review menciona "migrar para Pydantic v2"
  como R1, mas a versão já é v2. O que falta é *usar* modelos tipados para os dados
  internos — não migrar versão.
- **`validators.py`** já modernizado com `ConfigDict`, `model_validator`, `field_validator`
  (sintaxe Pydantic v2 correcta).
- **Schemas da API** já usam `BaseModel` Pydantic para request/response.
- **Reconciliação DFC pós-correção** (ver `docs/reconciliacao_dfc_correcao.md`):
  o tratamento de imparidades em base bruta, IDA dinâmico e rend_equiv_patrimonial
  foi corrigido e documentado. O gap residual (P8) é diferente e menor.

---

## Anexo — Referência à code review externa

O ficheiro original da review (`grestel-code-review-findings.json`) contém 8
recomendações (R1-R8), 5 alertas de qualidade (CQ1-CQ5), 4 de segurança (S1-S4)
e 5 de manutenibilidade (M1-M5). Este documento cobre os mesmos pontos com
contexto do projeto. Onde a review diverge da realidade (ex: "sem Pydantic v2"),
prevalece o estado actual do código.
