import os
import re
import json
import ssl
import smtplib
import requests
import unicodedata

from datetime import datetime, timezone, timedelta
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

# Tempo maior para evitar perder uma busca boa
# simplesmente porque a SearchAPI demorou.
TIMEOUT_SEARCHAPI = 120

FUSO_BRASIL = timezone(timedelta(hours=-3))
AGORA_BRASIL = datetime.now(FUSO_BRASIL)

HORA = AGORA_BRASIL.hour
DIA_SEMANA = AGORA_BRASIL.weekday()

PERIODO = "MANHÃ" if HORA < 13 else "TARDE"


# ============================================================
# ROTAÇÃO
#
# 2 buscas por execução.
#
# Hot Wheels domina praticamente todas as rodadas.
# Queries curtas para tentar pegar 40 resultados.
# ============================================================

ROTACOES = {

    # SEGUNDA
    0: {
        "MANHÃ": [
            "Hot Wheels Car Culture",
            "Hot Wheels Boulevard",
        ],
        "TARDE": [
            "Hot Wheels Silver Series",
            "Hot Wheels Modern Classics",
        ],
    },

    # TERÇA
    1: {
        "MANHÃ": [
            "Hot Wheels Car Culture",
            "Hot Wheels Japan Historics",
        ],
        "TARDE": [
            "Hot Wheels Fast Furious Premium",
            "Hot Wheels Pop Culture",
        ],
    },

    # QUARTA
    2: {
        "MANHÃ": [
            "Hot Wheels Boulevard",
            "Hot Wheels Race Day",
        ],
        "TARDE": [
            "Hot Wheels Car Culture",
            "Mini GT",
        ],
    },

    # QUINTA
    3: {
        "MANHÃ": [
            "Hot Wheels Car Culture",
            "Hot Wheels Vintage Racing",
        ],
        "TARDE": [
            "Hot Wheels Silver Series",
            "Hot Wheels Boulevard",
        ],
    },

    # SEXTA
    4: {
        "MANHÃ": [
            "Hot Wheels Car Culture",
            "Hot Wheels Boulevard",
        ],
        "TARDE": [
            "Hot Wheels Car Culture",
            "Hot Wheels Team Transport",
        ],
    },

    # SÁBADO
    5: {
        "MANHÃ": [
            "Hot Wheels Car Culture",
            "Hot Wheels Silver Series",
        ],
        "TARDE": [
            "Hot Wheels Boulevard",
            "Kaido House",
        ],
    },

    # DOMINGO
    6: {
        "MANHÃ": [
            "Hot Wheels Car Culture",
            "Hot Wheels Boulevard",
        ],
        "TARDE": [
            "Hot Wheels Silver Series",
            "Mini GT Kaido House",
        ],
    },
}

BUSCAS = ROTACOES[DIA_SEMANA][PERIODO]


# ============================================================
# LOJAS BRASILEIRAS ACEITAS
# ============================================================

LOJAS_BRASIL = [
    "mercado livre",
    "mercadolivre",
    "mercadolivre.com.br",

    "amazon.com.br",
    "amazon brasil",

    "shopee",
    "shopee brasil",

    "magalu",
    "magazine luiza",

    "casas bahia",

    "ri happy",

    "americanas",

    "extra",

    "ponto",
]


# ============================================================
# LOJAS PROIBIDAS
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
    "plaza japan",
    "amiami",
    "suruga",
    "japan booster",
]


# ============================================================
# IMPORTAÇÃO
# ============================================================

TERMOS_IMPORTACAO = [
    "produto internacional",
    "compra internacional",
    "envio internacional",
    "international shipping",
    "imported",
    "importado dos estados unidos",
    "importado do japão",
    "importado do japao",
    "importação",
    "importacao",
]


# ============================================================
# ANÚNCIOS DE VARIAÇÃO
#
# Evita aqueles:
# "vários modelos"
# "escolha o seu"
# onde o preço pode ser só da opção mais barata.
# ============================================================

TERMOS_ANUNCIO_VARIAVEL = [
    "varios modelos",
    "vários modelos",
    "diversos modelos",
    "escolha o seu",
    "escolha seu",
    "a escolha",
    "modelos variados",
    "modelo a escolher",
    "escolha o modelo",
    "selecione o modelo",
    "cores sortidas",
    "sortido",
]


# ============================================================
# SÉRIES HOT WHEELS
# ============================================================

SERIES_HW = [
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

    ("silver series", "Silver Series"),

    ("elite 64", "Elite 64"),
    ("rlc", "RLC"),

    ("car culture", "Car Culture"),

    ("premium", "Premium"),
]


# ============================================================
# MODELOS TOP
# ============================================================

MODELOS_TOP = [
    "ferrari",
    "testarossa",
    "f40",
    "f50",

    "porsche",
    "911",
    "gt3",
    "gt2",
    "carrera",

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

    "lancer evolution",
    "evolution",

    "mazda",

    "nissan",
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
        c
        for c in texto
        if not unicodedata.combining(c)
    )

    return texto


# ============================================================
# VENDEDOR
# ============================================================

def pegar_vendedor(item):

    return str(
        item.get("seller")
        or item.get("source")
        or item.get("store")
        or ""
    ).strip()


# ============================================================
# LOJA BR
# ============================================================

def loja_brasileira(item):

    vendedor = normalizar(
        pegar_vendedor(item)
    )

    titulo = normalizar(
        item.get("title", "")
    )

    combinado = (
        vendedor
        + " "
        + titulo
    )

    if not vendedor:
        return False

    for loja in LOJAS_PROIBIDAS:

        if normalizar(loja) in vendedor:
            return False

    for termo in TERMOS_IMPORTACAO:

        if normalizar(termo) in combinado:
            return False

    for loja in LOJAS_BRASIL:

        if normalizar(loja) in vendedor:
            return True

    return False


# ============================================================
# PREÇO
# ============================================================

def converter_preco_texto(valor):

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
    ).strip()

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


def pegar_preco(item):

    preco = item.get(
        "extracted_price"
    )

    if isinstance(
        preco,
        (int, float)
    ):
        return float(preco)

    return converter_preco_texto(
        item.get("price")
    )


def pegar_preco_original(item):

    return converter_preco_texto(
        item.get("original_price")
    )


# ============================================================
# DESCONTO
# ============================================================

def calcular_desconto(
    preco,
    antigo
):

    if not preco or not antigo:
        return 0

    if antigo <= preco:
        return 0

    desconto = (
        (
            antigo - preco
        )
        /
        antigo
    ) * 100

    return round(
        desconto,
        1
    )


# ============================================================
# MARCA
# ============================================================

def identificar_marca(titulo):

    t = normalizar(
        titulo
    )

    if "kaido house" in t:
        return "Kaido House"

    if (
        "mini gt" in t
        or "minigt" in t
    ):
        return "Mini GT"

    if "tarmac works" in t:
        return "Tarmac Works"

    if "pop race" in t:
        return "Pop Race"

    if (
        "inno64" in t
        or "inno 64" in t
    ):
        return "Inno64"

    if "hot wheels" in t:
        return "Hot Wheels"

    return None


# ============================================================
# SÉRIE
# ============================================================

def identificar_serie(titulo):

    t = normalizar(
        titulo
    )

    for termo, nome in SERIES_HW:

        if normalizar(
            termo
        ) in t:

            return nome

    return ""


# ============================================================
# ESCALA ERRADA
# ============================================================

def escala_errada(titulo):

    t = normalizar(
        titulo
    )

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
        "1:48",
        "1/48",
    ]

    return any(
        escala in t
        for escala in escalas
    )


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
        "coleção completa",
        "kit com",
        "kit de",
        "lote",
        "pack com",
        "5 miniaturas",
        "10 miniaturas",
        "20 miniaturas",
        "caixa fechada",
    ]

    return any(
        normalizar(termo) in t
        for termo in termos
    )


# ============================================================
# VARIAÇÕES
# ============================================================

def anuncio_variavel(titulo):

    t = normalizar(
        titulo
    )

    return any(
        normalizar(termo) in t
        for termo in TERMOS_ANUNCIO_VARIAVEL
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

    if anuncio_variavel(titulo):
        return False

    marca = identificar_marca(
        titulo
    )

    if not marca:
        return False

    # Hot Wheels básico é descartado.
    if marca == "Hot Wheels":

        serie = identificar_serie(
            titulo
        )

        if not serie:
            return False

    return True


# ============================================================
# PREÇO MÁXIMO PARA ANALISAR
# ============================================================

def preco_valido(
    marca,
    serie,
    preco
):

    if preco is None:
        return False

    # Proteção contra parcela.
    if preco < 20:
        return False

    if marca == "Hot Wheels":

        if serie == "Silver Series":
            return preco <= 70

        # Apertado.
        if serie == "Team Transport":
            return preco <= 145

        if serie in [
            "Elite 64",
            "RLC"
        ]:
            return preco <= 180

        # Premium unitário
        return preco <= 85

    if marca == "Mini GT":
        return preco <= 135

    if marca == "Kaido House":
        return preco <= 180

    if marca == "Tarmac Works":
        return preco <= 150

    if marca == "Pop Race":
        return preco <= 150

    if marca == "Inno64":
        return preco <= 160

    return False


# ============================================================
# MODELOS TOP
# ============================================================

def quantidade_modelos_top(titulo):

    t = normalizar(
        titulo
    )

    encontrados = set()

    for modelo in MODELOS_TOP:

        modelo_n = normalizar(
            modelo
        )

        if modelo_n in t:

            encontrados.add(
                modelo_n
            )

    return len(
        encontrados
    )


# ============================================================
# SCORE DA LOJA
#
# Mercado Livre sobe,
# mas não transforma preço ruim em oferta.
# ============================================================

def score_loja(vendedor):

    v = normalizar(
        vendedor
    )

    if (
        "mercadolivre" in v
        or "mercado livre" in v
    ):
        return 15

    if "amazon" in v:
        return 7

    if "magalu" in v:
        return 6

    if "shopee" in v:
        return 5

    if "casas bahia" in v:
        return 4

    if "ri happy" in v:
        return 4

    return 0


# ============================================================
# SCORE
# ============================================================

def calcular_score(oferta):

    score = 0

    titulo = oferta["titulo"]
    marca = oferta["marca"]
    serie = oferta["serie"]
    preco = oferta["preco"]
    desconto = oferta["desconto"]
    vendedor = oferta["vendedor"]

    # ========================================================
    # LOJA
    # ========================================================

    score += score_loja(
        vendedor
    )

    # ========================================================
    # MODELO TOP
    # ========================================================

    qtd_top = quantidade_modelos_top(
        titulo
    )

    if qtd_top >= 1:
        score += 10

    if qtd_top >= 2:
        score += 5

    # ========================================================
    # HOT WHEELS
    # ========================================================

    if marca == "Hot Wheels":

        score += 15

        series_fortes = [
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
        ]

        if serie in series_fortes:

            score += 18

        elif serie == "Car Culture":

            score += 18

        elif serie == "Boulevard":

            score += 18

        elif serie == "Fast & Furious":

            score += 17

        elif serie == "Pop Culture":

            score += 12

        elif serie == "Silver Series":

            score += 8

        elif serie == "Team Transport":

            score += 12

        elif serie in [
            "Elite 64",
            "RLC"
        ]:

            score += 15

        elif serie == "Premium":

            score += 10

        # ====================================================
        # TEAM TRANSPORT
        # ====================================================

        if serie == "Team Transport":

            if preco <= 100:
                score += 45

            elif preco <= 110:
                score += 40

            elif preco <= 120:
                score += 34

            elif preco <= 125:
                score += 30

            elif preco <= 130:
                score += 24

            elif preco <= 135:
                score += 18

            elif preco <= 140:
                score += 10

            else:
                score += 2

        # ====================================================
        # ELITE/RLC
        # ====================================================

        elif serie in [
            "Elite 64",
            "RLC"
        ]:

            if preco <= 100:
                score += 40

            elif preco <= 125:
                score += 30

            elif preco <= 150:
                score += 20

            elif preco <= 170:
                score += 8

        # ====================================================
        # PREMIUM UNITÁRIO
        # ====================================================

        else:

            if preco <= 45:
                score += 50

            elif preco <= 50:
                score += 46

            elif preco <= 55:
                score += 41

            elif preco <= 60:
                score += 35

            elif preco <= 65:
                score += 29

            elif preco <= 70:
                score += 21

            elif preco <= 75:
                score += 12

            elif preco <= 80:
                score += 5

            elif preco <= 85:
                score -= 3

    # ========================================================
    # MINI GT
    # ========================================================

    elif marca == "Mini GT":

        score += 20

        if preco <= 85:
            score += 45

        elif preco <= 95:
            score += 38

        elif preco <= 105:
            score += 30

        elif preco <= 115:
            score += 22

        elif preco <= 125:
            score += 14

        elif preco <= 135:
            score += 5

    # ========================================================
    # KAIDO HOUSE
    # ========================================================

    elif marca == "Kaido House":

        score += 20

        if preco <= 125:
            score += 50

        elif preco <= 135:
            score += 42

        elif preco <= 145:
            score += 34

        elif preco <= 155:
            score += 26

        elif preco <= 165:
            score += 18

        elif preco <= 175:
            score += 8

        else:
            score -= 5

    # ========================================================
    # OUTROS PREMIUM
    # ========================================================

    else:

        score += 18

        if preco <= 90:
            score += 40

        elif preco <= 105:
            score += 32

        elif preco <= 120:
            score += 24

        elif preco <= 135:
            score += 15

        elif preco <= 150:
            score += 5

    # ========================================================
    # DESCONTO
    # ========================================================

    if desconto >= 35:
        score += 30

    elif desconto >= 25:
        score += 22

    elif desconto >= 20:
        score += 17

    elif desconto >= 15:
        score += 12

    elif desconto >= 10:
        score += 6

    return score


# ============================================================
# CLASSIFICAÇÃO
# ============================================================

def classificar(score):

    if score >= 90:
        return "💎 ACHADO"

    if score >= 75:
        return "🚨 IMPERDÍVEL"

    if score >= 60:
        return "🔥 BOA OFERTA"

    return "👀 INTERESSANTE"


# ============================================================
# SEARCHAPI
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

    try:

        resposta = requests.get(
            SEARCH_URL,
            params=params,
            timeout=TIMEOUT_SEARCHAPI
        )

    except requests.exceptions.Timeout:

        print(
            "TIMEOUT SEARCHAPI:"
        )

        print(
            "A consulta demorou mais de",
            TIMEOUT_SEARCHAPI,
            "segundos."
        )

        # NÃO tenta novamente.
        # Evita gastar uma segunda consulta.
        return [], False

    except Exception as erro:

        print(
            "ERRO SEARCHAPI:",
            erro
        )

        return [], False

    print(
        "STATUS SEARCHAPI:",
        resposta.status_code
    )

    if resposta.status_code != 200:

        print(
            resposta.text[:1000]
        )

        return [], False

    try:

        dados = resposta.json()

    except Exception as erro:

        print(
            "ERRO JSON:",
            erro
        )

        return [], False

    resultados = dados.get(
        "shopping_results",
        []
    )

    return resultados, True


# ============================================================
# LINK
# ============================================================

def pegar_link(item):

    return str(
        item.get("product_link")
        or item.get("link")
        or ""
    )


# ============================================================
# CHAVE
# ============================================================

def chave_oferta(oferta):

    product_id = oferta.get(
        "product_id"
    )

    if product_id:
        return str(product_id)

    titulo = normalizar(
        oferta["titulo"]
    )

    vendedor = normalizar(
        oferta["vendedor"]
    )

    titulo = re.sub(
        r"\s+",
        " ",
        titulo
    ).strip()

    return (
        titulo
        + "|"
        + vendedor
    )


# ============================================================
# PREÇO BR
# ============================================================

def formatar_preco(valor):

    texto = f"{valor:,.2f}"

    texto = texto.replace(
        ",",
        "X"
    )

    texto = texto.replace(
        ".",
        ","
    )

    texto = texto.replace(
        "X",
        "."
    )

    return "R$ " + texto


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
# EMAIL
# ============================================================

def enviar_email(
    ofertas,
    estatisticas
):

    assunto = (
        f"🏎️ DIECAST: "
        f"{len(ofertas)} ofertas "
        f"- {PERIODO}"
    )

    linhas = []

    linhas.append(
        "🏎️ BUSCADOR DIECAST PREMIUM"
    )

    linhas.append(
        f"RODADA: {PERIODO}"
    )

    linhas.append(
        AGORA_BRASIL.strftime(
            "%d/%m/%Y %H:%M"
        )
    )

    linhas.append(
        "=" * 72
    )

    if not ofertas:

        linhas.append("")

        linhas.append(
            "Nenhuma oferta realmente boa encontrada."
        )

    for oferta in ofertas:

        linhas.append("")

        linhas.append(
            oferta["classificacao"]
        )

        linhas.append("")

        linhas.append(
            "LOJA: "
            + oferta["vendedor"]
        )

        linhas.append(
            "MARCA: "
            + oferta["marca"]
        )

        if oferta["serie"]:

            linhas.append(
                "SÉRIE: "
                + oferta["serie"]
            )

        linhas.append(
            "TÍTULO: "
            + oferta["titulo"]
        )

        linhas.append(
            "PREÇO TOTAL: "
            + formatar_preco(
                oferta["preco"]
            )
        )

        linhas.append(
            "PARCELAMENTO: IGNORADO"
        )

        if oferta[
            "preco_original"
        ]:

            linhas.append(
                "PREÇO ANTERIOR: "
                + formatar_preco(
                    oferta[
                        "preco_original"
                    ]
                )
            )

        if oferta[
            "desconto"
        ] > 0:

            linhas.append(
                f"DESCONTO REAL: "
                f"{oferta['desconto']:.1f}%"
            )

        linhas.append(
            f"SCORE: "
            f"{oferta['score']}"
        )

        linhas.append(
            "LINK: "
            + oferta["link"]
        )

        linhas.append(
            "-" * 72
        )

    linhas.append("")

    linhas.append(
        "=" * 72
    )

    linhas.append(
        "BUSCAS UTILIZADAS:"
    )

    for busca in BUSCAS:

        linhas.append(
            "- " + busca
        )

    linhas.append("")

    linhas.append(
        f"CONSULTAS COM RESPOSTA 200: "
        f"{estatisticas['consultas_ok']}"
    )

    linhas.append(
        f"CONSULTAS COM FALHA/TIMEOUT: "
        f"{estatisticas['consultas_falha']}"
    )

    linhas.append(
        f"RESULTADOS ANALISADOS: "
        f"{estatisticas['analisados']}"
    )

    linhas.append(
        f"LOJAS/INTERNACIONAIS DESCARTADOS: "
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

    contexto_ssl = ssl.create_default_context()

    with smtplib.SMTP_SSL(
        "smtp.gmail.com",
        465,
        context=contexto_ssl
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


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)

    print(
        "BUSCADOR DIECAST - PREMIUM NACIONAL V3"
    )

    print(
        "DATA:",
        AGORA_BRASIL.strftime(
            "%d/%m/%Y %H:%M"
        )
    )

    print(
        "RODADA:",
        PERIODO
    )

    print(
        "BUSCAS PLANEJADAS:",
        len(BUSCAS)
    )

    print("=" * 80)

    candidatos = []

    estatisticas = {
        "consultas_ok": 0,
        "consultas_falha": 0,
        "analisados": 0,
        "lojas": 0,
        "produtos": 0,
        "precos": 0,
    }

    # ========================================================
    # BUSCAS
    # ========================================================

    for numero, termo in enumerate(
        BUSCAS,
        start=1
    ):

        print()

        print(
            f"BUSCA "
            f"{numero}/{len(BUSCAS)}"
        )

        print()

        print(
            termo
        )

        resultados, sucesso = (
            buscar_shopping(
                termo
            )
        )

        if sucesso:

            estatisticas[
                "consultas_ok"
            ] += 1

        else:

            estatisticas[
                "consultas_falha"
            ] += 1

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
        # RESULTADOS
        # ====================================================

        for item in resultados:

            if not loja_brasileira(
                item
            ):

                estatisticas[
                    "lojas"
                ] += 1

                continue

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

            desconto = calcular_desconto(
                preco,
                antigo
            )

            oferta = {
                "titulo": titulo,

                "marca": marca,

                "serie": serie,

                "vendedor": pegar_vendedor(
                    item
                ),

                "preco": preco,

                "preco_original": antigo,

                "desconto": desconto,

                "link": pegar_link(
                    item
                ),

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
    # DEDUPLICAÇÃO
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

        elif (
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
    # QUALIDADE FINAL
    #
    # 55 é o mínimo.
    # Então "interessante" agora precisa ter alguma qualidade.
    # ========================================================

    ofertas = [
        oferta
        for oferta in ofertas
        if oferta["score"] >= 55
    ]

    # ========================================================
    # ORDENAR
    # ========================================================

    ofertas.sort(
        key=lambda x: (
            -x["score"],
            x["preco"]
        )
    )

    ofertas = ofertas[
        :MAX_OFERTAS_EMAIL
    ]

    # ========================================================
    # HISTÓRICO DIÁRIO
    # ========================================================

    hoje = AGORA_BRASIL.strftime(
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
        ][chave] = {

            "titulo":
                oferta["titulo"],

            "preco":
                oferta["preco"],

            "score":
                oferta["score"],

            "loja":
                oferta["vendedor"],
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
                oferta["vendedor"]
                + "\n"
            )

            arquivo.write(
                formatar_preco(
                    oferta["preco"]
                )
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
            oferta[
                "classificacao"
            ]
        )

        print()

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

        if oferta["serie"]:

            print(
                "SÉRIE:",
                oferta["serie"]
            )

        print(
            "TÍTULO:",
            oferta["titulo"]
        )

        print(
            "PREÇO TOTAL:",
            formatar_preco(
                oferta["preco"]
            )
        )

        print(
            "PARCELAMENTO: IGNORADO"
        )

        if oferta["desconto"]:

            print(
                "DESCONTO REAL:",
                str(
                    oferta[
                        "desconto"
                    ]
                )
                + "%"
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
        "Enviando relatório..."
    )

    try:

        enviar_email(
            ofertas,
            estatisticas
        )

        print(
            "📧 EMAIL ENVIADO."
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

    print("=" * 80)

    print(
        "RESUMO"
    )

    print("=" * 80)

    print(
        "RODADA:",
        PERIODO
    )

    print(
        "BUSCAS:"
    )

    for busca in BUSCAS:

        print(
            " -",
            busca
        )

    print()

    print(
        "CONSULTAS COM STATUS 200:",
        estatisticas[
            "consultas_ok"
        ]
    )

    print(
        "CONSULTAS COM FALHA/TIMEOUT:",
        estatisticas[
            "consultas_falha"
        ]
    )

    print(
        "RESULTADOS ANALISADOS:",
        estatisticas[
            "analisados"
        ]
    )

    print(
        "INTERNACIONAIS/LOJAS DESCARTADOS:",
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

    print("=" * 80)


# ============================================================
# EXECUTAR
# ============================================================

if __name__ == "__main__":
    main()
