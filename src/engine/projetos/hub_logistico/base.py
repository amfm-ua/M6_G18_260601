"""Hub Logístico M6 — primitivas partilhadas.

Carregamento dos pressupostos (m6_hub_assumptions.yaml) e funções de base
reutilizadas pelos restantes módulos do pacote: depreciação por pool de
ativo, juros capitalizados (NCRF 10), iteração das tranches de empréstimo
e custo médio ponderado da dívida.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from ...inputs import DATA_DIR, YEARS


def _hub_assumptions_path() -> Path:
    return DATA_DIR / "subsidiarias" / "hub_logistico" / "m6_hub_assumptions.yaml"


def load() -> dict:
    """Carrega m6_hub_assumptions.yaml."""
    with open(_hub_assumptions_path(), "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _dep_por_ano(proj: dict, year: int) -> float:
    """Depreciação total de todos os pools num dado ano.

    Cada pool deprecia montante/vida_util por ano, a partir de
    max(ano_inicio_pool, ano_inicio_beneficios) e durante vida_util anos.
    Pools com excluir_analise_incremental: true são ignorados (sunk costs).
    """
    pools = proj["capex"]["pools"]
    ano_inicio_op = int(proj["ano_inicio_beneficios"])
    total = 0.0
    for pool in pools.values():
        if pool.get("excluir_analise_incremental", False):
            continue
        montante = float(pool["montante"])
        vida_util = int(pool["vida_util_anos"])
        ano_pool = int(pool["ano_inicio"])
        dep_pool = montante / vida_util
        ano_dep_inicio = max(ano_pool, ano_inicio_op)
        ano_dep_fim = ano_dep_inicio + vida_util - 1
        if ano_dep_inicio <= year <= ano_dep_fim:
            total += dep_pool
    return total


def _juros_capitalizados_map(hub: dict) -> dict[int, float]:
    """
    Juros capitalizados no custo do ativo por ano de construção — NCRF 10.

    Fundamento académico (NCRF 10 §8):
    «Os custos de empréstimos que sejam diretamente atribuíveis à aquisição,
    construção ou produção de um ativo qualificável devem ser capitalizados
    como parte do custo desse ativo.»

    O hub logístico qualifica como «ativo qualificável» porque o período de
    construção e instalação é substancial (≥ 12 meses — NCRF 10 §5). A
    capitalização cessa quando o ativo está substancialmente pronto para o
    uso pretendido (NCRF 10 §22), i.e., quando arranca a operação (2026).

    Impacto no modelo:
      • DR: juros capitalizados NÃO reconhecidos como gasto financeiro
      • Balanço: AFT ↑ pelo montante capitalizado → maior base depreciável
      • DFC: o juro é SEMPRE saída de caixa real (NCRF 2 §33b) — capturado
              no fluxo_financiamento, independentemente do tratamento contab.
      • FCF unlevered: exclui juros por natureza (desalavancado); efeito
              indireto via depreciação mais alta nos anos operacionais

    Retorna: {ano: montante_capitalizado} — zero nos anos fora do período.
    """
    proj = hub["projeto_hub"]
    jc_cfg = proj.get("juros_capitalizaveis", {})

    if not jc_cfg.get("capitalizar", False):
        return {y: 0.0 for y in YEARS}

    ano_ini = int(jc_cfg.get("ano_inicio_capitalizacao", 9999))
    ano_fim = int(jc_cfg.get("ano_fim_capitalizacao", 0))

    result: dict[int, float] = {y: 0.0 for y in YEARS}

    for _, tranche in _iter_emprestimos(proj):
        capital = float(tranche["montante"])
        taxa = float(tranche["taxa_juro"])
        desembolso_ano = int(tranche["desembolso"])

        saldo = 0.0
        for y in YEARS:
            if y == desembolso_ano:
                saldo = capital
            juros_y = saldo * taxa if saldo > 0 else 0.0
            if ano_ini <= y <= ano_fim:
                result[y] += juros_y

    return result


def _iter_emprestimos(proj: dict):
    """Itera sobre todas as tranches de empréstimo (exclui PT2030 e entradas sem amortizacao_anual)."""
    for nome, v in proj["financiamento"].items():
        if isinstance(v, dict) and "amortizacao_anual" in v:
            yield nome, v


def _juros_capitalizados_map_por_tranche(hub: dict) -> dict[str, dict[int, float]]:
    """Juros capitalizados por tranche e por ano — NCRF 10.

    Versão desagregada de _juros_capitalizados_map: devolve um dicionário
    {nome_tranche: {ano: montante_capitalizado}} para permitir construir o
    mapa de serviço da dívida individualmente por fonte de capital alheio.
    """
    proj = hub["projeto_hub"]
    jc_cfg = proj.get("juros_capitalizaveis", {})

    if not jc_cfg.get("capitalizar", False):
        return {nome: {y: 0.0 for y in YEARS} for nome, _ in _iter_emprestimos(proj)}

    ano_ini = int(jc_cfg.get("ano_inicio_capitalizacao", 9999))
    ano_fim = int(jc_cfg.get("ano_fim_capitalizacao", 0))

    result: dict[str, dict[int, float]] = {}
    for nome, tranche in _iter_emprestimos(proj):
        capital = float(tranche["montante"])
        taxa = float(tranche["taxa_juro"])
        desembolso_ano = int(tranche["desembolso"])
        result[nome] = {y: 0.0 for y in YEARS}
        saldo = 0.0
        for y in YEARS:
            if y == desembolso_ano:
                saldo = capital
            juros_y = saldo * taxa if saldo > 0 else 0.0
            if ano_ini <= y <= ano_fim:
                result[nome][y] = juros_y

    return result


def _kd_ponderado(proj: dict) -> float:
    """Custo médio ponderado da dívida (kd) sobre todas as tranches de empréstimo."""
    total_montante = 0.0
    total_custo = 0.0
    for _, tr in _iter_emprestimos(proj):
        m = float(tr["montante"])
        total_montante += m
        total_custo += m * float(tr["taxa_juro"])
    return total_custo / total_montante if total_montante > 0 else 0.0
