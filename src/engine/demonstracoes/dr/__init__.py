"""
Módulo: engine/statements/dr.py — Demonstração de Resultados Consolidada (2024-2029)
Versão: v2 — Estrutura modular temática
Idioma: Português Europeu

OBJETIVO ACADÉMICO:
Este módulo constrói a Demonstração de Resultados (DR), que evidencia:
  - Receita de vendas (produto e mercadorias)
  - Custos operacionais (CMVMC, Pessoal, FSE)
  - Resultados operacionais (EBIT = EBITDA - Depreciação)
  - Resultados financeiros (juros, subsídios, outros rendimentos)
  - Resultado antes e depois de impostos (RAI, Resultado Líquido)

ESTRUTURA DA DR (Fluxo de Cálculo):
  1. RECEITAS OPERACIONAIS:
     - Vendas Produtos: calculadas por produto com crescimento volume × crescimento preço
     - Vendas Mercadorias: vendidas a margens definidas por categoria

  2. CUSTOS OPERACIONAIS:
     - CMVMC (Custo de Mercadorias Vendidas e Matérias-Primas): % da receita
     - Pessoal: base + crescimento de headcount
     - FSE (Fornecimentos e Serviços Externos): base + crescimento e detalhe por rubrica
     - Depreciação: do plano plurianual de investimento
     - Imparidades: 0,5% dos saldos de clientes (estimativa de crédito duvidoso)

  3. RESULTADOS OPERACIONAIS:
     - EBITDA = Receita - CMVMC - Pessoal - FSE
     - EBIT = EBITDA - Depreciação

  4. RESULTADOS FINANCEIROS:
     - Juros (carga financeira): do plano de financiamento
     - Subsídios: se houver (ex: Hub Logístico)
     - Outros Rendimentos: cedência de pessoal, equivalência patrimonial, câmbio

  5. RESULTADO ANTES DE IMPOSTOS (RAI):
     - RAI = EBIT + (Juros) + (Outros Rendimentos) + (Outros Gastos) + (Imparidades)

  6. IMPOSTO SOBRE RENDIMENTO (IRC):
     - ICE (art. 41.º-A EBF): dedução à matéria coletável (~342k€ em 2024, cresce 3%/ano)
     - Taxa geral: 21% (2024) / 20% (2025+) — Grestel é grande empresa
     - Derrama Municipal: 1,5%
     - Derrama Estadual: 3% se lucro tributável > 1,5M€
     - SIFIDE II (CFI): crédito 380k€ em 2025 (ANI) + ~130k€/ano a partir de 2026
     - Tributação Autónoma (art. 88.º CIRC): ~22k€ em 2024, indexado 3%/ano

  7. RESULTADO LÍQUIDO:
     - = RAI - IRC

LÓGICA FINANCEIRA CRÍTICA:
  - 2024: dados reais (input de Base2024), não projetado
  - 2025: ano completo (12 meses) — VN e custos calculados para o período integral
  - 2026-2029: períodos completos (12 meses)
  - Crescimentos cumulativos aplicados ano a ano
  - Imparidades crescem com saldo de clientes (indica risco de crédito)
"""
from .build import build_dr

__all__ = ["build_dr"]
