import os
import re
import statistics
import requests

API_KEY = os.getenv("SERPAPI_KEY")
URL = "https://serpapi.com/search.json"

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

TENDENCIAS_QUENTES = [
    ("Ferrari F40 RLC", ["ferrari", "f40", "rlc"]),
    ("Ferrari Testarossa", ["ferrari", "testarossa"]),
    ("Ferrari 250 GTO", ["ferrari", "250", "gto"]),
    ("Ferrari Enzo", ["ferrari", "enzo"]),
    ("Ferrari 499P", ["ferrari", "499p"]),
    ("Ferrari F50", ["ferrari", "f50"]),
    ("Porsche 993 GT2", ["porsche", "993", "gt2"]),
    ("Porsche 917K", ["porsche", "917k"]),
    ("Porsche Carrera GT", ["porsche", "carrera", "gt"]),
    ("Porsche 911 Carrera RS", ["porsche", "911", "carrera", "rs"]),
    ("Porsche 911 GT3 RS", ["porsche", "911", "gt3", "rs"]),
    ("Nissan Skyline BNR32", ["nissan", "skyline", "bnr32"]),
    ("NISMO 270R", ["nismo", "270r"]),
    ("Toyota Supra VeilSide", ["toyota", "supra", "veilside"]),
    ("Lamborghini Countach", ["lamborghini", "countach"]),
    ("Mazda RX-7 RE-Amemiya", ["mazda", "rx-7", "re-amemiya"]),
    ("Nissan Skyline R33", ["nissan", "skyline", "r33"]),
    ("Ford Mustang GTD", ["ford", "mustang", "gtd"]),
    ("Koenigsegg Agera RS", ["koenigsegg", "agera", "rs"])
]

BUSCAS = [
    'site:mercadolivre.com.br "Hot Wheels Premium" ("Ferrari" OR "Porsche" OR "Lamborghini" OR "McLaren" OR "BMW" OR "Mercedes" OR "Audi") ("R$ 49" OR "R$ 55" OR "R$ 59" OR "R$ 65" OR "R$ 69" OR oferta OR desconto) -usado',

    'site:mercadolivre.com.br ("Hot Wheels Car Culture" OR "Hot Wheels Boulevard" OR "Hot Wheels Silver Series" OR "Hot Wheels Pop Culture") ("Ferrari" OR "Porsche" OR "Skyline" OR "Supra" OR "RX-7") ("R$ 49" OR "R$ 59" OR "R$ 69" OR oferta) -usado',

    'site:mercadolivre.com.br "Hot Wheels Premium" "Ferrari" -usado',

    'site:mercadolivre.com.br "Hot Wheels Premium" "Porsche" -usado',

    'site:mercadolivre.com.br "Hot Wheels Premium" ("Skyline" OR "Supra" OR "RX-7") -usado',

    'site:mercadolivre.com.br "Mini GT" ("Ferrari" OR "Porsche" OR "Lamborghini" OR "McLaren" OR "Skyline" OR "GT-R" OR "Supra" OR "RX-7") -usado',

    'site:mercadolivre.com.br "Mini GT" ("R$ 99" OR "R$ 109" OR "R$ 119" OR "R$ 129" OR "R$ 139" OR "R$ 149") -usado',

    'site:mercadolivre.com.br "Kaido House" ("oferta" OR desconto OR promoção) -usado',

    'site:mercadolivre.com.br "Tarmac Works" ("oferta" OR desconto OR promoção) -usado',

    'site:mercadolivre.com.br ("Pop Race" OR "Inno64" OR "Greenlight" OR "M2 Machines" OR "Tomica Premium" OR "Majorette Premium") ("oferta" OR desconto OR promoção) -usado'
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


def texto_normalizado(texto):
    return re.sub(r'\s+', ' ', (texto or "").lower()).strip()


def identificar_marca(titulo, link):
    combinado = texto_normalizado(f"{titulo} {link}")

    if "kaido house" in combinado:
        return "Kaido House"
    if "mini gt" in combinado:
        return "Mini GT"
    if "tarmac works" in combinado:
        return "Tarmac Works"
    if "pop race" in combinado:
        return "Pop Race"
    if "inno64" in combinado or "inno 64" in combinado:
        return "Inno64"
    if "matchbox" in combinado:
        return "Matchbox"
    if "hot wheels" in combinado:
        return "Hot Wheels"
    if "majorette" in combinado:
        return "Majorette"
    if "greenlight" in combinado:
        return "Greenlight"
    if "m2 machines" in combinado:
        return "M2 Machines"
    if "tomica" in combinado:
        return "Tomica"

    return "Outra"


def identificar_carros_top(titulo):
    t = texto_normalizado(titulo)
    return [carro for carro in CARROS_TOP if carro.lower() in t]


def identificar_tendencia(titulo):
    t = texto_normalizado(titulo)

    for nome, termos in TENDENCIAS_QUENTES:
        if all(termo.lower() in t for termo in termos):
            return nome

    return None


def link_valido(link):
    formatos = [
        "/p/",
        "/up/",
        "produto.mercadolivre.com.br/MLB-"
    ]
    return bool(link) and any(f in link for f in formatos)


def deve_excluir(titulo):
    t = texto_normalizado(titulo)
    return any(p in t for p in PALAVRAS_EXCLUIR)


def hot_wheels_valido(titulo, link):
    combinado = texto_normalizado(f"{titulo} {link}")

    if "hot wheels" not in combinado:
        return True

    return any(p in combinado for p in HOT_WHEELS_PERMITIDOS)


def preco_valido(marca, preco):
    if preco is None:
        return False

    if marca not in FAIXAS_VALIDAS:
        return True

    minimo, maximo = FAIXAS_VALIDAS[marca]
    return minimo <= preco <= maximo


def extrair_precos_texto(texto):
    valores = re.findall(r'R\$\s*([\d\.]+,\d{2})', texto or "")
    precos = []

    for valor in valores:
        try:
            precos.append(
                float(valor.replace(".", "").replace(",", "."))
            )
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


links_vistos = set()
resultados = []

for numero, busca in enumerate(BUSCAS, start=1):

    print(f"Executando busca {numero}/{len(BUSCAS)}...")

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
        print("ERRO:", resposta.status_code)
        continue

    dados = resposta.json()

    for item in dados.get("organic_results", []):

        titulo = item.get("title", "")
        link = item.get("link", "")
        trecho = item.get("snippet", "")

        if not link_valido(link):
            continue

        if link in links_vistos:
            continue

        if deve_excluir(titulo):
            continue

        if not hot_wheels_valido(titulo, link):
            continue

        links_vistos.add(link)

        marca = identificar_marca(titulo, link)

        preco = preco_rich_snippet(item)

        if preco is None:
            precos = extrair_precos_texto(trecho)

            validos = [
                p for p in precos
                if preco_valido(marca, p)
            ]

            if validos:
                preco = validos[0]

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
            "carros_top": identificar_carros_top(titulo),
            "tendencia": identificar_tendencia(titulo),
            "link": link
        })


ofertas = []

for item in resultados:

    preco = item["preco"]
    marca = item["marca"]
    desconto = item["desconto"]

    item["status"] = None

    if desconto is not None and desconto >= 15:
        item["status"] = "🔥🔥 DESCONTO DE 15% OU MAIS"

    elif (
        marca == "Hot Wheels"
        and preco is not None
        and preco < 69
    ):
        item["status"] = "🚨 HOT WHEELS PREMIUM ABAIXO DE R$69"

    elif (
        marca == "Hot Wheels"
        and preco is not None
        and preco < 99
    ):
        item["status"] = "🔥 HOT WHEELS PREMIUM ABAIXO DE R$99"

    elif (
        marca == "Mini GT"
        and preco is not None
        and preco < 150
    ):
        item["status"] = "🔥 MINI GT ABAIXO DE R$150"

    if item["status"]:
        ofertas.append(item)


ordem = {
    "🚨 HOT WHEELS PREMIUM ABAIXO DE R$69": 0,
    "🔥🔥 DESCONTO DE 15% OU MAIS": 1,
    "🔥 HOT WHEELS PREMIUM ABAIXO DE R$99": 2,
    "🔥 MINI GT ABAIXO DE R$150": 3
}

ofertas.sort(
    key=lambda x: (
        ordem.get(x["status"], 99),
        x["preco"] if x["preco"] else 999999
    )
)


print()
print("=" * 80)
print("OFERTAS ENCONTRADAS:", len(ofertas))
print("=" * 80)
print()

for item in ofertas:

    print(item["status"])
    print("MARCA DIECAST:", item["marca"])

    if item["carros_top"]:
        print(
            "CARRO TOP:",
            ", ".join(item["carros_top"])
        )

    if item["tendencia"]:
        print(
            "🔥 TENDENCIA:",
            item["tendencia"]
        )

    print("TITULO:", item["titulo"])

    if item["preco"] is not None:
        print(
            f"PRECO: R$ {item['preco']:.2f}"
        )

    if item["desconto"] is not None:
        print(
            f"DESCONTO: {item['desconto']:.1f}%"
        )

    print("LINK:", item["link"])
    print("-" * 80)
