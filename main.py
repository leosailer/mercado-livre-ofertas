import os
import re
import requests

API_KEY = os.getenv("SERPAPI_KEY")

BUSCAS = [
    'site:mercadolivre.com.br ("Hot Wheels" OR "Hot Wheels Premium") ("1:64" OR miniatura) -usado',
    'site:mercadolivre.com.br ("Matchbox") ("1:64" OR miniatura) -usado',
    'site:mercadolivre.com.br ("Mini GT" OR "Kaido House") ("1:64") -usado',
    'site:mercadolivre.com.br ("Tarmac Works" OR "Tomica") ("1:64") -usado',
    'site:mercadolivre.com.br ("Majorette" OR "Greenlight" OR "M2 Machines") ("1:64") -usado'
]

URL = "https://serpapi.com/search.json"


def preco_rich_snippet(item):
    rich = item.get("rich_snippet", {})

    for posicao in ["top", "bottom"]:
        dados = rich.get(posicao, {}).get("detected_extensions", {})

        preco = dados.get("price")
        moeda = dados.get("currency")

        if preco is not None:
            try:
                return float(preco), f"rich_snippet ({moeda or 'moeda não informada'})"
            except:
                pass

    return None, None


def preco_do_texto(texto):
    valores = re.findall(r'R\$\s*([\d\.]+,\d{2})', texto)

    precos = []

    for valor in valores:
        try:
            numero = float(valor.replace(".", "").replace(",", "."))
            precos.append(numero)
        except:
            pass

    if not precos:
        return None, None

    # Evita pegar valores pequenos que normalmente são parcelas.
    # Como fallback, usa o MAIOR valor em R$ encontrado no snippet.
    return max(precos), "snippet"


links_vistos = set()
resultados = []

for busca in BUSCAS:

    parametros = {
        "engine": "google",
        "q": busca,
        "hl": "pt-br",
        "gl": "br",
        "num": 10,
        "api_key": API_KEY
    }

    resposta = requests.get(URL, params=parametros, timeout=30)

    if resposta.status_code != 200:
        print("ERRO NA BUSCA:", resposta.status_code)
        continue

    dados = resposta.json()

    for item in dados.get("organic_results", []):

        titulo = item.get("title", "")
        link = item.get("link", "")
        trecho = item.get("snippet", "")

        if "lista.mercadolivre.com.br" in link:
            continue

        if "mercadolivre.com.br" not in link:
            continue

        if link in links_vistos:
            continue

        links_vistos.add(link)

        preco, fonte = preco_rich_snippet(item)

        if preco is None:
            preco, fonte = preco_do_texto(trecho)

        resultados.append({
            "titulo": titulo,
            "link": link,
            "preco": preco,
            "fonte": fonte,
            "trecho": trecho
        })


resultados.sort(
    key=lambda x: (
        x["preco"] is None,
        x["preco"] if x["preco"] else 999999
    )
)

print("\nPRODUTOS ENCONTRADOS:", len(resultados))
print()

for item in resultados[:30]:

    print("TITULO:", item["titulo"])

    if item["preco"] is not None:
        print(f"PRECO: R$ {item['preco']:.2f}")
        print("FONTE DO PRECO:", item["fonte"])
    else:
        print("PRECO: não identificado")

    print("LINK:", item["link"])
    print("TRECHO:", item["trecho"])
    print("-" * 80)
