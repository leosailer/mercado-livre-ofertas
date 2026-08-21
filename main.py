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


# =========================================================
# HOT WHEELS - LINHAS QUE QUEREMOS
# =========================================================

SERIES_HOT_WHEELS = [
    # Premium principais
    "car culture",
    "boulevard",
    "pop culture",
    "team transport",
    "premium fast & furious",
    "fast & furious premium",
    "premium fast and furious",
    "fast and furious premium",

    # Colecionador
    "elite 64",
    "rlc",
    "red line club",

    # Silver
    "silver series",

    # Car Culture - mixes/subséries
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

    # Termos genéricos premium
    "hot wheels premium",
    "real riders",
    "metal/metal",
    "metal metal"
]


# =========================================================
# CARROS QUE AUMENTAM NOSSA COBERTURA
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
    "Corvette",
    "Lexus",
    "Lotus"
]


# =========================================================
# MODELOS QUENTES
# =========================================================

MODELOS_QUENTES = [
    "Ferrari Testarossa",
    "Ferrari F40",
    "Ferrari F50",
    "Ferrari 250 GTO",
    "Ferrari 499P",
    "Porsche 911 GT3 RS",
    "Porsche 993 GT2",
    "Porsche Carrera GT",
    "Nissan Skyline R32",
    "Nissan Skyline R33",
    "Nissan Skyline R34",
    "Toyota Supra",
    "Mazda RX-7",
    "Honda NSX",
    "Koenigsegg Agera",
    "Koenigsegg One",
    "Lamborghini Countach",
    "Lamborghini Huracan"
]


# =========================================================
# BUSCAS SHOPPING
#
# NÃO colocamos preços na consulta.
# Isso evita casar com parcelas.
# =========================================================

BUSCAS = [

    # Essa busca é MUITO importante.
    # Pegaria seu Testarossa.
    '"Hot Wheels Car Culture"',

    # Mixes Car Culture
    '"Hot Wheels Modern Classics" OR "Hot Wheels Japan Historics"',

    # Boulevard
    '"Hot Wheels Boulevard"',

    # Silver
    '"Hot Wheels Silver Series"',

    # Pop Culture / Fast & Furious
    '"Hot Wheels Pop Culture" OR "Hot Wheels Premium Fast Furious"',

    # Carros mais desejados
    '"Hot Wheels" Ferrari Porsche Lamborghini Skyline Supra RX-7 premium',

    # MINI GT
    '"Mini GT" Porsche Lamborghini McLaren Skyline GT-R Supra RX-7 BMW',

    # Outras marcas premium
    '"Kaido House" OR "Tarmac Works" OR "Pop Race" OR "Inno64"'
]


# =========================================================
# FILTROS GERAIS
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
    "display para",
    "garagem",
    "roda avulsa",
    "pneu avulso",
    "protetor blister"
]


TERMOS_INTERNACIONAIS = [
    "compra internacional",
    "envio internacional",
    "frete internacional",
    "international shipping",
    "international purchase",
    "produto internacional",
    "importado",
    "importação",
    "importacao",
    "taxa de importação",
    "taxas de importação",
    "import fees",
    "ships from china",
    "china internacional",
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
# PREÇOS PLAUSÍVEIS
#
# Apenas proteção contra dado quebrado.
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
# FUNÇÕES BÁSICAS
# =========================================================

def normalizar(texto):
    return re.sub(
        r"\s+",
        " ",
        (texto or "").lower()
    ).strip()


# =========================================================
# IDENTIFICAR LOJA
# =========================================================

def identificar_loja(source, link):

    texto = normalizar(
        f"{source} {link}"
    )

    if (
        "mercado livre" in texto
        or "mercadolivre" in texto
    ):
        return "Mercado Livre"

    if (
        "amazon.com.br" in texto
        or "amazon brasil" in texto
        or source.lower() == "amazon"
    ):
        return "Amazon"

    return None


# =========================================================
# LINK DIRETO
# =========================================================

def obter_link(item):

    possibilidades = [
        item.get("link"),
        item.get("product_link"),
        item.get("offer_link")
    ]

    for link in possibilidades:

        if not link:
            continue

        link_lower = link.lower()

        if (
            "mercadolivre.com.br" in link_lower
            or "amazon.com.br" in link_lower
        ):
            return link

    return ""


# =========================================================
# IDENTIFICAR MARCA
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
# IDENTIFICAR SÉRIE HOT WHEELS
# =========================================================

def identificar_serie_hot_wheels(
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
#
# Aqui está a mudança principal:
# não precisa conter a palavra "Premium".
# Basta pertencer a uma série aceita.
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
        identificar_serie_hot_wheels(
            titulo,
            snippet
        )
        is not None
    )


# =========================================================
# CARRO TOP
# =========================================================

def identificar_carros_top(titulo):

    texto = normalizar(titulo)

    encontrados = []

    for carro in CARROS_TOP:

        if normalizar(carro) in texto:
            encontrados.append(carro)

    return encontrados


# =========================================================
# MODELO QUENTE
# =========================================================

def identificar_modelo_quente(titulo):

    texto = normalizar(titulo)

    for modelo in MODELOS_QUENTES:

        palavras = normalizar(
            modelo
        ).split()

        if all(
            palavra in texto
            for palavra in palavras
        ):
            return modelo

    return None


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


    if escalas:

        for escala in escalas:

            if escala != "64":
                return False


    return True


# =========================================================
# NOVO / NACIONAL
# =========================================================

def produto_valido(
    titulo,
    snippet,
    extensions,
    delivery,
    condition
):

    combinado = normalizar(
        " ".join([
            titulo or "",
            snippet or "",
            delivery or "",
            condition or "",
            " ".join(
                str(x)
                for x in (extensions or [])
            )
        ])
    )


    for termo in TERMOS_PROIBIDOS:

        if termo in combinado:
            return False


    for termo in TERMOS_INTERNACIONAIS:

        if termo in combinado:
            return False


    return True


# =========================================================
# PREÇO TOTAL
#
# SOMENTE extracted_price.
# installment nunca entra aqui.
# =========================================================

def obter_preco_total(
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


    # Confirma moeda brasileira pelo texto
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


    minimo, maximo = FAIXAS_VALIDAS[
        marca
    ]


    if not (
        minimo
        <= preco
        <= maximo
    ):
        return None


    # =====================================================
    # NÃO USAMOS:
    #
    # item.get("installment")
    #
    # MESMO QUE EXISTA.
    # =====================================================

    return preco


# =========================================================
# PREÇO ANTIGO E DESCONTO
# =========================================================

def obter_desconto_real(
    item,
    preco_atual
):

    antigo = item.get(
        "extracted_old_price"
    )


    if antigo is None:
        return None, None


    try:
        antigo = float(antigo)

    except:
        return None, None


    if antigo <= preco_atual:
        return None, None


    if antigo > preco_atual * 3:
        return None, None


    desconto = (
        (
            antigo - preco_atual
        )
        / antigo
    ) * 100


    if not (
        1
        <= desconto
        <= 80
    ):
        return None, None


    return antigo, desconto


# =========================================================
# CLASSIFICAÇÃO POR TIPO
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
    # HOT WHEELS - CARRINHO INDIVIDUAL
    # =====================================================

    if marca == "Hot Wheels":

        # Team Transport tem 2 veículos,
        # então precisa de teto diferente.
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


        # RLC / Elite costumam custar mais.
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


        # Premium / Car Culture / Boulevard etc.
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


    contexto = ssl.create_default_context()


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
# BUSCAR NO GOOGLE SHOPPING
# =========================================================

resultados = []
identificadores = set()

total_encontrados = 0
rejeitados_loja = 0
rejeitados_marca = 0
rejeitados_escala = 0
rejeitados_internacional = 0
rejeitados_preco = 0
rejeitados_basicos = 0


for numero, termo in enumerate(
    BUSCAS,
    start=1
):

    print(
        f"Busca Shopping "
        f"{numero}/{len(BUSCAS)}:"
    )

    print(
        termo
    )


    parametros = {
        "engine": "google_shopping",
        "q": termo,
        "hl": "pt-br",
        "gl": "br",
        "location": "Brazil",
        "api_key": SERPAPI_KEY
    }


    try:

        resposta = requests.get(
            SERP_URL,
            params=parametros,
            timeout=30
        )


    except Exception as erro:

        print(
            "ERRO:",
            erro
        )

        continue


    if resposta.status_code != 200:

        print(
            "ERRO HTTP:",
            resposta.status_code
        )

        print(
            resposta.text[:500]
        )

        continue


    dados = resposta.json()


    shopping = dados.get(
        "shopping_results",
        []
    )


    print(
        "Resultados:",
        len(shopping)
    )


    total_encontrados += len(
        shopping
    )


    for item in shopping:

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

        extensions = item.get(
            "extensions",
            []
        )

        delivery = (
            item.get("delivery")
            or item.get("shipping")
            or ""
        )

        condition = (
            item.get("second_hand_condition")
            or ""
        )


        link = obter_link(
            item
        )


        # =================================================
        # LOJA
        # =================================================

        loja = identificar_loja(
            source,
            link
        )


        if loja is None:

            rejeitados_loja += 1
            continue


        # =================================================
        # NOVO / NACIONAL
        # =================================================

        if not produto_valido(
            titulo,
            snippet,
            extensions,
            delivery,
            condition
        ):

            rejeitados_internacional += 1
            continue


        # =================================================
        # ESCALA
        # =================================================

        if not escala_valida(
            titulo,
            snippet
        ):

            rejeitados_escala += 1
            continue


        # =================================================
        # MARCA
        # =================================================

        marca = identificar_marca(
            titulo
        )


        if marca is None:

            rejeitados_marca += 1
            continue


        # =================================================
        # HOT WHEELS
        # =================================================

        serie = None


        if marca == "Hot Wheels":

            serie = identificar_serie_hot_wheels(
                titulo,
                snippet
            )


            if not hot_wheels_valido(
                titulo,
                snippet
            ):

                rejeitados_basicos += 1
                continue


        # =================================================
        # PREÇO TOTAL ESTRUTURADO
        # =================================================

        preco = obter_preco_total(
            item,
            marca
        )


        if preco is None:

            rejeitados_preco += 1
            continue


        # =================================================
        # DESCONTO REAL
        # =================================================

        preco_antigo, desconto = (
            obter_desconto_real(
                item,
                preco
            )
        )


        # =================================================
        # CLASSIFICA
        # =================================================

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


        # =================================================
        # DUPLICADO
        # =================================================

        product_id = str(
            item.get(
                "product_id",
                ""
            )
        )


        identificador = (
            product_id
            if product_id
            else normalizar(
                f"{loja}|{titulo}"
            )
        )


        if identificador in identificadores:
            continue


        identificadores.add(
            identificador
        )


        resultados.append({
            "id":
                identificador,

            "titulo":
                titulo,

            "link":
                link,

            "loja":
                loja,

            "marca":
                marca,

            "serie":
                serie,

            "preco":
                preco,

            "preco_antigo":
                preco_antigo,

            "desconto":
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

            "modelo_quente":
                identificar_modelo_quente(
                    titulo
                ),

            "delivery":
                delivery
        })


# =========================================================
# HISTÓRICO DIÁRIO
# =========================================================

historico = carregar_historico()

para_enviar = []


for item in resultados:

    chave = item["id"]

    registro = historico.get(
        chave
    )


    if registro is None:

        item["tipo_alerta"] = (
            "NOVA_OFERTA"
        )

        para_enviar.append(
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

        para_enviar.append(
            item
        )

        continue


    # MESMO DIA:
    # só se preço diminuir
    menor_dia = registro.get(
        "menor_preco_dia"
    )


    if (
        menor_dia is None
        or item["preco"] < menor_dia
    ):

        item[
            "preco_anterior_encontrado"
        ] = menor_dia

        item["tipo_alerta"] = (
            "QUEDA_PRECO"
        )

        para_enviar.append(
            item
        )


# =========================================================
# ORDENAR
# =========================================================

para_enviar.sort(
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

    for item in para_enviar:

        if (
            item["loja"]
            == "Mercado Livre"
            and item["link"]
        ):

            arquivo.write(
                item["link"] + "\n"
            )


with open(
    ARQUIVO_AMAZON,
    "w",
    encoding="utf-8"
) as arquivo:

    for item in para_enviar:

        if (
            item["loja"]
            == "Amazon"
            and item["link"]
        ):

            arquivo.write(
                item["link"] + "\n"
            )


# =========================================================
# EMAIL
# =========================================================

if para_enviar:

    corpo = []

    corpo.append(
        "🚗 BUSCADOR DIECAST"
    )

    corpo.append(
        f"Data: {HOJE}"
    )

    corpo.append("")

    corpo.append(
        f"Ofertas encontradas: "
        f"{len(para_enviar)}"
    )

    corpo.append("")


    for numero, item in enumerate(
        para_enviar,
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


        if item["modelo_quente"]:

            corpo.append(
                "📈 Modelo quente: "
                + item["modelo_quente"]
            )


        corpo.append(
            f"Produto: "
            f"{item['titulo']}"
        )


        corpo.append("")


        if (
            item.get(
                "tipo_alerta"
            )
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
            f"💰 PREÇO TOTAL: "
            f"R$ {item['preco']:.2f}"
        )


        if item["desconto"] is not None:

            corpo.append(
                f"🔥 DESCONTO REAL: "
                f"{item['desconto']:.0f}%"
            )


        corpo.append(
            f"🔎 Motivo: "
            f"{item['motivo']}"
        )


        if item["delivery"]:

            corpo.append(
                f"🚚 Entrega: "
                f"{item['delivery']}"
            )


        corpo.append("")

        corpo.append(
            "🔗 LINK:"
        )

        corpo.append(
            item["link"]
            or "Link direto não informado pelo Shopping"
        )


        corpo.append("")

        corpo.append(
            "📲 TEXTO PRONTO PARA WHATSAPP"
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
            or "COLE AQUI O LINK"
        )


        corpo.append("")

        corpo.append(
            "⚠️ Preço pode mudar "
            "a qualquer momento."
        )

        corpo.append("")


    email_ok = enviar_email(
        f"🚨 {len(para_enviar)} "
        "oferta(s) Diecast",
        "\n".join(corpo)
    )


else:

    corpo = f"""
🔎 BUSCADOR DIECAST

Data: {HOJE}

Busca concluída normalmente.

Nenhuma NOVA oferta elegível foi encontrada nesta rodada.

✅ Google Shopping usado como fonte de preço
✅ Parcelas ignoradas
✅ Mercado Livre monitorado
✅ Amazon Brasil monitorada
✅ Internacional bloqueado quando identificado
✅ Escalas diferentes de 1:64 bloqueadas
✅ Hot Wheels básicos bloqueados
✅ Car Culture monitorado
✅ Modern Classics monitorado
✅ Japan Historics monitorado
✅ Boulevard monitorado
✅ Silver Series monitorado
✅ Pop Culture monitorado
✅ Premium Fast & Furious monitorado

DADOS:

Resultados Shopping analisados:
{total_encontrados}

Rejeitados por loja:
{rejeitados_loja}

Rejeitados por marca:
{rejeitados_marca}

Rejeitados por escala:
{rejeitados_escala}

Rejeitados por internacional/usado:
{rejeitados_internacional}

Hot Wheels básicos rejeitados:
{rejeitados_basicos}

Preços rejeitados:
{rejeitados_preco}
"""


    email_ok = enviar_email(
        "🔎 Diecast - Nenhuma nova oferta",
        corpo
    )


# =========================================================
# ATUALIZAR HISTÓRICO
# =========================================================

if (
    para_enviar
    and email_ok
):

    for item in para_enviar:

        chave = item["id"]
        preco = item["preco"]

        antigo = historico.get(
            chave,
            {}
        )


        menor_historico = antigo.get(
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
    "OFERTAS ENVIADAS:",
    len(para_enviar)
)

print("=" * 80)


for item in para_enviar:

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
        f"PREÇO TOTAL: "
        f"R$ {item['preco']:.2f}"
    )

    print(
        "PARCELAMENTO: IGNORADO"
    )


    if item["preco_antigo"] is not None:

        print(
            f"PREÇO ANTIGO: "
            f"R$ "
            f"{item['preco_antigo']:.2f}"
        )


    if item["desconto"] is not None:

        print(
            f"DESCONTO REAL: "
            f"{item['desconto']:.1f}%"
        )


    print(
        "LINK:",
        item["link"]
    )

    print(
        "-" * 80
    )


print()
print(
    "TOTAL SHOPPING ANALISADO:",
    total_encontrados
)

print(
    "HOT WHEELS BÁSICOS REJEITADOS:",
    rejeitados_basicos
)

print(
    "INTERNACIONAL/USADO REJEITADOS:",
    rejeitados_internacional
)

print(
    "ESCALA REJEITADA:",
    rejeitados_escala
)

print(
    "PREÇO REJEITADO:",
    rejeitados_preco
)


if email_ok:

    print(
        "📧 E-MAIL ENVIADO COM SUCESSO."
    )

else:

    print(
        "❌ E-MAIL NÃO FOI ENVIADO."
    )
