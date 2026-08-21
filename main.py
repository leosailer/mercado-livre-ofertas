import os
import re
import json
import ssl
import smtplib

from datetime import datetime
from zoneinfo import ZoneInfo
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import urlparse, parse_qs

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


# =========================================================
# SÉRIES HOT WHEELS QUE QUEREMOS
# =========================================================

SERIES_HOT_WHEELS = [

    # Premium
    "car culture",
    "boulevard",
    "pop culture",
    "team transport",

    # Fast & Furious premium
    "premium fast & furious",
    "fast & furious premium",
    "premium fast and furious",
    "fast and furious premium",

    # Collector
    "elite 64",
    "rlc",
    "red line club",

    # Silver
    "silver series",

    # Subséries / mixes conhecidos
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

    # Outros sinais
    "hot wheels premium",
    "real riders",
    "metal/metal",
    "metal metal"
]


# =========================================================
# CARROS TOP
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
    "Mercedes",
    "Audi",
    "Nissan Skyline",
    "Nissan GT-R",
    "Toyota Supra",
    "Mazda RX-7",
    "Honda NSX",
    "Honda Civic",
    "Mitsubishi Lancer",
    "Subaru Impreza",
    "Ford Mustang",
    "Corvette"
]


# =========================================================
# BUSCAS
# =========================================================

BUSCAS = [

    '"Hot Wheels Car Culture"',

    '"Hot Wheels Modern Classics"',

    '"Hot Wheels Japan Historics"',

    '"Hot Wheels Boulevard"',

    '"Hot Wheels Silver Series"',

    '"Hot Wheels Pop Culture" OR "Hot Wheels Fast Furious Premium"',

    '"Hot Wheels" Ferrari Porsche Lamborghini Skyline Supra RX-7 premium',

    '"Mini GT" Porsche Lamborghini McLaren Skyline GT-R Supra RX-7 BMW',

    '"Kaido House" Skyline Nissan Honda Datsun',

    '"Tarmac Works" OR "Pop Race" OR "Inno64" Porsche Ferrari Skyline RX-7'
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


# =========================================================
# ESCALAS QUE NÃO QUEREMOS
# =========================================================

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
#
# Isso NÃO define oferta.
# Serve apenas para eliminar valores absurdos.
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
# TEXTO
# =========================================================

def normalizar(texto):

    return re.sub(
        r"\s+",
        " ",
        (texto or "").lower()
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


    if (
        "amazon" in texto
    ):

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

        if serie in texto:

            return serie.title()


    return None


# =========================================================
# HOT WHEELS VÁLIDO
# =========================================================

def hot_wheels_valido(
    titulo,
    snippet=""
):

    texto = normalizar(
        f"{titulo} {snippet}"
    )


    if "hot wheels" not in texto:

        return True


    return (
        identificar_serie(
            titulo,
            snippet
        )
        is not None
    )


# =========================================================
# CARROS TOP
# =========================================================

def identificar_carros_top(
    titulo
):

    texto = normalizar(titulo)

    encontrados = []


    for carro in CARROS_TOP:

        if normalizar(carro) in texto:

            encontrados.append(
                carro
            )


    return encontrados


# =========================================================
# ESCALA
# =========================================================

def escala_valida(
    titulo,
    snippet=""
):

    texto = normalizar(
        f"{titulo} {snippet}"
    )


    for escala in ESCALAS_PROIBIDAS:

        if escala in texto:

            return False


    escalas = re.findall(
        r"\b1\s*[:/]\s*(\d{2})\b",
        texto
    )


    for escala in escalas:

        if escala != "64":

            return False


    return True


# =========================================================
# FILTRO NOVO / INTERNACIONAL
# =========================================================

def texto_produto_valido(texto):

    texto = normalizar(texto)


    for termo in TERMOS_PROIBIDOS:

        if termo in texto:

            return False


    for termo in TERMOS_INTERNACIONAIS:

        if termo in texto:

            return False


    return True


# =========================================================
# PREÇO SHOPPING
#
# IMPORTANTE:
#
# extracted_price pode, em alguns resultados,
# ser exatamente o preço da parcela.
#
# Então verificamos installment.
# =========================================================

def obter_preco_shopping(
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


    # -----------------------------------------------------
    # MOEDA
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # DETECTA SE extracted_price É PARCELA
    # -----------------------------------------------------

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


                # Se preço principal == parcela,
                # não é preço total confiável.
                if abs(
                    preco - parcela
                ) < 0.02:

                    return None


            except:

                pass


    # -----------------------------------------------------
    # TEXTO DE PARCELA
    # -----------------------------------------------------

    texto_lower = normalizar(
        item.get(
            "price",
            ""
        )
    )


    if (
        "/mês" in texto_lower
        or "/mes" in texto_lower
        or "/mo" in texto_lower
        or "por mês" in texto_lower
    ):

        return None


    # -----------------------------------------------------
    # FAIXA PLAUSÍVEL
    # -----------------------------------------------------

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
# DESCONTO PRELIMINAR
# =========================================================

def desconto_shopping(
    item,
    preco
):

    antigo = item.get(
        "extracted_old_price"
    )


    if antigo is None:

        return None


    try:

        antigo = float(
            antigo
        )

    except:

        return None


    if (
        antigo <= preco
        or antigo > preco * 3
    ):

        return None


    desconto = (
        (
            antigo
            - preco
        )
        / antigo
    ) * 100


    if (
        desconto < 1
        or desconto > 80
    ):

        return None


    return desconto


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


        # TEAM TRANSPORT
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


        # RLC / ELITE
        elif (
            "rlc" in serie_normal
            or "red line club" in serie_normal
            or "elite 64" in serie_normal
        ):

            if (
                desconto is not None
                and desconto >= 20
            ):

                return (
                    "🔥 BOA OFERTA",
                    1,
                    "HOT WHEELS COLLECTOR COM DESCONTO"
                )


        # PREMIUM / SILVER
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
# PEGAR PAGE TOKEN DO PRODUTO
# =========================================================

def obter_page_token(
    item
):

    token = item.get(
        "immersive_product_page_token"
    )


    if token:

        return token


    url_api = item.get(
        "serpapi_immersive_product_api"
    )


    if not url_api:

        return None


    try:

        parsed = urlparse(
            url_api
        )

        parametros = parse_qs(
            parsed.query
        )

        valores = parametros.get(
            "page_token"
        )


        if valores:

            return valores[0]


    except:

        pass


    return None


# =========================================================
# LINK DIRETO EXATO
#
# Essa é a parte mais importante.
#
# Faz consulta ao produto imersivo
# APENAS para oferta que seria enviada.
# =========================================================

def resolver_oferta_exata(
    item,
    loja_desejada,
    preco_alvo
):

    page_token = obter_page_token(
        item
    )


    if not page_token:

        return None


    parametros = {

        "engine":
            "google_immersive_product",

        "page_token":
            page_token,

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
            "ERRO AO RESOLVER LINK:",
            erro
        )

        return None


    if resposta.status_code != 200:

        print(
            "ERRO LINK DIRETO HTTP:",
            resposta.status_code
        )

        return None


    dados = resposta.json()


    product_results = dados.get(
        "product_results",
        {}
    )


    stores = product_results.get(
        "stores",
        []
    )


    # Algumas estruturas podem trazer stores
    # diretamente no JSON.
    if not stores:

        stores = dados.get(
            "stores",
            []
        )


    candidatos = []


    for store in stores:

        nome = normalizar(
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
        # CONFIRMA LOJA
        # =================================================

        if loja_desejada == "Mercado Livre":

            if not (
                "mercado livre" in nome
                or "mercadolivre.com.br"
                in link_lower
            ):

                continue


            if (
                "mercadolivre.com.br"
                not in link_lower
            ):

                continue


        elif loja_desejada == "Amazon":

            if not (
                "amazon" in nome
                or "amazon.com.br"
                in link_lower
            ):

                continue


            if (
                "amazon.com.br"
                not in link_lower
            ):

                continue


        else:

            continue


        # =================================================
        # BLOQUEIA INTERNACIONAL
        # =================================================

        detalhes = store.get(
            "details_and_offers",
            []
        )


        if isinstance(
            detalhes,
            list
        ):

            detalhes_texto = " ".join(
                str(x)
                for x in detalhes
            )

        else:

            detalhes_texto = str(
                detalhes
            )


        texto_validacao = " ".join([
            nome,
            store.get(
                "title",
                ""
            ),
            detalhes_texto,
            str(
                store.get(
                    "shipping",
                    ""
                )
            )
        ])


        if not texto_produto_valido(
            texto_validacao
        ):

            continue


        # =================================================
        # PREÇO REAL DA OFERTA DA LOJA
        # =================================================

        preco_store = store.get(
            "extracted_price"
        )


        if preco_store is None:

            continue


        try:

            preco_store = float(
                preco_store
            )

        except:

            continue


        diferenca = abs(
            preco_store
            - preco_alvo
        )


        percentual = (
            diferenca
            / preco_alvo
            if preco_alvo > 0
            else 999
        )


        candidatos.append({

            "link":
                link,

            "preco":
                preco_store,

            "diferenca":
                diferenca,

            "percentual":
                percentual,

            "preco_antigo":
                store.get(
                    "extracted_original_price"
                ),

            "nome":
                store.get(
                    "name",
                    ""
                )
        })


    if not candidatos:

        return None


    # Mais próximo do preço encontrado no Shopping.
    candidatos.sort(
        key=lambda x:
            x["diferenca"]
    )


    melhor = candidatos[0]


    # =====================================================
    # SÓ ACEITA SE O PREÇO DA LOJA FOR REALMENTE PRÓXIMO
    #
    # diferença máxima:
    # R$2 ou 2%
    # =====================================================

    if (
        melhor["diferenca"] > 2.00
        and melhor["percentual"] > 0.02
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
            "ERRO AO ENVIAR EMAIL:",
            erro
        )

        return False


# =========================================================
# ETAPA 1
# GOOGLE SHOPPING
# =========================================================

candidatos = []

ids_vistos = set()

total_shopping = 0
precos_parcelados_rejeitados = 0
internacionais_rejeitados = 0
escalas_rejeitadas = 0
basicos_rejeitados = 0


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
            "ERRO SHOPPING HTTP:",
            resposta.status_code
        )

        continue


    dados = resposta.json()


    shopping_results = dados.get(
        "shopping_results",
        []
    )


    print(
        "RESULTADOS SHOPPING:",
        len(shopping_results)
    )


    total_shopping += len(
        shopping_results
    )


    for item in shopping_results:

        titulo = item.get(
            "title",
            ""
        )

        source = item.get(
            "source",
            ""
        )

        snippet = item.get(
            "snippet",
            ""
        )


        # =================================================
        # LOJA
        # =================================================

        loja = identificar_loja(
            source
        )


        if loja is None:

            continue


        # =================================================
        # TEXTO / INTERNACIONAL
        # =================================================

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

            internacionais_rejeitados += 1
            continue


        # =================================================
        # ESCALA
        # =================================================

        if not escala_valida(
            titulo,
            snippet
        ):

            escalas_rejeitadas += 1
            continue


        # =================================================
        # MARCA
        # =================================================

        marca = identificar_marca(
            titulo
        )


        if marca is None:

            continue


        # =================================================
        # HOT WHEELS
        # =================================================

        serie = None


        if marca == "Hot Wheels":

            serie = identificar_serie(
                titulo,
                snippet
            )


            if serie is None:

                basicos_rejeitados += 1
                continue


        # =================================================
        # PREÇO
        # =================================================

        preco = obter_preco_shopping(
            item,
            marca
        )


        if preco is None:

            precos_parcelados_rejeitados += 1
            continue


        desconto = desconto_shopping(
            item,
            preco
        )


        classificacao = classificar(
            marca,
            serie,
            preco,
            desconto
        )


        if classificacao is None:

            continue


        ranking, ordem, motivo = (
            classificacao
        )


        product_id = str(
            item.get(
                "product_id",
                ""
            )
        )


        if not product_id:

            # Sem product ID não conseguimos
            # resolver anúncio exato.
            continue


        chave = (
            f"{loja}|"
            f"{product_id}"
        )


        if chave in ids_vistos:

            continue


        ids_vistos.add(
            chave
        )


        candidatos.append({

            "id":
                chave,

            "product_id":
                product_id,

            "titulo":
                titulo,

            "loja":
                loja,

            "marca":
                marca,

            "serie":
                serie,

            "preco_shopping":
                preco,

            "desconto_shopping":
                desconto,

            "ranking":
                ranking,

            "ranking_ordem":
                ordem,

            "motivo":
                motivo,

            "carros_top":
                identificar_carros_top(
                    titulo
                ),

            "shopping_item":
                item
        })


# =========================================================
# ETAPA 2
# FILTRO DE HISTÓRICO ANTES DE GASTAR API EXTRA
# =========================================================

historico = carregar_historico()

para_resolver = []


for item in candidatos:

    registro = historico.get(
        item["id"]
    )


    # NUNCA MANDOU
    if registro is None:

        item["tipo_alerta"] = (
            "NOVA_OFERTA"
        )

        para_resolver.append(
            item
        )

        continue


    # NOVO DIA
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


    # MESMO DIA:
    # só interessa resolver novamente
    # se o preço do Shopping aparentemente caiu.
    menor_dia = registro.get(
        "menor_preco_dia"
    )


    if (
        menor_dia is None
        or item[
            "preco_shopping"
        ] < menor_dia
    ):

        item[
            "tipo_alerta"
        ] = "QUEDA_PRECO"

        item[
            "preco_anterior_encontrado"
        ] = menor_dia

        para_resolver.append(
            item
        )


# =========================================================
# ETAPA 3
# RESOLVER O LINK DIRETO DO ANÚNCIO EXATO
# =========================================================

ofertas_finais = []

sem_link_direto = 0
preco_divergente = 0


for numero, item in enumerate(
    para_resolver,
    start=1
):

    print()

    print(
        f"RESOLVENDO LINK "
        f"{numero}/"
        f"{len(para_resolver)}"
    )

    print(
        item["titulo"]
    )


    oferta_store = resolver_oferta_exata(

        item["shopping_item"],

        item["loja"],

        item["preco_shopping"]
    )


    if oferta_store is None:

        sem_link_direto += 1

        print(
            "DESCARTADO:"
            " não achei anúncio direto "
            "com o mesmo preço."
        )

        continue


    preco_real = oferta_store[
        "preco"
    ]


    # =====================================================
    # RECLASSIFICA COM O PREÇO DA LOJA
    # =====================================================

    preco_antigo = oferta_store.get(
        "preco_antigo"
    )

    desconto_real = None


    if preco_antigo is not None:

        try:

            preco_antigo = float(
                preco_antigo
            )


            if (
                preco_antigo
                > preco_real
            ):

                desconto_real = (
                    (
                        preco_antigo
                        - preco_real
                    )
                    / preco_antigo
                ) * 100


        except:

            preco_antigo = None


    classificacao = classificar(

        item["marca"],

        item["serie"],

        preco_real,

        desconto_real
    )


    # Depois de pegar o preço REAL
    # pode deixar de ser oferta.
    if classificacao is None:

        preco_divergente += 1

        print(
            "DESCARTADO:"
            " preço real não atende "
            "aos filtros."
        )

        continue


    ranking, ordem, motivo = (
        classificacao
    )


    item_final = {

        "id":
            item["id"],

        "titulo":
            item["titulo"],

        "loja":
            item["loja"],

        "marca":
            item["marca"],

        "serie":
            item["serie"],

        "preco":
            preco_real,

        "preco_antigo":
            preco_antigo,

        "desconto":
            desconto_real,

        "link":
            oferta_store["link"],

        "ranking":
            ranking,

        "ranking_ordem":
            ordem,

        "motivo":
            motivo,

        "carros_top":
            item["carros_top"],

        "tipo_alerta":
            item["tipo_alerta"],

        "preco_anterior_encontrado":
            item.get(
                "preco_anterior_encontrado"
            )
    }


    ofertas_finais.append(
        item_final
    )


# =========================================================
# ORDENAR
# =========================================================

ofertas_finais.sort(

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

    for item in ofertas_finais:

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

    for item in ofertas_finais:

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

if ofertas_finais:

    corpo = []

    corpo.append(
        "🚗 BUSCADOR DIECAST"
    )

    corpo.append(
        f"Data: {HOJE}"
    )

    corpo.append("")

    corpo.append(
        "✅ PREÇO CONFIRMADO NA LOJA"
    )

    corpo.append(
        "✅ LINK DIRETO DO ANÚNCIO"
    )

    corpo.append(
        "✅ PARCELAMENTO IGNORADO"
    )

    corpo.append("")


    for numero, item in enumerate(
        ofertas_finais,
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


        if item["carros_top"]:

            corpo.append(
                "🏎️ Carro top: "
                + ", ".join(
                    item["carros_top"]
                )
            )


        corpo.append(
            f"Produto: "
            f"{item['titulo']}"
        )

        corpo.append("")


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
                f"R$ "
                f"{item['preco_antigo']:.2f}"
            )


        corpo.append(
            f"💰 PREÇO REAL: "
            f"R$ {item['preco']:.2f}"
        )


        if (
            item["desconto"]
            is not None
        ):

            corpo.append(
                f"🔥 DESCONTO: "
                f"{item['desconto']:.0f}%"
            )


        corpo.append(
            f"🔎 Motivo: "
            f"{item['motivo']}"
        )

        corpo.append("")

        corpo.append(
            "🔗 ANÚNCIO DIRETO:"
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


        if item["serie"]:

            corpo.append(
                f"🏁 {item['serie']}"
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


        if (
            item["desconto"]
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
            item["link"]
        )

        corpo.append("")

        corpo.append(
            "⚠️ Preço pode mudar "
            "a qualquer momento."
        )

        corpo.append("")


    email_ok = enviar_email(

        f"🚨 {len(ofertas_finais)} "
        "oferta(s) Diecast",

        "\n".join(
            corpo
        )
    )


else:

    corpo = f"""
🔎 BUSCADOR DIECAST

Data: {HOJE}

Busca concluída normalmente.

Nenhuma NOVA oferta com PREÇO E LINK DIRETO confirmados foi encontrada.

✅ Google Shopping usado para descoberta
✅ Preço da parcela não é aceito
✅ Oferta conferida na loja antes do envio
✅ Link direto obrigatório
✅ Nenhum link de pesquisa é enviado
✅ Mercado Livre monitorado
✅ Amazon Brasil monitorada
✅ Hot Wheels básicos bloqueados
✅ Escala errada bloqueada
✅ Internacional bloqueado quando identificado

RESUMO:

Resultados Shopping analisados:
{total_shopping}

Candidatos que passaram nos filtros:
{len(candidatos)}

Candidatos novos/queda para conferir:
{len(para_resolver)}

Descartados por não achar link direto exato:
{sem_link_direto}

Descartados porque o preço real não atendia:
{preco_divergente}

Preço parcelado/inválido rejeitado:
{precos_parcelados_rejeitados}

Internacional/usado rejeitado:
{internacionais_rejeitados}

Escala errada rejeitada:
{escalas_rejeitadas}

Hot Wheels básico rejeitado:
{basicos_rejeitados}
"""


    email_ok = enviar_email(

        "🔎 Diecast - Nenhuma nova oferta",

        corpo
    )


# =========================================================
# HISTÓRICO
# =========================================================

if (
    ofertas_finais
    and email_ok
):

    for item in ofertas_finais:

        chave = item["id"]

        preco = item["preco"]

        registro_antigo = (
            historico.get(
                chave,
                {}
            )
        )


        menor_historico = (
            registro_antigo.get(
                "menor_preco_historico",
                preco
            )
        )


        historico[chave] = {

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
    "OFERTAS CONFIRMADAS E ENVIADAS:",
    len(ofertas_finais)
)

print("=" * 80)


for item in ofertas_finais:

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
        "PARCELAMENTO: IGNORADO"
    )


    if (
        item["desconto"]
        is not None
    ):

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
    "SEM LINK DIRETO:",
    sem_link_direto
)

print(
    "PREÇO REAL FORA DOS FILTROS:",
    preco_divergente
)

print(
    "PREÇO PARCELADO/INVÁLIDO:",
    precos_parcelados_rejeitados
)


if email_ok:

    print(
        "📧 E-MAIL ENVIADO COM SUCESSO."
    )

else:

    print(
        "❌ E-MAIL NÃO FOI ENVIADO."
    )
