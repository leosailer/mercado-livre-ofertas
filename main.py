import os
import re
import json
import ssl
import smtplib
import unicodedata

from datetime import datetime
from zoneinfo import ZoneInfo
from email.message import EmailMessage
from pathlib import Path

import requests


# =========================================================
# CONFIGURAÇÕES
# =========================================================

SERPAPI_KEY = os.getenv("SERPAPI_KEY")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
EMAIL_DESTINO = os.getenv("EMAIL_DESTINO")

SERP_URL = "https://serpapi.com/search.json"

ARQUIVO_HISTORICO = Path("ofertas_vistas.json")
ARQUIVO_ML = Path("links_para_afiliado.txt")
ARQUIVO_AMAZON = Path("links_amazon.txt")

FUSO_BRASIL = ZoneInfo("America/Sao_Paulo")
HOJE = datetime.now(FUSO_BRASIL).date().isoformat()

VERSAO_HISTORICO = "v6"


# =========================================================
# HOT WHEELS - LINHAS PREMIUM / COLLECTOR
# =========================================================

SERIES_HOT_WHEELS = [

    # PREMIUM
    "premium",
    "car culture",
    "boulevard",
    "pop culture",
    "entertainment",
    "premium entertainment",

    # FAST & FURIOUS
    "fast & furious",
    "fast and furious",
    "fast & furious premium",
    "fast and furious premium",

    # TEAM TRANSPORT
    "team transport",

    # COLLECTOR
    "elite 64",
    "rlc",
    "red line club",

    # SILVER
    "silver series",

    # CAR CULTURE / MIXES
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
    "euro speed",
    "canyon warriors",
    "cargo carriers",
    "open track",
    "door slammers",
    "wild terrain",
    "dragstrip demons",
    "drag strip demons",
    "vintage racing",
    "street tuners",
    "aerostyles",

    # SINAIS PREMIUM
    "real riders",
    "metal/metal",
    "metal metal",

    # SETS
    "collector set",
    "premium collector",
    "premium set",
    "display set"
]


# =========================================================
# MODELOS TOP
#
# Quanto maior o número, maior a prioridade.
# =========================================================

MODELOS_TOP_SCORE = {

    # FERRARI
    "ferrari testarossa": 35,
    "ferrari f40": 40,
    "ferrari f50": 40,
    "ferrari 250 gto": 40,
    "ferrari 499p": 35,
    "ferrari": 25,

    # PORSCHE
    "porsche 911": 30,
    "porsche 935": 30,
    "porsche 993": 32,
    "porsche carrera": 30,
    "porsche": 22,

    # NISSAN / JDM
    "skyline r34": 35,
    "skyline r33": 30,
    "skyline r32": 30,
    "skyline": 25,
    "nissan gtr": 28,
    "nissan gt r": 28,

    # TOYOTA
    "supra": 28,

    # MAZDA
    "rx7": 28,
    "rx 7": 28,

    # HONDA
    "nsx": 25,
    "honda crx": 22,
    "civic": 18,

    # EUROPEUS / SUPERCARS
    "lamborghini": 25,
    "mclaren": 25,
    "koenigsegg": 30,
    "bugatti": 30,

    # ALEMÃES
    "bmw m3": 25,
    "bmw m1": 22,
    "bmw": 16,

    "audi quattro": 22,
    "audi": 15,

    "mercedes amg": 20,
    "mercedes": 15,

    # OUTROS
    "lancer evolution": 25,
    "mustang": 18,
    "corvette": 18,
    "datsun 510": 25
}


# =========================================================
# TERMOS FORTES PARA CONFERIR PRODUTO
# =========================================================

TERMOS_FORTES = [

    "ferrari",
    "testarossa",
    "f40",
    "f50",
    "250 gto",
    "499p",

    "porsche",
    "911",
    "935",
    "993",
    "gt3",
    "gt2",
    "carrera",

    "lamborghini",
    "countach",
    "huracan",

    "mclaren",
    "koenigsegg",

    "bmw",
    "m1",
    "m3",
    "m4",
    "m5",

    "audi",
    "quattro",

    "mercedes",
    "amg",

    "mustang",
    "svo",

    "datsun",
    "510",

    "skyline",
    "r32",
    "r33",
    "r34",

    "gtr",
    "gt-r",

    "supra",

    "rx7",
    "rx-7",

    "nsx",
    "civic",

    "corvette",

    "spiderman",
    "spider man",
    "ground fx"
]


# =========================================================
# BUSCAS
#
# Agora temos buscas gerais + buscas de modelos quentes.
# =========================================================

BUSCAS = [

    # =====================================================
    # PREMIUM GERAIS
    # =====================================================

    '"Hot Wheels Car Culture"',

    '"Hot Wheels Boulevard"',

    '"Hot Wheels Silver Series"',

    '"Hot Wheels Pop Culture"',

    '"Hot Wheels Premium Entertainment"',

    '"Hot Wheels Team Transport"',

    '"Hot Wheels Fast Furious Premium"',

    # =====================================================
    # MIXES CAR CULTURE
    # =====================================================

    '("Hot Wheels Modern Classics" OR '
    '"Hot Wheels Japan Historics" OR '
    '"Hot Wheels Race Day" OR '
    '"Hot Wheels Circuit Legends" OR '
    '"Hot Wheels Mountain Drifters" OR '
    '"Hot Wheels Ronin Run" OR '
    '"Hot Wheels Vintage Racing")',

    # =====================================================
    # FERRARI PREMIUM
    # =====================================================

    '"Hot Wheels" Ferrari '
    '("Car Culture" OR Premium OR Boulevard OR '
    '"Real Riders")',

    # =====================================================
    # PORSCHE PREMIUM
    # =====================================================

    '"Hot Wheels" Porsche '
    '("Car Culture" OR Premium OR Boulevard OR '
    '"Real Riders")',

    # =====================================================
    # SKYLINE / JDM
    # =====================================================

    '"Hot Wheels" '
    '(Skyline OR "GT-R" OR Supra OR RX-7) '
    '("Car Culture" OR Premium OR Boulevard OR '
    '"Real Riders")',

    # =====================================================
    # LAMBORGHINI / MCLAREN / SUPERCARS
    # =====================================================

    '"Hot Wheels" '
    '(Lamborghini OR McLaren OR Koenigsegg OR Bugatti) '
    '(Premium OR "Car Culture" OR Boulevard)',

    # =====================================================
    # BMW / AUDI / MERCEDES
    # =====================================================

    '"Hot Wheels" '
    '(BMW OR Audi OR Mercedes) '
    '(Premium OR "Car Culture" OR Boulevard OR '
    '"Silver Series")',

    # =====================================================
    # COLLECTOR
    # =====================================================

    '("Hot Wheels Elite 64" OR '
    '"Hot Wheels RLC" OR '
    '"Hot Wheels Red Line Club")',

    # =====================================================
    # MINI GT
    # =====================================================

    '"Mini GT" '
    'Ferrari Porsche Lamborghini McLaren Skyline GT-R '
    'Supra RX-7 BMW Mercedes Audi Honda',

    # =====================================================
    # KAIDO HOUSE
    # =====================================================

    '"Kaido House" '
    'Skyline GT-R Nissan Honda Datsun NSX Civic BMW Porsche',

    # =====================================================
    # TARMAC / POP RACE / INNO64
    # =====================================================

    '("Tarmac Works" OR "Pop Race" OR "Inno64") '
    'Porsche Ferrari Skyline GT-R RX-7 Lamborghini '
    'McLaren BMW Mercedes',

    # =====================================================
    # OUTRAS PREMIUM
    # =====================================================

    '("Matchbox Collectors" OR '
    '"Majorette Premium" OR '
    '"Tomica Premium") '
    'Porsche Ferrari Lamborghini BMW Skyline Supra'
]


# =========================================================
# FILTROS
# =========================================================

TERMOS_PROIBIDOS = [
    "usado",
    "used",
    "loose",
    "sem blister",
    "sem embalagem",
    "avariado",
    "recondicionado",
    "refurbished",
    "diorama",
    "expositor",
    "garagem",
    "roda avulsa",
    "pneu avulso",
    "protetor blister"
]


TERMOS_INTERNACIONAIS = [
    "compra internacional",
    "envio internacional",
    "frete internacional",
    "produto internacional",
    "international shipping",
    "international purchase",
    "importado",
    "importação",
    "importacao",
    "taxa de importação",
    "taxas de importação",
    "import fees",
    "ships from china",
    "enviado da china",
    "enviado do exterior",
    "envio do exterior",
    "enviado dos estados unidos"
]


ESCALAS_PROIBIDAS = [
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
    "1:50",
    "1/50"
]


FAIXAS_VALIDAS = {

    "Hot Wheels": (
        35,
        1000
    ),

    "Mini GT": (
        65,
        500
    ),

    "Kaido House": (
        90,
        700
    ),

    "Tarmac Works": (
        75,
        700
    ),

    "Pop Race": (
        75,
        700
    ),

    "Inno64": (
        75,
        700
    ),

    "Matchbox": (
        25,
        500
    ),

    "Majorette": (
        30,
        400
    ),

    "Greenlight": (
        45,
        500
    ),

    "M2 Machines": (
        50,
        600
    ),

    "Tomica": (
        35,
        400
    )
}


# =========================================================
# NORMALIZAÇÃO
# =========================================================

def remover_acentos(texto):

    texto = unicodedata.normalize(
        "NFKD",
        texto or ""
    )

    return "".join(
        c
        for c in texto
        if not unicodedata.combining(c)
    )


def normalizar(texto):

    texto = remover_acentos(
        texto or ""
    ).lower()

    texto = texto.replace(
        "spider-man",
        "spiderman"
    )

    texto = texto.replace(
        "spider man",
        "spiderman"
    )

    texto = texto.replace(
        "rx-7",
        "rx7"
    )

    texto = texto.replace(
        "gt-r",
        "gtr"
    )

    texto = re.sub(
        r"[^a-z0-9]+",
        " ",
        texto
    )

    return re.sub(
        r"\s+",
        " ",
        texto
    ).strip()


# =========================================================
# LOJA
# =========================================================

def identificar_loja(source):

    texto = normalizar(
        source
    )

    if (
        "mercado livre" in texto
        or "mercadolivre" in texto
    ):

        return "Mercado Livre"


    if "amazon" in texto:

        return "Amazon"


    return None


# =========================================================
# MARCA
# =========================================================

def identificar_marca(titulo):

    texto = normalizar(
        titulo
    )


    if "kaido house" in texto:
        return "Kaido House"

    if "mini gt" in texto:
        return "Mini GT"

    if "tarmac works" in texto:
        return "Tarmac Works"

    if "pop race" in texto:
        return "Pop Race"

    if (
        "inno64" in texto
        or "inno 64" in texto
    ):
        return "Inno64"

    if "matchbox" in texto:
        return "Matchbox"

    if "hot wheels" in texto:
        return "Hot Wheels"

    if "majorette" in texto:
        return "Majorette"

    if "greenlight" in texto:
        return "Greenlight"

    if "m2 machines" in texto:
        return "M2 Machines"

    if "tomica" in texto:
        return "Tomica"


    return None


# =========================================================
# SÉRIE
# =========================================================

def identificar_serie(
    titulo,
    snippet=""
):

    texto = normalizar(
        f"{titulo} {snippet}"
    )


    series_ordenadas = sorted(
        SERIES_HOT_WHEELS,
        key=len,
        reverse=True
    )


    for serie in series_ordenadas:

        if normalizar(
            serie
        ) in texto:

            return serie.title()


    return None


# =========================================================
# MODELO TOP + SCORE
# =========================================================

def identificar_modelo_top(
    titulo
):

    texto = normalizar(
        titulo
    )

    melhor_modelo = None
    melhor_score = 0


    for modelo, score in (
        MODELOS_TOP_SCORE.items()
    ):

        modelo_normal = normalizar(
            modelo
        )


        if modelo_normal in texto:

            if score > melhor_score:

                melhor_modelo = modelo

                melhor_score = score


    return (
        melhor_modelo,
        melhor_score
    )


# =========================================================
# ESCALA
# =========================================================

def escala_valida(
    titulo,
    snippet=""
):

    texto_original = (
        f"{titulo} {snippet}"
    ).lower()


    for escala in ESCALAS_PROIBIDAS:

        if escala in texto_original:

            return False


    escalas = re.findall(
        r"\b1\s*[:/]\s*(\d{2})\b",
        texto_original
    )


    for escala in escalas:

        if escala != "64":

            return False


    return True


# =========================================================
# INTERNACIONAL / USADO
# =========================================================

def texto_produto_valido(
    texto
):

    texto = normalizar(
        texto
    )


    for termo in TERMOS_PROIBIDOS:

        if normalizar(
            termo
        ) in texto:

            return False


    for termo in TERMOS_INTERNACIONAIS:

        if normalizar(
            termo
        ) in texto:

            return False


    return True


# =========================================================
# IDENTIDADE PRODUTO
# =========================================================

PALAVRAS_GENERICAS = {
    "hot",
    "wheels",
    "mattel",
    "premium",
    "silver",
    "series",
    "car",
    "culture",
    "carrinho",
    "carro",
    "miniatura",
    "miniature",
    "diecast",
    "modelo",
    "model",
    "escala",
    "original",
    "colecao",
    "collection",
    "diversos",
    "sortido",
    "sortidos",
    "cores",
    "cor",
    "novo",
    "nova",
    "2025",
    "2026",
    "164",
    "64"
}


def tokens_produto(texto):

    palavras = normalizar(
        texto
    ).split()

    return {
        palavra
        for palavra in palavras
        if (
            len(palavra) >= 2
            and palavra
            not in PALAVRAS_GENERICAS
        )
    }


def termos_fortes_presentes(
    texto
):

    texto_normal = normalizar(
        texto
    )

    encontrados = set()


    for termo in TERMOS_FORTES:

        termo_normal = normalizar(
            termo
        )


        if termo_normal in texto_normal:

            encontrados.add(
                termo_normal
            )


    return encontrados


def produto_corresponde(
    titulo_original,
    titulo_store,
    link_store,
    serie_original=None
):

    resolvido = normalizar(
        f"{titulo_store} {link_store}"
    )


    fortes_original = (
        termos_fortes_presentes(
            titulo_original
        )
    )


    fortes_resolvido = (
        termos_fortes_presentes(
            f"{titulo_store} {link_store}"
        )
    )


    if fortes_original:

        comuns = (
            fortes_original
            .intersection(
                fortes_resolvido
            )
        )


        if not comuns:

            return False


    tokens_original = (
        tokens_produto(
            titulo_original
        )
    )


    tokens_resolvido = (
        tokens_produto(
            resolvido
        )
    )


    if (
        len(tokens_original)
        >= 2
    ):

        comuns_tokens = (
            tokens_original
            .intersection(
                tokens_resolvido
            )
        )


        if len(
            comuns_tokens
        ) == 0:

            return False


    if serie_original:

        serie_resolvida = (
            identificar_serie(
                titulo_store,
                link_store
            )
        )


        if serie_resolvida:

            original_norm = normalizar(
                serie_original
            )

            resolvida_norm = normalizar(
                serie_resolvida
            )


            if (
                original_norm
                != "premium"
                and original_norm
                != resolvida_norm
            ):

                return False


    return True


# =========================================================
# PREÇO SHOPPING
# =========================================================

def preco_shopping_valido(
    item,
    marca
):

    preco = item.get(
        "extracted_price"
    )


    if preco is None:

        return None


    try:

        preco = float(
            preco
        )

    except:

        return None


    installment = item.get(
        "installment"
    )


    if isinstance(
        installment,
        dict
    ):

        parcela = installment.get(
            "extracted_price"
        )


        if parcela is not None:

            try:

                parcela = float(
                    parcela
                )


                if abs(
                    preco - parcela
                ) < 0.02:

                    return None


            except:

                pass


    preco_texto = str(
        item.get(
            "price",
            ""
        )
    ).upper()


    if preco_texto:

        if (
            "R$"
            not in preco_texto
            and "BRL"
            not in preco_texto
        ):

            return None


    if marca not in FAIXAS_VALIDAS:

        return None


    minimo, maximo = (
        FAIXAS_VALIDAS[
            marca
        ]
    )


    if not (
        minimo
        <= preco
        <= maximo
    ):

        return None


    return preco


# =========================================================
# SCORE DE OPORTUNIDADE
# =========================================================

def calcular_score(
    marca,
    serie,
    preco,
    desconto,
    titulo
):

    score = 0

    serie_normal = normalizar(
        serie or ""
    )


    # =====================================================
    # MODELO
    # =====================================================

    modelo_top, score_modelo = (
        identificar_modelo_top(
            titulo
        )
    )

    score += score_modelo


    # =====================================================
    # SÉRIE
    # =====================================================

    if "car culture" in serie_normal:
        score += 20

    elif "boulevard" in serie_normal:
        score += 20

    elif "team transport" in serie_normal:
        score += 18

    elif "pop culture" in serie_normal:
        score += 15

    elif "fast furious" in serie_normal:
        score += 18

    elif "silver series" in serie_normal:
        score += 10

    elif (
        "elite 64" in serie_normal
        or "rlc" in serie_normal
    ):
        score += 20

    elif "premium" in serie_normal:
        score += 15


    # =====================================================
    # PREÇO
    # =====================================================

    if marca == "Hot Wheels":

        if preco <= 54.99:
            score += 40

        elif preco <= 59.99:
            score += 35

        elif preco <= 69:
            score += 28

        elif preco <= 79:
            score += 20

        elif preco <= 89:
            score += 12


    elif marca == "Mini GT":

        if preco < 100:
            score += 40

        elif preco < 110:
            score += 32

        elif preco < 130:
            score += 22

        elif preco < 150:
            score += 12


    elif marca == "Kaido House":

        if preco <= 159:
            score += 45

        elif preco <= 169:
            score += 35

        elif preco < 199:
            score += 22


    # =====================================================
    # DESCONTO
    # =====================================================

    if desconto is not None:

        if desconto >= 40:
            score += 40

        elif desconto >= 30:
            score += 30

        elif desconto >= 20:
            score += 20

        elif desconto >= 15:
            score += 10


    return (
        score,
        modelo_top
    )


# =========================================================
# RANKING
# =========================================================

def classificar(
    marca,
    serie,
    preco,
    desconto,
    titulo
):

    score, modelo_top = (
        calcular_score(
            marca,
            serie,
            preco,
            desconto,
            titulo
        )
    )


    # =====================================================
    # PRIMEIRO VERIFICA SE ENTRA NOS FILTROS
    # =====================================================

    elegivel = False
    motivo = None


    if marca == "Hot Wheels":

        serie_normal = normalizar(
            serie or ""
        )


        if (
            "team transport"
            in serie_normal
        ):

            if preco <= 149:

                elegivel = True

                motivo = (
                    "TEAM TRANSPORT "
                    "ATÉ R$149"
                )


        elif (
            "elite 64"
            in serie_normal
            or "rlc"
            in serie_normal
            or "red line club"
            in serie_normal
        ):

            if (
                desconto is not None
                and desconto >= 15
            ):

                elegivel = True

                motivo = (
                    "COLLECTOR "
                    "COM DESCONTO"
                )


        else:

            if preco <= 99:

                elegivel = True

                motivo = (
                    "HOT WHEELS PREMIUM/"
                    "SILVER ATÉ R$99"
                )


            elif (
                desconto is not None
                and desconto >= 20
            ):

                elegivel = True

                motivo = (
                    "HOT WHEELS PREMIUM "
                    "COM 20%+ OFF"
                )


    elif marca == "Mini GT":

        if preco < 150:

            elegivel = True

            motivo = (
                "MINI GT "
                "ABAIXO DE R$150"
            )


    elif marca == "Kaido House":

        if preco < 199:

            elegivel = True

            motivo = (
                "KAIDO HOUSE "
                "ABAIXO DE R$199"
            )


        elif (
            desconto is not None
            and desconto >= 25
        ):

            elegivel = True

            motivo = (
                "KAIDO HOUSE "
                "COM 25%+ OFF"
            )


    else:

        if (
            desconto is not None
            and desconto >= 15
        ):

            elegivel = True

            motivo = (
                "DESCONTO REAL "
                "DE 15% OU MAIS"
            )


    if not elegivel:

        return None


    # =====================================================
    # RANKING PELO SCORE
    # =====================================================

    if score >= 80:

        ranking = "💎 ACHADO"
        ordem = 0


    elif score >= 60:

        ranking = "🚨 IMPERDÍVEL"
        ordem = 1


    elif score >= 40:

        ranking = "🔥 BOA OFERTA"
        ordem = 2


    else:

        ranking = "👀 INTERESSANTE"
        ordem = 3


    return (
        ranking,
        ordem,
        motivo,
        score,
        modelo_top
    )


# =========================================================
# PAGE TOKEN
# =========================================================

def obter_page_token(item):

    return item.get(
        "immersive_product_page_token"
    )


# =========================================================
# PREÇO REAL STORE
# =========================================================

def preco_real_store(store):

    total = store.get(
        "extracted_total"
    )


    if total is not None:

        try:

            total = float(
                total
            )


            if total > 0:

                return total


        except:

            pass


    parcelamento = str(
        store.get(
            "installments_description",
            ""
        )
    )


    duracao = store.get(
        "monthly_payment_duration"
    )


    if (
        parcelamento
        or duracao
    ):

        return None


    preco = store.get(
        "extracted_price"
    )


    if preco is None:

        return None


    try:

        return float(
            preco
        )


    except:

        return None


# =========================================================
# PREÇO ANTIGO
# =========================================================

def preco_antigo_store(store):

    possibilidades = [

        store.get(
            "extracted_original_price"
        ),

        store.get(
            "extracted_old_price"
        )
    ]


    for valor in possibilidades:

        if valor is None:

            continue


        try:

            valor = float(
                valor
            )


            if valor > 0:

                return valor


        except:

            pass


    return None


# =========================================================
# RESOLVER LINK EXATO
# =========================================================

def resolver_link_exato(
    shopping_item,
    loja,
    preco_shopping,
    titulo_original,
    serie_original
):

    page_token = obter_page_token(
        shopping_item
    )


    if not page_token:

        return None


    parametros = {

        "engine":
            "google_immersive_product",

        "page_token":
            page_token,

        "more_stores":
            "true",

        "api_key":
            SERPAPI_KEY
    }


    try:

        resposta = requests.get(
            SERP_URL,
            params=parametros,
            timeout=30
        )


    except Exception as erro:

        print(
            "ERRO LINK:",
            erro
        )

        return None


    if resposta.status_code != 200:

        print(
            "ERRO LINK HTTP:",
            resposta.status_code
        )

        return None


    dados = resposta.json()


    produto = dados.get(
        "product_results",
        {}
    )


    stores = produto.get(
        "stores",
        []
    )


    if not stores:

        stores = dados.get(
            "stores",
            []
        )


    candidatos = []


    for store in stores:

        link = store.get(
            "link",
            ""
        )


        if not link:

            continue


        link_lower = (
            link.lower()
        )


        # =================================================
        # LOJA
        # =================================================

        if loja == "Mercado Livre":

            if (
                "mercadolivre.com.br"
                not in link_lower
            ):

                continue


        elif loja == "Amazon":

            if (
                "amazon.com.br"
                not in link_lower
            ):

                continue


        else:

            continue


        titulo_store = (
            store.get(
                "title",
                ""
            )
        )


        # =================================================
        # MESMO PRODUTO
        # =================================================

        if not produto_corresponde(
            titulo_original,
            titulo_store,
            link,
            serie_original
        ):

            print()

            print(
                "REJEITADO POR "
                "PRODUTO DIFERENTE:"
            )

            print(
                "ORIGINAL:",
                titulo_original
            )

            print(
                "RESOLVIDO:",
                titulo_store
                or link
            )

            continue


        # =================================================
        # INTERNACIONAL / USADO
        # =================================================

        texto_validacao = " ".join([

            titulo_store,

            str(
                store.get(
                    "name",
                    ""
                )
            ),

            str(
                store.get(
                    "details_and_offers",
                    ""
                )
            ),

            str(
                store.get(
                    "shipping",
                    ""
                )
            ),

            str(
                store.get(
                    "delivery",
                    ""
                )
            )
        ])


        if not texto_produto_valido(
            texto_validacao
        ):

            continue


        # =================================================
        # PREÇO REAL
        # =================================================

        preco_real = (
            preco_real_store(
                store
            )
        )


        if preco_real is None:

            continue


        # =================================================
        # PREÇO ANTIGO
        # =================================================

        antigo = (
            preco_antigo_store(
                store
            )
        )


        diferenca = abs(
            preco_real
            - preco_shopping
        )


        percentual = (
            diferenca
            / preco_shopping
            if preco_shopping > 0
            else 999
        )


        candidatos.append({

            "link":
                link,

            "titulo_store":
                titulo_store,

            "preco":
                preco_real,

            "preco_antigo":
                antigo,

            "diferenca":
                diferenca,

            "percentual":
                percentual
        })


    if not candidatos:

        return None


    candidatos.sort(
        key=lambda x:
            x["diferenca"]
    )


    melhor = candidatos[0]


    # tolerância de preço
    if (
        melhor[
            "diferenca"
        ] > 5
        and melhor[
            "percentual"
        ] > 0.05
    ):

        return None


    return melhor


# =========================================================
# HISTÓRICO
# =========================================================

def carregar_historico():

    if not ARQUIVO_HISTORICO.exists():

        return {}


    try:

        with open(
            ARQUIVO_HISTORICO,
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
        ARQUIVO_HISTORICO,
        "w",
        encoding="utf-8"
    ) as arquivo:

        json.dump(
            historico,
            arquivo,
            ensure_ascii=False,
            indent=2
        )


# =========================================================
# E-MAIL
# =========================================================

def enviar_email(
    assunto,
    corpo
):

    if (
        not EMAIL_DESTINO
        or not GMAIL_APP_PASSWORD
    ):

        print(
            "Credenciais de e-mail ausentes."
        )

        return False


    mensagem = EmailMessage()

    mensagem[
        "Subject"
    ] = assunto

    mensagem[
        "From"
    ] = EMAIL_DESTINO

    mensagem[
        "To"
    ] = EMAIL_DESTINO


    mensagem.set_content(
        corpo
    )


    contexto = (
        ssl.create_default_context()
    )


    try:

        with smtplib.SMTP_SSL(
            "smtp.gmail.com",
            465,
            context=contexto
        ) as servidor:

            servidor.login(
                EMAIL_DESTINO,
                GMAIL_APP_PASSWORD
            )

            servidor.send_message(
                mensagem
            )


        print(
            "EMAIL ENVIADO "
            "COM SUCESSO."
        )


        return True


    except Exception as erro:

        print(
            "ERRO EMAIL:",
            erro
        )


        return False


# =========================================================
# ETAPA 1 - SHOPPING
# =========================================================

candidatos = []

ids_vistos = set()

total_shopping = 0

rejeitados_parcela = 0
rejeitados_internacional = 0
rejeitados_escala = 0
rejeitados_basico = 0


for numero, termo in enumerate(
    BUSCAS,
    start=1
):

    print()

    print(
        f"BUSCA "
        f"{numero}/"
        f"{len(BUSCAS)}"
    )

    print(
        termo
    )


    parametros = {

        "engine":
            "google_shopping",

        "q":
            termo,

        "hl":
            "pt-br",

        "gl":
            "br",

        "location":
            "Brazil",

        "api_key":
            SERPAPI_KEY
    }


    try:

        resposta = requests.get(
            SERP_URL,
            params=parametros,
            timeout=30
        )


    except Exception as erro:

        print(
            "ERRO SHOPPING:",
            erro
        )

        continue


    if resposta.status_code != 200:

        print(
            "ERRO HTTP:",
            resposta.status_code
        )

        continue


    dados = resposta.json()


    shopping = dados.get(
        "shopping_results",
        []
    )


    print(
        "RESULTADOS:",
        len(shopping)
    )


    total_shopping += len(
        shopping
    )


    for item in shopping:

        titulo = item.get(
            "title",
            ""
        )

        snippet = item.get(
            "snippet",
            ""
        )

        source = item.get(
            "source",
            ""
        )


        loja = identificar_loja(
            source
        )


        if loja is None:

            continue


        texto_validacao = " ".join([

            titulo,

            snippet,

            str(
                item.get(
                    "extensions",
                    ""
                )
            ),

            str(
                item.get(
                    "delivery",
                    ""
                )
            ),

            str(
                item.get(
                    "second_hand_condition",
                    ""
                )
            )
        ])


        if not texto_produto_valido(
            texto_validacao
        ):

            rejeitados_internacional += 1

            continue


        if not escala_valida(
            titulo,
            snippet
        ):

            rejeitados_escala += 1

            continue


        marca = identificar_marca(
            titulo
        )


        if marca is None:

            continue


        serie = None


        if marca == "Hot Wheels":

            serie = identificar_serie(
                titulo,
                snippet
            )


            if serie is None:

                rejeitados_basico += 1

                continue


        preco = preco_shopping_valido(
            item,
            marca
        )


        if preco is None:

            rejeitados_parcela += 1

            continue


        # =================================================
        # CLASSIFICAÇÃO PRELIMINAR
        # =================================================

        classificacao = classificar(
            marca,
            serie,
            preco,
            None,
            titulo
        )


        if classificacao is None:

            continue


        product_id = str(
            item.get(
                "product_id",
                ""
            )
        )


        page_token = obter_page_token(
            item
        )


        if (
            not product_id
            or not page_token
        ):

            continue


        id_produto = (
            f"{VERSAO_HISTORICO}|"
            f"{loja}|"
            f"{product_id}"
        )


        if (
            id_produto
            in ids_vistos
        ):

            continue


        ids_vistos.add(
            id_produto
        )


        candidatos.append({

            "id":
                id_produto,

            "titulo":
                titulo,

            "marca":
                marca,

            "serie":
                serie,

            "loja":
                loja,

            "preco_shopping":
                preco,

            "shopping_item":
                item
        })


# =========================================================
# ETAPA 2 - HISTÓRICO
# =========================================================

historico = carregar_historico()

para_resolver = []


for item in candidatos:

    registro = historico.get(
        item["id"]
    )


    if registro is None:

        item[
            "tipo_alerta"
        ] = "NOVA_OFERTA"

        para_resolver.append(
            item
        )

        continue


    if (
        registro.get(
            "ultima_data_enviada"
        )
        != HOJE
    ):

        item[
            "tipo_alerta"
        ] = "OFERTA_DO_DIA"

        para_resolver.append(
            item
        )

        continue


    menor = registro.get(
        "menor_preco_dia"
    )


    if (
        menor is None
        or item[
            "preco_shopping"
        ] < menor
    ):

        item[
            "tipo_alerta"
        ] = "QUEDA_PRECO"

        item[
            "preco_anterior_encontrado"
        ] = menor

        para_resolver.append(
            item
        )


# =========================================================
# ETAPA 3 - CONFIRMAÇÃO
# =========================================================

ofertas_brutas = []

sem_confirmacao = 0
preco_fora = 0


for numero, item in enumerate(
    para_resolver,
    start=1
):

    print()

    print(
        f"CONFIRMANDO "
        f"{numero}/"
        f"{len(para_resolver)}"
    )

    print(
        item[
            "titulo"
        ]
    )


    exata = resolver_link_exato(

        item[
            "shopping_item"
        ],

        item[
            "loja"
        ],

        item[
            "preco_shopping"
        ],

        item[
            "titulo"
        ],

        item[
            "serie"
        ]
    )


    if exata is None:

        sem_confirmacao += 1

        print(
            "DESCARTADO:"
            " não confirmou produto + "
            "preço + link."
        )

        continue


    preco_real = exata[
        "preco"
    ]

    preco_antigo = exata[
        "preco_antigo"
    ]


    desconto = None


    if (
        preco_antigo is not None
        and preco_antigo
        > preco_real
    ):

        desconto = (
            (
                preco_antigo
                - preco_real
            )
            / preco_antigo
        ) * 100


    titulo_final = (
        exata[
            "titulo_store"
        ]
        or item[
            "titulo"
        ]
    )


    classificacao = classificar(

        item[
            "marca"
        ],

        item[
            "serie"
        ],

        preco_real,

        desconto,

        titulo_final
    )


    if classificacao is None:

        preco_fora += 1

        continue


    (
        ranking,
        ordem,
        motivo,
        score,
        modelo_top
    ) = classificacao


    ofertas_brutas.append({

        "id":
            item["id"],

        "titulo":
            titulo_final,

        "marca":
            item["marca"],

        "serie":
            item["serie"],

        "loja":
            item["loja"],

        "preco":
            preco_real,

        "preco_antigo":
            preco_antigo,

        "desconto":
            desconto,

        "link":
            exata["link"],

        "ranking":
            ranking,

        "ranking_ordem":
            ordem,

        "motivo":
            motivo,

        "score":
            score,

        "modelo_top":
            modelo_top,

        "tipo_alerta":
            item["tipo_alerta"],

        "preco_anterior_encontrado":
            item.get(
                "preco_anterior_encontrado"
            )
    })


# =========================================================
# DEDUPLICAÇÃO INTELIGENTE
#
# Mesmo modelo + mesma série:
# mantém o anúncio MAIS BARATO.
# =========================================================

melhores = {}


for item in ofertas_brutas:

    modelo = (
        item[
            "modelo_top"
        ]
        or normalizar(
            item["titulo"]
        )
    )


    chave = (
        normalizar(
            str(
                item[
                    "serie"
                ]
            )
        ),
        normalizar(
            modelo
        )
    )


    atual = melhores.get(
        chave
    )


    if (
        atual is None
        or item[
            "preco"
        ] < atual[
            "preco"
        ]
    ):

        melhores[
            chave
        ] = item


ofertas = list(
    melhores.values()
)


duplicados_removidos = (
    len(
        ofertas_brutas
    )
    - len(
        ofertas
    )
)


# =========================================================
# ORDENAR
#
# Primeiro ranking,
# depois maior score,
# depois menor preço.
# =========================================================

ofertas.sort(

    key=lambda x: (

        x[
            "ranking_ordem"
        ],

        -x[
            "score"
        ],

        x[
            "preco"
        ]
    )
)


# =========================================================
# LINKS
# =========================================================

with open(
    ARQUIVO_ML,
    "w",
    encoding="utf-8"
) as arquivo:

    for item in ofertas:

        if (
            item[
                "loja"
            ]
            == "Mercado Livre"
        ):

            arquivo.write(
                item[
                    "link"
                ]
                + "\n"
            )


with open(
    ARQUIVO_AMAZON,
    "w",
    encoding="utf-8"
) as arquivo:

    for item in ofertas:

        if (
            item[
                "loja"
            ]
            == "Amazon"
        ):

            arquivo.write(
                item[
                    "link"
                ]
                + "\n"
            )


# =========================================================
# EMAIL
# =========================================================

if ofertas:

    corpo = []

    corpo.append(
        "🚗 BUSCADOR DIECAST"
    )

    corpo.append(
        f"Data: {HOJE}"
    )

    corpo.append("")

    corpo.append(
        "✅ Produto conferido"
    )

    corpo.append(
        "✅ Preço total conferido"
    )

    corpo.append(
        "✅ Link direto conferido"
    )

    corpo.append(
        "✅ Modelos quentes priorizados"
    )

    corpo.append(
        "✅ Duplicatas filtradas"
    )

    corpo.append("")


    for numero, item in enumerate(
        ofertas,
        start=1
    ):

        corpo.append(
            "=" * 65
        )


        corpo.append(
            f"{numero}. "
            f"{item['ranking']}"
        )


        corpo.append(
            f"⭐ SCORE: "
            f"{item['score']}"
        )


        corpo.append(
            f"🛍️ Loja: "
            f"{item['loja']}"
        )


        corpo.append(
            f"🏷️ Marca: "
            f"{item['marca']}"
        )


        if item[
            "serie"
        ]:

            corpo.append(
                f"🏁 Série: "
                f"{item['serie']}"
            )


        if item[
            "modelo_top"
        ]:

            corpo.append(
                f"📈 MODELO QUENTE: "
                f"{item['modelo_top'].upper()}"
            )


        corpo.append(
            f"Produto: "
            f"{item['titulo']}"
        )


        if (
            item[
                "preco_antigo"
            ]
            is not None
        ):

            corpo.append(
                f"❌ De: "
                f"R$ "
                f"{item['preco_antigo']:.2f}"
            )


        corpo.append(
            f"💰 PREÇO REAL: "
            f"R$ "
            f"{item['preco']:.2f}"
        )


        if (
            item[
                "desconto"
            ]
            is not None
        ):

            corpo.append(
                f"🔥 Desconto: "
                f"{item['desconto']:.0f}%"
            )


        corpo.append(
            f"🔎 Motivo: "
            f"{item['motivo']}"
        )


        corpo.append("")

        corpo.append(
            "🔗 LINK DIRETO:"
        )

        corpo.append(
            item[
                "link"
            ]
        )


        corpo.append("")

        corpo.append(
            "📲 TEXTO PARA WHATSAPP"
        )

        corpo.append("")

        corpo.append(
            item[
                "ranking"
            ]
        )


        if item[
            "modelo_top"
        ]:

            corpo.append(
                "📈 MODELO QUENTE"
            )


        corpo.append(
            f"🏎️ "
            f"*{item['titulo']}*"
        )


        if (
            item[
                "preco_antigo"
            ]
            is not None
        ):

            corpo.append(
                f"❌ De R$ "
                f"{item['preco_antigo']:.2f}"
            )


        corpo.append(
            f"💰 *Por R$ "
            f"{item['preco']:.2f}*"
        )


        if (
            item[
                "desconto"
            ]
            is not None
        ):

            corpo.append(
                f"🔥 "
                f"{item['desconto']:.0f}% OFF"
            )


        corpo.append("")

        corpo.append(
            "🛒 Comprar:"
        )

        corpo.append(
            item[
                "link"
            ]
        )

        corpo.append("")

        corpo.append(
            "⚠️ Preço pode mudar "
            "a qualquer momento."
        )

        corpo.append("")


    email_ok = enviar_email(

        f"🚨 "
        f"{len(ofertas)} "
        "oferta(s) Diecast",

        "\n".join(
            corpo
        )
    )


else:

    corpo = f"""
🔎 BUSCADOR DIECAST

Data: {HOJE}

Busca concluída.

Nenhuma nova oferta totalmente confirmada.

LINHAS MONITORADAS:

✅ Hot Wheels Premium
✅ Car Culture
✅ Boulevard
✅ Pop Culture
✅ Premium Entertainment
✅ Team Transport
✅ Fast & Furious Premium
✅ Modern Classics
✅ Japan Historics
✅ Race Day
✅ Circuit Legends
✅ Vintage Racing
✅ Elite 64
✅ RLC
✅ Silver Series

OUTRAS MARCAS:

✅ Mini GT
✅ Kaido House
✅ Tarmac Works
✅ Pop Race
✅ Inno64
✅ Matchbox Collectors
✅ Majorette Premium
✅ Tomica Premium

FAIXAS:

Hot Wheels Premium:
até R$99

Mini GT:
abaixo de R$150

Kaido House:
abaixo de R$199

RESUMO:

Shopping analisados:
{total_shopping}

Candidatos:
{len(candidatos)}

Candidatos desta rodada:
{len(para_resolver)}

Sem confirmação completa:
{sem_confirmacao}

Preço fora dos filtros:
{preco_fora}

Duplicados removidos:
{duplicados_removidos}

Preço parcelado/inválido:
{rejeitados_parcela}

Internacional/usado:
{rejeitados_internacional}

Escala errada:
{rejeitados_escala}

Hot Wheels básico:
{rejeitados_basico}
"""


    email_ok = enviar_email(

        "🔎 Diecast - Nenhuma nova oferta",

        corpo
    )


# =========================================================
# HISTÓRICO
# =========================================================

if (
    ofertas
    and email_ok
):

    for item in ofertas:

        chave = item[
            "id"
        ]

        preco = item[
            "preco"
        ]


        anterior = historico.get(
            chave,
            {}
        )


        menor_historico = (
            anterior.get(
                "menor_preco_historico",
                preco
            )
        )


        historico[
            chave
        ] = {

            "titulo":
                item[
                    "titulo"
                ],

            "marca":
                item[
                    "marca"
                ],

            "serie":
                item[
                    "serie"
                ],

            "loja":
                item[
                    "loja"
                ],

            "link":
                item[
                    "link"
                ],

            "score":
                item[
                    "score"
                ],

            "ultima_data_enviada":
                HOJE,

            "menor_preco_dia":
                preco,

            "menor_preco_historico":
                min(
                    menor_historico,
                    preco
                )
        }


    salvar_historico(
        historico
    )


# =========================================================
# LOG FINAL
# =========================================================

print()
print("=" * 80)

print(
    "OFERTAS CONFIRMADAS:",
    len(ofertas)
)

print("=" * 80)


for item in ofertas:

    print(
        item[
            "ranking"
        ]
    )


    print(
        "SCORE:",
        item[
            "score"
        ]
    )


    print(
        "LOJA:",
        item[
            "loja"
        ]
    )


    print(
        "MARCA:",
        item[
            "marca"
        ]
    )


    if item[
        "serie"
    ]:

        print(
            "SÉRIE:",
            item[
                "serie"
            ]
        )


    if item[
        "modelo_top"
    ]:

        print(
            "MODELO QUENTE:",
            item[
                "modelo_top"
            ]
        )


    print(
        "TÍTULO:",
        item[
            "titulo"
        ]
    )


    print(
        f"PREÇO REAL: "
        f"R$ "
        f"{item['preco']:.2f}"
    )


    print(
        "PARCELA: IGNORADA"
    )


    if (
        item[
            "desconto"
        ]
        is not None
    ):

        print(
            f"DESCONTO: "
            f"{item['desconto']:.1f}%"
        )


    print(
        "MOTIVO:",
        item[
            "motivo"
        ]
    )


    print(
        "LINK DIRETO:",
        item[
            "link"
        ]
    )


    print(
        "-" * 80
    )


print()

print(
    "SHOPPING ANALISADOS:",
    total_shopping
)

print(
    "CANDIDATOS:",
    len(candidatos)
)

print(
    "SEM CONFIRMAÇÃO:",
    sem_confirmacao
)

print(
    "DUPLICADOS REMOVIDOS:",
    duplicados_removidos
)

print(
    "PREÇO FORA DOS FILTROS:",
    preco_fora
)


if email_ok:

    print(
        "📧 E-MAIL ENVIADO."
    )

else:

    print(
        "❌ E-MAIL FALHOU."
    )
