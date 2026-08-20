import os
import requests

API_KEY = os.getenv("SERPAPI_KEY")

BUSCAS = [
    'site:mercadolivre.com.br ("Hot Wheels" OR "Hot Wheels Premium") ("1:64" OR miniatura) -usado',
    'site:mercadolivre.com.br ("Matchbox") ("1:64" OR miniatura) -usado',
    'site:mercadolivre.com.br ("Mini GT" OR "Kaido House") ("1:64") -usado',
    'site:mercadolivre.com.br ("Tarmac Works" OR "Tomica") ("1:64") -usado',
    'site:mercadolivre.com.br ("Majorette" OR "Greenlight" OR "M2 Machines") ("1:64") -usado'
]

url = "https://serpapi.com/search.json"

links_vistos = set()
resultados_finais = []

for busca in BUSCAS:

    parametros = {
        "engine": "google",
        "q": busca,
        "hl": "pt-br",
        "gl": "br",
        "num": 10,
        "api_key": API_KEY
    }

    resposta = requests.get(url, params=parametros, timeout=30)

    if resposta.status_code != 200:
        print("ERRO NA BUSCA:", resposta.status_code)
        continue

    dados = resposta.json()

    for item in dados.get("organic_results", []):

        titulo = item.get("title", "")
        link = item.get("link", "")
        trecho = item.get("snippet", "")

        # Ignora páginas gerais de pesquisa
        if "lista.mercadolivre.com.br" in link:
            continue

        # Evita resultados repetidos
        if link in links_vistos:
            continue

        # Só Mercado Livre
        if "mercadolivre.com.br" not in link:
            continue

        links_vistos.add(link)

        resultados_finais.append({
            "titulo": titulo,
            "link": link,
            "trecho": trecho
        })

print("\nOFERTAS / PRODUTOS ENCONTRADOS:", len(resultados_finais))
print()

for item in resultados_finais[:30]:
    print("TITULO:", item["titulo"])
    print("LINK:", item["link"])
    print("TRECHO:", item["trecho"])
    print("-" * 80)
