import os
import re
import json
import smtplib
import requests
import unicodedata

from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


# ============================================================
# CONFIGURAÇÕES
# ============================================================

SEARCHAPI_KEY = os.environ["SEARCHAPI_KEY"]

EMAIL_DESTINO = os.environ["EMAIL_DESTINO"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]

SEARCH_URL = "https://www.searchapi.io/api/v1/search"

HISTORICO_ARQUIVO = "ofertas_vistas.json"
LINKS_ARQUIVO = "links_para_afiliado.txt"

MAX_RESULTADOS_EMAIL = 20


# ============================================================
# BUSCAS
# ============================================================

BUSCAS = [

    # Hot Wheels Premium
    'Hot Wheels Premium Car Culture Boulevard',

    # Linhas Car Culture
    'Hot Wheels Car Culture Modern Classics Japan Historics Race Day',

    # Outras linhas premium
    'Hot Wheels Premium Pop Culture Fast Furious Team Transport',

    # Silver
    'Hot Wheels Silver Series',

    # Modelos premium procurados
    'Hot Wheels Premium Ferrari Porsche Skyline Supra RX-7 NSX Lamborghini',

    # Marcas premium 1:64
    'Mini GT Kaido House Tarmac Works Pop Race Inno64',
]


# ============================================================
# TERMOS HOT WHEELS PREMIUM
# ============================================================

SERIES_PREMIUM = [

    "car culture",
    "boulevard",
    "pop culture",
    "team transport",
    "fast furious",
    "fast & furious",

    "modern classics",
    "japan historics",
    "race day",
    "circuit legends",
    "thrill climbers",
    "mountain drifters",
    "deutschland design",
    "ronin run",
    "exotic envy",
    "slide street",
    "power trip",
    "vintage racing",

    "premium",
    "elite 64",
    "rlc",
]


# ============================================================
# MODELOS DE ALTO INTERESSE
# ============================================================

MODELOS_TOP = [

    "ferrari",
    "porsche",

    "skyline",
    "r32",
    "r33",
    "r34",
    "gtr",
    "gt-r",

    "supra",

    "rx-7",
    "rx7",

    "nsx",

    "lamborghini",
    "mclaren",

    "bmw",
    "audi",

    "mustang",

    "civic",
    "s2000",

    "silvia",
    "180sx",
    "240sx",

    "datsun",
    "911",

    "evolution",
    "lancer",
]


# ============================================================
# LOJAS INTERNACIONAIS BLOQUEADAS
# ============================================================

LOJAS_BLOQUEADAS = [

    "aliexpress",
    "ebay",
    "temu",
    "etsy",
    "banggood",
    "dhgate",
    "alibaba",
]


# ============================================================
# PALAVRAS QUE INDICAM IMPORTAÇÃO
# ============================================================

TERMOS_IMPORTACAO = [

    "internacional",
    "importação",
    "importacao",
    "produto internacional",
    "compra internacional",
    "envio internacional",
    "international",
    "imported",
]


# ============================================================
# NORMALIZAÇÃO
# ============================================================

def normalizar(texto):

    if texto is None:
        return ""

    texto = str(texto).lower()

    texto = unicodedata.normalize(
        "NFKD",
        texto
    )

    texto = "".join(
        c for c in texto
        if not unicodedata.combining(c)
    )

    return texto


# ============================================================
# PREÇO
# ============================================================

def pegar_preco(item):

    preco = item.get("extracted_price")

    if preco is not None:

        try:
            return float(preco)

        except:
            pass

    texto = item.get("price")

    if not texto:
        return None

    texto = str(texto)

    texto = texto.replace("R$", "")
    texto = texto.strip()

    # brasileiro
    texto = texto.replace(".", "")
    texto = texto.replace(",", ".")

    match = re.search(
        r"\d+(?:\.\d+)?",
        texto
    )

    if not match:
        return None

    try:
        return float(match.group())

    except:
        return None


# ============================================================
# PREÇO ORIGINAL
# ============================================================

def pegar_preco_original(item):

    preco = item.get("original_price")

    if preco is None:
        return None

    if isinstance(preco, (int, float)):
        return float(preco)

    texto = str(preco)

    texto = texto.replace("R$", "")
    texto = texto.strip()

    texto = texto.replace(".", "")
    texto = texto.replace(",", ".")

    match = re.search(
        r"\d+(?:\.\d+)?",
        texto
    )

    if not match:
        return None

    try:
        return float(match.group())

    except:
        return None


# ============================================================
# DESCONTO
# ============================================================

def calcular_desconto(preco, antigo):

    if not preco:
        return 0

    if not antigo:
        return 0

    if antigo <= preco:
        return 0

    return round(
        ((antigo - preco) / antigo) * 100,
        1
    )


# ============================================================
# IDENTIFICAR MARCA
# ============================================================

def identificar_marca(titulo):

    t = normalizar(titulo)

    if "kaido house" in t:
        return "Kaido House"

    if "mini gt" in t or "minigt" in t:
        return "Mini GT"

    if "tarmac works" in t:
        return "Tarmac Works"

    if "pop race" in t:
        return "Pop Race"

    if "inno64" in t or "inno 64" in t:
        return "Inno64"

    if "hot wheels" in t:
        return "Hot Wheels"

    return None


# ============================================================
# IDENTIFICAR SÉRIE
# ============================================================

def identificar_serie(titulo):

    t = normalizar(titulo)

    mapa = [

        ("silver series", "Silver Series"),
        ("modern classics", "Modern Classics"),
        ("japan historics", "Japan Historics"),
        ("race day", "Race Day"),
        ("circuit legends", "Circuit Legends"),
        ("thrill climbers", "Thrill Climbers"),
        ("mountain drifters", "Mountain Drifters"),
        ("deutschland design", "Deutschland Design"),
        ("ronin run", "Ronin Run"),
        ("exotic envy", "Exotic Envy"),
        ("slide street", "Slide Street"),
        ("power trip", "Power Trip"),
        ("vintage racing", "Vintage Racing"),
        ("team transport", "Team Transport"),
        ("boulevard", "Boulevard"),
        ("pop culture", "Pop Culture"),
        ("fast furious", "Fast & Furious"),
        ("fast & furious", "Fast & Furious"),
        ("elite 64", "Elite 64"),
        ("rlc", "RLC"),
        ("car culture", "Car Culture"),
    ]

    for termo, nome in mapa:

        if termo in t:
            return nome

    if "premium" in t:
        return "Premium"

    return ""


# ============================================================
# LOJA INTERNACIONAL
# ============================================================

def loja_bloqueada(item):

    vendedor = normalizar(
        item.get("seller")
    )

    titulo = normalizar(
        item.get("title")
    )

    combinado = vendedor + " " + titulo

    for loja in LOJAS_BLOQUEADAS:

        if loja in combinado:
            return True

    for termo in TERMOS_IMPORTACAO:

        if normalizar(termo) in combinado:
            return True

    return False


# ============================================================
# KIT / LOTE
# ============================================================

def parece_kit(titulo):

    t = normalizar(titulo)

    termos = [

        "set completo",
        "kit com",
        "kit de",
        "lote",
        "colecao completa",
        "coleção completa",
        "5 miniaturas",
        "10 miniaturas",
        "pack",
        "multipack",
    ]

    for termo in termos:

        if normalizar(termo) in t:
            return True

    return False


# ============================================================
# ESCALA ERRADA
# ============================================================

def escala_errada(titulo):

    t = normalizar(titulo)

    escalas = [

        "1:18",
        "1/18",

        "1:24",
        "1/24",

        "1:32",
        "1/32",

        "1:36",
        "1/36",

        "1:43",
        "1/43",
    ]

    for escala in escalas:

        if escala in t:
            return True

    return False


# ============================================================
# PRODUTO DE INTERESSE
# ============================================================

def produto_interessante(item):

    titulo = item.get("title", "")

    marca = identificar_marca(titulo)

    if not marca:
        return False

    if loja_bloqueada(item):
        return False

    if escala_errada(titulo):
        return False

    if parece_kit(titulo):
        return False

    t = normalizar(titulo)

    if marca == "Hot Wheels":

        if "silver series" in t:
            return True

        for serie in SERIES_PREMIUM:

            if serie in t:
                return True

        return False

    return True


# ============================================================
# FILTRO DE PREÇO
# ============================================================

def preco_aceitavel(marca, serie, preco):

    if preco is None:
        return False

    # Evitar preço obviamente quebrado
    if preco < 20:
        return False

    if marca == "Hot Wheels":

        if serie == "Silver Series":
            return preco <= 80

        if serie in [
            "Team Transport",
            "Elite 64",
            "RLC"
        ]:
            return preco <= 180

        return preco <= 100

    if marca == "Mini GT":
        return preco <= 150

    if marca == "Kaido House":
        return preco < 199

    if marca == "Tarmac Works":
        return preco <= 170

    if marca == "Pop Race":
        return preco <= 170

    if marca == "Inno64":
        return preco <= 180

    return False


# ============================================================
# SCORE
# ============================================================

def calcular_score(oferta):

    score = 0

    titulo = normalizar(
        oferta["titulo"]
    )

    preco = oferta["preco"]
    marca = oferta["marca"]
    serie = oferta["serie"]
    desconto = oferta["desconto"]

    # --------------------------------------------------------
    # MODELOS TOP
    # --------------------------------------------------------

    for modelo in MODELOS_TOP:

        if modelo in titulo:
            score += 8

    # --------------------------------------------------------
    # HOT WHEELS
    # --------------------------------------------------------

    if marca == "Hot Wheels":

        if serie == "Car Culture":
            score += 15

        elif serie in [
            "Modern Classics",
            "Japan Historics",
            "Race Day",
            "Circuit Legends",
            "Thrill Climbers",
            "Mountain Drifters",
            "Deutschland Design",
            "Ronin Run",
            "Exotic Envy",
            "Slide Street",
            "Power Trip",
            "Vintage Racing",
        ]:
            score += 18

        elif serie == "Boulevard":
            score += 18

        elif serie == "Fast & Furious":
            score += 16

        elif serie == "Pop Culture":
            score += 12

        elif serie == "Silver Series":
            score += 10

        elif serie == "Team Transport":
            score += 10

        elif serie in ["Elite 64", "RLC"]:
            score += 15

        elif serie == "Premium":
            score += 10

        if preco <= 55:
            score += 35

        elif preco <= 65:
            score += 28

        elif preco <= 75:
            score += 20

        elif preco <= 85:
            score += 12

        elif preco <= 95:
            score += 5

    # --------------------------------------------------------
    # MINI GT
    # --------------------------------------------------------

    elif marca == "Mini GT":

        score += 15

        if preco <= 100:
            score += 30

        elif preco <= 120:
            score += 22

        elif preco <= 135:
            score += 14

        else:
            score += 5

    # --------------------------------------------------------
    # KAIDO
    # --------------------------------------------------------

    elif marca == "Kaido House":

        score += 20

        if preco <= 140:
            score += 35

        elif preco <= 160:
            score += 25

        elif preco <= 180:
            score += 15

        else:
            score += 7

    # --------------------------------------------------------
    # OUTRAS
    # --------------------------------------------------------

    else:

        score += 10

        if preco <= 110:
            score += 25

        elif preco <= 140:
            score += 15

        else:
            score += 5

    # --------------------------------------------------------
    # DESCONTO
    # --------------------------------------------------------

    if desconto >= 30:
        score += 30

    elif desconto >= 20:
        score += 20

    elif desconto >= 15:
        score += 12

    elif desconto >= 10:
        score += 5

    # --------------------------------------------------------
    # MERCADO LIVRE
    # --------------------------------------------------------

    vendedor = normalizar(
        oferta["vendedor"]
    )

    if "mercadolivre" in vendedor:
        score += 8

    return score


# ============================================================
# CLASSIFICAÇÃO
# ============================================================

def classificar(score):

    if score >= 65:
        return "🚨 IMPERDÍVEL"

    if score >= 45:
        return "🔥 BOA OFERTA"

    return "👀 INTERESSANTE"


# ============================================================
# BUSCAR SHOPPING
# ============================================================

def buscar_shopping(termo):

    params = {

        "engine": "google_shopping",

        "q": termo,

        "gl": "br",

        "hl": "pt-br",

        "location": "Brazil",

        "condition": "new",

        "api_key": SEARCHAPI_KEY,
    }

    r = requests.get(
        SEARCH_URL,
        params=params,
        timeout=45
    )

    if r.status_code != 200:

        print(
            "ERRO SEARCHAPI:",
            r.status_code
        )

        print(
            r.text[:500]
        )

        return []

    return r.json().get(
        "shopping_results",
        []
    )


# ============================================================
# HISTÓRICO
# ============================================================

def carregar_historico():

    if not os.path.exists(HISTORICO_ARQUIVO):
        return {}

    try:

        with open(
            HISTORICO_ARQUIVO,
            "r",
            encoding="utf-8"
        ) as arquivo:

            return json.load(
                arquivo
            )

    except:
        return {}


def salvar_historico(historico):

    with open(
        HISTORICO_ARQUIVO,
        "w",
        encoding="utf-8"
    ) as arquivo:

        json.dump(
            historico,
            arquivo,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# CHAVE DA OFERTA
# ============================================================

def chave_oferta(oferta):

    produto_id = oferta.get(
        "product_id"
    )

    if produto_id:
        return str(produto_id)

    return normalizar(
        oferta["titulo"]
        + "|"
        + oferta["vendedor"]
    )


# ============================================================
# E-MAIL
# ============================================================

def enviar_email(ofertas, estatisticas):

    agora = datetime.now().strftime(
        "%d/%m/%Y %H:%M"
    )

    assunto = (
        f"🏎️ Ofertas Diecast — "
        f"{len(ofertas)} encontradas"
    )

    linhas = []

    linhas.append(
        "BUSCADOR DE OFERTAS DIECAST"
    )

    linhas.append(
        agora
    )

    linhas.append(
        "=" * 70
    )

    if not ofertas:

        linhas.append("")
        linhas.append(
            "Nenhuma oferta realmente boa encontrada nesta busca."
        )

    for oferta in ofertas:

        linhas.append("")
        linhas.append(
            oferta["classificacao"]
        )

        linhas.append("")
        linhas.append(
            f"MARCA: {oferta['marca']}"
        )

        if oferta["serie"]:

            linhas.append(
                f"SÉRIE: {oferta['serie']}"
            )

        linhas.append(
            f"TÍTULO: {oferta['titulo']}"
        )

        linhas.append(
            f"LOJA: {oferta['vendedor']}"
        )

        linhas.append(
            f"PREÇO: R$ {oferta['preco']:.2f}"
            .replace(".", ",")
        )

        if oferta["preco_original"]:

            linhas.append(
                f"PREÇO ANTERIOR: "
                f"R$ {oferta['preco_original']:.2f}"
                .replace(".", ",")
            )

        if oferta["desconto"] > 0:

            linhas.append(
                f"DESCONTO: "
                f"{oferta['desconto']:.1f}%"
            )

        linhas.append(
            f"SCORE: {oferta['score']}"
        )

        linhas.append(
            f"LINK: {oferta['link']}"
        )

        linhas.append(
            "-" * 70
        )

    linhas.append("")
    linhas.append("=" * 70)

    linhas.append(
        f"SHOPPING ANALISADOS: "
        f"{estatisticas['analisados']}"
    )

    linhas.append(
        f"REJEITADOS INTERNACIONAIS/LOJA: "
        f"{estatisticas['internacionais']}"
    )

    linhas.append(
        f"REJEITADOS POR PRODUTO: "
        f"{estatisticas['produto']}"
    )

    linhas.append(
        f"REJEITADOS POR PREÇO: "
        f"{estatisticas['preco']}"
    )

    linhas.append(
        f"OFERTAS ENVIADAS: "
        f"{len(ofertas)}"
    )

    corpo = "\n".join(
        linhas
    )

    mensagem = MIMEMultipart()

    mensagem["From"] = EMAIL_DESTINO
    mensagem["To"] = EMAIL_DESTINO
    mensagem["Subject"] = assunto

    mensagem.attach(
        MIMEText(
            corpo,
            "plain",
            "utf-8"
        )
    )

    context = __import__(
        "ssl"
    ).create_default_context()

    with smtplib.SMTP_SSL(
        "smtp.gmail.com",
        465,
        context=context
    ) as servidor:

        servidor.login(
            EMAIL_DESTINO,
            GMAIL_APP_PASSWORD
        )

        servidor.sendmail(
            EMAIL_DESTINO,
            EMAIL_DESTINO,
            mensagem.as_string()
        )

    print(
        "EMAIL ENVIADO COM SUCESSO."
    )


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

def main():

    print("=" * 80)
    print("BUSCADOR DIECAST")
    print("SEARCHAPI / GOOGLE SHOPPING")
    print("=" * 80)

    todos = []

    estatisticas = {

        "analisados": 0,

        "internacionais": 0,

        "produto": 0,

        "preco": 0,
    }

    # --------------------------------------------------------
    # BUSCAS
    # --------------------------------------------------------

    for numero, termo in enumerate(
        BUSCAS,
        start=1
    ):

        print()
        print(
            f"BUSCA {numero}/{len(BUSCAS)}"
        )

        print(
            termo
        )

        resultados = buscar_shopping(
            termo
        )

        print(
            "RESULTADOS:",
            len(resultados)
        )

        estatisticas["analisados"] += len(
            resultados
        )

        for item in resultados:

            if loja_bloqueada(item):

                estatisticas[
                    "internacionais"
                ] += 1

                continue

            if not produto_interessante(item):

                estatisticas[
                    "produto"
                ] += 1

                continue

            titulo = item.get(
                "title",
                ""
            )

            marca = identificar_marca(
                titulo
            )

            serie = identificar_serie(
                titulo
            )

            preco = pegar_preco(
                item
            )

            if not preco_aceitavel(
                marca,
                serie,
                preco
            ):

                estatisticas[
                    "preco"
                ] += 1

                continue

            antigo = pegar_preco_original(
                item
            )

            desconto = calcular_desconto(
                preco,
                antigo
            )

            link = (
                item.get("product_link")
                or item.get("link")
                or ""
            )

            oferta = {

                "titulo": titulo,

                "marca": marca,

                "serie": serie,

                "vendedor": (
                    item.get("seller")
                    or "Não informado"
                ),

                "preco": preco,

                "preco_original": antigo,

                "desconto": desconto,

                "link": link,

                "product_id": item.get(
                    "product_id"
                ),

                "product_token": item.get(
                    "product_token"
                ),
            }

            oferta["score"] = calcular_score(
                oferta
            )

            oferta["classificacao"] = classificar(
                oferta["score"]
            )

            todos.append(
                oferta
            )

    # ========================================================
    # REMOVER DUPLICADOS
    # ========================================================

    melhores = {}

    for oferta in todos:

        chave = chave_oferta(
            oferta
        )

        atual = melhores.get(
            chave
        )

        if atual is None:

            melhores[chave] = oferta

            continue

        # Mantém o menor preço
        if oferta["preco"] < atual["preco"]:

            melhores[chave] = oferta

    ofertas = list(
        melhores.values()
    )

    # ========================================================
    # ORDENAR
    # ========================================================

    ofertas.sort(
        key=lambda x: (
            -x["score"],
            x["preco"]
        )
    )

    # ========================================================
    # EVITAR OFERTA FRACA
    # ========================================================

    ofertas = [

        oferta

        for oferta in ofertas

        if oferta["score"] >= 30

    ]

    ofertas = ofertas[
        :MAX_RESULTADOS_EMAIL
    ]

    # ========================================================
    # HISTÓRICO
    # ========================================================

    historico = carregar_historico()

    hoje = datetime.now().strftime(
        "%Y-%m-%d"
    )

    if historico.get(
        "data"
    ) != hoje:

        historico = {

            "data": hoje,

            "ofertas": {}
        }

    for oferta in ofertas:

        chave = chave_oferta(
            oferta
        )

        historico[
            "ofertas"
        ][chave] = {

            "titulo": oferta["titulo"],

            "preco": oferta["preco"],

            "score": oferta["score"],
        }

    salvar_historico(
        historico
    )

    # ========================================================
    # ARQUIVO DE LINKS
    # ========================================================

    with open(
        LINKS_ARQUIVO,
        "w",
        encoding="utf-8"
    ) as arquivo:

        for oferta in ofertas:

            arquivo.write(
                oferta["titulo"]
                + "\n"
            )

            arquivo.write(
                oferta["link"]
                + "\n\n"
            )

    # ========================================================
    # TERMINAL
    # ========================================================

    print()
    print("=" * 80)

    print(
        "OFERTAS SELECIONADAS:",
        len(ofertas)
    )

    print("=" * 80)

    for oferta in ofertas:

        print()
        print(
            oferta["classificacao"]
        )

        print(
            "MARCA:",
            oferta["marca"]
        )

        print(
            "SÉRIE:",
            oferta["serie"]
        )

        print(
            "TÍTULO:",
            oferta["titulo"]
        )

        print(
            "LOJA:",
            oferta["vendedor"]
        )

        print(
            "PREÇO:",
            f"R$ {oferta['preco']:.2f}"
        )

        print(
            "SCORE:",
            oferta["score"]
        )

        print(
            "LINK:",
            oferta["link"]
        )

        print(
            "-" * 80
        )

    # ========================================================
    # EMAIL
    # ========================================================

    print()
    print(
        "Enviando e-mail..."
    )

    enviar_email(
        ofertas,
        estatisticas
    )

    print()
    print("=" * 80)

    print(
        "SHOPPING ANALISADOS:",
        estatisticas["analisados"]
    )

    print(
        "INTERNACIONAIS/LOJAS REJEITADOS:",
        estatisticas["internacionais"]
    )

    print(
        "PRODUTOS REJEITADOS:",
        estatisticas["produto"]
    )

    print(
        "PREÇOS REJEITADOS:",
        estatisticas["preco"]
    )

    print(
        "OFERTAS ENVIADAS:",
        len(ofertas)
    )

    print("=" * 80)


if __name__ == "__main__":

    main()
