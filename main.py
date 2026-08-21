import os
import requests

TOKEN = os.environ["ML_ACCESS_TOKEN"]

headers = {
    "Authorization": f"Bearer {TOKEN}"
}

url = "https://api.mercadolibre.com/products/search"

params = {
    "status": "active",
    "site_id": "MLB",
    "q": "Hot Wheels Car Culture",
    "limit": 20
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

print("TOTAL:", dados.get("paging", {}).get("total"))
print("RESULTADOS:", len(dados.get("results", [])))
print("=" * 80)

for produto in dados.get("results", []):
    print("PRODUCT ID:", produto.get("id"))
    print("NOME:", produto.get("name"))
    print("STATUS:", produto.get("status"))
    print("DOMÍNIO:", produto.get("domain_id"))
    print("-" * 80)
