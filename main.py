import os
import requests

API_KEY = os.environ["SEARCHAPI_KEY"]

url = "https://www.searchapi.io/api/v1/search"

params = {
    "engine": "google_shopping",
    "q": "Hot Wheels Car Culture",
    "gl": "br",
    "hl": "pt-br",
    "location": "Brazil",
    "condition": "new",
    "api_key": API_KEY
}

print("=" * 80)
print("TESTE SEARCHAPI - GOOGLE SHOPPING BRASIL")
print("=" * 80)

r = requests.get(
    url,
    params=params,
    timeout=40
)

print("STATUS:", r.status_code)

if r.status_code != 200:
    print(r.text)
    raise SystemExit(1)

dados = r.json()

resultados = dados.get("shopping_results", [])

print("RESULTADOS:", len(resultados))
print("=" * 80)

for numero, item in enumerate(resultados[:10], start=1):

    print()
    print("PRODUTO", numero)
    print("TÍTULO:", item.get("title"))
    print("VENDEDOR:", item.get("seller"))
    print("PREÇO:", item.get("price"))
    print("PREÇO EXTRAÍDO:", item.get("extracted_price"))
    print("PREÇO ORIGINAL:", item.get("original_price"))
    print("DESCONTO/TAG:", item.get("tag"))
    print("ENTREGA:", item.get("delivery"))
    print("PRODUCT ID:", item.get("product_id"))
    print("PRODUCT TOKEN:", "SIM" if item.get("product_token") else "NÃO")
    print("PRODUCT LINK:", item.get("product_link"))
    print("-" * 80)

print()
print("=" * 80)

if resultados:
    print("🔥 SEARCHAPI FUNCIONOU.")
else:
    print("❌ API RESPONDEU, MAS NÃO RETORNOU PRODUTOS.")
