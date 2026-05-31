import requests
import json

# Check /api/run endpoint
print("=== /api/run ===")
r = requests.post('http://localhost:8000/api/run?cenario=Base')
print(f"Status: {r.status_code}")
if r.status_code != 200:
    print(f"Response: {r.json()}")
else:
    print(f"Keys: {list(r.json().keys())}")

# Check /api/scenarios
print("\n=== /api/scenarios ===")
r2 = requests.get('http://localhost:8000/api/scenarios')
print(f"Status: {r2.status_code}")
print(f"Response: {r2.json() if r2.status_code == 200 else r2.text}")

# Check what POST /api/run needs
print("\n=== Try with all params ===")
r3 = requests.post('http://localhost:8000/api/run?cenario=Base&hub_on=true&ecogres_on=true&cozedura_on=false')
print(f"Status: {r3.status_code}")
if r3.status_code == 200:
    print(f"Keys: {list(r3.json().keys())}")
else:
    print(f"Response: {r3.json()}")
