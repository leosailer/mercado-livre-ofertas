import os
import requests

ACCESS_TOKEN = os.getenv("ML_ACCESS_TOKEN")

URL = "https://api.mercadolibre.com/sites/MLB/search"

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}"
}

parametros = {
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

    print("\nOFERTAS ENCONTRADAS:\n")

    for produto in dados.get("results", []):
        print("Produto:", produto.get("title"))
        print("Preço: R$", produto.get("price"))
        print("Link:", produto.get("permalink"))
        print("-" * 50)

else:
    print("ERRO:")
    print(resposta.text)
