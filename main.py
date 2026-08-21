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

VERSAO_HISTORICO = "v4"


# =========================================================
# HOT WHEELS - SÉRIES DE INTERESSE
# =========================================================

SERIES_HOT_WHEELS = [
    "premium",
    "car culture",
    "boulevard",
    "pop culture",
    "team transport",
    "fast & furious",
    "fast and furious",
    "silver series",
    "elite 64",
    "rlc",
    "red line club",

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

    "real riders",
    "metal/metal",
    "metal metal"
]


# =========================================================
# CARROS / TERMOS FORTES
#
# Se um destes aparece no produto original,
# precisa aparecer também no anúncio resolvido.
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
    "993",
    "gt3",
    "gt2",
    "carrera",

    "lamborghini",
    "countach",
    "huracan",

    "mclaren",

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

    "koenigsegg",

    "spiderman",
    "spider man",

    "ground fx"
]


# =========================================================
# BUSCAS
# =========================================================

BUSCAS = [
    '"Hot Wheels Car Culture"',

    '"Hot Wheels Silver Series"',

    '"Hot Wheels Boulevard" "Hot Wheels Pop Culture"',

    '"Hot Wheels Team Transport" "Hot Wheels Fast Furious"',

    '"Hot Wheels Premium" Ferrari Porsche Lamborghini Skyline Supra RX-7',

    '"Mini GT" "Kaido House" "Tarmac Works" "Pop Race" "Inno64"'
]


# =========================================================
# TERMOS PROIBIDOS
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


# =========================================================
# FAIXAS PLAUSÍVEIS
# =========================================================

FAIXAS_VALIDAS = {
    "Hot Wheels": (35, 800),
    "Mini GT": (65, 500),
    "Kaido House": (100, 700),
    "Tarmac Works": (75, 700),
    "Pop Race": (75, 700),
    "Inno64": (75, 700),
    "Matchbox": (25, 500),
    "Majorette": (30, 400),
    "Greenlight": (45, 500),
    "M2 Machines": (50, 600),
    "Tomica": (35, 400)
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

    texto = normalizar(source)

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

    texto = normalizar(titulo)

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
# SÉRIE HOT WHEELS
# =========================================================

def identificar_serie(
    titulo,
    snippet=""
):

    texto = normalizar(
        f"{titulo} {snippet}"
    )

    for serie in SERIES_HOT_WHEELS:

        if normalizar(serie) in texto:
            return serie.title()

    return None


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

def texto_produto_valido(texto):

    texto = normalizar(texto)

    for termo in TERMOS_PROIBIDOS:

        if normalizar(termo) in texto:
            return False

    for termo in TERMOS_INTERNACIONAIS:

        if normalizar(termo) in texto:
            return False

    return True


# =========================================================
# TERMOS IMPORTANTES DO PRODUTO
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
            and palavra not in PALAVRAS_GENERICAS
        )
    }


def termos_fortes_presentes(texto):

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


# =========================================================
# VALIDAÇÃO DE IDENTIDADE
#
# Impede:
# Mustang -> Ferrari
# Datsun -> BMW
# etc.
# =========================================================

def produto_corresponde(
    titulo_original,
    titulo_store,
    link_store,
    serie_original=None
):

    resolvido = normalizar(
        f"{titulo_store} {link_store}"
    )

    original = normalizar(
        titulo_original
    )


    # =====================================================
    # 1 - TERMOS FORTES
    # =====================================================

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

        intersecao_fortes = (
            fortes_original
            .intersection(
                fortes_resolvido
            )
        )


        # Se original contém carro/modelo forte,
        # pelo menos UM precisa aparecer no resolvido.
        if not intersecao_fortes:

            return False


    # =====================================================
    # 2 - TOKENS ESPECÍFICOS
    # =====================================================

    tokens_original = tokens_produto(
        original
    )

    tokens_resolvido = tokens_produto(
        resolvido
    )


    if tokens_original:

        comuns = (
            tokens_original
            .intersection(
                tokens_resolvido
            )
        )


        # Título muito específico:
        # exige alguma coincidência.
        if (
            len(tokens_original) >= 2
            and len(comuns) == 0
        ):

            return False


    # =====================================================
    # 3 - SÉRIE
    #
    # Se conseguimos identificar a série também
    # no anúncio resolvido, ela não pode ser outra
    # completamente diferente.
    # =====================================================

    if serie_original:

        serie_resolvida = identificar_serie(
            titulo_store,
            link_store
        )


        if (
            serie_resolvida
            and normalizar(
                serie_resolvida
            )
            != normalizar(
                serie_original
            )
        ):

            # Premium é genérico e pode resolver
            # como Car Culture/Boulevard etc.
            if (
                normalizar(
                    serie_original
                )
                != "premium"
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

        preco = float(preco)

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
            "R$" not in preco_texto
            and "BRL" not in preco_texto
        ):

            return None


    if marca not in FAIXAS_VALIDAS:
        return None


    minimo, maximo = (
        FAIXAS_VALIDAS[marca]
    )


    if not (
        minimo
        <= preco
        <= maximo
    ):

        return None


    return preco


# =========================================================
# CLASSIFICAÇÃO
# =========================================================

def classificar(
    marca,
    serie,
    preco,
    desconto
):

    serie_normal = normalizar(
        serie or ""
    )


    # =====================================================
    # HOT WHEELS
    # =====================================================

    if marca == "Hot Wheels":

        if (
            "team transport"
            in serie_normal
        ):

            if preco <= 119:

                return (
                    "🚨 IMPERDÍVEL",
                    0,
                    "TEAM TRANSPORT ATÉ R$119"
                )

            if preco <= 149:

                return (
                    "🔥 BOA OFERTA",
                    1,
                    "TEAM TRANSPORT ATÉ R$149"
                )


        elif (
            "rlc" in serie_normal
            or "red line club"
            in serie_normal
            or "elite 64"
            in serie_normal
        ):

            if (
                desconto is not None
                and desconto >= 20
            ):

                return (
                    "🔥 BOA OFERTA",
                    1,
                    "COLLECTOR COM DESCONTO"
                )


        else:

            if preco <= 59.99:

                return (
                    "🚨 IMPERDÍVEL",
                    0,
                    "HOT WHEELS PREMIUM/SILVER ATÉ R$59,99"
                )

            if preco <= 69:

                return (
                    "🚨 IMPERDÍVEL",
                    0,
                    "HOT WHEELS PREMIUM/SILVER ABAIXO DE R$69"
                )

            if preco <= 89:

                return (
                    "🔥 BOA OFERTA",
                    1,
                    "HOT WHEELS PREMIUM/SILVER ATÉ R$89"
                )

            if preco <= 99:

                return (
                    "👀 INTERESSANTE",
                    2,
                    "HOT WHEELS PREMIUM/SILVER ATÉ R$99"
                )


    # =====================================================
    # MINI GT
    # =====================================================

    if marca == "Mini GT":

        if preco < 110:

            return (
                "🚨 IMPERDÍVEL",
                0,
                "MINI GT ABAIXO DE R$110"
            )

        if preco < 130:

            return (
                "🔥 BOA OFERTA",
                1,
                "MINI GT ABAIXO DE R$130"
            )

        if preco < 150:

            return (
                "👀 INTERESSANTE",
                2,
                "MINI GT ABAIXO DE R$150"
            )


    # =====================================================
    # OUTRAS MARCAS
    # =====================================================

    if (
        desconto is not None
        and desconto >= 30
    ):

        return (
            "🚨 IMPERDÍVEL",
            0,
            "DESCONTO REAL DE 30% OU MAIS"
        )


    if (
        desconto is not None
        and desconto >= 20
    ):

        return (
            "🔥 BOA OFERTA",
            1,
            "DESCONTO REAL DE 20% OU MAIS"
        )


    if (
        desconto is not None
        and desconto >= 15
    ):

        return (
            "👀 INTERESSANTE",
            2,
            "DESCONTO REAL DE 15% OU MAIS"
        )


    return None


# =========================================================
# PAGE TOKEN
# =========================================================

def obter_page_token(item):

    return item.get(
        "immersive_product_page_token"
    )


# =========================================================
# PREÇO REAL DO STORE
# =========================================================

def preco_real_store(store):

    # Total do parcelamento tem prioridade
    total = store.get(
        "extracted_total"
    )


    if total is not None:

        try:

            total = float(total)

            if total > 0:
                return total

        except:

            pass


    # Se existe parcelamento e NÃO existe total,
    # descartamos.
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

        return float(preco)

    except:

        return None


# =========================================================
# PREÇO ANTIGO STORE
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

            valor = float(valor)

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

        nome_loja = normalizar(
            store.get(
                "name",
                ""
            )
        )

        link = store.get(
            "link",
            ""
        )


        if not link:
            continue


        link_lower = link.lower()


        # =================================================
        # LOJA CORRETA
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
        # PRODUTO PRECISA SER O MESMO
        # =================================================

        if not produto_corresponde(
            titulo_original,
            titulo_store,
            link,
            serie_original
        ):

            print(
                "REJEITADO POR PRODUTO DIFERENTE:"
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
            nome_loja,
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
        # PREÇO TOTAL REAL
        # =================================================

        preco_real = preco_real_store(
            store
        )


        if preco_real is None:
            continue


        preco_antigo = preco_antigo_store(
            store
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
                preco_antigo,

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


    # =====================================================
    # PREÇO PRECISA SER PRÓXIMO
    #
    # tolerância: R$5 ou 5%
    # =====================================================

    if (
        melhor["diferenca"] > 5
        and melhor["percentual"] > 0.05
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
# EMAIL
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

    mensagem["Subject"] = assunto
    mensagem["From"] = EMAIL_DESTINO
    mensagem["To"] = EMAIL_DESTINO

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
            "EMAIL ENVIADO COM SUCESSO."
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
        f"BUSCA {numero}/"
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


        classificacao = classificar(
            marca,
            serie,
            preco,
            None
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


        if id_produto in ids_vistos:
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

        item["tipo_alerta"] = (
            "NOVA_OFERTA"
        )

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

        item["tipo_alerta"] = (
            "OFERTA_DO_DIA"
        )

        para_resolver.append(
            item
        )

        continue


    menor = registro.get(
        "menor_preco_dia"
    )


    if (
        menor is None
        or item["preco_shopping"]
        < menor
    ):

        item["tipo_alerta"] = (
            "QUEDA_PRECO"
        )

        item[
            "preco_anterior_encontrado"
        ] = menor

        para_resolver.append(
            item
        )


# =========================================================
# ETAPA 3 - CONFIRMAR LINK + PRODUTO + PREÇO
# =========================================================

ofertas = []

links_finais_vistos = set()

sem_link = 0
produto_diferente = 0
preco_fora = 0
duplicados_finais = 0


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
        item["titulo"]
    )


    exata = resolver_link_exato(
        item["shopping_item"],
        item["loja"],
        item["preco_shopping"],
        item["titulo"],
        item["serie"]
    )


    if exata is None:

        sem_link += 1

        print(
            "DESCARTADO:"
            " não confirmou produto + "
            "preço + link."
        )

        continue


    link_final = exata["link"]


    # =====================================================
    # DUPLICADO PELO ANÚNCIO FINAL
    # =====================================================

    link_limpo = (
        link_final.split("?")[0]
    )


    if link_limpo in links_finais_vistos:

        duplicados_finais += 1

        print(
            "DESCARTADO:"
            " anúncio final duplicado."
        )

        continue


    links_finais_vistos.add(
        link_limpo
    )


    preco_real = exata[
        "preco"
    ]


    preco_antigo = exata[
        "preco_antigo"
    ]


    desconto = None


    if (
        preco_antigo is not None
        and preco_antigo > preco_real
    ):

        desconto = (
            (
                preco_antigo
                - preco_real
            )
            / preco_antigo
        ) * 100


    classificacao = classificar(
        item["marca"],
        item["serie"],
        preco_real,
        desconto
    )


    if classificacao is None:

        preco_fora += 1

        print(
            "DESCARTADO:"
            " preço confirmado não "
            "atende os filtros."
        )

        continue


    ranking, ordem, motivo = (
        classificacao
    )


    ofertas.append({
        "id":
            item["id"],

        "titulo":
            exata["titulo_store"]
            or item["titulo"],

        "titulo_shopping":
            item["titulo"],

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
            link_final,

        "ranking":
            ranking,

        "ranking_ordem":
            ordem,

        "motivo":
            motivo,

        "tipo_alerta":
            item["tipo_alerta"],

        "preco_anterior_encontrado":
            item.get(
                "preco_anterior_encontrado"
            )
    })


# =========================================================
# ORDENAR
# =========================================================

ofertas.sort(
    key=lambda x: (
        x["ranking_ordem"],
        x["preco"]
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
            item["loja"]
            == "Mercado Livre"
        ):

            arquivo.write(
                item["link"]
                + "\n"
            )


with open(
    ARQUIVO_AMAZON,
    "w",
    encoding="utf-8"
) as arquivo:

    for item in ofertas:

        if (
            item["loja"]
            == "Amazon"
        ):

            arquivo.write(
                item["link"]
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
        "✅ Parcelamento ignorado"
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
            f"🛍️ Loja: "
            f"{item['loja']}"
        )

        corpo.append(
            f"🏷️ Marca: "
            f"{item['marca']}"
        )


        if item["serie"]:

            corpo.append(
                f"🏁 Série: "
                f"{item['serie']}"
            )


        corpo.append(
            f"Produto: "
            f"{item['titulo']}"
        )


        if (
            item["tipo_alerta"]
            == "QUEDA_PRECO"
        ):

            anterior = item.get(
                "preco_anterior_encontrado"
            )

            if anterior is not None:

                corpo.append(
                    f"📉 Antes hoje: "
                    f"R$ {anterior:.2f}"
                )


        if (
            item["preco_antigo"]
            is not None
        ):

            corpo.append(
                f"❌ De: "
                f"R$ {item['preco_antigo']:.2f}"
            )


        corpo.append(
            f"💰 PREÇO REAL: "
            f"R$ {item['preco']:.2f}"
        )


        if item["desconto"] is not None:

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
            item["link"]
        )

        corpo.append("")

        corpo.append(
            "📲 TEXTO PARA WHATSAPP"
        )

        corpo.append("")

        corpo.append(
            item["ranking"]
        )

        corpo.append(
            f"🏎️ *{item['titulo']}*"
        )


        if (
            item["preco_antigo"]
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


        if item["desconto"] is not None:

            corpo.append(
                f"🔥 "
                f"{item['desconto']:.0f}% OFF"
            )


        corpo.append("")

        corpo.append(
            "🛒 Comprar:"
        )

        corpo.append(
            item["link"]
        )

        corpo.append("")

        corpo.append(
            "⚠️ Preço pode mudar."
        )

        corpo.append("")


    email_ok = enviar_email(
        f"🚨 {len(ofertas)} "
        "oferta(s) Diecast",
        "\n".join(corpo)
    )


else:

    corpo = f"""
🔎 BUSCADOR DIECAST

Data: {HOJE}

Busca concluída.

Nenhuma nova oferta totalmente confirmada.

Shopping analisados:
{total_shopping}

Candidatos:
{len(candidatos)}

Candidatos desta rodada:
{len(para_resolver)}

Sem confirmação completa:
{sem_link}

Anúncios finais duplicados:
{duplicados_finais}

Preço confirmado fora dos filtros:
{preco_fora}

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
# SALVAR HISTÓRICO
# =========================================================

if (
    ofertas
    and email_ok
):

    for item in ofertas:

        chave = item["id"]

        preco = item["preco"]

        anterior = historico.get(
            chave,
            {}
        )


        menor_historico = anterior.get(
            "menor_preco_historico",
            preco
        )


        historico[
            chave
        ] = {
            "titulo":
                item["titulo"],

            "marca":
                item["marca"],

            "serie":
                item["serie"],

            "loja":
                item["loja"],

            "link":
                item["link"],

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
        item["ranking"]
    )

    print(
        "LOJA:",
        item["loja"]
    )

    print(
        "MARCA:",
        item["marca"]
    )

    if item["serie"]:

        print(
            "SÉRIE:",
            item["serie"]
        )

    print(
        "TÍTULO:",
        item["titulo"]
    )

    print(
        f"PREÇO REAL: "
        f"R$ {item['preco']:.2f}"
    )

    print(
        "PARCELA: IGNORADA"
    )


    if item["desconto"] is not None:

        print(
            f"DESCONTO: "
            f"{item['desconto']:.1f}%"
        )


    print(
        "LINK DIRETO:",
        item["link"]
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
    sem_link
)

print(
    "DUPLICADOS FINAIS:",
    duplicados_finais
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
