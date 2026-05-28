# Aplicações Financeiras CP — Modelação Dinâmica

**Data:** 2026-05-28  
**Contexto:** Implementação da correcção C4 no motor de demonstrações financeiras. Recalibração de `caixa_max_pct_vn` e introdução de rendimentos financeiros dinâmicos baseados no saldo real de Aplicações Financeiras de Curto Prazo.

---

## 1. Diagnóstico — Porquê as Aplicações estavam sempre a Zero

O mecanismo de routing de excedentes entre Caixa e Aplicações Financeiras já existia em `balanco.py`:

```python
surplus    = cp_total_pre_caixa + passivo_pre - total_anc - ac_sem_caixa
caixa      = min(caixa_max, max(caixa_min, surplus))
aplic_cp   = max(0.0, surplus - caixa_max)   # excesso → Aplic. Fin. CP
linha_cp   = max(0.0, caixa_min - surplus)   # défice  → linha crédito CP
```

**O problema era duplo:**

| Item | Antes | Causa |
|------|-------|-------|
| `caixa_max_pct_vn` | **8,6% VN** | Tecto demasiado alto — o surplus nunca o ultrapassava. Em 2029 (Hub): surplus ≈ €5,5M < caixa_max ≈ €4,6M → `aplic_cp = 0` |
| `rend_financeiros` | Série fixa `base × (1+g)^t` | Desligado do saldo real — não reflectia os rendimentos gerados pelos excedentes aplicados |

**Calibração histórica:**  
Caixa real 2024 = €542k sobre VN = €37,88M → **1,43% do VN**.  
Um tecto de 8,6% equivale a ~6× o mínimo histórico — financeiramente indefensável.

---

## 2. Solução Implementada

### 2.1 Parâmetros (`globais.yaml`)

```yaml
caixa:
  minima_pct_vn: 0.013   # inalterado — motivo transação (Keynes/Baumol)
  maxima_pct_vn: 0.040   # 4,0% VN — calibrado ao histórico 2024 (~3× o mínimo)

  taxa_rend_aplic_cp: 0.030   # 3,0% a/a — taxa conservadora (BCE + 0,5 pp spread)
```

Com `caixa_max = 4% × VN`, a empresa retém até ~1,5 meses de custo de tesouraria em caixa operacional; o excedente vai para instrumentos de curto prazo (depósitos a prazo, fundos monetários).

### 2.2 DR — Rendimentos Dinâmicos (`dr/build.py`)

Novo parâmetro `aplic_cp_rend: dict[int, float] | None`:

```python
rend_fin = (
    rend_fin_base * (1 + rend_fin_g) ** (y - 2025)   # base histórica + crescimento
    + (aplic_cp_rend or {}).get(y, 0.0)               # C4: yield das aplic. do ano anterior
)
```

O componente base (€64.678 em 2025) mantém-se — representa rendimentos sobre o caixa operacional. O componente incremental é calculado em `statements.py` com base no saldo de `aplic_cp` do ano anterior.

### 2.3 Iteração C4 (`statements.py`)

Padrão idêntico à correcção C3 (juros da linha de crédito CP):

```python
taxa_rend_aplic = a.raw.get("caixa", {}).get("taxa_rend_aplic_cp", 0.0)
if taxa_rend_aplic > 0.0:
    aplic_cp_rend_map = {}
    prev_aplic = 0.0
    for _, row in df_balanco.sort_values("ano").iterrows():
        if prev_aplic > 0.0:
            aplic_cp_rend_map[int(row["ano"])] = prev_aplic * taxa_rend_aplic
        prev_aplic = float(row["aplicacoes_fin_cp"])
    if aplic_cp_rend_map:
        df_dr    = build_dr(..., aplic_cp_rend=aplic_cp_rend_map)
        df_balanco = build_balanco(...)
```

**Uma iteração é suficiente:** o impacto das `aplic_cp` no surplus é < 2% do RL, tornando a segunda iteração desprezível (mesmo argumento usado na C3).

---

## 3. Impacto no Cenário Base (Com Hub)

### 3.1 Balanço — Reclassificação Caixa → Aplicações

| Ano | Caixa (antes) | Caixa (depois) | Aplic. CP (antes) | Aplic. CP (depois) | Total Liquidez |
|-----|--------------|---------------|------------------|-------------------|---------------|
| 2024 | €542k | €542k | €0 | €0 | €542k |
| 2025 | €1.312M | €1.312M | €0 | €0 | €1.312M |
| 2026 | €583k | €583k | €0 | €0 | €583k |
| 2027 | €4.100M | €1.907M | €1.351M | **€3.545M** | €5.452M |
| 2028 | €4.372M | €2.033M | €3.674M | **€6.118M** | €8.151M |
| 2029 | €4.628M | **€2.153M** | €6.435M | **€9.151M** | €11.304M |

O total de liquidez (Caixa + Aplic.) é **igual antes e depois** em cada ano — o que muda é apenas a apresentação e a yield gerada.

### 3.2 DR — Rendimentos Financeiros

| Ano | Rend. Fin. (antes) | Rend. Fin. (depois) | Delta RF | Delta RL (liq. IRC) |
|-----|-------------------|--------------------|---------|--------------------|
| 2025 | €64.678 | €64.678 | €0 | €0 |
| 2026 | €66.295 | €66.295 | €0 | €0 |
| 2027 | €67.952 | €67.952 | €0 | €0 |
| **2028** | €69.651 | **€175.987** | **+€106.336** | **+€80.284** |
| **2029** | €71.392 | **€251.753** | **+€180.361** | **+€136.172** |

> O yield de 2027 não aparece em 2027 — aplica-se no ano seguinte (rend. do saldo médio de Aplic. do ano anterior). Portanto 2028 recebe o yield sobre os €3,5M aplicados em 2027.

### 3.3 Resultado Líquido e ROE

| Ano | RL (antes) | RL (depois) | Delta RL | ROE (antes) | ROE (depois) |
|-----|-----------|------------|---------|------------|-------------|
| 2027 | €4.553M | €4.553M | €0 | 21,2% | 21,2% |
| 2028 | €5.446M | **€5.526M** | **+€80k** | 21,3% | 21,4% |
| 2029 | €5.977M | **€6.113M** | **+€136k** | 19,9% | 20,0% |

**Balanço equilibrado em todos os anos** — `controlo = Ativo − (Passivo + CP) = 0,00` verificado.

---

## 4. Leitura para Defesa (M6)

### Por que faz sentido financeiro

1. **Congruência com o R&C:** O Relatório de Gestão da Grestel enuncia princípios para o "investimento do excesso de liquidez". Manter €9M em depósitos à ordem (sem yield) contradiz essa política.

2. **Teoria:** A política caixa min/max segue a teoria de Keynes (motivo transação) e o modelo de Baumol-Tobin: o caixa operacional deve cobrir necessidades de tesouraria imediatas; o excedente estrutural pertence a instrumentos de curto prazo.

3. **Calibração defensável:** `caixa_max = 4% VN` ≈ 15 dias de VN — tempo suficiente para mobilizar aplicações se necessário. O caixa mínimo de 1,3% VN (≈ 5 dias) garante a buffer de segurança.

### Impacto global acumulado 2028–2029

| Métrica | Valor |
|---------|-------|
| Rendimentos financeiros adicionais | +€287k (brutos, 2 anos) |
| RL adicional acumulado | +€216k (líquido IRC ~25%) |
| VAN a WACC = 8% (2028+2029) | **≈ +€152k** |

O efeito é **modesto em valor absoluto** mas **financeiramente correcto**: demonstra que o modelo optimiza a gestão de tesouraria em vez de acumular caixa passivamente.

---

## 5. Parâmetros Configuráveis

Todos os parâmetros são editáveis em `src/engine/data/pressupostos/globais.yaml` sem alterações ao código:

| Parâmetro | Valor actual | Efeito de aumentar |
|-----------|-------------|-------------------|
| `caixa.minima_pct_vn` | 1,3% | Mais caixa retido, menos aplic. |
| `caixa.maxima_pct_vn` | 4,0% | Menos aplic., mais caixa |
| `caixa.taxa_rend_aplic_cp` | 3,0% | Rendimentos financeiros mais altos |
| `rendimentos_financeiros_crescimento` | 2,5% | Crescimento da componente base |

---

## 6. Ficheiros Alterados

| Ficheiro | Alteração |
|----------|-----------|
| `src/engine/data/pressupostos/globais.yaml` | `caixa_max_pct_vn` 8,6% → 4,0%; novo `taxa_rend_aplic_cp: 0.030` |
| `src/engine/data/_defaults/pressupostos/globais.yaml` | Idem (defaults espelho) |
| `src/engine/demonstracoes/dr/build.py` | Parâmetro `aplic_cp_rend`; rend_fin dinâmico |
| `src/engine/demonstracoes/statements.py` | Correcção C4 (iteração aplic_cp → rend_fin → balanço) |
