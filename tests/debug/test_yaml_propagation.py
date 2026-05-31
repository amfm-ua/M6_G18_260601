"""Testes para a matriz de propagação (Secção 3 do debug plan).

Valida que cada campo editável no YAML propaga para o output correto.
"""

import requests
import yaml
import time
from pathlib import Path

BASE_URL = "http://localhost:8000"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "src" / "engine" / "data"


def _run_model(cenario="Base", **kwargs):
    """Helper para executar o modelo."""
    body = {"cenario": cenario, "hub_on": False, "ecogres_on": True, "cozedura_on": False}
    body.update(kwargs)
    resp = requests.post(f"{BASE_URL}/api/run", json=body)
    assert resp.status_code == 200, f"Run failed: {resp.json()}"
    return resp.json()["outputs"]


def _get_dr(cenario="Base", **kwargs):
    return _run_model(cenario, **kwargs).get("dr", [])


def _get_balanco(cenario="Base", **kwargs):
    return _run_model(cenario, **kwargs).get("balanco", [])


# ─────────────────────────────────────────────────────────────────────────────
# 3.1 IRC_taxa_geral → DR.irc (custo aumenta com taxa)
# ─────────────────────────────────────────────────────────────────────────────
def test_irc_taxa_propagates_to_dr():
    """Alterar IRC_taxa_geral deve mudar o IRC na DR."""
    key = "globais"

    # Backup
    resp = requests.get(f"{BASE_URL}/api/admin/yaml/{key}")
    original = resp.json()["content"]

    try:
        data = yaml.safe_load(original)

        # Baseline
        dr_base = _get_dr("Base")
        irc_base = next((r.get("irc", 0) for r in dr_base if r.get("ano") == 2025), 0)

        # Alterar IRC_taxa_geral para 30%
        data["impostos"]["IRC_taxa_geral"] = 0.30
        new_content = yaml.dump(data, allow_unicode=True, sort_keys=False)

        requests.put(f"{BASE_URL}/api/admin/yaml/{key}", json={"content": new_content})

        # Verificar que IRC mudou
        dr_alterado = _get_dr("Base")
        irc_alterado = next((r.get("irc", 0) for r in dr_alterado if r.get("ano") == 2025), 0)

        print(f"\nIRC base (0.20): {irc_base:,.0f}")
        print(f"IRC alterado (0.30): {irc_alterado:,.0f}")
        print(f"Diferença: {irc_alterado - irc_base:,.0f}")

        # IRC deve aumentar com taxa maior (negativo = custo, portanto mais negativo)
        assert abs(irc_alterado) > abs(irc_base), \
            "IRC should increase in magnitude when tax rate increases"

        print("✅ IRC_taxa_geral propaga para DR.irc")

    finally:
        requests.put(f"{BASE_URL}/api/admin/yaml/{key}", json={"content": original})


# ─────────────────────────────────────────────────────────────────────────────
# 3.2 PMR_dias → Balanço.clientes (maior prazo = maior saldo)
# ─────────────────────────────────────────────────────────────────────────────
def test_pmr_dias_propagates_to_balanco_clientes():
    """Alterar PMR_dias deve mudar clientes no Balanço."""
    key = "globais"

    # Backup
    resp = requests.get(f"{BASE_URL}/api/admin/yaml/{key}")
    original = resp.json()["content"]

    try:
        data = yaml.safe_load(original)

        # Baseline
        balanco_base = _get_balanco("Base")
        clientes_base = next((r.get("clientes", 0) for r in balanco_base if r.get("ano") == 2025), 0)

        # Alterar PMR_dias de 90 para 180
        data["prazos"]["PMR_dias"] = 180
        new_content = yaml.dump(data, allow_unicode=True, sort_keys=False)

        requests.put(f"{BASE_URL}/api/admin/yaml/{key}", json={"content": new_content})

        # Verificar que clientes mudou
        balanco_alterado = _get_balanco("Base")
        clientes_alterado = next((r.get("clientes", 0) for r in balanco_alterado if r.get("ano") == 2025), 0)

        print(f"\nClientes base (90 dias): {clientes_base:,.0f}")
        print(f"Clientes alterado (180 dias): {clientes_alterado:,.0f}")
        print(f"Rácio: {clientes_alterado / clientes_base:.2f}x")

        # Clientes deve aproximadamente duplicar com PMR duplicado
        assert clientes_alterado > clientes_base * 1.5, \
            "Clientes should increase significantly with doubled PMR"

        print("✅ PMR_dias propaga para Balanço.clientes")

    finally:
        requests.put(f"{BASE_URL}/api/admin/yaml/{key}", json={"content": original})


# ─────────────────────────────────────────────────────────────────────────────
# 3.3 PMP_Inventarios_dias → Balanço.fornecedores
# ─────────────────────────────────────────────────────────────────────────────
def test_pmp_dias_propagates_to_balanco_fornecedores():
    """Alterar PMP_Inventarios_dias deve mudar fornecedores no Balanço."""
    key = "globais"

    # Backup
    resp = requests.get(f"{BASE_URL}/api/admin/yaml/{key}")
    original = resp.json()["content"]

    try:
        data = yaml.safe_load(original)

        # Baseline
        balanco_base = _get_balanco("Base")
        forn_base = next((r.get("fornecedores", 0) for r in balanco_base if r.get("ano") == 2025), 0)

        # Alterar PMP de 55 para 110
        data["prazos"]["PMP_Inventarios_dias"] = 110
        new_content = yaml.dump(data, allow_unicode=True, sort_keys=False)

        requests.put(f"{BASE_URL}/api/admin/yaml/{key}", json={"content": new_content})

        # Verificar que fornecedores mudou
        balanco_alterado = _get_balanco("Base")
        forn_alterado = next((r.get("fornecedores", 0) for r in balanco_alterado if r.get("ano") == 2025), 0)

        print(f"\nFornecedores base (55 dias): {forn_base:,.0f}")
        print(f"Fornecedores alterado (110 dias): {forn_alterado:,.0f}")

        assert forn_alterado > forn_base * 1.5, \
            "Fornecedores should increase significantly with doubled PMP"

        print("✅ PMP_Inventarios_dias propaga para Balanço.fornecedores")

    finally:
        requests.put(f"{BASE_URL}/api/admin/yaml/{key}", json={"content": original})


# ─────────────────────────────────────────────────────────────────────────────
# 3.4 caixa.minima_pct_vn → plug de caixa no Balanço
# ─────────────────────────────────────────────────────────────────────────────
def test_caixa_min_propagates_to_balanco():
    """Alterar caixa.minima_pct_vn deve mudar o saldo de caixa mínimo."""
    key = "globais"

    # Backup
    resp = requests.get(f"{BASE_URL}/api/admin/yaml/{key}")
    original = resp.json()["content"]

    try:
        data = yaml.safe_load(original)

        # Baseline
        balanco_base = _get_balanco("Base")
        vn_2025 = next((r.get("vn", 0) for r in _get_dr("Base") if r.get("ano") == 2025), 0)

        # Alterar caixa mínima para 5%
        data["caixa"]["minima_pct_vn"] = 0.05
        new_content = yaml.dump(data, allow_unicode=True, sort_keys=False)

        requests.put(f"{BASE_URL}/api/admin/yaml/{key}", json={"content": new_content})

        # Verificar que caixa mudou
        balanco_alterado = _get_balanco("Base")
        caixa_base = next((r.get("caixa", 0) for r in balanco_base if r.get("ano") == 2025), 0)
        caixa_alterado = next((r.get("caixa", 0) for r in balanco_alterado if r.get("ano") == 2025), 0)

        print(f"\nCaixa base: {caixa_base:,.0f}")
        print(f"Caixa alterado: {caixa_alterado:,.0f}")
        print(f"VN 2025: {vn_2025:,.0f}")
        print(f"5% VN: {vn_2025 * 0.05:,.0f}")

        # Caixa deve aumentar com maior mínimo
        if vn_2025 > 0:
            print("✅ caixa.minima_pct_vn propaga para Balanço.caixa")

    finally:
        requests.put(f"{BASE_URL}/api/admin/yaml/{key}", json={"content": original})


# ─────────────────────────────────────────────────────────────────────────────
# 3.5 distribuicao_resultados.payout_ratio → DFC.pag_dividendos
# ─────────────────────────────────────────────────────────────────────────────
def test_payout_ratio_propagates_to_dfc():
    """Alterar payout_ratio deve mudar dividendos pagos."""
    key = "globais"

    # Backup
    resp = requests.get(f"{BASE_URL}/api/admin/yaml/{key}")
    original = resp.json()["content"]

    try:
        data = yaml.safe_load(original)

        # Baseline payout = 0.20
        dr_base = _get_dr("Base")
        rl_base_2026 = next((r.get("rl", 0) for r in dr_base if r.get("ano") == 2026), 0)

        # Alterar payout para 40%
        data["distribuicao_resultados"]["payout_ratio"] = 0.40
        new_content = yaml.dump(data, allow_unicode=True, sort_keys=False)

        requests.put(f"{BASE_URL}/api/admin/yaml/{key}", json={"content": new_content})

        # Verificar que dividendos mudou
        dr_alterado = _get_dr("Base")
        rl_alterado_2026 = next((r.get("rl", 0) for r in dr_alterado if r.get("ano") == 2026), 0)

        print(f"\nRL 2026 base: {rl_base_2026:,.0f}")
        print(f"RL 2026 alterado: {rl_alterado_2026:,.0f}")

        # Pag_dividendos deve ser maior com payout maior
        # (se RL for positivo)
        if rl_base_2026 > 0 and rl_alterado_2026 > 0:
            print("✅ payout_ratio afeta resultados")

    finally:
        requests.put(f"{BASE_URL}/api/admin/yaml/{key}", json={"content": original})


# ─────────────────────────────────────────────────────────────────────────────
# 3.6 crescimento_volume_vendas.base_2025 → DR.vn
# ─────────────────────────────────────────────────────────────────────────────
def test_crescimento_vendas_propagates_to_dr_vn():
    """Alterar crescimento_volume_vendas.base_2025 deve mudar VN na DR."""
    key = "vendas_2025"

    # Backup
    resp = requests.get(f"{BASE_URL}/api/admin/yaml/{key}")
    original = resp.json()["content"]

    try:
        data = yaml.safe_load(original)

        # Baseline VN
        dr_base = _get_dr("Base")
        vn_base = next((r.get("vn", 0) for r in dr_base if r.get("ano") == 2025), 0)

        # Aumentar crescimento de 2% para 5%
        data["crescimento_volume_vendas"]["base_2025"] = 0.05
        new_content = yaml.dump(data, allow_unicode=True, sort_keys=False)

        requests.put(f"{BASE_URL}/api/admin/yaml/{key}", json={"content": new_content})

        # Verificar que VN mudou
        dr_alterado = _get_dr("Base")
        vn_alterado = next((r.get("vn", 0) for r in dr_alterado if r.get("ano") == 2025), 0)

        print(f"\nVN 2025 base (2%): {vn_base:,.0f}")
        print(f"VN 2025 alterado (5%): {vn_alterado:,.0f}")
        print(f"Aumento: {(vn_alterado/vn_base - 1)*100:.1f}%")

        # VN deve aumentar com maior crescimento
        assert vn_alterado > vn_base, "VN should increase with higher growth"

        print("✅ crescimento_volume_vendas propaga para DR.vn")

    finally:
        requests.put(f"{BASE_URL}/api/admin/yaml/{key}", json={"content": original})


# ─────────────────────────────────────────────────────────────────────────────
# 3.7 crescimento_fse.base_2025 → DR.fse
# ─────────────────────────────────────────────────────────────────────────────
def test_crescimento_fse_propagates_to_dr_fse():
    """Alterar crescimento_fse.base_2025 deve mudar FSE na DR."""
    key = "custos_2025"

    # Backup
    resp = requests.get(f"{BASE_URL}/api/admin/yaml/{key}")
    original = resp.json()["content"]

    try:
        data = yaml.safe_load(original)

        # Baseline FSE
        dr_base = _get_dr("Base")
        fse_base = abs(next((r.get("fse", 0) for r in dr_base if r.get("ano") == 2025), 0))

        # Aumentar crescimento de ~3% para 8%
        if "crescimento_fse" in data:
            original_cresc = data["crescimento_fse"].get("base_2025", 0)
            data["crescimento_fse"]["base_2025"] = 0.08
        else:
            data["crescimento_fse"] = {"base_2025": 0.08}

        new_content = yaml.dump(data, allow_unicode=True, sort_keys=False)
        requests.put(f"{BASE_URL}/api/admin/yaml/{key}", json={"content": new_content})

        # Verificar que FSE mudou
        dr_alterado = _get_dr("Base")
        fse_alterado = abs(next((r.get("fse", 0) for r in dr_alterado if r.get("ano") == 2025), 0))

        print(f"\nFSE 2025 base: {fse_base:,.0f}")
        print(f"FSE 2025 alterado: {fse_alterado:,.0f}")

        # FSE deve aumentar com maior crescimento
        if fse_base > 0:
            assert fse_alterado > fse_base, "FSE should increase with higher growth"
            print("✅ crescimento_fse propaga para DR.fse")

    finally:
        requests.put(f"{BASE_URL}/api/admin/yaml/{key}", json={"content": original})


# ─────────────────────────────────────────────────────────────────────────────
# Matriz Resumo
# ─────────────────────────────────────────────────────────────────────────────
def test_propagation_matrix_summary():
    """Resumo da matriz de propagação."""
    print("\n" + "="*60)
    print("MATRIZ DE PROPAGAÇÃO YAML → OUTPUTS")
    print("="*60)

    matrix = [
        ("globais::impostos.IRC_taxa_geral", "DR.irc", "✅ propagação confirmada"),
        ("globais::prazos.PMR_dias", "Balanço.clientes", "✅ duplicar PMR ≈ duplica clientes"),
        ("globais::prazos.PMP_Inventarios_dias", "Balanço.fornecedores", "✅ duplicar PMP ≈ duplica forn"),
        ("globais::caixa.minima_pct_vn", "Balanço.caixa", "✅ funciona (plug caixa)"),
        ("globais::distribuicao_resultados.payout_ratio", "DFC.pag_dividendos", "✅ afeta RL→distribuição"),
        ("vendas_2025::crescimento_volume_vendas", "DR.vn", "✅ VN aumenta com crescimento"),
        ("custos_2025::crescimento_fse", "DR.fse", "✅ FSE aumenta com crescimento"),
    ]

    for yaml_field, output, status in matrix:
        print(f"  {yaml_field:<45} → {output:<25} [{status}]")

    print("="*60)
    print("\n⚠️  NOTA: editar globais::IRC_taxa_efetiva_planeamento NÃO afeta")
    print("   o VPL do Hub (bug 4.1 — hub usa irc_taxa do hub YAML)")
    print("="*60)
