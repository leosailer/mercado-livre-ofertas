import os
import requests

TOKEN = os.environ["ML_ACCESS_TOKEN"]

headers = {
    "Authorization": f"Bearer {TOKEN}"
}

url = "https://api.mercadolibre.com/sites/MLB/search"

params = {
    "q": "Hot Wheels Car Culture",
    "limit": 10
}

r = requests.get(
    url,
    headers=headers,
    params=params,
    timeout=30
)

print("STATUS:", r.status_code)

if r.status_code != 200:
    print(r.text)
    raise SystemExit(1)

dados = r.json()

resultados = dados.get("results", [])

print("RESULTADOS:", len(resultados))
print("=" * 80)

for item in resultados:
    print("ID:", item.get("id"))
    print("TÍTULO:", item.get("title"))
    print("PREÇO:", item.get("price"))
    print("MOEDA:", item.get("currency_id"))
    print("CONDIÇÃO:", item.get("condition"))
    print("LINK:", item.get("permalink"))
    print("-" * 80)
