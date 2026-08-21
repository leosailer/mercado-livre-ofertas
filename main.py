import os
import re
import json
import ssl
import smtplib

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

# Mudamos a lógica de preço/link.
# Isso evita que o histórico quebrado das versões anteriores
# esconda ofertas corretas nesta primeira execução.
VERSAO_HISTORICO = "v3"


# =========================================================
# HOT WHEELS - LINHAS/SÉRIES QUE QUEREMOS
# =========================================================

SERIES_HOT_WHEELS = [

    # PREMIUM
    "premium",
    "car culture",
    "boulevard",
    "pop culture",
    "team transport",

    # FAST & FURIOUS
    "fast & furious",
    "fast and furious",

    # SILVER
    "silver series",

    # COLLECTOR
    "elite 64",
    "rlc",
    "red line club",

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

    # SINAIS PREMIUM
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
#
# Reduzi para buscas mais abrangentes.
# Assim gastamos menos SerpApi por rodada.
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
#
# NÃO definem promoção.
# Só bloqueiam dado evidentemente absurdo.
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

        if serie in texto:
            return serie.title()

    return None


# =========================================================
# CARRO TOP
# =========================================================

def identificar_carros_top(titulo):

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
# INTERNACIONAL / USADO
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
# Só para descobrir candidatos.
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


    # =====================================================
    # NÃO ACEITA extracted_price SE FOR A PARCELA
    # =====================================================

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


    # =====================================================
    # MOEDA
    # =====================================================

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

        # TEAM TRANSPORT
        if "team transport" in serie_normal:

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
                    "COLLECTOR COM DESCONTO"
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
# PAGE TOKEN
# =========================================================

def obter_page_token(item):

    return item.get(
        "immersive_product_page_token"
    )


# =========================================================
# PREÇO REAL DA LOJA
#
# CORREÇÃO PRINCIPAL:
#
# Se houver extracted_total,
# usamos ele.
#
# extracted_price pode ser só parcela.
# =========================================================

def preco_real_store(store):

    # =====================================================
    # 1 - TOTAL DO PARCELAMENTO
    # =====================================================

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


    # =====================================================
    # 2 - PREÇO NORMAL
    #
    # Só usamos extracted_price quando NÃO existe
    # indicação clara de parcelamento.
    # =====================================================

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

        # Tem parcelamento mas não veio total:
        # preço não é confiável.
        return None


    preco = store.get(
        "extracted_price"
    )

    if preco is None:
        return None

    try:

        preco = float(preco)

    except:

        return None

    return preco


# =========================================================
# PREÇO ANTIGO DA LOJA
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
    preco_shopping
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

        # IMPORTANTÍSSIMO
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
        # CONFIRMA MERCADO LIVRE
        # =================================================

        if loja == "Mercado Livre":

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


        # =================================================
        # CONFIRMA AMAZON
        # =================================================

        elif loja == "Amazon":

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
        # INTERNACIONAL / USADO
        # =================================================

        texto = " ".join([
            str(
                store.get(
                    "title",
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
            texto
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


        antigo = preco_antigo_store(
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

            "preco":
                preco_real,

            "preco_antigo":
                antigo,

            "diferenca":
                diferenca,

            "percentual":
                percentual,

            "store":
                store
        })


    if not candidatos:

        return None


    # Mais próximo do Shopping
    candidatos.sort(
        key=lambda x:
            x["diferenca"]
    )


    melhor = candidatos[0]


    # =====================================================
    # ACEITA PEQUENA VARIAÇÃO
    #
    # Até R$5 ou 5%.
    #
    # Isso evita jogar fora produto porque o Google
    # atualizou alguns minutos antes/depois da loja.
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
# 1 - BUSCAR NO SHOPPING
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

    print(termo)


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
        # CLASSIFICA PRELIMINARMENTE
        # =================================================

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
                item,

            "carros_top":
                identificar_carros_top(
                    titulo
                )
        })


# =========================================================
# 2 - HISTÓRICO
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
        or item[
            "preco_shopping"
        ] < menor
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
# 3 - CONFIRMAR PREÇO + LINK EXATO
# =========================================================

ofertas = []

sem_link = 0
preco_nao_bateu = 0


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

        item["preco_shopping"]
    )


    if exata is None:

        sem_link += 1

        print(
            "DESCARTADO:"
            " não foi possível confirmar "
            "preço + anúncio direto."
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

        preco_nao_bateu += 1

        print(
            "DESCARTADO:"
            " preço confirmado não é oferta."
        )

        continue


    ranking, ordem, motivo = (
        classificacao
    )


    ofertas.append({

        "id":
            item["id"],

        "titulo":
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
            exata["link"],

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

        if item["loja"] == "Amazon":

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
        "✅ PREÇO TOTAL CONFIRMADO"
    )

    corpo.append(
        "✅ LINK DIRETO CONFIRMADO"
    )

    corpo.append(
        "✅ PARCELA IGNORADA"
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
            f"🛍️ {item['loja']}"
        )

        corpo.append(
            f"🏷️ {item['marca']}"
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
            item["preco_antigo"]
            is not None
        ):

            corpo.append(
                f"❌ De R$ "
                f"{item['preco_antigo']:.2f}"
            )


        corpo.append(
            f"💰 PREÇO REAL: "
            f"R$ {item['preco']:.2f}"
        )


        if item["desconto"] is not None:

            corpo.append(
                f"🔥 DESCONTO: "
                f"{item['desconto']:.0f}%"
            )


        corpo.append(
            f"🔎 {item['motivo']}"
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

        corpo.append(
            f"💰 *R$ "
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

        "\n".join(
            corpo
        )
    )


else:

    corpo = f"""
🔎 BUSCADOR DIECAST

Data: {HOJE}

Busca concluída.

Nenhuma NOVA oferta com preço e link direto confirmados.

Shopping analisados:
{total_shopping}

Candidatos:
{len(candidatos)}

Candidatos desta rodada:
{len(para_resolver)}

Sem confirmação de link/preço:
{sem_link}

Preço confirmado fora dos critérios:
{preco_nao_bateu}

Parcelas/preços inválidos rejeitados:
{rejeitados_parcela}

Internacionais/usados rejeitados:
{rejeitados_internacional}

Escala errada:
{rejeitados_escala}

Hot Wheels básicos:
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
# LOG
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
    "LINK/PREÇO NÃO CONFIRMADO:",
    sem_link
)

print(
    "PREÇO FORA DOS CRITÉRIOS:",
    preco_nao_bateu
)


if email_ok:

    print(
        "📧 E-MAIL ENVIADO."
    )

else:

    print(
        "❌ E-MAIL FALHOU."
    )
