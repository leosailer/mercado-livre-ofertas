import os
import requests

API_KEY = os.getenv("SERPAPI_KEY")

url = "https://serpapi.com/search.json"

parametros = {
    "engine": "google",
    "q": 'site:mercadolivre.com.br ("hot wheels" OR matchbox OR "mini gt" OR diecast OR "1:64") ("promoção" OR oferta OR desconto OR "R$")',
    "hl": "pt-br",
    "gl": "br",
    "num": 10,
    "api_key": API_KEY
}

resposta = requests.get(url, params=parametros, timeout=30)

print("STATUS:", resposta.status_code)

if resposta.status_code != 200:
    print("ERRO:")
    print(resposta.text)
    exit()

dados = resposta.json()

resultados = dados.get("organic_results", [])

print("\nRESULTADOS ENCONTRADOS:", len(resultados))
print()

for item in resultados:
    titulo = item.get("title", "")
    link = item.get("link", "")
    trecho = item.get("snippet", "")

    if "mercadolivre.com.br" in link:
        print("TITULO:", titulo)
        print("LINK:", link)
        print("TRECHO:", trecho)
        print("-" * 70)
