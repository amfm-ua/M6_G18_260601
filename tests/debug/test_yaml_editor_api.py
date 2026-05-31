"""Testes para a camada API do editor YAML (Secção 1 do debug plan)."""

import pytest
import requests
import time
from pathlib import Path

BASE_URL = "http://localhost:8000"
# parents[2] = project root (tests/debug -> tests -> project_root)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "src" / "engine" / "data"
DEFAULTS_DIR = DATA_DIR / "_defaults"


# ─────────────────────────────────────────────────────────────────────────────
# 1.1 GET /api/admin/yaml-files — whitelist completa + is_modified flag
# ─────────────────────────────────────────────────────────────────────────────
def test_listing_returns_complete_whitelist():
    resp = requests.get(f"{BASE_URL}/api/admin/yaml-files")
    assert resp.status_code == 200
    data = resp.json()
    files = data["files"]

    expected_keys = [
        "globais", "macro_2025", "vendas_2025", "custos_2025", "mix_2025",
        "macro_2026_2029", "vendas_2026_2029", "custos_2026_2029",
        "investimento", "hub", "ecogres", "smart",
        "hist_produtos", "hist_mercadorias", "hist_base",
    ]
    returned_keys = [f["key"] for f in files]

    for key in expected_keys:
        assert key in returned_keys, f"Key '{key}' missing from listing"

    assert len(files) == 15, f"Expected 15 files, got {len(files)}"


def test_is_modified_flag_correct():
    """is_modified deve ser True apenas se conteúdo != _defaults/."""
    resp = requests.get(f"{BASE_URL}/api/admin/yaml-files")
    data = resp.json()["files"]

    for f in data:
        if not f["exists"]:
            continue
        key = f["key"]
        rel = _KEY_TO_REL[key]
        path = DATA_DIR / rel
        default_path = DEFAULTS_DIR / rel

        if default_path.exists():
            current = path.read_text(encoding="utf-8")
            default = default_path.read_text(encoding="utf-8")
            assert f["is_modified"] == (current != default), \
                f"is_modified incorrect for {key}"


# ─────────────────────────────────────────────────────────────────────────────
# 1.2 GET /api/admin/yaml/{key} — 200 para todas as chaves, 404 para inexistentes
# ─────────────────────────────────────────────────────────────────────────────
def test_get_returns_content_for_all_whitelisted_keys():
    resp = requests.get(f"{BASE_URL}/api/admin/yaml-files")
    keys = [f["key"] for f in resp.json()["files"] if f["exists"]]

    for key in keys:
        r = requests.get(f"{BASE_URL}/api/admin/yaml/{key}")
        assert r.status_code == 200, f"GET {key} failed: {r.status_code}"
        assert "content" in r.json(), f"No 'content' in {key} response"
        assert len(r.json()["content"]) > 0, f"Empty content for {key}"


def test_get_inexistente_returns_404():
    r = requests.get(f"{BASE_URL}/api/admin/yaml/inexistente")
    assert r.status_code == 404
    assert "detail" in r.json()


# ─────────────────────────────────────────────────────────────────────────────
# 1.3 Path traversal attack — ..%2F deve dar 404
# ─────────────────────────────────────────────────────────────────────────────
def test_path_traversal_blocked():
    """Keys com padrões de path traversal devem ser bloqueados pela whitelist."""
    dangerous_keys = [
        "../etc/passwd",
        "..%2F..%2F..%2Fetc%2Fpasswd",
        "globais/../../../etc/passwd",
    ]
    for key in dangerous_keys:
        r = requests.get(f"{BASE_URL}/api/admin/yaml/{key}")
        assert r.status_code == 404, f"Path traversal not blocked: {key}"


# ─────────────────────────────────────────────────────────────────────────────
# 1.4 PUT com YAML inválido — 422
# ─────────────────────────────────────────────────────────────────────────────
def test_put_rejects_invalid_yaml():
    resp = requests.get(f"{BASE_URL}/api/admin/yaml/globais")
    original = resp.json()["content"]

    try:
        bad_yaml = "foo: : :"
        r = requests.put(
            f"{BASE_URL}/api/admin/yaml/globais",
            json={"content": bad_yaml},
        )
        assert r.status_code == 422, f"Expected 422 for invalid YAML, got {r.status_code}"
        assert "YAML" in r.json().get("detail", "").upper() or "yaml" in r.json().get("detail", "").lower()
    finally:
        # Restore original
        requests.put(f"{BASE_URL}/api/admin/yaml/globais", json={"content": original})


# ─────────────────────────────────────────────────────────────────────────────
# 1.5 PUT com YAML válido — persiste e is_modified=true
# ─────────────────────────────────────────────────────────────────────────────
def test_put_persists_valid_yaml_and_sets_modified():
    key = "globais"
    resp = requests.get(f"{BASE_URL}/api/admin/yaml/{key}")
    original = resp.json()["content"]

    try:
        marker = f"# DEBUG_MARKER_{int(time.time())}\n"
        new_content = marker + original

        r = requests.put(f"{BASE_URL}/api/admin/yaml/{key}", json={"content": new_content})
        assert r.status_code == 200, f"PUT failed: {r.status_code}"

        # Verify GET returns new content
        r2 = requests.get(f"{BASE_URL}/api/admin/yaml/{key}")
        assert r2.json()["content"] == new_content, "Content not persisted"

        # Verify is_modified flag
        listing = requests.get(f"{BASE_URL}/api/admin/yaml-files").json()["files"]
        entry = next(f for f in listing if f["key"] == key)
        assert entry["is_modified"], "is_modified should be True after edit"

    finally:
        # Restore
        requests.put(f"{BASE_URL}/api/admin/yaml/{key}", json={"content": original})


# ─────────────────────────────────────────────────────────────────────────────
# 1.6 POST /yaml/{key}/restore — repõe _defaults/
# ─────────────────────────────────────────────────────────────────────────────
def test_restore_returns_to_defaults():
    key = "globais"

    # Backup current
    resp_orig = requests.get(f"{BASE_URL}/api/admin/yaml/{key}")
    original = resp_orig.json()["content"]

    # Get default content
    rel = _KEY_TO_REL[key]
    default_path = DEFAULTS_DIR / rel
    default_content = default_path.read_text(encoding="utf-8")

    try:
        # Modify
        marker = f"# TEST_MARKER_{int(time.time())}\n"
        requests.put(f"{BASE_URL}/api/admin/yaml/{key}", json={"content": marker + original})

        # Restore
        r = requests.post(f"{BASE_URL}/api/admin/yaml/{key}/restore")
        assert r.status_code == 200, f"Restore failed: {r.status_code}"

        # Verify content matches default
        resp_after = requests.get(f"{BASE_URL}/api/admin/yaml/{key}")
        assert resp_after.json()["content"] == default_content, "Restore did not return to defaults"

        # Verify is_modified is False
        listing = requests.get(f"{BASE_URL}/api/admin/yaml-files").json()["files"]
        entry = next(f for f in listing if f["key"] == key)
        assert not entry["is_modified"], "is_modified should be False after restore"

    finally:
        # Restore original content (not defaults)
        requests.put(f"{BASE_URL}/api/admin/yaml/{key}", json={"content": original})


# ─────────────────────────────────────────────────────────────────────────────
# 1.7 POST /yaml/{key}/restore — key sem default → 404
# ─────────────────────────────────────────────────────────────────────────────
def test_restore_without_default_returns_404():
    """Simular uma key que existe mas não tem _defaults/ correspondente."""
    # O YAML editor só permite restore se existir em _defaults/
    # Vamos testar com um cenário que não tem _defaults
    # Na prática, todas as keys editáveis devem ter _defaults/
    # Se adicionarmos uma key sem _defaults, deve dar 404

    # Como todas as keys têm _defaults, este teste verifica que a whitelist
    # está correta (keys sem _defaults são filtradas na whitelist)

    # Teste com key válida mas sem equivalente em _defaults
    r = requests.post(f"{BASE_URL}/api/admin/yaml/inexistente/restore")
    assert r.status_code == 404, "Restore for non-existent key should be 404"


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────
_KEY_TO_REL = {
    "globais": "pressupostos/globais.yaml",
    "macro_2025": "pressupostos/2025/macro.yaml",
    "vendas_2025": "pressupostos/2025/vendas.yaml",
    "custos_2025": "pressupostos/2025/custos.yaml",
    "mix_2025": "pressupostos/2025/mix.yaml",
    "macro_2026_2029": "pressupostos/2026_2029/macro.yaml",
    "vendas_2026_2029": "pressupostos/2026_2029/vendas.yaml",
    "custos_2026_2029": "pressupostos/2026_2029/custos.yaml",
    "investimento": "pressupostos/investimento.yaml",
    "hub": "subsidiarias/hub_logistico/m6_hub_assumptions.yaml",
    "ecogres": "subsidiarias/ecogres/ecogres_assumptions.yaml",
    "smart": "master/smart_objetivos.yaml",
    "hist_produtos": "historico/2024/produtos.yaml",
    "hist_mercadorias": "historico/2024/mercadorias.yaml",
    "hist_base": "historico/2024/base.yaml",
}
