import os
import re
import statistics
import requests

API_KEY = os.getenv("SERPAPI_KEY")
URL = "https://serpapi.com/search.json"


# =========================================================
# CARROS / MARCAS QUE QUEREMOS CAÇAR
# =========================================================

CARROS_TOP = [
    "Ferrari",
    "Porsche",
    "Lamborghini",
    "McLaren",
    "Aston Martin",
    "Koenigsegg",
    "Bugatti",
    "Pagani",
    "BMW",
    "Mercedes AMG",
    "Audi",
    "Nissan Skyline",
    "Nissan GT-R",
    "Toyota Supra",
    "Mazda RX-7",
    "Honda NSX",
    "Honda Civic Type R",
    "Mitsubishi Lancer Evolution",
    "Subaru Impreza",
    "Ford Mustang",
    "Corvette"
]


# =========================================================
# TENDÊNCIAS / LANÇAMENTOS QUENTES
# Atualizado em agosto/2026
# =========================================================

TENDENCIAS_QUENTES = [

    # HOT WHEELS 2026
    "Ferrari F40 RLC",
    "Ferrari Testarossa",
    "Ferrari 250 GTO",
    "Ferrari Enzo",
    "Ferrari 499P",
    "Ferrari F50",
    "Porsche 993 GT2",
    "Porsche 917K",
    "Nissan Skyline BNR32",
    "NISMO 270R",
    "Mercedes 190E Evo II",

    # MINI GT
    "Toyota Supra VeilSide",
    "Lamborghini Countach",
    "Mazda RX-7 RE-Amemiya",
    "Nissan Skyline Kenmeri",
    "Nissan Skyline R33",
    "Nissan GT-R Nismo 2024",
    "Porsche Carrera GT",
    "Lamborghini Murcielago LB",

    # TARMAC WORKS
    "URAS Skyline ER34",
    "Porsche 928",
    "Ford Mustang GTD",
    "Koenigsegg Agera RS",
    "Porsche 911 Carrera RS",
    "Porsche GT3 RS",
    "Nissan VeilSide Fairlady Z",
    "Toyota GR Corolla"
]


# =========================================================
# BUSCAS
# =========================================================

BUSCAS = [

    # HOT WHEELS PREMIUM / ESPECIAIS
    'site:mercadolivre.com.br '
    '("Hot Wheels Premium" OR "Hot Wheels Car Culture" OR '
    '"Hot Wheels Boulevard" OR "Hot Wheels Silver Series" OR '
    '"Hot Wheels Team Transport" OR "Hot Wheels RLC" OR '
    '"Hot Wheels Pop Culture") '
    '("Ferrari" OR "Porsche" OR "Lamborghini" OR "McLaren") '
    '-usado',

    # HOT WHEELS JAPONESES / EUROPEUS
    'site:mercadolivre.com.br '
    '("Hot Wheels Premium" OR "Car Culture" OR "Boulevard") '
    '("Skyline" OR "GT-R" OR "Supra" OR "RX-7" OR '
    '"BMW" OR "Mercedes" OR "Audi") '
    '-usado',

    # FERRARI ESPECIFICAMENTE
    'site:mercadolivre.com.br '
    '"Hot Wheels" '
    '("Ferrari Testarossa" OR "Ferrari 250 GTO" OR '
    '"Ferrari F40" OR "Ferrari F50" OR '
    '"Ferrari 499P" OR "LaFerrari" OR "Enzo Ferrari") '
    '-usado',

    # MINI GT
    'site:mercadolivre.com.br '
    '"Mini GT" '
    '("Ferrari" OR "Porsche" OR "Lamborghini" OR '
    '"McLaren" OR "Skyline" OR "GT-R" OR '
    '"Supra" OR "RX-7") '
    '-usado',

    # MINI GT OFERTAS
    'site:mercadolivre.com.br '
    '"Mini GT" '
    '("oferta" OR "promoção" OR desconto OR "R$") '
    '-usado',

    # KAIDO HOUSE
    'site:mercadolivre.com.br '
    '"Kaido House" '
    '("Skyline" OR "Datsun" OR "Honda" OR "Nissan" OR oferta) '
    '-usado',

    # TARMAC WORKS
    'site:mercadolivre.com.br '
    '"Tarmac Works" '
    '("Porsche" OR "Skyline" OR "GT-R" OR "Ferrari" OR '
    '"Mustang" OR "Koenigsegg" OR "Toyota") '
    '-usado',

    # OUTRAS MARCAS PREMIUM 1:64
    'site:mercadolivre.com.br '
    '("Pop Race" OR "Inno64" OR "Greenlight" OR '
    '"M2 Machines" OR "Tomica Premium" OR '
    '"Majorette Premium") '
    '("Ferrari" OR "Porsche" OR "Lamborghini" OR '
    '"Skyline" OR "Supra") '
    '-usado',

    # LANÇAMENTOS / NOVIDADES
    'site:mercadolivre.com.br '
    '("Hot Wheels Premium" OR "Mini GT" OR "Tarmac Works") '
    '("2026" OR lançamento OR novidade OR "novo") '
    '-usado',

    # DESCONTOS
    'site:mercadolivre.com.br '
    '("Hot Wheels Premium" OR "Mini GT" OR "Kaido House" OR '
    '"Tarmac Works") '
    '("15% OFF" OR "20% OFF" OR "25% OFF" OR '
    '"30% OFF" OR promoção OR oferta) '
    '-usado'
]


# =========================================================
# FILTROS
# =========================================================

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
    "pop culture",
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
    "Tomica": (30, 600),
    "Pop Race": (50, 700),
    "Inno64": (50, 700)
}


# =========================================================
# FUNÇÕES
# =========================================================

def identificar_marca(titulo):

    t = titulo.lower()

    if "kaido house" in t:
        return "Kaido House"

    if "mini gt" in t:
        return "Mini GT"

    if "tarmac works" in t:
        return "Tarmac Works"

    if "pop race" in t:
        return "Pop Race"

    if "inno64" in t or "inno 64" in t:
        return "Inno64"

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


def identificar_carro_top(titulo):

    t = titulo.lower()

    encontrados = []

    for carro in CARROS_TOP:

        if carro.lower() in t:
            encontrados.append(carro)

    return encontrados


def identificar_tendencia(titulo):

    t = titulo.lower()

    for tendencia in TENDENCIAS_QUENTES:

        palavras = tendencia.lower().split()

        # Considera tendência quando pelo menos 2 termos coincidem
        coincidencias = sum(
            1 for palavra in palavras
            if palavra in t
        )

        if coincidencias >= 2:
            return tendencia

    return None


def link_valido(link):

    formatos = [
        "/p/",
        "/up/",
        "produto.mercadolivre.com.br/MLB-"
    ]

    return (
        link
        and any(x in link for x in formatos)
    )


def deve_excluir(titulo):

    t = titulo.lower()

    return any(
        palavra in t
        for palavra in PALAVRAS_EXCLUIR
    )


def hot_wheels_valido(titulo):

    t = titulo.lower()

    if "hot wheels" not in t:
        return True

    return any(
        palavra in t
        for palavra in HOT_WHEELS_PERMITIDOS
    )


def preco_valido(marca, preco):

    if preco is None:
        return False

    if marca not in FAIXAS_VALIDAS:
        return True

    minimo, maximo = FAIXAS_VALIDAS[marca]

    return minimo <= preco <= maximo


def extrair_precos_texto(texto):

    encontrados = re.findall(
        r'R\$\s*([\d\.]+,\d{2})',
        texto or ""
    )

    precos = []

    for valor in encontrados:

        try:

            numero = float(
                valor
                .replace(".", "")
                .replace(",", ".")
            )

            precos.append(numero)

        except:
            pass

    return precos


def preco_rich_snippet(item):

    rich = item.get(
        "rich_snippet",
        {}
    )

    for posicao in [
        "top",
        "bottom"
    ]:

        detected = rich.get(
            posicao,
            {}
        ).get(
            "detected_extensions",
            {}
        )

        preco = detected.get(
            "price"
        )

        if preco is not None:

            try:
                return float(preco)

            except:
                pass

    return None


def detectar_desconto(
    trecho,
    preco_atual
):

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

            percentual = float(
                resultado.group(1)
            )

            if 0 < percentual <= 80:
                return percentual


    precos = extrair_precos_texto(
        trecho
    )

    candidatos = [
        p for p in precos
        if preco_atual < p <= preco_atual * 2.5
    ]

    if not candidatos:
        return None

    preco_anterior = max(
        candidatos
    )

    desconto = (
        (
            preco_anterior
            - preco_atual
        )
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
        "pop race",
        "inno64",
        "premium",
        "miniatura",
        "diecast",
        "carrinho",
        "escala",
        "1:64",
        "1/64"
    ]

    for palavra in remover:
        texto = texto.replace(
            palavra,
            " "
        )

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
        palavra
        for palavra in texto.split()
        if (
            len(palavra) >= 3
            and palavra not in ignorar
        )
    }


def calcular_mediana_mercado(
    item,
    todos
):

    palavras = palavras_modelo(
        item["titulo"]
    )

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

        outras = palavras_modelo(
            outro["titulo"]
        )

        comuns = palavras.intersection(
            outras
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


# =========================================================
# EXECUTA AS BUSCAS
# =========================================================

links_vistos = set()
resultados = []


for numero, busca in enumerate(
    BUSCAS,
    start=1
):

    print(
        f"Executando busca "
        f"{numero}/{len(BUSCAS)}..."
    )

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
        "organic_results",
        []
    ):

        titulo = item.get(
            "title",
            ""
        )

        link = item.get(
            "link",
            ""
        )

        trecho = item.get(
            "snippet",
            ""
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

            precos = extrair_precos_texto(
                trecho
            )

            validos = [
                p for p in precos
                if preco_valido(
                    marca,
                    p
                )
            ]

            if validos:
                preco = validos[0]


        if not preco_valido(
            marca,
            preco
        ):
            preco = None


        desconto = detectar_desconto(
            trecho,
            preco
        )


        carros_top = identificar_carro_top(
            titulo
        )


        tendencia = identificar_tendencia(
            titulo
        )


        resultados.append({

            "titulo": titulo,

            "marca": marca,

            "preco": preco,

            "desconto": desconto,

            "carros_top": carros_top,

            "tendencia": tendencia,

            "link": link
        })


# =========================================================
# CLASSIFICA AS OFERTAS
# =========================================================

ofertas = []


for item in resultados:

    preco = item["preco"]
    marca = item["marca"]
    desconto = item["desconto"]


    mediana = calcular_mediana_mercado(
        item,
        resultados
    )


    item["mediana"] = mediana
    item["status"] = None


    # DESCONTO >= 15%

    if (
        desconto is not None
        and desconto >= 15
    ):

        item["status"] = (
            "🔥🔥 DESCONTO DE 15% OU MAIS"
        )


    # HOT WHEELS PREMIUM / ESPECIAL < 99

    elif (
        marca == "Hot Wheels"
        and preco is not None
        and preco < 99
    ):

        item["status"] = (
            "🔥 HOT WHEELS ESPECIAL ABAIXO DE R$99"
        )


    # MINI GT < 150

    elif (
        marca == "Mini GT"
        and preco is not None
        and preco < 150
    ):

        item["status"] = (
            "🔥 MINI GT ABAIXO DE R$150"
        )


    # ABAIXO DO MERCADO

    elif (
        mediana is not None
        and preco is not None
        and preco <= mediana * 0.85
    ):

        item["status"] = (
            "🔥 ABAIXO DO MERCADO"
        )


    # MODELO QUENTE COM PREÇO IDENTIFICADO

    elif (
        item["tendencia"]
        and preco is not None
    ):

        item["status"] = (
            "🆕 MODELO QUENTE / LANÇAMENTO"
        )


    if item["status"]:
        ofertas.append(item)


# =========================================================
# ORDEM
# =========================================================

ordem = {

    "🔥🔥 DESCONTO DE 15% OU MAIS": 0,

    "🔥 HOT WHEELS ESPECIAL ABAIXO DE R$99": 1,

    "🔥 MINI GT ABAIXO DE R$150": 2,

    "🔥 ABAIXO DO MERCADO": 3,

    "🆕 MODELO QUENTE / LANÇAMENTO": 4
}


ofertas.sort(
    key=lambda x: (

        ordem.get(
            x["status"],
            99
        ),

        x["preco"]
        if x["preco"]
        else 999999
    )
)


# =========================================================
# RESULTADO
# =========================================================

print()
print("=" * 80)

print(
    "OFERTAS ENCONTRADAS:",
    len(ofertas)
)

print("=" * 80)
print()


for item in ofertas:

    print(
        item["status"]
    )

    print(
        "MARCA DIECAST:",
        item["marca"]
    )


    if item["carros_top"]:

        print(
            "CARRO TOP:",
            ", ".join(
                item["carros_top"]
            )
        )


    if item["tendencia"]:

        print(
            "🔥 TENDENCIA:",
            item["tendencia"]
        )


    print(
        "TITULO:",
        item["titulo"]
    )


    if item["preco"] is not None:

        print(
            f"PRECO: "
            f"R$ {item['preco']:.2f}"
        )


    if item["desconto"] is not None:

        print(
            f"DESCONTO: "
            f"{item['desconto']:.1f}%"
        )


    if item["mediana"] is not None:

        print(
            "MEDIANA MERCADO: "
            f"R$ {item['mediana']:.2f}"
        )


    print(
        "LINK:",
        item["link"]
    )

    print(
        "-" * 80
    )
