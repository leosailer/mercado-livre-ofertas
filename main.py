import os
import re
import json
import ssl
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
# ROTAÇÃO DE BUSCAS
#
# GitHub Actions trabalha em UTC.
#
# 11:00 UTC = 08:00 Brasil
# 20:00 UTC = 17:00 Brasil
#
# Cada execução = somente 2 créditos SearchAPI.
# ============================================================

hora_utc = datetime.utcnow().hour


if hora_utc < 16:

    PERIODO = "MANHÃ"

    BUSCAS = [

        (
            "Hot Wheels Premium Car Culture Modern Classics "
            "Japan Historics Race Day Ferrari Porsche Skyline "
            "Supra RX-7 Mercado Livre"
        ),

        (
            "Hot Wheels Premium Boulevard Silver Series "
            "Ferrari Porsche Skyline Supra BMW Nissan "
            "Mercado Livre"
        ),
    ]

else:

    PERIODO = "TARDE"

    BUSCAS = [

        (
            "Hot Wheels Premium Fast Furious Pop Culture "
            "Vintage Racing Circuit Legends Thrill Climbers "
            "Team Transport Mercado Livre"
        ),

        (
            "Mini GT Kaido House Tarmac Works Pop Race Inno64 "
            "Skyline Porsche Ferrari Supra Nissan Honda "
            "Mercado Livre"
        ),
    ]


# ============================================================
# LOJAS BRASILEIRAS PERMITIDAS
#
# REGRA:
# se a loja não estiver aqui, NÃO ENTRA.
# ============================================================

LOJAS_BRASIL = [

    # Mercado Livre
    "mercado livre",
    "mercadolivre",
    "mercadolivre.com.br",

    # Amazon Brasil
    "amazon.com.br",
    "amazon brasil",

    # Shopee
    "shopee",
    "shopee brasil",

    # Magalu
    "magalu",
    "magazine luiza",

    # Casas Bahia
    "casas bahia",

    # Ri Happy
    "ri happy",

    # Americanas
    "americanas",
]


# ============================================================
# LOJAS INTERNACIONAIS / NÃO DESEJADAS
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

    "top collectibles",

    "japan booster",

    "japan hobby",

    "plaza japan",

    "suruga",

    "amiami",
]


# ============================================================
# TERMOS DE IMPORTAÇÃO
# ============================================================

TERMOS_IMPORTACAO = [

    "produto internacional",

    "compra internacional",

    "envio internacional",

    "international shipping",

    "imported from",

    "importado dos estados unidos",

    "importado do japao",

    "importado do japão",
]


# ============================================================
# LINHAS HOT WHEELS QUE QUEREMOS
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

    ("fast and furious", "Fast & Furious"),

    ("fast furious", "Fast & Furious"),

    ("elite 64", "Elite 64"),

    ("rlc", "RLC"),

    ("car culture", "Car Culture"),

    ("premium", "Premium"),
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

    "mazda",

    "nissan",
]


# ============================================================
# NORMALIZAR TEXTO
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
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    )

    return texto


# ============================================================
# VERIFICAR LOJA BRASILEIRA
# ============================================================

def loja_brasileira(item):

    vendedor = normalizar(
        item.get("seller", "")
    )

    titulo = normalizar(
        item.get("title", "")
    )

    combinado = vendedor + " " + titulo

    if not vendedor:
        return False

    # ---------------------------------------------
    # BLOQUEIO EXPLÍCITO
    # ---------------------------------------------

    for proibida in LOJAS_PROIBIDAS:

        if normalizar(proibida) in vendedor:
            return False

    # ---------------------------------------------
    # BLOQUEIO DE IMPORTAÇÃO
    # ---------------------------------------------

    for termo in TERMOS_IMPORTACAO:

        if normalizar(termo) in combinado:
            return False

    # ---------------------------------------------
    # WHITELIST BR
    # ---------------------------------------------

    for permitida in LOJAS_BRASIL:

        if normalizar(permitida) in vendedor:
            return True

    return False


# ============================================================
# PEGAR PREÇO REAL
# ============================================================

def pegar_preco(item):

    valor = item.get(
        "extracted_price"
    )

    if isinstance(
        valor,
        (int, float)
    ):

        return float(valor)

    texto = str(
        item.get(
            "price",
            ""
        )
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

        return float(
            numero
        )

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

        return float(
            numero
        )

    except:

        return None


# ============================================================
# CALCULAR DESCONTO REAL
# ============================================================

def desconto_real(
    preco,
    antigo
):

    if not preco:
        return 0

    if not antigo:
        return 0

    if antigo <= preco:
        return 0

    desconto = (
        (antigo - preco)
        /
        antigo
    ) * 100

    return round(
        desconto,
        1
    )


# ============================================================
# IDENTIFICAR MARCA
# ============================================================

def identificar_marca(titulo):

    t = normalizar(
        titulo
    )

    if "kaido house" in t:
        return "Kaido House"

    if (
        "mini gt" in t
        or
        "minigt" in t
    ):
        return "Mini GT"

    if "tarmac works" in t:
        return "Tarmac Works"

    if "pop race" in t:
        return "Pop Race"

    if (
        "inno64" in t
        or
        "inno 64" in t
    ):
        return "Inno64"

    if "hot wheels" in t:
        return "Hot Wheels"

    return None


# ============================================================
# IDENTIFICAR SÉRIE HOT WHEELS
# ============================================================

def identificar_serie(titulo):

    t = normalizar(
        titulo
    )

    for termo, nome in SERIES_HW:

        if termo in t:
            return nome

    return ""


# ============================================================
# ESCALA ERRADA
# ============================================================

def escala_errada(titulo):

    t = normalizar(
        titulo
    )

    escalas_proibidas = [

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

        "1:48",
        "1/48",
    ]

    for escala in escalas_proibidas:

        if escala in t:
            return True

    return False


# ============================================================
# KIT / LOTE
# ============================================================

def kit_ou_lote(titulo):

    t = normalizar(
        titulo
    )

    termos = [

        "set completo",

        "colecao completa",

        "kit com",

        "kit de",

        "lote",

        "pack com",

        "5 miniaturas",

        "10 miniaturas",

        "20 miniaturas",

        "caixa fechada",
    ]

    for termo in termos:

        if normalizar(termo) in t:
            return True

    return False


# ============================================================
# PRODUTO VÁLIDO
# ============================================================

def produto_valido(item):

    titulo = item.get(
        "title",
        ""
    )

    # ---------------------------------------------
    # LOJA BR
    # ---------------------------------------------

    if not loja_brasileira(
        item
    ):
        return False

    # ---------------------------------------------
    # ESCALA
    # ---------------------------------------------

    if escala_errada(
        titulo
    ):
        return False

    # ---------------------------------------------
    # KIT
    # ---------------------------------------------

    if kit_ou_lote(
        titulo
    ):
        return False

    # ---------------------------------------------
    # MARCA
    # ---------------------------------------------

    marca = identificar_marca(
        titulo
    )

    if not marca:
        return False

    # ---------------------------------------------
    # HOT WHEELS TEM QUE SER PREMIUM/SÉRIE
    # ---------------------------------------------

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

def preco_valido(
    marca,
    serie,
    preco
):

    if preco is None:
        return False

    # ---------------------------------------------
    # PROTEÇÃO CONTRA PARCELA
    # ---------------------------------------------

    if preco < 20:
        return False

    # ---------------------------------------------
    # HOT WHEELS
    # ---------------------------------------------

    if marca == "Hot Wheels":

        if serie == "Silver Series":

            return preco <= 70

        if serie == "Team Transport":

            return preco <= 160

        if serie in [
            "Elite 64",
            "RLC"
        ]:

            return preco <= 180

        # Premium normal
        return preco <= 85

    # ---------------------------------------------
    # MINI GT
    # ---------------------------------------------

    if marca == "Mini GT":

        return preco <= 140

    # ---------------------------------------------
    # KAIDO
    # ---------------------------------------------

    if marca == "Kaido House":

        return preco < 199

    # ---------------------------------------------
    # TARMAC
    # ---------------------------------------------

    if marca == "Tarmac Works":

        return preco <= 155

    # ---------------------------------------------
    # POP RACE
    # ---------------------------------------------

    if marca == "Pop Race":

        return preco <= 155

    # ---------------------------------------------
    # INNO64
    # ---------------------------------------------

    if marca == "Inno64":

        return preco <= 165

    return False


# ============================================================
# SCORE DA OFERTA
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

    vendedor = normalizar(
        oferta["vendedor"]
    )

    # ========================================================
    # MODELOS TOP
    # ========================================================

    modelo_top = False

    for modelo in MODELOS_TOP:

        if modelo in titulo:

            score += 5

            modelo_top = True

    if modelo_top:

        score += 5

    # ========================================================
    # HOT WHEELS
    # ========================================================

    if marca == "Hot Wheels":

        score += 10

        # ---------------------------------------------
        # LINHAS MAIS IMPORTANTES
        # ---------------------------------------------

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

            score += 16

        elif serie == "Car Culture":

            score += 15

        elif serie == "Boulevard":

            score += 17

        elif serie == "Fast & Furious":

            score += 15

        elif serie == "Pop Culture":

            score += 10

        elif serie == "Silver Series":

            score += 8

        elif serie == "Team Transport":

            score += 8

        elif serie in [
            "Elite 64",
            "RLC"
        ]:

            score += 15

        elif serie == "Premium":

            score += 8

        # ====================================================
        # PREÇO HOT WHEELS
        # ====================================================

        if preco <= 50:

            score += 45

        elif preco <= 55:

            score += 38

        elif preco <= 60:

            score += 32

        elif preco <= 65:

            score += 26

        elif preco <= 70:

            score += 18

        elif preco <= 75:

            score += 10

        elif preco <= 80:

            score += 5

        else:

            score += 0

    # ========================================================
    # MINI GT
    # ========================================================

    elif marca == "Mini GT":

        score += 18

        if preco <= 90:

            score += 40

        elif preco <= 100:

            score += 32

        elif preco <= 110:

            score += 25

        elif preco <= 120:

            score += 18

        elif preco <= 130:

            score += 10

        else:

            score += 4

    # ========================================================
    # KAIDO HOUSE
    # ========================================================

    elif marca == "Kaido House":

        score += 22

        if preco <= 130:

            score += 40

        elif preco <= 145:

            score += 32

        elif preco <= 160:

            score += 24

        elif preco <= 180:

            score += 14

        else:

            score += 5

    # ========================================================
    # TARMAC / POP RACE / INNO
    # ========================================================

    else:

        score += 15

        if preco <= 100:

            score += 35

        elif preco <= 115:

            score += 27

        elif preco <= 130:

            score += 18

        elif preco <= 145:

            score += 10

        else:

            score += 4

    # ========================================================
    # DESCONTO
    # ========================================================

    if desconto >= 30:

        score += 30

    elif desconto >= 20:

        score += 20

    elif desconto >= 15:

        score += 12

    elif desconto >= 10:

        score += 5

    # ========================================================
    # PRIORIDADE DE LOJA
    # ========================================================

    if (
        "mercadolivre" in vendedor
        or
        "mercado livre" in vendedor
    ):

        # Mercado Livre é prioridade
        score += 30

        # HW Premium no Mercado Livre
        if marca == "Hot Wheels":

            score += 15

    elif "amazon" in vendedor:

        score += 10

    elif "magalu" in vendedor:

        score += 7

    elif "shopee" in vendedor:

        score += 5

    elif "casas bahia" in vendedor:

        score += 5

    elif "ri happy" in vendedor:

        score += 5

    return score


# ============================================================
# CLASSIFICAÇÃO
# ============================================================

def classificar(score):

    if score >= 80:

        return "🚨 IMPERDÍVEL"

    if score >= 55:

        return "🔥 BOA OFERTA"

    return "👀 INTERESSANTE"


# ============================================================
# BUSCAR GOOGLE SHOPPING
# ============================================================

def buscar_shopping(
    termo
):

    params = {

        "engine": "google_shopping",

        "q": termo,

        "gl": "br",

        "hl": "pt-br",

        "location": "Brazil",

        "condition": "new",

        "api_key": SEARCHAPI_KEY,
    }

    try:

        resposta = requests.get(
            SEARCH_URL,
            params=params,
            timeout=45
        )

    except Exception as erro:

        print(
            "ERRO DE CONEXÃO:",
            erro
        )

        return []

    print(
        "STATUS SEARCHAPI:",
        resposta.status_code
    )

    if resposta.status_code != 200:

        print(
            resposta.text[:500]
        )

        return []

    try:

        dados = resposta.json()

    except:

        print(
            "ERRO AO LER JSON."
        )

        return []

    return dados.get(
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
        ) as arquivo:

            return json.load(
                arquivo
            )

    except:

        return {}


def salvar_historico(
    historico
):

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

def chave_oferta(
    oferta
):

    produto_id = oferta.get(
        "product_id"
    )

    if produto_id:

        return str(
            produto_id
        )

    return normalizar(
        oferta["titulo"]
        +
        "|"
        +
        oferta["vendedor"]
    )


# ============================================================
# FORMATAR PREÇO
# ============================================================

def formatar_preco(
    valor
):

    return (
        f"R$ {valor:.2f}"
    ).replace(
        ".",
        ","
    )


# ============================================================
# ENVIAR EMAIL
# ============================================================

def enviar_email(
    ofertas,
    estatisticas
):

    agora = datetime.now().strftime(
        "%d/%m/%Y %H:%M"
    )

    assunto = (
        f"🏎️ {len(ofertas)} ofertas Diecast "
        f"- {PERIODO}"
    )

    linhas = []

    linhas.append(
        "🏎️ BUSCADOR DIECAST"
    )

    linhas.append(
        f"RODADA: {PERIODO}"
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
            "Nenhuma oferta nacional realmente boa encontrada."
        )

    for oferta in ofertas:

        linhas.append("")

        linhas.append(
            oferta["classificacao"]
        )

        linhas.append("")

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
            "PREÇO: "
            +
            formatar_preco(
                oferta["preco"]
            )
        )

        if oferta[
            "preco_original"
        ]:

            linhas.append(
                "PREÇO ANTERIOR: "
                +
                formatar_preco(
                    oferta[
                        "preco_original"
                    ]
                )
            )

        if oferta[
            "desconto"
        ] > 0:

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

    linhas.append(
        "=" * 70
    )

    linhas.append(
        f"RESULTADOS ANALISADOS: "
        f"{estatisticas['analisados']}"
    )

    linhas.append(
        f"LOJAS DESCARTADAS: "
        f"{estatisticas['lojas']}"
    )

    linhas.append(
        f"PRODUTOS DESCARTADOS: "
        f"{estatisticas['produtos']}"
    )

    linhas.append(
        f"PREÇOS DESCARTADOS: "
        f"{estatisticas['precos']}"
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
            mensagem.as_string()
        )

    print(
        "📧 EMAIL ENVIADO COM SUCESSO."
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "=" * 80
    )

    print(
        "BUSCADOR DIECAST - VERSÃO PREMIUM BR"
    )

    print(
        f"RODADA: {PERIODO}"
    )

    print(
        "BUSCAS SEARCHAPI: 2"
    )

    print(
        "=" * 80
    )

    candidatos = []

    estatisticas = {

        "analisados": 0,

        "lojas": 0,

        "produtos": 0,

        "precos": 0,
    }

    # ========================================================
    # EXECUTAR AS 2 BUSCAS
    # ========================================================

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

        estatisticas[
            "analisados"
        ] += len(
            resultados
        )

        # ====================================================
        # ANALISAR RESULTADOS
        # ====================================================

        for item in resultados:

            # ---------------------------------------------
            # LOJA
            # ---------------------------------------------

            if not loja_brasileira(
                item
            ):

                estatisticas[
                    "lojas"
                ] += 1

                continue

            # ---------------------------------------------
            # PRODUTO
            # ---------------------------------------------

            if not produto_valido(
                item
            ):

                estatisticas[
                    "produtos"
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

            # ---------------------------------------------
            # PREÇO
            # ---------------------------------------------

            if not preco_valido(
                marca,
                serie,
                preco
            ):

                estatisticas[
                    "precos"
                ] += 1

                continue

            antigo = pegar_preco_original(
                item
            )

            desconto = desconto_real(
                preco,
                antigo
            )

            link = (
                item.get(
                    "product_link"
                )
                or
                item.get(
                    "link"
                )
                or
                ""
            )

            oferta = {

                "titulo": titulo,

                "marca": marca,

                "serie": serie,

                "vendedor": (
                    item.get(
                        "seller"
                    )
                    or
                    "Não informado"
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

            oferta[
                "score"
            ] = calcular_score(
                oferta
            )

            oferta[
                "classificacao"
            ] = classificar(
                oferta[
                    "score"
                ]
            )

            candidatos.append(
                oferta
            )

    # ========================================================
    # REMOVER DUPLICADOS
    # ========================================================

    unicos = {}

    for oferta in candidatos:

        chave = chave_oferta(
            oferta
        )

        existente = unicos.get(
            chave
        )

        if existente is None:

            unicos[
                chave
            ] = oferta

            continue

        # Se duplicou, mantém o menor preço

        if (
            oferta["preco"]
            <
            existente["preco"]
        ):

            unicos[
                chave
            ] = oferta

    ofertas = list(
        unicos.values()
    )

    # ========================================================
    # REMOVER OFERTAS FRACAS
    # ========================================================

    ofertas = [

        oferta

        for oferta in ofertas

        if oferta[
            "score"
        ] >= 40

    ]

    # ========================================================
    # ORDENAR
    # ========================================================

    ofertas.sort(

        key=lambda oferta: (

            -oferta[
                "score"
            ],

            oferta[
                "preco"
            ]
        )
    )

    # ========================================================
    # LIMITAR EMAIL
    # ========================================================

    ofertas = ofertas[
        :MAX_OFERTAS_EMAIL
    ]

    # ========================================================
    # HISTÓRICO DIÁRIO
    #
    # TODO DIA RECOMEÇA.
    # Portanto uma oferta encontrada ontem pode aparecer
    # novamente hoje.
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

        chave = chave_oferta(
            oferta
        )

        historico[
            "ofertas"
        ][
            chave
        ] = {

            "titulo": oferta[
                "titulo"
            ],

            "preco": oferta[
                "preco"
            ],

            "score": oferta[
                "score"
            ],

            "loja": oferta[
                "vendedor"
            ],
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
                oferta[
                    "titulo"
                ]
            )

            arquivo.write(
                "\n"
            )

            arquivo.write(
                oferta[
                    "link"
                ]
            )

            arquivo.write(
                "\n\n"
            )

    # ========================================================
    # RESULTADO NO GITHUB
    # ========================================================

    print()

    print(
        "=" * 80
    )

    print(
        "OFERTAS NACIONAIS SELECIONADAS:",
        len(
            ofertas
        )
    )

    print(
        "=" * 80
    )

    for oferta in ofertas:

        print()

        print(
            oferta[
                "classificacao"
            ]
        )

        print(
            "LOJA:",
            oferta[
                "vendedor"
            ]
        )

        print(
            "MARCA:",
            oferta[
                "marca"
            ]
        )

        print(
            "SÉRIE:",
            oferta[
                "serie"
            ]
        )

        print(
            "TÍTULO:",
            oferta[
                "titulo"
            ]
        )

        print(
            "PREÇO:",
            formatar_preco(
                oferta[
                    "preco"
                ]
            )
        )

        if oferta[
            "desconto"
        ]:

            print(
                "DESCONTO:",
                str(
                    oferta[
                        "desconto"
                    ]
                )
                +
                "%"
            )

        print(
            "SCORE:",
            oferta[
                "score"
            ]
        )

        print(
            "LINK:",
            oferta[
                "link"
            ]
        )

        print(
            "-" * 80
        )

    # ========================================================
    # EMAIL SEMPRE
    # ========================================================

    print()

    print(
        "Enviando relatório por e-mail..."
    )

    try:

        enviar_email(
            ofertas,
            estatisticas
        )

    except Exception as erro:

        print(
            "❌ ERRO AO ENVIAR EMAIL:"
        )

        print(
            erro
        )

    # ========================================================
    # RESUMO
    # ========================================================

    print()

    print(
        "=" * 80
    )

    print(
        "RESUMO DA EXECUÇÃO"
    )

    print(
        "=" * 80
    )

    print(
        "PERÍODO:",
        PERIODO
    )

    print(
        "BUSCAS CONSUMIDAS:",
        len(
            BUSCAS
        )
    )

    print(
        "RESULTADOS ANALISADOS:",
        estatisticas[
            "analisados"
        ]
    )

    print(
        "LOJAS NÃO BRASILEIRAS DESCARTADAS:",
        estatisticas[
            "lojas"
        ]
    )

    print(
        "PRODUTOS DESCARTADOS:",
        estatisticas[
            "produtos"
        ]
    )

    print(
        "PREÇOS DESCARTADOS:",
        estatisticas[
            "precos"
        ]
    )

    print(
        "OFERTAS ENVIADAS:",
        len(
            ofertas
        )
    )

    print(
        "=" * 80
    )


# ============================================================
# EXECUTAR
# ============================================================

if __name__ == "__main__":

    main()
