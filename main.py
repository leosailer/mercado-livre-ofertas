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

FUSO_BRASIL = timezone(timedelta(hours=-3))
AGORA_BRASIL = datetime.now(FUSO_BRASIL)


# ============================================================
# ROTAÇÃO INTELIGENTE DAS BUSCAS
#
# REGRA:
# - somente 2 buscas por execução
# - queries CURTAS
# - nunca juntar um monte de séries
# - Hot Wheels domina a busca
# - marcas premium alternativas entram em rotação
# ============================================================

HORA = AGORA_BRASIL.hour
DIA_SEMANA = AGORA_BRASIL.weekday()


if HORA < 13:
    PERIODO = "MANHÃ"
else:
    PERIODO = "TARDE"


ROTACOES = {

    # SEGUNDA
    0: {
        "MANHÃ": [
            "Hot Wheels Premium",
            "Hot Wheels Car Culture",
        ],
        "TARDE": [
            "Hot Wheels Boulevard",
            "Hot Wheels Silver Series",
        ],
    },

    # TERÇA
    1: {
        "MANHÃ": [
            "Hot Wheels Modern Classics",
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
            "Hot Wheels Premium",
            "Hot Wheels Race Day",
        ],
        "TARDE": [
            "Hot Wheels Boulevard",
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
            "Kaido House",
        ],
    },

    # SEXTA
    4: {
        "MANHÃ": [
            "Hot Wheels Premium",
            "Hot Wheels Boulevard",
        ],
        "TARDE": [
            "Hot Wheels Team Transport",
            "Mini GT Kaido House",
        ],
    },

    # SÁBADO
    5: {
        "MANHÃ": [
            "Hot Wheels Car Culture",
            "Hot Wheels Silver Series",
        ],
        "TARDE": [
            "Tarmac Works",
            "Pop Race",
        ],
    },

    # DOMINGO
    6: {
        "MANHÃ": [
            "Hot Wheels Premium",
            "Hot Wheels Boulevard",
        ],
        "TARDE": [
            "Hot Wheels Car Culture",
            "Inno64",
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
# LOJAS E TERMOS PROIBIDOS
# ============================================================

LOJAS_PROIBIDAS = [
    "ebay",
    "aliexpress",
    "aliexpress-",
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
# MODELOS QUE MERECEM PRIORIDADE
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
    "evo",

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

    texto = unicodedata.normalize("NFKD", texto)

    return "".join(
        c for c in texto
        if not unicodedata.combining(c)
    )


# ============================================================
# VENDEDOR
# ============================================================

def pegar_vendedor(item):
    vendedor = (
        item.get("seller")
        or item.get("source")
        or item.get("store")
        or ""
    )

    return str(vendedor).strip()


# ============================================================
# LOJA NACIONAL
# ============================================================

def loja_brasileira(item):

    vendedor = normalizar(pegar_vendedor(item))
    titulo = normalizar(item.get("title", ""))

    combinado = vendedor + " " + titulo

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

    if isinstance(valor, (int, float)):
        return float(valor)

    texto = str(valor)

    texto = texto.replace("R$", "").strip()

    match = re.search(r"[\d\.,]+", texto)

    if not match:
        return None

    numero = match.group()

    if "," in numero:
        numero = numero.replace(".", "")
        numero = numero.replace(",", ".")

    try:
        return float(numero)
    except:
        return None


def pegar_preco(item):

    # extracted_price normalmente é o preço total estruturado.
    preco = item.get("extracted_price")

    if isinstance(preco, (int, float)):
        return float(preco)

    return converter_preco_texto(
        item.get("price")
    )


def pegar_preco_original(item):

    valor = item.get("original_price")

    return converter_preco_texto(valor)


# ============================================================
# DESCONTO
# ============================================================

def calcular_desconto(preco, antigo):

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
# SÉRIE HOT WHEELS
# ============================================================

def identificar_serie(titulo):

    t = normalizar(titulo)

    for termo, nome in SERIES_HW:

        if normalizar(termo) in t:
            return nome

    return ""


# ============================================================
# ESCALA
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
        "1:48",
        "1/48",
    ]

    return any(
        escala in t
        for escala in proibidas
    )


# ============================================================
# KIT / LOTE
# ============================================================

def kit_ou_lote(titulo):

    t = normalizar(titulo)

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
# PRODUTO VÁLIDO
# ============================================================

def produto_valido(item):

    titulo = item.get("title", "")

    if not loja_brasileira(item):
        return False

    if escala_errada(titulo):
        return False

    if kit_ou_lote(titulo):
        return False

    marca = identificar_marca(titulo)

    if not marca:
        return False

    # Hot Wheels básico não interessa.
    # Queremos linhas premium/colecionáveis.
    if marca == "Hot Wheels":

        serie = identificar_serie(titulo)

        if not serie:
            return False

    return True


# ============================================================
# LIMITES DE PREÇO
# ============================================================

def preco_valido(marca, serie, preco):

    if preco is None:
        return False

    # Proteção contra valores absurdamente baixos
    # que podem ser parcelas.
    if preco < 20:
        return False

    if marca == "Hot Wheels":

        if serie == "Silver Series":
            return preco <= 75

        if serie == "Team Transport":
            return preco <= 170

        if serie in ["Elite 64", "RLC"]:
            return preco <= 190

        # Premium unitário normal
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
# MODELO DESEJADO
# ============================================================

def quantidade_modelos_top(titulo):

    t = normalizar(titulo)

    encontrados = set()

    for modelo in MODELOS_TOP:

        if normalizar(modelo) in t:
            encontrados.add(modelo)

    return len(encontrados)


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
    vendedor = normalizar(oferta["vendedor"])

    # ========================================================
    # MERCADO LIVRE
    # ========================================================

    if (
        "mercadolivre" in vendedor
        or "mercado livre" in vendedor
    ):
        score += 30

        if marca == "Hot Wheels":
            score += 15

    elif "amazon" in vendedor:
        score += 10

    elif "magalu" in vendedor:
        score += 8

    elif "shopee" in vendedor:
        score += 6

    elif "casas bahia" in vendedor:
        score += 5

    elif "ri happy" in vendedor:
        score += 5

    # ========================================================
    # MODELOS TOP
    # ========================================================

    qtd_top = quantidade_modelos_top(titulo)

    if qtd_top >= 1:
        score += 10

    if qtd_top >= 2:
        score += 5

    # ========================================================
    # HOT WHEELS
    # ========================================================

    if marca == "Hot Wheels":

        score += 10

        SERIES_MAIS_FORTES = [
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

        if serie in SERIES_MAIS_FORTES:
            score += 18

        elif serie == "Boulevard":
            score += 18

        elif serie == "Car Culture":
            score += 17

        elif serie == "Fast & Furious":
            score += 16

        elif serie == "Pop Culture":
            score += 12

        elif serie == "Silver Series":
            score += 9

        elif serie == "Team Transport":
            score += 8

        elif serie in ["Elite 64", "RLC"]:
            score += 15

        elif serie == "Premium":
            score += 8

        # PREÇO HOT WHEELS

        if serie == "Team Transport":

            if preco <= 110:
                score += 35
            elif preco <= 130:
                score += 25
            elif preco <= 150:
                score += 15
            else:
                score += 5

        elif serie in ["Elite 64", "RLC"]:

            if preco <= 100:
                score += 35
            elif preco <= 130:
                score += 25
            elif preco <= 160:
                score += 15
            else:
                score += 5

        else:

            if preco <= 50:
                score += 45

            elif preco <= 55:
                score += 40

            elif preco <= 60:
                score += 34

            elif preco <= 65:
                score += 28

            elif preco <= 70:
                score += 21

            elif preco <= 75:
                score += 15

            elif preco <= 80:
                score += 8

            elif preco <= 85:
                score += 3

            else:
                score -= 5

    # ========================================================
    # MINI GT
    # ========================================================

    elif marca == "Mini GT":

        score += 20

        if preco <= 90:
            score += 40

        elif preco <= 105:
            score += 30

        elif preco <= 120:
            score += 20

        elif preco <= 135:
            score += 10

        else:
            score += 3

    # ========================================================
    # KAIDO HOUSE
    # ========================================================

    elif marca == "Kaido House":

        score += 25

        if preco <= 125:
            score += 45

        elif preco <= 140:
            score += 38

        elif preco <= 155:
            score += 30

        elif preco <= 170:
            score += 20

        elif preco <= 185:
            score += 10

        else:
            score += 3

    # ========================================================
    # OUTRAS PREMIUM
    # ========================================================

    else:

        score += 18

        if preco <= 100:
            score += 35

        elif preco <= 120:
            score += 25

        elif preco <= 140:
            score += 15

        else:
            score += 5

    # ========================================================
    # DESCONTO REAL
    # ========================================================

    if desconto >= 30:
        score += 30

    elif desconto >= 20:
        score += 20

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
        return "🚨 IMPERDÍVEL"

    if score >= 65:
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
            timeout=45
        )

    except Exception as erro:

        print("ERRO DE CONEXÃO:", erro)

        return []

    print(
        "STATUS SEARCHAPI:",
        resposta.status_code
    )

    if resposta.status_code != 200:

        print(resposta.text[:1000])

        return []

    try:

        dados = resposta.json()

    except Exception as erro:

        print(
            "ERRO JSON:",
            erro
        )

        return []

    resultados = dados.get(
        "shopping_results",
        []
    )

    return resultados


# ============================================================
# LINK
# ============================================================

def pegar_link(item):

    candidatos = [
        item.get("product_link"),
        item.get("link"),
    ]

    for link in candidatos:

        if link:
            return str(link)

    return ""


# ============================================================
# CHAVE PARA DUPLICADOS
# ============================================================

def chave_oferta(oferta):

    product_id = oferta.get("product_id")

    if product_id:
        return str(product_id)

    titulo = normalizar(oferta["titulo"])
    vendedor = normalizar(oferta["vendedor"])

    # Limpeza leve para reduzir duplicação
    titulo = re.sub(
        r"\s+",
        " ",
        titulo
    ).strip()

    return titulo + "|" + vendedor


# ============================================================
# FORMATAR PREÇO
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

    if not os.path.exists(HISTORICO_ARQUIVO):
        return {}

    try:

        with open(
            HISTORICO_ARQUIVO,
            "r",
            encoding="utf-8"
        ) as arquivo:

            return json.load(arquivo)

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

def enviar_email(ofertas, estatisticas):

    assunto = (
        f"🏎️ DIECAST: {len(ofertas)} ofertas "
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
            "Nenhuma oferta realmente interessante encontrada."
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

        if oferta["preco_original"]:

            linhas.append(
                "PREÇO ANTERIOR: "
                + formatar_preco(
                    oferta["preco_original"]
                )
            )

        if oferta["desconto"] > 0:

            linhas.append(
                f"DESCONTO REAL: "
                f"{oferta['desconto']:.1f}%"
            )

        linhas.append(
            f"SCORE: {oferta['score']}"
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

    corpo = "\n".join(linhas)

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
        "BUSCADOR DIECAST - PREMIUM NACIONAL"
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
        "BUSCAS SEARCHAPI:",
        len(BUSCAS)
    )

    print("=" * 80)

    candidatos = []

    estatisticas = {
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
            f"BUSCA {numero}/{len(BUSCAS)}"
        )

        print()

        print(termo)

        print()

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

        # ====================================================
        # RESULTADOS
        # ====================================================

        for item in resultados:

            # LOJA

            if not loja_brasileira(item):

                estatisticas["lojas"] += 1

                continue

            # PRODUTO

            if not produto_valido(item):

                estatisticas["produtos"] += 1

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

                estatisticas["precos"] += 1

                continue

            antigo = pegar_preco_original(
                item
            )

            desconto = calcular_desconto(
                preco,
                antigo
            )

            vendedor = pegar_vendedor(
                item
            )

            link = pegar_link(
                item
            )

            oferta = {
                "titulo": titulo,
                "marca": marca,
                "serie": serie,
                "vendedor": vendedor,
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

            unicos[chave] = oferta

            continue

        # mantém a opção de menor preço

        if oferta["preco"] < existente["preco"]:

            unicos[chave] = oferta

    ofertas = list(
        unicos.values()
    )

    # ========================================================
    # SCORE MÍNIMO
    # ========================================================

    ofertas = [
        oferta
        for oferta in ofertas
        if oferta["score"] >= 45
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
    #
    # IMPORTANTE:
    # zeramos conceitualmente todo novo dia.
    #
    # Portanto:
    # se apareceu ontem a R$ 59,90
    # e hoje continua R$ 59,90,
    # PODE aparecer novamente.
    # ========================================================

    hoje = AGORA_BRASIL.strftime(
        "%Y-%m-%d"
    )

    historico = carregar_historico()

    if historico.get("data") != hoje:

        historico = {
            "data": hoje,
            "ofertas": {}
        }

    for oferta in ofertas:

        chave = chave_oferta(
            oferta
        )

        historico["ofertas"][chave] = {
            "titulo": oferta["titulo"],
            "preco": oferta["preco"],
            "score": oferta["score"],
            "loja": oferta["vendedor"],
        }

    salvar_historico(
        historico
    )

    # ========================================================
    # LINKS PARA AFILIADO
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
            oferta["classificacao"]
        )

        print()

        print(
            "LOJA:",
            oferta["vendedor"]
        )

        print(
            "MARCA:",
            oferta["marca"]
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
                    oferta["desconto"]
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
        "CRÉDITOS SEARCHAPI CONSUMIDOS:",
        len(BUSCAS)
    )

    print(
        "RESULTADOS ANALISADOS:",
        estatisticas["analisados"]
    )

    print(
        "INTERNACIONAIS/LOJAS DESCARTADOS:",
        estatisticas["lojas"]
    )

    print(
        "PRODUTOS DESCARTADOS:",
        estatisticas["produtos"]
    )

    print(
        "PREÇOS DESCARTADOS:",
        estatisticas["precos"]
    )

    print(
        "OFERTAS ENVIADAS:",
        len(ofertas)
    )

    print("=" * 80)


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":
    main()
