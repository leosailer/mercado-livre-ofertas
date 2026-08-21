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

MAX_OFERTAS_EMAIL = 20


# ============================================================
# SOMENTE 2 BUSCAS POR EXECUÇÃO
# ============================================================

BUSCAS = [
    (
        'Hot Wheels Premium Car Culture Boulevard Silver Series '
        'Modern Classics Japan Historics Race Day Ferrari Porsche '
        'Skyline Supra RX-7 NSX'
    ),

    (
        'Mini GT Kaido House Tarmac Works Pop Race Inno64 '
        'Skyline Porsche Ferrari Honda Nissan BMW 1:64'
    ),
]


# ============================================================
# WHITELIST BRASILEIRA
#
# Qualquer loja que NÃO estiver aqui será descartada.
# ============================================================

LOJAS_BRASIL = [
    "mercado livre",
    "mercadolivre",
    "mercadolivre.com.br",

    "amazon.com.br",
    "amazon brasil",

    "magalu",
    "magazine luiza",

    "casas bahia",

    "ri happy",

    "shopee",
    "shopee brasil",

    "americanas",

    "mercado car",
]


# ============================================================
# BLOQUEIO EXTRA
# ============================================================

LOJAS_PROIBIDAS = [
    "ebay",
    "aliexpress",
    "temu",
    "etsy",
    "alibaba",
    "banggood",
    "dhgate",

    "boost gear",
    "carolinasdiecast",
    "carolina's diecast",
    "aussie hobbies",
    "awesomediecast",
    "1-64specialist",
    "1:64 specialist",
]


# ============================================================
# LINHAS HOT WHEELS
# ============================================================

SERIES_HW = [
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

    ("fast & furious", "Fast & Furious"),
    ("fast furious", "Fast & Furious"),

    ("elite 64", "Elite 64"),
    ("rlc", "RLC"),

    ("car culture", "Car Culture"),
    ("premium", "Premium"),
]


# ============================================================
# CARROS MAIS INTERESSANTES
# ============================================================

MODELOS_TOP = [
    "ferrari",
    "porsche",

    "skyline",
    "r32",
    "r33",
    "r34",
    "gt-r",
    "gtr",

    "supra",

    "rx-7",
    "rx7",

    "nsx",

    "lamborghini",
    "mclaren",

    "bmw",
    "audi",

    "civic",
    "s2000",

    "silvia",

    "datsun",

    "mustang",

    "911",

    "lancer",
    "evolution",
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
# LOJA BRASILEIRA
# ============================================================

def loja_brasileira(item):

    vendedor = normalizar(
        item.get("seller", "")
    )

    if not vendedor:
        return False

    for proibida in LOJAS_PROIBIDAS:

        if normalizar(proibida) in vendedor:
            return False

    for permitida in LOJAS_BRASIL:

        if normalizar(permitida) in vendedor:
            return True

    return False


# ============================================================
# PREÇO
# ============================================================

def pegar_preco(item):

    valor = item.get("extracted_price")

    if isinstance(valor, (int, float)):
        return float(valor)

    texto = str(
        item.get("price", "")
    )

    texto = texto.replace(
        "R$",
        ""
    )

    texto = texto.strip()

    match = re.search(
        r"[\d\.,]+",
        texto
    )

    if not match:
        return None

    valor = match.group()

    if "," in valor:

        valor = valor.replace(".", "")
        valor = valor.replace(",", ".")

    try:
        return float(valor)

    except:
        return None


# ============================================================
# PREÇO ORIGINAL
# ============================================================

def pegar_preco_original(item):

    valor = item.get(
        "original_price"
    )

    if valor is None:
        return None

    if isinstance(
        valor,
        (int, float)
    ):
        return float(valor)

    texto = str(valor)

    texto = texto.replace(
        "R$",
        ""
    )

    match = re.search(
        r"[\d\.,]+",
        texto
    )

    if not match:
        return None

    numero = match.group()

    if "," in numero:

        numero = numero.replace(
            ".",
            ""
        )

        numero = numero.replace(
            ",",
            "."
        )

    try:
        return float(numero)

    except:
        return None


# ============================================================
# DESCONTO
# ============================================================

def desconto_real(preco, antigo):

    if not preco or not antigo:
        return 0

    if antigo <= preco:
        return 0

    return round(
        ((antigo - preco) / antigo) * 100,
        1
    )


# ============================================================
# MARCA
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
# SÉRIE
# ============================================================

def identificar_serie(titulo):

    t = normalizar(titulo)

    for termo, nome in SERIES_HW:

        if termo in t:
            return nome

    return ""


# ============================================================
# ESCALA ERRADA
# ============================================================

def escala_errada(titulo):

    t = normalizar(titulo)

    proibidas = [
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

    return any(
        x in t
        for x in proibidas
    )


# ============================================================
# KITS / LOTES
# ============================================================

def kit_ou_lote(titulo):

    t = normalizar(titulo)

    termos = [
        "set completo",
        "colecao completa",
        "kit com",
        "kit de",
        "lote",
        "pack com",
        "5 miniaturas",
        "10 miniaturas",
    ]

    return any(
        normalizar(x) in t
        for x in termos
    )


# ============================================================
# PRODUTO VÁLIDO
# ============================================================

def produto_valido(item):

    titulo = item.get(
        "title",
        ""
    )

    if not loja_brasileira(item):
        return False

    if escala_errada(titulo):
        return False

    if kit_ou_lote(titulo):
        return False

    marca = identificar_marca(
        titulo
    )

    if not marca:
        return False

    if marca == "Hot Wheels":

        serie = identificar_serie(
            titulo
        )

        if not serie:
            return False

    return True


# ============================================================
# PREÇO MÁXIMO
# ============================================================

def preco_valido(marca, serie, preco):

    if preco is None:
        return False

    # Proteção contra parcela / preço quebrado
    if preco < 20:
        return False

    if marca == "Hot Wheels":

        if serie == "Silver Series":
            return preco <= 75

        if serie == "Team Transport":
            return preco <= 170

        if serie in [
            "Elite 64",
            "RLC"
        ]:
            return preco <= 180

        # Premium normal
        return preco <= 90

    if marca == "Mini GT":
        return preco <= 145

    if marca == "Kaido House":
        return preco < 199

    if marca == "Tarmac Works":
        return preco <= 160

    if marca == "Pop Race":
        return preco <= 160

    if marca == "Inno64":
        return preco <= 170

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

    # MODELO TOP

    encontrou_top = False

    for modelo in MODELOS_TOP:

        if modelo in titulo:

            score += 6
            encontrou_top = True

    if encontrou_top:
        score += 5

    # HOT WHEELS

    if marca == "Hot Wheels":

        score += 10

        if serie in [
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
            score += 15

        elif serie == "Car Culture":
            score += 14

        elif serie == "Boulevard":
            score += 15

        elif serie == "Fast & Furious":
            score += 14

        elif serie == "Silver Series":
            score += 8

        elif serie == "Pop Culture":
            score += 8

        elif serie == "Team Transport":
            score += 8

        if preco <= 50:
            score += 35

        elif preco <= 60:
            score += 30

        elif preco <= 70:
            score += 22

        elif preco <= 80:
            score += 12

        elif preco <= 90:
            score += 5

    # MINI GT

    elif marca == "Mini GT":

        score += 18

        if preco <= 95:
            score += 35

        elif preco <= 110:
            score += 28

        elif preco <= 125:
            score += 20

        elif preco <= 140:
            score += 10

    # KAIDO

    elif marca == "Kaido House":

        score += 22

        if preco <= 130:
            score += 35

        elif preco <= 150:
            score += 28

        elif preco <= 170:
            score += 18

        elif preco < 199:
            score += 8

    # OUTRAS

    else:

        score += 15

        if preco <= 100:
            score += 30

        elif preco <= 125:
            score += 20

        elif preco <= 150:
            score += 10

    # DESCONTO REAL

    if desconto >= 30:
        score += 30

    elif desconto >= 20:
        score += 20

    elif desconto >= 15:
        score += 12

    elif desconto >= 10:
        score += 5

    # MERCADO LIVRE GANHA PRIORIDADE

    vendedor = normalizar(
        oferta["vendedor"]
    )

    if "mercado" in vendedor:
        score += 15

    elif "amazon" in vendedor:
        score += 10

    elif "magalu" in vendedor:
        score += 7

    elif "shopee" in vendedor:
        score += 5

    return score


# ============================================================
# CLASSIFICAÇÃO
# ============================================================

def classificacao(score):

    if score >= 70:
        return "🚨 IMPERDÍVEL"

    if score >= 50:
        return "🔥 BOA OFERTA"

    return "👀 INTERESSANTE"


# ============================================================
# SEARCH API
# ============================================================

def buscar(termo):

    params = {
        "engine": "google_shopping",
        "q": termo,

        "gl": "br",
        "hl": "pt-br",
        "location": "Brazil",

        "condition": "new",

        "api_key": SEARCHAPI_KEY,
    }

    resposta = requests.get(
        SEARCH_URL,
        params=params,
        timeout=45
    )

    print(
        "STATUS SEARCHAPI:",
        resposta.status_code
    )

    if resposta.status_code != 200:

        print(
            resposta.text[:500]
        )

        return []

    return resposta.json().get(
        "shopping_results",
        []
    )


# ============================================================
# HISTÓRICO
# ============================================================

def carregar_historico():

    if not os.path.exists(
        HISTORICO_ARQUIVO
    ):
        return {}

    try:

        with open(
            HISTORICO_ARQUIVO,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except:
        return {}


def salvar_historico(historico):

    with open(
        HISTORICO_ARQUIVO,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            historico,
            f,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# CHAVE ÚNICA
# ============================================================

def chave(oferta):

    product_id = oferta.get(
        "product_id"
    )

    if product_id:
        return str(product_id)

    return normalizar(
        oferta["titulo"]
        + "|"
        + oferta["vendedor"]
    )


# ============================================================
# EMAIL
# ============================================================

def enviar_email(ofertas, stats):

    data = datetime.now().strftime(
        "%d/%m/%Y %H:%M"
    )

    linhas = []

    linhas.append(
        "🏎️ BUSCADOR DIECAST"
    )

    linhas.append(
        data
    )

    linhas.append(
        "=" * 70
    )

    if not ofertas:

        linhas.append("")
        linhas.append(
            "Nenhuma oferta nacional realmente boa encontrada."
        )

    for oferta in ofertas:

        linhas.append("")
        linhas.append(
            oferta["classificacao"]
        )

        linhas.append(
            f"LOJA: {oferta['vendedor']}"
        )

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
            (
                f"PREÇO: R$ "
                f"{oferta['preco']:.2f}"
            ).replace(
                ".",
                ","
            )
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
        f"RESULTADOS ANALISADOS: "
        f"{stats['analisados']}"
    )

    linhas.append(
        f"LOJAS NÃO BRASILEIRAS DESCARTADAS: "
        f"{stats['lojas']}"
    )

    linhas.append(
        f"PRODUTOS DESCARTADOS: "
        f"{stats['produtos']}"
    )

    linhas.append(
        f"PREÇOS DESCARTADOS: "
        f"{stats['precos']}"
    )

    linhas.append(
        f"OFERTAS ENVIADAS: "
        f"{len(ofertas)}"
    )

    corpo = "\n".join(
        linhas
    )

    assunto = (
        f"🏎️ Diecast: "
        f"{len(ofertas)} ofertas nacionais"
    )

    msg = MIMEMultipart()

    msg["From"] = EMAIL_DESTINO
    msg["To"] = EMAIL_DESTINO
    msg["Subject"] = assunto

    msg.attach(
        MIMEText(
            corpo,
            "plain",
            "utf-8"
        )
    )

    import ssl

    context = ssl.create_default_context()

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
            msg.as_string()
        )

    print(
        "📧 EMAIL ENVIADO."
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print("BUSCADOR DIECAST - MODO ECONÔMICO")
    print("2 BUSCAS SEARCHAPI")
    print("=" * 80)

    candidatos = []

    stats = {
        "analisados": 0,
        "lojas": 0,
        "produtos": 0,
        "precos": 0,
    }

    # ========================================================
    # DUAS BUSCAS
    # ========================================================

    for numero, termo in enumerate(
        BUSCAS,
        start=1
    ):

        print()
        print(
            f"BUSCA {numero}/2"
        )

        print(
            termo
        )

        resultados = buscar(
            termo
        )

        print(
            "RESULTADOS:",
            len(resultados)
        )

        stats["analisados"] += len(
            resultados
        )

        for item in resultados:

            # LOJA

            if not loja_brasileira(item):

                stats["lojas"] += 1
                continue

            # PRODUTO

            if not produto_valido(item):

                stats["produtos"] += 1
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

            # PREÇO

            if not preco_valido(
                marca,
                serie,
                preco
            ):

                stats["precos"] += 1
                continue

            antigo = pegar_preco_original(
                item
            )

            desconto = desconto_real(
                preco,
                antigo
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

                "link": (
                    item.get("product_link")
                    or item.get("link")
                    or ""
                ),

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

            oferta[
                "classificacao"
            ] = classificacao(
                oferta["score"]
            )

            candidatos.append(
                oferta
            )

    # ========================================================
    # DEDUPLICAÇÃO
    # ========================================================

    unicos = {}

    for oferta in candidatos:

        k = chave(
            oferta
        )

        if k not in unicos:

            unicos[k] = oferta

        else:

            if (
                oferta["preco"]
                <
                unicos[k]["preco"]
            ):

                unicos[k] = oferta

    ofertas = list(
        unicos.values()
    )

    # ========================================================
    # REMOVER COISA FRACA
    # ========================================================

    ofertas = [
        o
        for o in ofertas
        if o["score"] >= 35
    ]

    # ========================================================
    # RANKING
    # ========================================================

    ofertas.sort(
        key=lambda o: (
            -o["score"],
            o["preco"]
        )
    )

    ofertas = ofertas[
        :MAX_OFERTAS_EMAIL
    ]

    # ========================================================
    # HISTÓRICO DIÁRIO
    # ========================================================

    hoje = datetime.now().strftime(
        "%Y-%m-%d"
    )

    historico = carregar_historico()

    if historico.get(
        "data"
    ) != hoje:

        historico = {
            "data": hoje,
            "ofertas": {}
        }

    for oferta in ofertas:

        historico[
            "ofertas"
        ][
            chave(oferta)
        ] = {
            "titulo": oferta["titulo"],
            "preco": oferta["preco"],
            "score": oferta["score"],
        }

    salvar_historico(
        historico
    )

    # ========================================================
    # LINKS
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
        "OFERTAS NACIONAIS:",
        len(ofertas)
    )

    print("=" * 80)

    for oferta in ofertas:

        print()
        print(
            oferta["classificacao"]
        )

        print(
            "LOJA:",
            oferta["vendedor"]
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
            "PREÇO:",
            (
                f"R$ {oferta['preco']:.2f}"
            ).replace(
                ".",
                ","
            )
        )

        if oferta["desconto"]:

            print(
                "DESCONTO:",
                f"{oferta['desconto']}%"
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
    # EMAIL SEMPRE
    # ========================================================

    print()
    print(
        "Enviando relatório..."
    )

    enviar_email(
        ofertas,
        stats
    )

    print()
    print("=" * 80)

    print(
        "RESULTADOS ANALISADOS:",
        stats["analisados"]
    )

    print(
        "LOJAS NÃO BRASILEIRAS DESCARTADAS:",
        stats["lojas"]
    )

    print(
        "PRODUTOS DESCARTADOS:",
        stats["produtos"]
    )

    print(
        "PREÇOS DESCARTADOS:",
        stats["precos"]
    )

    print(
        "OFERTAS ENVIADAS:",
        len(ofertas)
    )

    print("=" * 80)


if __name__ == "__main__":
    main()
