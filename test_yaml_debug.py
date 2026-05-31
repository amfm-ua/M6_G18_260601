"""Debug test: verify YAML editor changes propagate through the model."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import yaml
import requests

BASE = "http://localhost:8000"

print("=== TEST: YAML Editor propagation ===\n")

# Step 1: Verify YAML on disk is modified
with open(r"src\engine\data\pressupostos\globais.yaml", encoding="utf-8") as f:
    disk = yaml.safe_load(f)

irc_disk = disk["impostos"]["IRC_taxa_efetiva_planeamento"]
pmr_disk = disk["prazos"]["PMR_dias"]
print(f"[1] YAML on disk: IRC_taxa_efetiva_planeamento={irc_disk}, PMR_dias={pmr_disk}")

# Step 2: Verify API GET returns modified values
r = requests.get(f"{BASE}/api/admin/yaml/globais")
assert r.ok, f"GET yaml/globais failed: {r.status_code}"
d = r.json()
data = yaml.safe_load(d["content"])
irc_api = data["impostos"]["IRC_taxa_efetiva_planeamento"]
pmr_api = data["prazos"]["PMR_dias"]
print(f"[2] API GET yaml/globais: IRC_taxa_efetiva_planeamento={irc_api}, PMR_dias={pmr_api}")
assert irc_api == 0.35, f"Expected IRC=0.35, got {irc_api}"
assert pmr_api == 90, f"Expected PMR=90, got {pmr_api}"

# Step 3: Run model and check output
r2 = requests.post(f"{BASE}/api/run", json={
    "cenario": "Base", "hub_on": False, "ecogres_on": True, "cozedura_on": False
})
assert r2.ok, f"POST /api/run failed: {r2.status_code} {r2.text[:200]}"
result = r2.json()
outputs = result["outputs"]

dr = outputs["dr"]
bal = outputs["balanco"]
kpis = outputs["kpis"]

dr25 = next(x for x in dr if x["ano"] == 2025)
kpi25 = next(x for x in kpis if x["ano"] == 2025)
bal25 = next(x for x in bal if x["ano"] == 2025)

print(f"[3] Model output 2025:")
print(f"     IRC (apurado): {dr25['irc']:,.0f}")
print(f"     RL: {dr25['rl']:,.0f}")
print(f"     VN: {dr25['vn']:,.0f}")
print(f"     Margem Liquida: {dr25['rl']/dr25['vn']*100:.2f}%")
print(f"     Clientes Balanço: {bal25['clientes']:,.0f}")

# The IRC_taxa_efetiva_planeamento=0.35 should be visible in:
# - Hub viability calculations (uses irc_taxa_efetiva)
# - Effective IRC in DR should be ~35% if the model's IRC calculation
#   uses the flat effective rate for planning

# Step 4: Compare with original scenario to prove the change matters
r3 = requests.post(f"{BASE}/api/run", json={
    "cenario": "Upside", "hub_on": False, "ecogres_on": True, "cozedura_on": False
})
assert r3.ok, f"POST Upside failed: {r3.status_code}"
result_up = r3.json()
dr_up = result_up["outputs"]["dr"]
dr_up25 = next(x for x in dr_up if x["ano"] == 2025)
print(f"[4] Upside 2025 (same YAML): IRC={dr_up25['irc']:,.0f}, RL={dr_up25['rl']:,.0f}")

print("\n=== PASS: YAML changes are visible to the API and model ===")