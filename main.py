import os
import re
import statistics
import requests

API_KEY = os.getenv("SERPAPI_KEY")

URL = "https://serpapi.com/search.json"

BUSCAS = [
    'site:mercadolivre.com.br ("Hot Wheels Premium" OR "Hot Wheels Silver Series" OR "Hot Wheels Boulevard" OR "Hot Wheels Car Culture" OR "Hot Wheels Team Transport" OR "Hot Wheels RLC") -usado',
    'site:mercadolivre.com.br "Mini GT" "1:64" -usado',
    'site:mercadolivre.com.br "Kaido House" "1:64" -usado',
    'site:mercadolivre.com.br "Tarmac Works" "1:64" -usado',
    'site:mercadolivre.com.br ("Matchbox Collectors" OR "Matchbox Moving Parts" OR "Matchbox Premium") -usado',
    'site:mercadolivre.com.br ("Majorette Premium" OR "Greenlight" OR "M2 Machines" OR "Tomica Premium") "1:64" -usado'
]

PALAVRAS_EXCLUIR = [
    "expositor",
    "display",
    "estante",
    "prateleira",
    "garagem",
    "diorama",
    "adesivo",
    "roda",
    "pneu",
    "case",
    "caixa organizadora",
    "suporte",
    "protetor blister"
]

HOT_WHEELS_PERMITIDOS = [
    "premium",
    "silver series",
    "boulevard",
    "car culture",
    "team transport",
    "rlc",
    "collector",
    "collectors",
    "edição especial",
    "edicao especial",
    "anniversary",
    "aniversário",
    "aniversario"
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


def link_valido(link):
    if not link:
        return False

    formatos = [
        "/p/",
        "/up/",
        "produto.mercadolivre.com.br/MLB-"
    ]

    return any(f in link for f in formatos)


def deve_excluir(titulo):
    t = titulo.lower()

    return any(p in t for p in PALAVRAS_EXCLUIR)


def hot_wheels_valido(titulo):
    t = titulo.lower()

    if "hot wheels" not in t:
        return True

    return any(p in t for p in HOT_WHEELS_PERMITIDOS)


def extrair_precos_texto(texto):
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

    return precos


def preco_rich_snippet(item):
    rich = item.get("rich_snippet", {})

    for posicao in ["top", "bottom"]:
        detected = rich.get(
            posicao, {}
        ).get("detected_extensions", {})

        preco = detected.get("price")

        if preco is not None:
            try:
                return float(preco)
            except:
                pass

    return None


def detectar_desconto(trecho, preco_atual):
    if not trecho or not preco_atual:
        return None

    precos = extrair_precos_texto(trecho)

    if len(precos) < 2:
        return None

    candidatos_maiores = [
        p for p in precos
        if p > preco_atual
    ]

    if not candidatos_maiores:
        return None

    preco_anterior = max(candidatos_maiores)

    desconto = (
        (preco_anterior - preco_atual)
        / preco_anterior
    ) * 100

    if desconto < 0 or desconto > 90:
        return None

    return desconto


def palavra_chave_modelo(titulo):
    titulo = titulo.lower()

    remover = [
        "hot wheels",
        "mini gt",
        "kaido house",
        "tarmac works",
        "matchbox",
        "majorette",
        "greenlight",
        "m2 machines",
        "tomica",
        "premium",
        "1:64",
        "1/64",
        "miniatura",
        "carrinho",
        "diecast"
    ]

    for palavra in remover:
        titulo = titulo.replace(palavra, " ")

    titulo = re.sub(r'[^a-z0-9\s\-]', ' ', titulo)

    palavras = [
        p for p in titulo.split()
        if len(p) >= 3
    ]

    return " ".join(palavras[:5])


def calcular_media_mercado(item, todos):
    chave = palavra_chave_modelo(
        item["titulo"]
    )

    if len(chave) < 4:
        return None

    palavras = set(chave.split())

    semelhantes = []

    for outro in todos:

        if outro["preco"] is None:
            continue

        if outro["marca"] != item["marca"]:
            continue

        chave_outro = palavra_chave_modelo(
            outro["titulo"]
        )

        palavras_outro = set(
            chave_outro.split()
        )

        intersecao = palavras.intersection(
            palavras_outro
        )

        if len(intersecao) >= 2:
            semelhantes.append(
                outro["preco"]
            )

    if len(semelhantes) < 2:
        return None

    return statistics.median(semelhantes)


links_vistos = set()
resultados = []


for busca in BUSCAS:

    parametros = {
        "engine": "google",
        "q": busca,
        "hl": "pt-br",
        "gl": "br",
        "num": 20,
        "api_key": API_KEY
    }

    resposta = requests.get(
        URL,
        params=parametros,
        timeout=30
    )

    if resposta.status_code != 200:
        print(
            "Erro:",
            resposta.status_code
        )
        continue

    dados = resposta.json()

    for item in dados.get(
        "organic_results", []
    ):

        titulo = item.get(
            "title", ""
        )

        link = item.get(
            "link", ""
        )

        trecho = item.get(
            "snippet", ""
        )

        if not link_valido(link):
            continue

        if link in links_vistos:
            continue

        if deve_excluir(titulo):
            continue

        if not hot_wheels_valido(titulo):
            continue

        links_vistos.add(link)

        marca = identificar_marca(
            titulo
        )

        preco = preco_rich_snippet(
            item
        )

        if preco is None:
            precos_texto = extrair_precos_texto(
                trecho
            )

            if precos_texto:
                preco = max(precos_texto)

        desconto = detectar_desconto(
            trecho,
            preco
        )

        resultados.append({
            "titulo": titulo,
            "marca": marca,
            "preco": preco,
            "desconto": desconto,
            "link": link,
            "trecho": trecho
        })


ofertas = []


for item in resultados:

    preco = item["preco"]
    marca = item["marca"]
    desconto = item["desconto"]

    media = calcular_media_mercado(
        item,
        resultados
    )

    item["media_mercado"] = media
    item["status"] = None

    # Regra 1:
    # desconto real >= 15%
    if desconto is not None and desconto >= 15:
        item["status"] = "🔥 DESCONTO >= 15%"

    # Regra 2:
    # Mini GT abaixo de R$150
    elif (
        marca == "Mini GT"
        and preco is not None
        and preco < 150
    ):
        item["status"] = "🔥 MINI GT ABAIXO DE R$150"

    # Regra 3:
    # demais abaixo da mediana
    elif (
        media is not None
        and preco is not None
        and preco <= media * 0.85
    ):
        item["status"] = "🔥 ABAIXO DO MERCADO"

    elif (
        media is not None
        and preco is not None
        and preco < media
    ):
        item["status"] = "✅ BOM PREÇO"

    if item["status"]:
        ofertas.append(item)


ordem = {
    "🔥 DESCONTO >= 15%": 0,
    "🔥 MINI GT ABAIXO DE R$150": 1,
    "🔥 ABAIXO DO MERCADO": 2,
    "✅ BOM PREÇO": 3
}


ofertas.sort(
    key=lambda x: (
        ordem.get(x["status"], 99),
        x["preco"] if x["preco"] else 999999
    )
)


print()
print(
    "OFERTAS ENCONTRADAS:",
    len(ofertas)
)
print()


for item in ofertas[:50]:

    print(item["status"])
    print("MARCA:", item["marca"])
    print("TITULO:", item["titulo"])

    if item["preco"] is not None:
        print(
            f"PRECO: R$ {item['preco']:.2f}"
        )

    if item["desconto"] is not None:
        print(
            f"DESCONTO: "
            f"{item['desconto']:.1f}%"
        )

    if item["media_mercado"] is not None:
        print(
            f"PRECO MEDIANO ENCONTRADO: "
            f"R$ {item['media_mercado']:.2f}"
        )

    print("LINK:", item["link"])
    print("-" * 80)
