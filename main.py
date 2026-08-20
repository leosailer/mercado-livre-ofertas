import os
import re
import statistics
import requests

API_KEY = os.getenv("SERPAPI_KEY")
URL = "https://serpapi.com/search.json"

BUSCAS = [
    'site:mercadolivre.com.br "Hot Wheels Premium" ("Ferrari" OR "Porsche" OR "Lamborghini" OR "McLaren" OR "BMW" OR "Mercedes" OR "Audi" OR "Bugatti") -usado',
    'site:mercadolivre.com.br "Hot Wheels Premium" ("Nissan Skyline" OR "Toyota Supra" OR "Honda NSX" OR "Mazda RX-7" OR "Ford Mustang" OR "Corvette") -usado',
    'site:mercadolivre.com.br ("Hot Wheels Silver Series" OR "Hot Wheels Boulevard" OR "Hot Wheels Car Culture" OR "Hot Wheels Team Transport" OR "Hot Wheels RLC") -usado',
    'site:mercadolivre.com.br "Hot Wheels Premium" ("R$ 55" OR "R$ 59" OR "R$ 69" OR "R$ 79" OR oferta OR promoção OR desconto) -usado',

    'site:mercadolivre.com.br "Mini GT" "1:64" -usado',
    'site:mercadolivre.com.br "Mini GT" ("Ferrari" OR "Porsche" OR "Lamborghini" OR "Nissan" OR "BMW" OR "Mercedes" OR "McLaren") -usado',

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
    "roda avulsa",
    "pneu avulso",
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

FAIXAS_VALIDAS = {
    "Hot Wheels": (20, 1000),
    "Matchbox": (20, 600),
    "Mini GT": (40, 500),
    "Kaido House": (70, 700),
    "Tarmac Works": (50, 700),
    "Majorette": (20, 500),
    "Greenlight": (40, 600),
    "M2 Machines": (40, 700),
    "Tomica": (30, 600)
}


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
    formatos = [
        "/p/",
        "/up/",
        "produto.mercadolivre.com.br/MLB-"
    ]

    return link and any(x in link for x in formatos)


def deve_excluir(titulo):
    t = titulo.lower()
    return any(p in t for p in PALAVRAS_EXCLUIR)


def hot_wheels_valido(titulo):
    t = titulo.lower()

    if "hot wheels" not in t:
        return True

    return any(p in t for p in HOT_WHEELS_PERMITIDOS)


def preco_valido(marca, preco):
    if preco is None:
        return False

    if marca not in FAIXAS_VALIDAS:
        return True

    minimo, maximo = FAIXAS_VALIDAS[marca]
    return minimo <= preco <= maximo


def extrair_precos_texto(texto):
    valores = re.findall(
        r'R\$\s*([\d\.]+,\d{2})',
        texto or ""
    )

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
    if not preco_atual:
        return None

    padroes = [
        r'(\d{1,2})%\s*(?:OFF|off)',
        r'(\d{1,2})%\s*de\s*desconto',
        r'desconto\s*de\s*(\d{1,2})%'
    ]

    for padrao in padroes:
        resultado = re.search(
            padrao,
            trecho or "",
            re.IGNORECASE
        )

        if resultado:
            percentual = float(resultado.group(1))

            if 0 < percentual <= 80:
                return percentual

    precos = extrair_precos_texto(trecho)

    candidatos = [
        p for p in precos
        if preco_atual < p <= preco_atual * 2.5
    ]

    if not candidatos:
        return None

    preco_anterior = max(candidatos)

    desconto = (
        (preco_anterior - preco_atual)
        / preco_anterior
    ) * 100

    if 5 <= desconto <= 80:
        return desconto

    return None


def palavras_modelo(titulo):
    texto = titulo.lower()

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
        "miniatura",
        "diecast",
        "carrinho",
        "escala",
        "1:64",
        "1/64"
    ]

    for palavra in remover:
        texto = texto.replace(palavra, " ")

    texto = re.sub(
        r'[^a-z0-9áéíóúãõâêôç\s\-]',
        ' ',
        texto
    )

    ignorar = {
        "para",
        "com",
        "sem",
        "colecao",
        "coleção",
        "modelo",
        "carro",
        "novo",
        "produto"
    }

    return {
        p for p in texto.split()
        if len(p) >= 3 and p not in ignorar
    }


def calcular_media_mercado(item, todos):
    palavras = palavras_modelo(item["titulo"])
    semelhantes = []

    for outro in todos:

        if outro is item:
            continue

        if outro["marca"] != item["marca"]:
            continue

        if not preco_valido(
            outro["marca"],
            outro["preco"]
        ):
            continue

        outras_palavras = palavras_modelo(
            outro["titulo"]
        )

        comuns = palavras.intersection(
            outras_palavras
        )

        if len(comuns) < 3:
            continue

        semelhantes.append(
            outro["preco"]
        )

    if len(semelhantes) < 3:
        return None

    mediana = statistics.median(
        semelhantes
    )

    if not preco_valido(
        item["marca"],
        mediana
    ):
        return None

    return mediana


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
            "ERRO:",
            resposta.status_code
        )
        continue

    dados = resposta.json()

    for item in dados.get(
        "organic_results", []
    ):

        titulo = item.get("title", "")
        link = item.get("link", "")
        trecho = item.get("snippet", "")

        if not link_valido(link):
            continue

        if link in links_vistos:
            continue

        if deve_excluir(titulo):
            continue

        if not hot_wheels_valido(titulo):
            continue

        links_vistos.add(link)

        marca = identificar_marca(titulo)

        preco = preco_rich_snippet(item)

        if preco is None:
            precos = extrair_precos_texto(trecho)

            precos_validos = [
                p for p in precos
                if preco_valido(marca, p)
            ]

            if precos_validos:
                preco = precos_validos[0]

        if not preco_valido(marca, preco):
            preco = None

        desconto = detectar_desconto(
            trecho,
            preco
        )

        resultados.append({
            "titulo": titulo,
            "marca": marca,
            "preco": preco,
            "desconto": desconto,
            "link": link
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

    if desconto is not None and desconto >= 15:

        item["status"] = (
            "🔥 DESCONTO DE 15% OU MAIS"
        )

    elif (
        marca == "Hot Wheels"
        and preco is not None
        and "premium" in item["titulo"].lower()
        and preco < 99
    ):

        item["status"] = (
            "🔥 HOT WHEELS PREMIUM ABAIXO DE R$99"
        )

    elif (
        marca == "Mini GT"
        and preco is not None
        and preco < 150
    ):

        item["status"] = (
            "🔥 MINI GT ABAIXO DE R$150"
        )

    elif (
        media is not None
        and preco is not None
        and preco <= media * 0.85
    ):

        item["status"] = (
            "🔥 ABAIXO DO MERCADO"
        )

    if item["status"]:
        ofertas.append(item)


ordem = {
    "🔥 DESCONTO DE 15% OU MAIS": 0,
    "🔥 HOT WHEELS PREMIUM ABAIXO DE R$99": 1,
    "🔥 MINI GT ABAIXO DE R$150": 2,
    "🔥 ABAIXO DO MERCADO": 3
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


for item in ofertas:

    print(item["status"])
    print("MARCA:", item["marca"])
    print("TITULO:", item["titulo"])

    if item["preco"] is not None:
        print(
            f"PRECO: R$ {item['preco']:.2f}"
        )

    if item["desconto"] is not None:
        print(
            f"DESCONTO: {item['desconto']:.1f}%"
        )

    if item["media_mercado"] is not None:
        print(
            "MEDIANA DE PRODUTOS SEMELHANTES: "
            f"R$ {item['media_mercado']:.2f}"
        )

    print("LINK:", item["link"])
    print("-" * 80)
