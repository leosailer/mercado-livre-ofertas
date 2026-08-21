import os
import re
import json
import ssl
import smtplib
import statistics
from datetime import datetime
from zoneinfo import ZoneInfo
from email.message import EmailMessage
from pathlib import Path

import requests


# =========================================================
# CONFIGURAÇÕES
# =========================================================

API_KEY = os.getenv("SERPAPI_KEY")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
EMAIL_DESTINO = os.getenv("EMAIL_DESTINO")

SERP_URL = "https://serpapi.com/search.json"

ARQUIVO_HISTORICO = Path("ofertas_vistas.json")
ARQUIVO_ML = Path("links_para_afiliado.txt")
ARQUIVO_AMAZON = Path("links_amazon.txt")

FUSO_BRASIL = ZoneInfo("America/Sao_Paulo")
HOJE = datetime.now(FUSO_BRASIL).date().isoformat()


# =========================================================
# MARCAS / CARROS DE INTERESSE
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
    "Mercedes AMG",
    "Audi",
    "Nissan Skyline",
    "Nissan GT-R",
    "Toyota Supra",
    "Mazda RX-7",
    "Honda NSX",
    "Honda Civic Type R",
    "Mitsubishi Lancer Evolution",
    "Subaru Impreza",
    "Ford Mustang",
    "Corvette",
    "Lexus",
    "Lotus"
]


MODELOS_QUENTES = [
    "Ferrari F40",
    "Ferrari Testarossa",
    "Ferrari 250 GTO",
    "Ferrari F50",
    "Ferrari 499P",
    "Porsche 911 GT3 RS",
    "Porsche 993 GT2",
    "Porsche Carrera GT",
    "Nissan Skyline R32",
    "Nissan Skyline R33",
    "Nissan Skyline R34",
    "Toyota Supra",
    "Mazda RX-7",
    "Mazda RX-7 VeilSide",
    "Koenigsegg Agera RS",
    "Koenigsegg One:1",
    "Lamborghini Countach",
    "Lamborghini Huracan",
    "Ford Mustang GTD",
    "Toyota GR Corolla"
]


# =========================================================
# BUSCAS
# =========================================================

DOMINIOS = "(site:mercadolivre.com.br OR site:amazon.com.br)"

EXCLUSOES = (
    '-usado '
    '-loose '
    '-"compra internacional" '
    '-"envio internacional" '
    '-importado '
    '-importação '
    '-"1:32" '
    '-"1:43" '
    '-"1:24" '
    '-"1:18" '
)


BUSCAS = [

    # HOT WHEELS PREMIUM - PREÇO BAIXO
    f'{DOMINIOS} '
    '"Hot Wheels Premium" '
    '("Ferrari" OR "Porsche" OR "Lamborghini" OR "McLaren" OR '
    '"BMW" OR "Mercedes" OR "Audi" OR "Skyline" OR "Supra") '
    '("R$ 49" OR "R$ 55" OR "R$ 59" OR "R$ 65" OR "R$ 69" '
    'OR oferta OR promoção OR desconto) '
    f'{EXCLUSOES}',

    # SILVER / BOULEVARD / CAR CULTURE
    f'{DOMINIOS} '
    '("Hot Wheels Silver Series" OR '
    '"Hot Wheels Boulevard" OR '
    '"Hot Wheels Car Culture" OR '
    '"Hot Wheels Pop Culture") '
    '("Ferrari" OR "Porsche" OR "Skyline" OR '
    '"Supra" OR "RX-7" OR "Lamborghini") '
    '("R$ 49" OR "R$ 59" OR "R$ 69" OR '
    'oferta OR promoção OR desconto) '
    f'{EXCLUSOES}',

    # FERRARI / PORSCHE
    f'{DOMINIOS} '
    '("Hot Wheels Premium" OR "Silver Series" OR "Car Culture") '
    '("Ferrari" OR "Porsche") '
    '("15% OFF" OR "20% OFF" OR "30% OFF" OR '
    'oferta OR promoção OR desconto) '
    f'{EXCLUSOES}',

    # MINI GT ATÉ 150
    f'{DOMINIOS} '
    '"Mini GT" '
    '("Ferrari" OR "Porsche" OR "Lamborghini" OR "McLaren" OR '
    '"Skyline" OR "GT-R" OR "Supra" OR "RX-7" OR "BMW") '
    '("R$ 89" OR "R$ 99" OR "R$ 109" OR "R$ 119" OR '
    '"R$ 129" OR "R$ 139" OR "R$ 149" OR oferta OR promoção) '
    f'{EXCLUSOES}',

    # DESCONTOS GRANDES
    f'{DOMINIOS} '
    '("Hot Wheels Premium" OR "Mini GT" OR "Kaido House" OR '
    '"Tarmac Works" OR "Pop Race" OR "Inno64") '
    '("15% OFF" OR "20% OFF" OR "25% OFF" OR '
    '"30% OFF" OR "40% OFF" OR "oferta relâmpago") '
    f'{EXCLUSOES}',

    # TARMAC / POP RACE / INNO64
    f'{DOMINIOS} '
    '("Tarmac Works" OR "Pop Race" OR "Inno64") '
    '("Ferrari" OR "Porsche" OR "Skyline" OR "Supra" OR '
    '"RX-7" OR "Koenigsegg" OR "McLaren") '
    '(oferta OR promoção OR desconto) '
    f'{EXCLUSOES}',

    # MODELOS QUENTES
    f'{DOMINIOS} '
    '("Hot Wheels Premium" OR "Mini GT" OR "Tarmac Works") '
    '("Ferrari F40" OR "Ferrari Testarossa" OR '
    '"Porsche 911 GT3" OR "Skyline R32" OR "Skyline R34" OR '
    '"Mazda RX-7" OR "Koenigsegg") '
    '(oferta OR promoção OR desconto OR 2026) '
    f'{EXCLUSOES}',

    # OUTRAS LINHAS
    f'{DOMINIOS} '
    '("Majorette Premium" OR "Tomica Premium" OR '
    '"Greenlight" OR "M2 Machines" OR '
    '"Matchbox Collectors" OR "Matchbox Moving Parts") '
    '("Ferrari" OR "Porsche" OR "Lamborghini" OR '
    '"Skyline" OR "Supra" OR "BMW" OR "Mustang") '
    '(oferta OR promoção OR desconto) '
    f'{EXCLUSOES}'
]


# =========================================================
# FILTROS
# =========================================================

PALAVRAS_EXCLUIR = [
    "usado",
    "loose",
    "sem blister",
    "sem embalagem",
    "avariado",
    "expositor",
    "display",
    "diorama",
    "garagem",
    "estante",
    "prateleira",
    "roda avulsa",
    "pneu avulso",
    "protetor blister"
]


TERMOS_INTERNACIONAIS = [
    "compra internacional",
    "envio internacional",
    "frete internacional",
    "produto internacional",
    "international shopping",
    "importado",
    "importação",
    "importacao",
    "taxas de importação",
    "taxa de importação",
    "enviado do exterior",
    "envio do exterior",
    "enviado dos estados unidos",
    "envio dos estados unidos",
    "envio da china",
    "produto dos estados unidos"
]


# Para sermos conservadores:
# precisa existir algum indício de entrega/estoque no Brasil.

SINAIS_NACIONAIS = [
    "frete grátis",
    "frete gratis",
    "entrega amanhã",
    "entrega amanha",
    "entrega hoje",
    "chegará",
    "chegara",
    "mercado envios",
    "full",
    "estoque no brasil",
    "envio nacional",
    "pronta entrega",
    "pronta-entrega",
    "entrega rápida",
    "entrega rapida",
    "prime",
    "amazon.com.br"
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


HOT_WHEELS_PERMITIDOS = [
    "premium",
    "silver series",
    "boulevard",
    "car culture",
    "pop culture",
    "team transport",
    "rlc",
    "collector",
    "collectors",
    "edição especial",
    "edicao especial",
    "anniversary",
    "aniversário",
    "aniversario"
]


FAIXAS_VALIDAS = {
    "Hot Wheels": (30, 600),
    "Matchbox": (20, 400),
    "Mini GT": (60, 400),
    "Kaido House": (90, 500),
    "Tarmac Works": (70, 500),
    "Pop Race": (70, 500),
    "Inno64": (70, 500),
    "Majorette": (25, 300),
    "Greenlight": (40, 400),
    "M2 Machines": (50, 500),
    "Tomica": (30, 300)
}


# =========================================================
# UTILIDADES
# =========================================================

def normalizar(texto):
    return re.sub(
        r"\s+",
        " ",
        (texto or "").lower()
    ).strip()


def identificar_loja(link):

    l = normalizar(link)

    if "amazon.com.br" in l:
        return "Amazon"

    if "mercadolivre.com.br" in l:
        return "Mercado Livre"

    return "Outra"


def link_valido(link):

    if not link:
        return False

    if "amazon.com.br" in link:
        return (
            "/dp/" in link
            or "/gp/product/" in link
        )

    if "mercadolivre.com.br" in link:
        return (
            "/p/" in link
            or "/up/" in link
            or "produto.mercadolivre.com.br/MLB-" in link
        )

    return False


# =========================================================
# ESCALA
# =========================================================

def escala_valida(titulo, trecho):

    texto = normalizar(
        f"{titulo} {trecho}"
    )

    # Bloqueia explicitamente escalas erradas
    if any(
        escala in texto
        for escala in ESCALAS_PROIBIDAS
    ):
        return False

    # Se tiver escala explícita, queremos 1:64
    tem_alguma_escala = re.search(
        r"\b1\s*[:/]\s*\d{2}\b",
        texto
    )

    if tem_alguma_escala:

        if (
            "1:64" not in texto
            and "1/64" not in texto
        ):
            return False

    return True


# =========================================================
# NACIONAL
# =========================================================

def produto_nacional(titulo, trecho, loja):

    texto = normalizar(
        f"{titulo} {trecho}"
    )

    # Qualquer sinal internacional = fora
    if any(
        termo in texto
        for termo in TERMOS_INTERNACIONAIS
    ):
        return False

    # Amazon Brasil:
    # domínio brasileiro + nenhum sinal de importação
    if loja == "Amazon":

        return True

    # Mercado Livre:
    # queremos pelo menos algum sinal de entrega local
    if loja == "Mercado Livre":

        if any(
            sinal in texto
            for sinal in SINAIS_NACIONAIS
        ):
            return True

        # Sem comprovação de origem nacional:
        # melhor descartar do que mandar internacional.
        return False

    return False


# =========================================================
# OUTROS FILTROS
# =========================================================

def deve_excluir(titulo):

    texto = normalizar(titulo)

    return any(
        palavra in texto
        for palavra in PALAVRAS_EXCLUIR
    )


def identificar_marca(titulo, link):

    texto = normalizar(
        f"{titulo} {link}"
    )

    if "kaido house" in texto:
        return "Kaido House"

    if "mini gt" in texto:
        return "Mini GT"

    if "tarmac works" in texto:
        return "Tarmac Works"

    if "pop race" in texto:
        return "Pop Race"

    if "inno64" in texto or "inno 64" in texto:
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

    return "Outra"


def hot_wheels_valido(titulo, link):

    texto = normalizar(
        f"{titulo} {link}"
    )

    if "hot wheels" not in texto:
        return True

    return any(
        termo in texto
        for termo in HOT_WHEELS_PERMITIDOS
    )


def identificar_carros_top(titulo):

    texto = normalizar(titulo)

    return [
        carro
        for carro in CARROS_TOP
        if carro.lower() in texto
    ]


def identificar_tendencia(titulo):

    texto = normalizar(titulo)

    for modelo in MODELOS_QUENTES:

        palavras = normalizar(
            modelo
        ).split()

        encontrados = sum(
            1
            for palavra in palavras
            if palavra in texto
        )

        if encontrados >= min(
            3,
            len(palavras)
        ):
            return modelo

    return None


# =========================================================
# PREÇO
# =========================================================

def preco_valido(marca, preco):

    if preco is None:
        return False

    if marca not in FAIXAS_VALIDAS:
        return True

    minimo, maximo = FAIXAS_VALIDAS[
        marca
    ]

    return minimo <= preco <= maximo


def preco_rich_snippet(item):

    rich = item.get(
        "rich_snippet",
        {}
    )

    for posicao in [
        "top",
        "bottom"
    ]:

        detected = rich.get(
            posicao,
            {}
        ).get(
            "detected_extensions",
            {}
        )

        preco = detected.get(
            "price"
        )

        if preco is not None:

            try:
                return float(preco)

            except:
                pass

    return None


# =========================================================
# EXTRAIR PREÇO SEM PEGAR PARCELA
# =========================================================

def extrair_precos_confiaveis(texto):

    texto = texto or ""

    resultados = []

    padrao = re.compile(
        r"R\$\s*([\d\.]+,\d{2})",
        re.IGNORECASE
    )

    for match in padrao.finditer(
        texto
    ):

        valor_texto = match.group(1)

        inicio = match.start()

        contexto_antes = texto[
            max(0, inicio - 20):
            inicio
        ].lower()


        # Exemplo:
        # 6x R$ 26,33
        # 10 x R$ 12,90
        # parcela R$ 20,00

        if re.search(
            r"\d+\s*x\s*$",
            contexto_antes
        ):
            continue


        if "parcela" in contexto_antes:
            continue


        try:

            valor = float(
                valor_texto
                .replace(".", "")
                .replace(",", ".")
            )

            resultados.append(
                valor
            )

        except:
            pass


    return resultados


def preco_snippet_confiavel(
    texto,
    marca
):

    valores = extrair_precos_confiaveis(
        texto
    )

    validos = [
        valor
        for valor in valores
        if preco_valido(
            marca,
            valor
        )
    ]

    if not validos:
        return None

    # Normalmente o preço principal aparece
    # antes do valor das parcelas.
    return validos[0]


# =========================================================
# DESCONTO
# =========================================================

def detectar_desconto(
    trecho,
    preco_atual
):

    if not preco_atual:
        return None


    # -----------------------------------------
    # 1. Só confia em percentual explícito
    # -----------------------------------------

    padroes_percentual = [
        r"(\d{1,2})%\s*(?:OFF|off)",
        r"(\d{1,2})%\s*de\s*desconto",
        r"desconto\s*de\s*(\d{1,2})%"
    ]


    for padrao in padroes_percentual:

        resultado = re.search(
            padrao,
            trecho or "",
            re.IGNORECASE
        )

        if resultado:

            desconto = float(
                resultado.group(1)
            )

            if 5 <= desconto <= 80:
                return desconto


    # -----------------------------------------
    # 2. "de R$ X por R$ Y"
    # -----------------------------------------

    padrao_de_por = re.search(
        r"de\s*R\$\s*([\d\.]+,\d{2}).{0,30}"
        r"por\s*R\$\s*([\d\.]+,\d{2})",
        trecho or "",
        re.IGNORECASE
    )


    if padrao_de_por:

        try:

            anterior = float(
                padrao_de_por.group(1)
                .replace(".", "")
                .replace(",", ".")
            )

            atual = float(
                padrao_de_por.group(2)
                .replace(".", "")
                .replace(",", ".")
            )


            if (
                anterior > atual
                and atual > 0
            ):

                desconto = (
                    (anterior - atual)
                    / anterior
                ) * 100


                if 5 <= desconto <= 80:

                    return desconto


        except:
            pass


    # Não inventa desconto usando parcelas
    return None


# =========================================================
# MEDIANA DE MERCADO
# =========================================================

def palavras_modelo(titulo):

    texto = normalizar(titulo)

    remover = [
        "hot wheels",
        "mini gt",
        "kaido house",
        "tarmac works",
        "pop race",
        "inno64",
        "matchbox",
        "majorette",
        "greenlight",
        "m2 machines",
        "tomica",
        "premium",
        "miniatura",
        "diecast",
        "carrinho",
        "1:64",
        "1/64"
    ]

    for palavra in remover:

        texto = texto.replace(
            palavra,
            " "
        )


    texto = re.sub(
        r"[^a-z0-9áéíóúãõâêôç\s\-]",
        " ",
        texto
    )


    ignorar = {
        "para",
        "com",
        "sem",
        "modelo",
        "carro",
        "produto",
        "novo",
        "coleção",
        "colecao"
    }


    return {
        palavra
        for palavra in texto.split()
        if (
            len(palavra) >= 3
            and palavra not in ignorar
        )
    }


def calcular_mediana_mercado(
    item,
    resultados
):

    palavras = palavras_modelo(
        item["titulo"]
    )

    precos = []


    for outro in resultados:

        if outro is item:
            continue

        if outro["marca"] != item["marca"]:
            continue

        if outro["preco"] is None:
            continue


        outras = palavras_modelo(
            outro["titulo"]
        )


        comuns = palavras.intersection(
            outras
        )


        if len(comuns) >= 3:

            precos.append(
                outro["preco"]
            )


    if len(precos) < 3:
        return None


    mediana = statistics.median(
        precos
    )


    filtrados = [
        preco
        for preco in precos
        if (
            mediana * 0.55
            <= preco
            <= mediana * 1.8
        )
    ]


    if len(filtrados) < 3:
        return None


    return statistics.median(
        filtrados
    )


# =========================================================
# RANKING
# =========================================================

def classificar(item):

    marca = item["marca"]
    preco = item["preco"]
    desconto = item["desconto"]
    mediana = item.get("mediana")


    # -----------------------------------------
    # HOT WHEELS
    # -----------------------------------------

    if (
        marca == "Hot Wheels"
        and preco is not None
        and preco < 69
    ):

        item["status"] = (
            "HOT WHEELS PREMIUM/SILVER "
            "ABAIXO DE R$69"
        )

        item["ranking"] = (
            "🚨 IMPERDÍVEL"
        )

        item["ranking_ordem"] = 0

        return item


    # -----------------------------------------
    # MINI GT < 110
    # -----------------------------------------

    if (
        marca == "Mini GT"
        and preco is not None
        and preco < 110
    ):

        item["status"] = (
            "MINI GT ABAIXO DE R$110"
        )

        item["ranking"] = (
            "🚨 IMPERDÍVEL"
        )

        item["ranking_ordem"] = 0

        return item


    # -----------------------------------------
    # DESCONTO >= 30
    # -----------------------------------------

    if (
        desconto is not None
        and desconto >= 30
    ):

        item["status"] = (
            "DESCONTO DE 30% OU MAIS"
        )

        item["ranking"] = (
            "🚨 IMPERDÍVEL"
        )

        item["ranking_ordem"] = 0

        return item


    # -----------------------------------------
    # HOT WHEELS < 89
    # -----------------------------------------

    if (
        marca == "Hot Wheels"
        and preco is not None
        and preco < 89
    ):

        item["status"] = (
            "HOT WHEELS PREMIUM/SILVER "
            "ABAIXO DE R$89"
        )

        item["ranking"] = (
            "🔥 BOA OFERTA"
        )

        item["ranking_ordem"] = 1

        return item


    # -----------------------------------------
    # MINI GT < 130
    # -----------------------------------------

    if (
        marca == "Mini GT"
        and preco is not None
        and preco < 130
    ):

        item["status"] = (
            "MINI GT ABAIXO DE R$130"
        )

        item["ranking"] = (
            "🔥 BOA OFERTA"
        )

        item["ranking_ordem"] = 1

        return item


    # -----------------------------------------
    # DESCONTO >= 20
    # -----------------------------------------

    if (
        desconto is not None
        and desconto >= 20
    ):

        item["status"] = (
            "DESCONTO DE 20% OU MAIS"
        )

        item["ranking"] = (
            "🔥 BOA OFERTA"
        )

        item["ranking_ordem"] = 1

        return item


    # -----------------------------------------
    # HOT WHEELS < 99
    # -----------------------------------------

    if (
        marca == "Hot Wheels"
        and preco is not None
        and preco < 99
    ):

        item["status"] = (
            "HOT WHEELS PREMIUM/SILVER "
            "ABAIXO DE R$99"
        )

        item["ranking"] = (
            "👀 INTERESSANTE"
        )

        item["ranking_ordem"] = 2

        return item


    # -----------------------------------------
    # MINI GT < 150
    # -----------------------------------------

    if (
        marca == "Mini GT"
        and preco is not None
        and preco < 150
    ):

        item["status"] = (
            "MINI GT ABAIXO DE R$150"
        )

        item["ranking"] = (
            "👀 INTERESSANTE"
        )

        item["ranking_ordem"] = 2

        return item


    # -----------------------------------------
    # 15% ABAIXO DA MEDIANA
    # -----------------------------------------

    if (
        mediana is not None
        and preco is not None
        and preco <= mediana * 0.85
    ):

        item["status"] = (
            "PREÇO ABAIXO DO MERCADO"
        )

        item["ranking"] = (
            "🔥 BOA OFERTA"
        )

        item["ranking_ordem"] = 1

        return item


    # -----------------------------------------
    # DESCONTO >= 15
    # -----------------------------------------

    if (
        desconto is not None
        and desconto >= 15
    ):

        item["status"] = (
            "DESCONTO DE 15% OU MAIS"
        )

        item["ranking"] = (
            "👀 INTERESSANTE"
        )

        item["ranking_ordem"] = 2

        return item


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


def salvar_historico(historico):

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
# EXECUTAR BUSCAS
# =========================================================

links_vistos = set()
resultados = []

rejeitados_internacionais = 0
rejeitados_escala = 0
rejeitados_preco = 0


for numero, busca in enumerate(
    BUSCAS,
    start=1
):

    print(
        f"Executando busca "
        f"{numero}/{len(BUSCAS)}..."
    )


    parametros = {
        "engine": "google",
        "q": busca,
        "hl": "pt-br",
        "gl": "br",
        "num": 20,
        "api_key": API_KEY
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

        continue


    dados = resposta.json()


    for item in dados.get(
        "organic_results",
        []
    ):

        titulo = item.get(
            "title",
            ""
        )

        link = item.get(
            "link",
            ""
        )

        trecho = item.get(
            "snippet",
            ""
        )


        if not link_valido(link):
            continue


        if link in links_vistos:
            continue


        if deve_excluir(titulo):
            continue


        loja = identificar_loja(
            link
        )


        # ESCALA
        if not escala_valida(
            titulo,
            trecho
        ):

            rejeitados_escala += 1
            continue


        # NACIONAL
        if not produto_nacional(
            titulo,
            trecho,
            loja
        ):

            rejeitados_internacionais += 1
            continue


        if not hot_wheels_valido(
            titulo,
            link
        ):

            continue


        links_vistos.add(
            link
        )


        marca = identificar_marca(
            titulo,
            link
        )


        # -----------------------------------------
        # PREÇO
        # -----------------------------------------

        preco = preco_rich_snippet(
            item
        )

        fonte_preco = None


        if preco is not None:

            fonte_preco = (
                "rich_snippet"
            )


        if preco is None:

            preco = preco_snippet_confiavel(
                trecho,
                marca
            )

            if preco is not None:

                fonte_preco = (
                    "snippet_filtrado"
                )


        if not preco_valido(
            marca,
            preco
        ):

            rejeitados_preco += 1
            continue


        desconto = detectar_desconto(
            trecho,
            preco
        )


        resultados.append({
            "titulo": titulo,
            "link": link,
            "trecho": trecho,
            "loja": loja,
            "marca": marca,
            "preco": preco,
            "fonte_preco": fonte_preco,
            "desconto": desconto,
            "carros_top":
                identificar_carros_top(
                    titulo
                ),
            "tendencia":
                identificar_tendencia(
                    titulo
                )
        })


# =========================================================
# CALCULAR MERCADO E CLASSIFICAR
# =========================================================

ofertas = []


for item in resultados:

    item["mediana"] = (
        calcular_mediana_mercado(
            item,
            resultados
        )
    )


    classificado = classificar(
        item
    )


    if classificado:

        ofertas.append(
            classificado
        )


# =========================================================
# HISTÓRICO DIÁRIO
# =========================================================

historico = carregar_historico()

para_enviar = []


for item in ofertas:

    link = item["link"]
    preco = item["preco"]

    registro = historico.get(
        link
    )


    # NUNCA ENVIADO
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
    # APENAS SE CAIR PREÇO
    menor_dia = registro.get(
        "menor_preco_dia"
    )


    if (
        menor_dia is None
        or preco < menor_dia
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
# ARQUIVOS
# =========================================================

with open(
    ARQUIVO_ML,
    "w",
    encoding="utf-8"
) as arquivo:

    for item in para_enviar:

        if item["loja"] == "Mercado Livre":

            arquivo.write(
                item["link"] + "\n"
            )


with open(
    ARQUIVO_AMAZON,
    "w",
    encoding="utf-8"
) as arquivo:

    for item in para_enviar:

        if item["loja"] == "Amazon":

            arquivo.write(
                item["link"] + "\n"
            )


# =========================================================
# E-MAIL
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
            "=" * 60
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


        if item["carros_top"]:

            corpo.append(
                "🏎️ Carro top: "
                + ", ".join(
                    item["carros_top"]
                )
            )


        if item["tendencia"]:

            corpo.append(
                "📈 Tendência: "
                + item["tendencia"]
            )


        corpo.append(
            f"Produto: "
            f"{item['titulo']}"
        )


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


        corpo.append(
            f"💰 PREÇO: "
            f"R$ {item['preco']:.2f}"
        )


        if item["desconto"] is not None:

            corpo.append(
                f"🔥 Desconto: "
                f"{item['desconto']:.1f}%"
            )


        corpo.append(
            f"🔎 Motivo: "
            f"{item['status']}"
        )


        corpo.append("")

        corpo.append(
            "🔗 LINK:"
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

Busca concluída.

Nenhuma nova oferta elegível foi encontrada.

✅ Somente produtos nacionais
✅ Escala 1:64
✅ Usados e loose bloqueados
✅ Parcelas não são usadas como preço
✅ Mercado Livre monitorado
✅ Amazon Brasil monitorada

Resultados rejeitados nesta rodada:

Internacionais / não confirmados nacionais:
{rejeitados_internacionais}

Escala incorreta:
{rejeitados_escala}

Preço não confiável:
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

        link = item["link"]
        preco = item["preco"]

        antigo = historico.get(
            link,
            {}
        )

        menor_historico = antigo.get(
            "menor_preco_historico",
            preco
        )

        menor_historico = min(
            menor_historico,
            preco
        )


        historico[
            link
        ] = {
            "titulo":
                item["titulo"],

            "marca":
                item["marca"],

            "loja":
                item["loja"],

            "ultima_data_enviada":
                HOJE,

            "menor_preco_dia":
                preco,

            "menor_preco_historico":
                menor_historico
        }


    salvar_historico(
        historico
    )


# =========================================================
# LOG
# =========================================================

print()

print(
    "=" * 80
)

print(
    "OFERTAS ENVIADAS:",
    len(para_enviar)
)

print(
    "=" * 80
)


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

    print(
        "TÍTULO:",
        item["titulo"]
    )

    print(
        f"PREÇO: "
        f"R$ {item['preco']:.2f}"
    )

    print(
        "FONTE DO PREÇO:",
        item["fonte_preco"]
    )


    if item["desconto"] is not None:

        print(
            f"DESCONTO: "
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
    "REJEITADOS - INTERNACIONAL / "
    "SEM CONFIRMAÇÃO NACIONAL:",
    rejeitados_internacionais
)

print(
    "REJEITADOS - ESCALA:",
    rejeitados_escala
)

print(
    "REJEITADOS - PREÇO:",
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
