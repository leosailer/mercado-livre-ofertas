import os
import re
import requests

API_KEY = os.getenv("SERPAPI_KEY")

BUSCAS = [
    'site:mercadolivre.com.br "Hot Wheels" "1:64" -usado',
    'site:mercadolivre.com.br "Matchbox" "1:64" -usado',
    'site:mercadolivre.com.br ("Mini GT" OR "Kaido House") "1:64" -usado',
    'site:mercadolivre.com.br "Tarmac Works" "1:64" -usado',
    'site:mercadolivre.com.br ("Majorette" OR "Greenlight" OR "M2 Machines" OR "Tomica") "1:64" -usado'
]

URL = "https://serpapi.com/search.json"

# Você poderá mudar estes valores depois
LIMITES = {
    "Hot Wheels": 30,
    "Matchbox": 35,
    "Mini GT": 100,
    "Kaido House": 140,
    "Tarmac Works": 110,
    "Majorette": 60,
    "Greenlight": 110,
    "M2 Machines": 130,
    "Tomica": 90
}

PALAVRAS_EXCLUIR = [
    "expositor",
    "display",
    "estante",
    "prateleira",
    "garagem",
    "diorama",
    "adesivo",
    "roda avulsa",
    "pneu avulso",
    "case",
    "caixa organizadora",
    "suporte"
]


def identificar_marca(titulo):
    t = titulo.lower()

    if "kaido house" in t:
        return "Kaido House"
    if "mini gt" in t:
        return "Mini GT"
    if "tarmac works" in t:
        return "Tarmac Works"
    if "matchbox" in t:
        return "Matchbox"
    if "hot wheels" in t:
        return "Hot Wheels"
    if "majorette" in t:
        return "Majorette"
    if "greenlight" in t:
        return "Greenlight"
    if "m2 machines" in t:
        return "M2 Machines"
    if "tomica" in t:
        return "Tomica"

    return "Outra"


def deve_excluir(titulo):
    titulo = titulo.lower()

    for palavra in PALAVRAS_EXCLUIR:
        if palavra in titulo:
            return True

    return False


def preco_rich_snippet(item):
    rich = item.get("rich_snippet", {})

    for posicao in ["top", "bottom"]:
        detected = rich.get(posicao, {}).get("detected_extensions", {})

        preco = detected.get("price")

        if preco is not None:
            try:
                return float(preco)
            except:
                pass

    return None


def preco_snippet(texto):
    valores = re.findall(r'R\$\s*([\d\.]+,\d{2})', texto)

    precos = []

    for valor in valores:
        try:
            numero = float(
                valor.replace(".", "").replace(",", ".")
            )
            precos.append(numero)
        except:
            pass

    if not precos:
        return None

    return max(precos)


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

    resposta = requests.get(
        URL,
        params=parametros,
        timeout=30
    )

    if resposta.status_code != 200:
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

        if deve_excluir(titulo):
            continue

        links_vistos.add(link)

        preco = preco_rich_snippet(item)

        if preco is None:
            preco = preco_snippet(trecho)

        marca = identificar_marca(titulo)

        status = "NORMAL"

        if preco and marca in LIMITES:

            limite = LIMITES[marca]

            if preco <= limite * 0.80:
                status = "🔥 PREÇO MUITO BOM"

            elif preco <= limite:
                status = "✅ PREÇO INTERESSANTE"

        resultados.append({
            "titulo": titulo,
            "marca": marca,
            "preco": preco,
            "status": status,
            "link": link
        })


# Primeiro aparecem os melhores
ordem = {
    "🔥 PREÇO MUITO BOM": 0,
    "✅ PREÇO INTERESSANTE": 1,
    "NORMAL": 2
}

resultados.sort(
    key=lambda x: (
        ordem[x["status"]],
        x["preco"] if x["preco"] else 999999
    )
)


print("\nCARRINHOS ENCONTRADOS:", len(resultados))
print()


for item in resultados[:40]:

    print(item["status"])
    print("MARCA:", item["marca"])
    print("TITULO:", item["titulo"])

    if item["preco"]:
        print(f"PRECO: R$ {item['preco']:.2f}")
    else:
        print("PRECO: não identificado")

    print("LINK:", item["link"])
    print("-" * 80)
