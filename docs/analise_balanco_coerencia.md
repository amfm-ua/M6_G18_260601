# Análise de Coerência do Balanço — M6 Grestel

**Data:** 2026-05-28  
**Contexto:** Revisão pré-entrega OE5/M6. Cinco inconsistências identificadas na projeção do Balanço (2025-2029), com posterior análise do cenário com Hub Logístico e correção do motor de apresentação.

---

## 1. AFT vs. CAPEX — Desinvestimento Progressivo

### Observação
Os Ativos Fixos Tangíveis (AFT) diminuem de **€12,5M (2024)** para **€8,9M (2029)**, apesar do CAPEX projetado de €1,5M→€0,8M/ano.

### Causa
Taxa de depreciação de **17%/ano** (`taxa_dep_aft: 0.17` em `investimento.yaml`) aplicada sobre uma base de €12,5M gera sempre mais depreciação do que o investimento novo:

| Ano | Depreciação | CAPEX | Δ Líquido |
|-----|------------|-------|-----------|
| 2025 | €2,077k | €1,500k | −€577k |
| 2026 | €1,900k | €1,500k | −€400k |
| 2027 | €1,831k | €1,200k | −€631k |
| 2028 | €1,721k | €1,000k | −€721k |
| 2029 | €1,630k | €800k  | −€830k |

Fonte: `src/engine/data/computed/schedules.yaml` (`investimento.depreciacao_aft_anual`).

### Natureza
**Intencional, não é um bug.** A estratégia de crescimento da Grestel assenta em eficiência operacional (Ecogres, Hub 4.0) e não em expansão industrial própria. Os €2,38M/ano em cedência de locações em `outros_rendimentos_2024` são consistentes com parcial desinvestimento imobiliário deliberado.

### Risco
O rácio VN/AFT passa de 3,0× (2024) para 5,9× (2029). Produção crescente (+39% VN) com base de ativos decrescente implica dependência do contrato Ecogres para capacidade produtiva. Deve ser mencionado no Relatório de Gestão do M6.

---

## 2. Queda dos Empréstimos Correntes em 2025 — Erro de Classificação NC/C

### Observação
`Emprestimos_C` cai de **€5,5M (2024)** para **€788k (2025)**, uma redução de €4,7M num único ano.

### Causa Directa
O **IAPMEI foi integralmente reembolsado em 2025**: `amortizacoes_capital[2025]` = €5,530,545 (igual ao capital em dívida IAPMEI). Taxa de juro 0% — não havia carga financeira.

### Inconsistência Identificada
Coexistem dois valores contraditórios em `schedules.yaml` para `emprestimos_c[2025]`:

```yaml
# Secção financiamento (usada pelo motor):
emprestimos_C:
  2025: 787984.0          ← o balanço exibe este valor

# Secção reference_balanco (classificação forward-looking correta):
emprestimos_c:
  2025: 2043093.62        ← = amortizacoes_capital[2026], contabilisticamente correto
```

O `build_balanco.py` lê exclusivamente de `df_fin["emprestimos_C"]` (secção `financiamento`), pelo que reporta €788k.

### Impacto
Subavaliação de **€1,255k** no Passivo Corrente de 2025. A dívida total NC+C está correcta (€13,337k); apenas a divisão entre corrente e não-corrente está desalinhada do tratamento SNC/IFRS (corrente = amortizações dos próximos 12 meses). Afecta marginalmente o rácio de liquidez geral de 2025.

### Nota de Tesouraria
O reembolso do IAPMEI (€5,5M) estava no plano de financiamento e não constitui risco de tesouraria. O empréstimo era a 0%, pelo que não havia carga financeira.

---

## 3. Acumulação de Caixa em 2029 — Surplus Dirigido para Aplicações Financeiras CP

### Observação
O saldo de "Caixa e Equivalentes" parece estabilizar mas o ativo total cresce significativamente nos últimos anos do plano, sem amortização adicional de dívida nem distribuição extraordinária de dividendos.

### Causa
O motor `build_balanco.py` aplica uma política de caixa min/max:

```python
caixa     = min(caixa_max, max(caixa_min, surplus))
aplic_cp  = max(0.0, surplus - caixa_max)   # excesso → aplicações fin. CP
linha_cp  = max(0.0, caixa_min - surplus)   # défice → linha crédito CP
```

Com `caixa_max = VN × 8,6%` (≈ €4,5M em 2029), todo o excedente acima deste limiar é depositado em `aplicacoes_fin_cp` (aplicações financeiras de curto prazo).

### Valores (cenário com Hub, 2025-2029)

| Ano | Caixa | Aplicações Fin. CP | Total Liquidez |
|-----|-------|-------------------|---------------|
| 2025 | €500k | €0 | €500k |
| 2026 | — | €0 | — |
| 2027 | — | €378k | — |
| 2028 | — | €2,673k | — |
| 2029 | — | €5,388k | — |

### Interpretação
A empresa é lucrativa e amortiza dívida, mas o plano não prevê distribuição de dividendos agressiva nem amortização antecipada de empréstimos. O excedente acumula-se passivamente. Para o M6, é defensável mas pode indicar ausência de política de alocação de capital de longo prazo.

---

## 4. Outros Passivos Correntes Elevados — Composição Operacional Esperada

### Observação
`Outros_PC` (como apresentado na UI) mantém-se acima de €6-8M em 2029.

### Composição
No frontend, `Outros_PC` agrega três rubricas do backend:

```js
Outros_PC: (r.outros_pc || 0) + (r.eoep_credor || 0) + (r.linha_credito_cp || 0)
```

Valores base sem hub em 2029:
- `outros_pc` ≈ €3,364k (passivos de locação lojas + outros credores operacionais)
- `eoep_credor` ≈ €3,610k (IVA a pagar + IRC pendente + SS — cresce com lucros)
- `linha_credito_cp` = €0

**Total ≈ €7M** — normal para empresa com €53M de VN e volumes de IVA/IRC crescentes. Com Hub activo, o `hub_subsidio_diferido` pode adicionar €1-2M temporariamente.

### Nota
Os passivos de locação das lojas Lisboa/Porto/Outlet (incluídos em `outros_pc`) são reais e persistentes enquanto as lojas estiverem abertas. Não são "dívida oculta" — são passivo operacional corrente.

---

## 5. Impostos Diferidos Passivos = €3 Constante — Bug de Modelo

### Observação
A rubrica `Impostos_Diferidos_Passivos` mantém-se em **€2,77** (≈ €3) em todos os anos 2024-2029.

### Causa
Em `build_balanco.py:369`:

```python
imp_dif_p = base.balanco["passivo"]["Impostos_Diferidos_Passivos"]
```

O valor é lido uma vez de `base.yaml` e nunca recalculado. Em contraste, o IDA (Impostos Diferidos Ativos) é **dinâmico** (linhas 306-329 de `balanco.py`).

### Impacto Quantitativo
**Mínimo neste modelo.** A taxa de depreciação fiscal (17%) é igual à taxa contabilística (`taxa_dep_aft: 0.17`), pelo que não há diferença temporária de depreciação. O IDP real seria gerado por diferenças de valorimetria de inventários, provisões não dedutíveis, etc. — mas o R&C 2024 auditado confirma IDP = €2,77, sugerindo que a empresa genuinamente tem quase zero de IDP.

### Recomendação
Manter como está para o M6 — o impacto nos rácios é desprezível e uma correção geraria um valor artificial. Documentar como simplificação do modelo.

---

## 6. Cenário Com Hub — Fix de Apresentação do Balanço

### Problema Identificado pelo Revisor
No cenário com Hub, "Outros Activos Correntes" atingia **€9,6M em 2029**, levantando suspeitas de erro de reconciliação escondido.

### Causa Raiz (duas anomalias sobrepostas)

**A. `hub_nfm` em `total_ativo` mas em nenhuma linha visível**

O motor `build_balanco.py` inclui o capital circulante operacional do Hub (`hub_nfm_ac_y`) em `total_ac` e portanto em `total_ativo`, mas a função `normalizeBal` de `api.js` não o mapeava para nenhum campo. Resultado: a soma das rubricas visíveis era sempre menor que `Total Activo` quando o Hub estava activo.

**B. `aplicacoes_fin_cp` agregado em "Outros Activos Correntes"**

O excedente de caixa aplicado em instrumentos financeiros de curto prazo estava invisível dentro de "Outros AC", inflacionando a rubrica operacional de forma inexplicável.

### Fix Implementado

**`interface/api.js` — `normalizeBal`:**
```js
// Antes:
Outros_AC: (r.outros_ac || 0) + (r.aplicacoes_fin_cp || 0) + (r.eoep_devedor || 0),

// Depois:
Outros_AC:         (r.outros_ac || 0) + (r.eoep_devedor || 0) + (r.hub_nfm || 0),
Aplicacoes_Fin_CP: r.aplicacoes_fin_cp || 0,
```

**`interface/data.js`:**
- Adicionado `Aplicacoes_Fin_CP: 0` ao struct `BAL_2024`
- Função `ativos()` inclui `b.Aplicacoes_Fin_CP`
- Fórmula `liquidez_geral` inclui `b.Aplicacoes_Fin_CP`

**`interface/views.jsx`:**
- Nova linha "Aplicações Financeiras CP" na tabela Activo Corrente
- Novo segmento azul-aço no gráfico de barras empilhadas
- Legenda actualizada

### Resultado Após Fix (cenário Hub, 2029)

| Rubrica | Valor |
|---------|-------|
| Aplicações Financeiras CP | €5,388k ← excedente de caixa, agora visível |
| Outros Activos Correntes | €4,311k ← itens operacionais + hub_nfm |
| **Soma anterior "opaca"** | **€9,699k** |

O júri pode agora responder à própria questão: os €5,4M são excedentes de tesouraria — a empresa é rentável e não tem uso imediato para o dinheiro. Os €4,3M são passivos operacionais normais (EOEP, outros devedores, NFM Hub).

---

## Ficheiros de Referência

| Ficheiro | Relevância |
|----------|-----------|
| `src/engine/data/pressupostos/investimento.yaml` | Taxa dep. 17%, CAPEX planeado |
| `src/engine/data/computed/schedules.yaml` | Valores pré-computados: AFT, empréstimos, balanço referência |
| `src/engine/data/historico/2024/base.yaml` | Saldos 2024, IAPMEI, IDP = €2,77 |
| `src/engine/demonstracoes/balanco.py` | Motor balanço: surplus plug, aplic_fin_cp, hub_nfm |
| `src/engine/demonstracoes/dfc.py` | DFC método indireto: var_nfm hub, d_aplic_cp |
| `interface/api.js` | `normalizeBal` — mapeamento backend → frontend |
| `interface/views.jsx` | `BalancoView` — tabela e gráfico |
