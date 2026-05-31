import requests
import json

r = requests.get('http://localhost:8000/api/hub/monte-carlo?cenario=Base&n=100')
data = r.json()
print(json.dumps({k: v for k, v in data.items() if k != 'histograma'}, indent=2))
