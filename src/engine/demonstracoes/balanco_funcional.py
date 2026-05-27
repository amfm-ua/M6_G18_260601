"""Balanço Funcional — Classificação de rubricas por função económica.

Requisito M6-R4: O plano de negócios deve incluir balanço funcional.
Diferencia do balanço patrimonial por classificar ativos e passivos
em fixo/circulante segundo a função económica (não a convertibilidade
em liquidez).

Estrutura:
  Ativo Fixo: Ativos que a empresa detém de forma duradoura
    - AFT líquido, Intangíveis, Goodwill, Subsidiárias (MEP),
      Outros ANCs, IDA
  Ativo Circulante: Ativos que se renovam no ciclo operacional
    - Inventários, Clientes, EOEP devedor, Outros AC, Caixa,
      Aplicações financeiras CP

  Capital Próprio: Como no balanço patrimonial
  Passivo Fixo (exigível a LP): Dívida e obrigações > 1 ano
    - Empréstimos NC, IDP
  Passivo Circulante (exigível a CP): Obrigações < 1 ano
    - Fornecedores, EOEP credor, Outros PC, Empréstimos C,
      Linha de crédito CP

Fundimento: FR = CP - AF (Fundo de Maneio Funcional)
  FR > 0 → equilíbrio financeiro (CP cobre AF + parte do AC)
  FR < 0 → desequilíbrio (AF financiado por dívida CP)
"""
from __future__ import annotations

import pandas as pd

from ..inputs import ALL_YEARS


def build_balanco_funcional(df_balanco: pd.DataFrame) -> pd.DataFrame:
    """Constrói o Balanço Funcional a partir do Balanço Patrimonial.
    
    Classifica rubricas em Fixo/Circulante por função económica,
    conforme NCRF 1 e requisitos M6.
    """
    rows = []
    
    for y in ALL_YEARS:
        bs = df_balanco[df_balanco.ano == y].iloc[0]
        
        # ── ATIVO FIXO ─────────────────────────────────────────────────────
        aft = float(bs.get("aft_liquido", 0.0))
        intang = float(bs.get("intangiveis_fim", 0.0))
        gw = float(bs.get("goodwill", 0.0))
        subs = float(bs.get("subsidiarias_fim", bs.get("subsidiarias", 0.0)))
        outros_anc = float(bs.get("anc_outros", 0.0)) - gw - subs - intang if "anc_outros" in bs.index else 0.0
        ida = float(bs.get("impost_dif_ativos", 0.0))
        
        ativo_fixo = aft + intang + gw + subs + outros_anc + ida
        
        # ── ATIVO CIRCULANTE ──────────────────────────────────────────────
        inv = float(bs.get("inventarios", 0.0))
        cli = float(bs.get("clientes", 0.0))
        eoep_dev = float(bs.get("eoep_devedor", 0.0))
        outros_ac = float(bs.get("outros_ac", 0.0))
        caixa = float(bs.get("caixa", 0.0))
        aplic = float(bs.get("aplicacoes_fin_cp", 0.0))
        
        ativo_circulante = inv + cli + eoep_dev + outros_ac + caixa + aplic
        
        total_ativo = ativo_fixo + ativo_circulante
        
        # ── CAPITAL PRÓPRIO ───────────────────────────────────────────────
        cp = float(bs.get("total_cp", 0.0))
        
        # ── PASSIVO FIXO (Exigível a Longo Prazo) ─────────────────────────
        emp_nc = float(bs.get("emprestimos_nc", 0.0))
        idp = float(bs.get("impost_dif_passivos", 0.0))
        
        passivo_fixo = emp_nc + idp
        
        # ── PASSIVO CIRCULANTE (Exigível a Curto Prazo) ───────────────────
        forn = float(bs.get("fornecedores", 0.0))
        eoep_cred = float(bs.get("eoep_credor", 0.0))
        outros_pc = float(bs.get("outros_pc", 0.0))
        emp_c = float(bs.get("emprestimos_c", 0.0))
        linha_cp = float(bs.get("linha_credito_cp", 0.0))
        
        passivo_circulante = forn + eoep_cred + outros_pc + emp_c + linha_cp
        
        total_passivo = passivo_fixo + passivo_circulante
        
        # ── FUNDAMENTAL RATIOS ────────────────────────────────────────────
        # Fundo de Maneio Funcional = CP - AF
        fmf = cp - ativo_fixo
        # Fundo de Maneio Líquido = AC - PC (mesmo valor por construção)
        fml = ativo_circulante - passivo_circulante
        
        # Rácio de autonomia financeira funcional
        autonomia_func = cp / total_ativo if total_ativo else 0.0
        
        # Rácio de solvabilidade funcional
        solv_func = cp / total_passivo if total_passivo else 0.0
        
        rows.append({
            "ano": y,
            "ativo_fixo": round(ativo_fixo),
            "ativo_circulante": round(ativo_circulante),
            "total_ativo_func": round(total_ativo),
            "capital_proprio": round(cp),
            "passivo_fixo": round(passivo_fixo),
            "passivo_circulante": round(passivo_circulante),
            "total_passivo_func": round(total_passivo),
            "fundo_maneio_funcional": round(fmf),
            "fundo_maneio_liquido": round(fml),
            "autonomia_funcional": round(autonomia_func, 4),
            "solvabilidade_funcional": round(solv_func, 4),
        })
    
    return pd.DataFrame(rows)
