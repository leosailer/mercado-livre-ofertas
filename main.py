import os
import requests

ACCESS_TOKEN = os.getenv("ML_ACCESS_TOKEN")

URL = "https://api.mercadolibre.com/products/search"

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}"
}

parametros = {
    "status": "active",
    "site_id": "MLB",
    "q": "iphone",
    "limit": 5
}

resposta = requests.get(
    URL,
    headers=headers,
    params=parametros,
    timeout=30
)

print("STATUS:", resposta.status_code)

if resposta.status_code == 200:
    dados = resposta.json()

    print("\nPRODUTOS ENCONTRADOS:\n")

    for produto in dados.get("results", []):
        print("ID:", produto.get("id"))
        print("Nome:", produto.get("name"))
        print("-" * 50)

else:
    print("ERRO:")
    print(resposta.text)
