# Extensão dos Cash Flows do Hub a 10 Anos (2030–2034) — Estado Atual

> Atualizado: 2026-05-28 · Módulo: `src/engine/projetos/hub_logistico/viabilidade.py`

## 1. Contexto e decisão

A avaliação do Hub Logístico exige **10 anos de fluxos de caixa (2025–2034)**,
correspondentes à vida útil do projeto. O motor financeiro core da Grestel,
porém, só projeta as demonstrações até **2029** (`ANO_FIM = 2029` em
`src/engine/config.py`). Os anos **2030–2034** são, por isso, obtidos por
**extrapolação** dentro de `viabilidade_hub()`, e o projeto é fechado com um
**valor terminal** em 2035.

**Decisão tomada (validada com a docente):** manter a abordagem por extrapolação
do EBITDA + valor terminal. A docente reconheceu que o "correto" em rigor teórico
seria estender o motor completo (DR + Balanço + DFC) até 2034, mas aceitou a
extrapolação como suficiente para o entregável. A extensão integral do motor fica
**em aberto como trabalho futuro** (ver §5).

## 2. Como está montada a estrutura

```
2025 ─────────── 2029 ─────────── 2034 ─── 2035
│                 │                 │         │
├─ FCF derivado do motor (real) ────┤         │
│  EBIT, depreciações, NFM, RFAI    │         │
│                 ├─ FCF extrapolado ┤         │
│                   só EBITDA op. ×(1+g)       │
│                   CAPEX = 0 · ΔNFM = 0       │
│                                     └─ Valor terminal (VLC + NFM)
```

- **2025–2029** — FCF derivado do motor via `hub_fcf()`: usa os mesmos EBIT,
  depreciações, NFM e RFAI que entram nas demonstrações consolidadas.
- **2030–2034** — extrapolação no loop de `viabilidade_hub()`:
  - **EBITDA operacional** cresce a `g = 3,5%/ano` (2% inflação + 1,5% real).
  - **Depreciação** vem do calendário contabilístico real dos pools (NCRF),
    decrescente à medida que activos atingem o fim da vida útil.
  - **IRC** recalculado sobre o EBIT resultante (com carry-forward do RFAI,
    CFI art. 23.º §6).
  - **CAPEX = 0** e **ΔNFM = 0** (premissa conservadora — ver §4).
- **2035 (valor terminal)** — valor líquido contabilístico dos activos +
  recuperação integral da NFM, com mais-valia = 0. Somado ao FCF de 2034.

> **Importante:** as demonstrações financeiras (DR, Balanço, DFC) **não** são
> estendidas a 2034 — param em 2029. Só a série de FCF do projeto (uso exclusivo
> em VAL/TIR/payback) cobre os 10 anos. Esta separação é metodologicamente
> correcta: a avaliação de projeto faz-se sobre FCF incrementais ao longo da vida
> útil, de forma autónoma face ao horizonte das demonstrações consolidadas
> (Brealey, Myers & Allen).

## 3. Mini-correção aplicada (2026-05-28)

### Problema

O EBITDA de 2029 inclui o **accrual do subsídio PT2030 (NCRF 22)** — em 2029,
≈ 282 521 €. A versão anterior crescia o **EBITDA total** a `g = 3,5%`, o que
fazia o accrual do subsídio também "crescer" 3,5%/ano. Isso é incorrecto: o
subsídio reconhece-se ao **ritmo da depreciação real** dos activos subsidiados
(`montante × dep_pools_y / capex_base`), não a uma taxa de crescimento.

### Solução

Separou-se, no loop de extensão, o **EBITDA operacional** do **reconhecimento do
subsídio**:

- `ebitda_op` (benefícios operacionais + margem B2C) → cresce a `g`.
- `pt2030_accrual_ext = montante × dep_pools_ext / capex_base` → segue a
  depreciação real (declina e termina com a vida útil dos pools).
- `ebitda_ext = ebitda_op_ext + pt2030_accrual_ext`.

A extensão fica assim **coerente com o tratamento dos anos do motor (2025–2029)**,
onde o accrual em EBITDA também é baseado em `dep_pools`.

### Impacto nos indicadores (cenário Base)

| Métrica            | Antes       | Depois          | Δ          |
| ------------------ | ----------- | --------------- | ---------- |
| VAL                | 2 913 761 € | **2 493 769 €** | −419 992 € |
| TIR                | 18,83 %     | **17,49 %**     | −1,34 pp   |
| Payback simples    | 6,03 anos   | **6,12 anos**   | +0,09      |
| Payback atualizado | 7,07 anos   | **7,37 anos**   | +0,30      |
| VALA (APV)         | 2 112 164 € | **1 917 263 €** | −194 901 € |

O efeito é **conservador**: ao deixar de inflacionar o accrual, o EBITDA dos anos
de extensão baixa, reduzindo VAL/TIR/VALA e alongando ligeiramente o payback.

### FCF e accrual após correção (2029–2034)

| Ano          | EBITDA    | Accrual PT2030 | FCF livre |
| ------------ | --------- | -------------- | --------- |
| 2029 (motor) | 1 020 462 | 282 521        | 975 120   |
| 2030         | 978 790   | 215 021        | 921 361   |
| 2031         | 917 772   | 127 271        | 844 600   |
| 2032         | 945 439   | 127 271        | 869 017   |
| 2033         | 974 075   | 127 271        | 894 288   |
| 2034         | 930 307   | 53 865         | 804 108   |

*(O FCF de 2034 não inclui ainda o valor terminal, somado à parte na série de
desconto `cashflows_val`.)*

## 4. Limitações conhecidas da extrapolação

1. **CAPEX = 0** nos anos de extensão — ignora reinvestimento de manutenção
   (~2% do activo bruto/ano seria o benchmark). Subestima a saída de caixa →
   **enviesa o VAL para cima** nesta componente.
2. **ΔNFM = 0** — ignora o crescimento natural do fundo de maneio com o EBITDA.
   Subestima a saída de caixa → mesmo sentido.

Ambas as simplificações empurram o VAL no sentido optimista; em contrapartida, a
ausência de novos benefícios e o accrual decrescente puxam no sentido conservador.
O efeito líquido é considerado materialmente pequeno (CAPEX manut. ~120 k€/ano e
ΔNFM ~15–20 k€/ano face a FCF de ~800–900 k€). Ver `docs/fcf_modelacao_hub.md` §4
para a parametrização alternativa, se vier a ser pedida.

## 5. Extensão integral do motor a 2034 — IMPLEMENTADA (via B)

**Estado (2026-05-28): feito.** A extensão de DR + Balanço + DFC consolidados a
2034 foi implementada pela **abordagem B (roll-forward de maturidade, opt-in)**,
documentada em [horizonte_10anos_extensao_motor.md](horizonte_10anos_extensao_motor.md).
Ligar com `run_model(..., horizonte_maturidade=True)`; desligada por defeito.

A via originalmente temida (abordagem A — empurrar `ANO_FIM`) **não** foi
necessária. O que a tornava arriscada era recriar as tabelas pré-computadas e
recalibrar as reconciliações sem a âncora do `reference_balanco`. Descobriu-se que
o **Balanço anual fecha por construção** via o *treasury plug* (não usa
`reference_balanco`), pelo que o roll-forward garante `controlo ≈ 0` em 2030–2034
sem recalibração. Pressupostos de maturidade adotados (g=2 %, CAPEX=amortizações,
dívida constante, payout mantido, IRC à taxa efectiva de 2029) — ver o doc dedicado.

Para referência, a abordagem A teria exigido: `config.py` `ANO_FIM` 2029→2034;
pressupostos novos 2030–2034; recriar `computed/schedules.yaml` (AFT/depreciações,
subsidiárias, dividendos, mapa de dívida, `reference_balanco`); e recalibrar as 3
reconciliações. A via B evita tudo isto ao isolar a extensão da fase de maturidade.
