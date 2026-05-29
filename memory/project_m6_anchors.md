---
name: project-m6-anchors
description: Números-âncora do modelo Grestel para o relatório M6 (viabilidade hub, DR/balanço/KPI, financiamento, APV, Monte Carlo) — valores do modelo ATUAL, autoritativos sobre docs antigos
metadata:
  type: project
---

Números-âncora confirmados contra o modelo ATUAL (run_model + viabilidade_hub + vala_hub + monte_carlo_hub, seed 42) para o relatório M6 do Hub Logístico 4.0. **Estes valores prevalecem sobre os docs/ antigos** (ex.: `analise_base_hub_vs_sem_hub.md` dizia VAL 2.110k/TIR 14,6% — DESATUALIZADO).

**Why:** o utilizador exigiu "confirmar com a realidade atual do modelo" ao preencher o relatório; vários docs têm economia stale (WACC 7,5%, BPI 10,7M como financiamento do hub, banda 6-12M).
**How to apply:** usar SEMPRE estes valores no relatório; o financiamento do hub NÃO é o empréstimo BPI 10,7M (esse é dívida histórica do grupo).

## Viabilidade hub (FCFF @ WACC 6,46%)
- VAL = €2.493.769 · TIR = 17,49% · Payback simples 6,12a · atualizado 7,37a · IR 1,4156
- Valor residual ativos €2.193.060 + NFM recovery 90.375 = VT €2.283.435 (sem perpetuidade)
- VAL @ WACC dinâmico (Miles-Ezzell) = €1.638.783
- Cashflows VAL 2025→2034: −3.105.000; −727.468; 897.100; 939.110; 975.120; 921.361; 844.600; 869.017; 894.288; 3.087.543

## APV / VALA (ke 16,62%; rf 3,1%; irc 23,5%)
- VALA = €1.917.263 = VAL_base(Ke) −591.546 + escudo fiscal juros 199.700 + PT2030 líquido 2.084.376 + RFAI 224.734

## Financiamento hub (CAPEX €6,0M: 2025=2.850k, 2026=3.150k)
- Tranche CGD €3.000k @4,15% + Linha BEI/IFD €1.500k @3,75% (carência 2025-27, amort 2028-37) → Kd 4,02%
- PT2030 subsídio €2.700k (recebido 2027, NCRF 22 dedução à depreciação) · RFAI €600k (crédito fiscal, carry 10a)
- Equity Grestel €1.500k · D/E 75/25 · tornado: CAPEX>B2C>pessoal>WACC>DMI>PT2030

## Monte Carlo (N=2000, seed 42)
- VAL mean €2.585.064 · p5 €1.368.586 · p50 €2.599.621 · p95 €3.743.315 · std €726.443
- P(VAL>0)=99,95% · P(TIR>WACC)=99,95% · TIR p5/p50/p95 = 12,6%/17,9%/23,7%
- Drivers (Pearson r): b2c +0,55 · capex −0,49 · pessoal +0,43 · wacc −0,41 · dmi_clearing +0,26 · pt2030 +0,21

## DR COM HUB (€, 2024→2029)
- VN 37.884.116 → 53.815.242 · EBITDA 4.149.679 → 10.126.617 · EBIT 1.980.964 → 7.721.349 · RL 1.390.209 → 6.065.240
## Balanço/KPI COM HUB 2029
- Total ativo €54.442.069 · Equity €31.409.364 · Autonomia fin 57,7% (sem hub 62,0%) · ROE 19,3% (sem hub 15,6%)
- Margem EBITDA 11,0%→18,8% · ND/EBITDA 4x→1x · taxa IRC efetiva 8,4%→20,2%
- ATL 2024 = €40.258.766 (CAPEX 6M ≈ 15% — banda enunciado 15-30%)

Ver [[project_horizonte_10anos]] para extensão 2030-34.
