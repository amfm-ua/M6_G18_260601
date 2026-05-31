"""Test IRC propagation through Hub viability."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests

BASE = "http://localhost:8000"

print("=== Hub viability test ===")
r = requests.get(f"{BASE}/api/hub/viability?cenario=Base")
print(f"Status: {r.status_code}")
if r.ok:
    d = r.json()
    print(f"VPL: {d.get('val', 'N/A')}")
    print(f"TIR: {d.get('tir', 'N/A')}")
else:
    print(f"Error: {r.text[:200]}")

print()
print("=== Assumptions effective IRC ===")
r2 = requests.get(f"{BASE}/api/assumptions/effective?cenario=Base&hub_on=False&ecogres_on=True")
print(f"Status: {r2.status_code}")
if r2.ok:
    d2 = r2.json()
    eff = d2.get("effective", d2)
    for k, v in eff.items():
        if "irc" in k.lower() or "taxa" in k.lower():
            print(f"  {k}: {v}")
else:
    print(f"Error: {r2.text[:200]}")

print()
print("=== DR IRC 2025 vs 2024 ===")
r3 = requests.post(f"{BASE}/api/run", json={"cenario": "Base", "hub_on": False, "ecogres_on": True})
if r3.ok:
    dr = r3.json()["outputs"]["dr"]
    for row in dr:
        print(f"  {row['ano']}: IRC={row['irc']:>12,.0f}, RL={row['rl']:>12,.0f}")
else:
    print(f"Error: {r3.status_code} {r3.text[:200]}")