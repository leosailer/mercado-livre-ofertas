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
# CARROS / MARCAS DE INTERESSE
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
    '-"frete internacional" '
    '-importado '
    '-importação '
    '-"1:32" '
    '-"1:43" '
    '-"1:24" '
    '-"1:18" '
)


BUSCAS = [

    f'{DOMINIOS} '
    '"Hot Wheels Premium" '
    '("Ferrari" OR "Porsche" OR "Lamborghini" OR "McLaren" OR '
    '"BMW" OR "Mercedes" OR "Audi" OR "Skyline" OR "Supra") '
    '(oferta OR promoção OR desconto OR "R$ 49" OR "R$ 55" OR '
    '"R$ 59" OR "R$ 65" OR "R$ 69") '
    f'{EXCLUSOES}',

    f'{DOMINIOS} '
    '("Hot Wheels Silver Series" OR '
    '"Hot Wheels Boulevard" OR '
    '"Hot Wheels Car Culture" OR '
    '"Hot Wheels Pop Culture") '
    '("Ferrari" OR "Porsche" OR "Skyline" OR '
    '"Supra" OR "RX-7" OR "Lamborghini") '
    '(oferta OR promoção OR desconto OR "R$ 59" OR "R$ 69") '
    f'{EXCLUSOES}',

    f'{DOMINIOS} '
    '("Hot Wheels Premium" OR "Silver Series" OR "Car Culture") '
    '("Ferrari" OR "Porsche") '
    '("15% OFF" OR "20% OFF" OR "30% OFF" OR oferta OR promoção) '
    f'{EXCLUSOES}',

    f'{DOMINIOS} '
    '"Mini GT" '
    '("Ferrari" OR "Porsche" OR "Lamborghini" OR "McLaren" OR '
    '"Skyline" OR "GT-R" OR "Supra" OR "RX-7" OR "BMW") '
    '("R$ 89" OR "R$ 99" OR "R$ 109" OR "R$ 119" OR '
    '"R$ 129" OR "R$ 139" OR "R$ 149" OR oferta OR promoção) '
    f'{EXCLUSOES}',

    f'{DOMINIOS} '
    '("Hot Wheels Premium" OR "Mini GT" OR "Kaido House" OR '
    '"Tarmac Works" OR "Pop Race" OR "Inno64") '
    '("15% OFF" OR "20% OFF" OR "25% OFF" OR '
    '"30% OFF" OR "40% OFF" OR "oferta relâmpago") '
    f'{EXCLUSOES}',

    f'{DOMINIOS} '
    '("Tarmac Works" OR "Pop Race" OR "Inno64") '
    '("Ferrari" OR "Porsche" OR "Skyline" OR "Supra" OR '
    '"RX-7" OR "Koenigsegg" OR "McLaren") '
    '(oferta OR promoção OR desconto) '
    f'{EXCLUSOES}',

    f'{DOMINIOS} '
    '("Hot Wheels Premium" OR "Mini GT" OR "Tarmac Works") '
    '("Ferrari F40" OR "Ferrari Testarossa" OR '
    '"Porsche 911 GT3" OR "Skyline R32" OR "Skyline R34" OR '
    '"Mazda RX-7" OR "Koenigsegg") '
    '(oferta OR promoção OR desconto OR 2026) '
    f'{EXCLUSOES}',

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
    "taxa de importação",
    "taxas de importação",
    "enviado do exterior",
    "envio do exterior",
    "enviado dos estados unidos",
    "envio dos estados unidos",
    "envio da china",
    "produto dos estados unidos"
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


# O mínimo ajuda a eliminar parcelas absurdas.
FAIXAS_VALIDAS = {
    "Hot Wheels": (35, 600),
    "Matchbox": (25, 400),
    "Mini GT": (65, 400),
    "Kaido House": (90, 500),
    "Tarmac Works": (75, 500),
    "Pop Race": (75, 500),
    "Inno64": (75, 500),
    "Majorette": (30, 300),
    "Greenlight": (45, 400),
    "M2 Machines": (50, 500),
    "Tomica": (35, 300)
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

    link = normalizar(link)

    if "amazon.com.br" in link:
        return "Amazon"

    if "mercadolivre.com.br" in link:
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

    if any(
        escala in texto
        for escala in ESCALAS_PROIBIDAS
    ):
        return False

    escalas = re.findall(
        r"\b1\s*[:/]\s*(\d{2})\b",
        texto
    )

    if escalas:
        return all(
            escala == "64"
            for escala in escalas
        )

    return True


# =========================================================
# INTERNACIONAL
# =========================================================

def produto_nacional(titulo, trecho, loja):

    texto = normalizar(
        f"{titulo} {trecho}"
    )

    if any(
        termo in texto
        for termo in TERMOS_INTERNACIONAIS
    ):
        return False

    # Amazon.com.br sem indicação explícita de importação.
    if loja == "Amazon":
        return True

    # Mercado Livre:
    # se aparecer "internacional/importado", já foi bloqueado acima.
    # Mantemos o resultado quando não há esse sinal.
    if loja == "Mercado Livre":
        return True

    return False


# =========================================================
# MARCA
# =========================================================

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


def deve_excluir(titulo):

    texto = normalizar(titulo)

    return any(
        palavra in texto
        for palavra in PALAVRAS_EXCLUIR
    )


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
        return False

    minimo, maximo = FAIXAS_VALIDAS[
        marca
    ]

    return minimo <= preco <= maximo


# =========================================================
# PREÇO ESTRUTURADO DO GOOGLE
# =========================================================

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

        preco = detected.get("price")
        moeda = detected.get("currency")


        if preco is None:
            continue


        # Se a moeda estiver informada,
        # só aceita Real.
        if moeda is not None:

            moeda_texto = str(
                moeda
            ).upper()

            if (
                "R$" not in moeda_texto
                and "BRL" not in moeda_texto
            ):
                continue


        try:
            return float(preco)

        except:
            continue


    return None


# =========================================================
# PREÇO NO TEXTO
# IGNORA PARCELAS
# =========================================================

def extrair_precos_a_vista(
    texto,
    marca
):

    texto = texto or ""

    encontrados = []

    regex = re.compile(
        r"R\$\s*([\d\.]+,\d{2})",
        re.IGNORECASE
    )


    for match in regex.finditer(
        texto
    ):

        valor_texto = match.group(1)

        inicio = match.start()
        fim = match.end()


        antes = texto[
            max(0, inicio - 35):
            inicio
        ].lower()


        depois = texto[
            fim:
            min(len(texto), fim + 35)
        ].lower()


        # =========================================
        # BLOQUEIA PARCELA
        # =========================================

        # 6x R$ 29,90
        # 12 x R$ 15,00
        if re.search(
            r"\d+\s*x\s*$",
            antes
        ):
            continue


        # parcela de R$ 29,90
        if (
            "parcela" in antes
            or "parcelas" in antes
        ):
            continue


        # 6 parcelas de R$
        if re.search(
            r"\d+\s+parcelas?\s+(?:de\s+)?$",
            antes
        ):
            continue


        # mensalidade
        if (
            "por mês" in depois
            or "/mês" in depois
            or "/mes" in depois
        ):
            continue


        try:

            valor = float(
                valor_texto
                .replace(".", "")
                .replace(",", ".")
            )

        except:
            continue


        if not preco_valido(
            marca,
            valor
        ):
            continue


        # =========================================
        # PONTUAÇÃO DO PREÇO
        # =========================================

        pontos = 0


        # Preço à vista / Pix é o melhor.
        if (
            "pix" in antes
            or "pix" in depois
        ):
            pontos += 100


        if (
            "à vista" in antes
            or "a vista" in antes
            or "à vista" in depois
            or "a vista" in depois
        ):
            pontos += 100


        # "por R$ 59,90"
        if re.search(
            r"\bpor\s*$",
            antes
        ):
            pontos += 80


        # "agora R$ 59,90"
        if re.search(
            r"\bagora\s*$",
            antes
        ):
            pontos += 70


        # preço promocional
        if (
            "oferta" in antes
            or "promoção" in antes
            or "promocao" in antes
        ):
            pontos += 30


        encontrados.append({
            "valor": valor,
            "pontos": pontos,
            "posicao": inicio
        })


    if not encontrados:
        return None


    # =========================================
    # PRIORIDADE:
    # 1. Pix / à vista / "por"
    # 2. menor preço total válido
    # =========================================

    maior_pontuacao = max(
        item["pontos"]
        for item in encontrados
    )


    if maior_pontuacao > 0:

        melhores = [
            item
            for item in encontrados
            if item["pontos"] == maior_pontuacao
        ]

        return min(
            item["valor"]
            for item in melhores
        )


    # Sem indicação clara:
    # pega o menor PREÇO TOTAL válido.
    # Parcelas já foram eliminadas acima.
    return min(
        item["valor"]
        for item in encontrados
    )


# =========================================================
# ESCOLHER PREÇO FINAL
# =========================================================

def obter_preco(item, marca):

    # Primeiro tenta texto:
    # porque conseguimos identificar Pix / à vista.
    preco_texto = extrair_precos_a_vista(
        item.get(
            "snippet",
            ""
        ),
        marca
    )


    if preco_texto is not None:

        return (
            preco_texto,
            "PREÇO À VISTA / R$"
        )


    # Depois usa structured data.
    preco_rich = preco_rich_snippet(
        item
    )


    if (
        preco_rich is not None
        and preco_valido(
            marca,
            preco_rich
        )
    ):

        return (
            preco_rich,
            "PREÇO ESTRUTURADO / R$"
        )


    return (
        None,
        None
    )


# =========================================================
# DESCONTO
# SÓ PERCENTUAL EXPLÍCITO
# =========================================================

def detectar_desconto(trecho):

    if not trecho:
        return None


    padroes = [
        r"(\d{1,2})%\s*(?:OFF|off)",
        r"(\d{1,2})%\s*de\s*desconto",
        r"desconto\s*de\s*(\d{1,2})%"
    ]


    for padrao in padroes:

        resultado = re.search(
            padrao,
            trecho,
            re.IGNORECASE
        )


        if resultado:

            desconto = float(
                resultado.group(1)
            )


            if 5 <= desconto <= 80:
                return desconto


    return None


# =========================================================
# MEDIANA
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
            mediana * 0.60
            <= preco
            <= mediana * 1.70
        )
    ]


    if len(filtrados) < 3:
        return None


    return statistics.median(
        filtrados
    )


# =========================================================
# CLASSIFICAÇÃO
# =========================================================

def classificar(item):

    marca = item["marca"]
    preco = item["preco"]
    desconto = item["desconto"]
    mediana = item.get(
        "mediana"
    )


    # Hot Wheels < 69
    if (
        marca == "Hot Wheels"
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


    # Mini GT < 110
    if (
        marca == "Mini GT"
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


    # desconto explícito >= 30
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


    # Hot Wheels < 89
    if (
        marca == "Hot Wheels"
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


    # Mini GT < 130
    if (
        marca == "Mini GT"
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


    # desconto >= 20
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


    # abaixo do mercado
    if (
        mediana is not None
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


    # Hot Wheels < 99
    if (
        marca == "Hot Wheels"
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


    # Mini GT < 150
    if (
        marca == "Mini GT"
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


    # desconto >= 15
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
# BUSCAS
# =========================================================

links_vistos = set()
resultados = []

rejeitados_internacional = 0
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


        if not link_valido(
            link
        ):
            continue


        if link in links_vistos:
            continue


        if deve_excluir(
            titulo
        ):
            continue


        loja = identificar_loja(
            link
        )


        if not escala_valida(
            titulo,
            trecho
        ):

            rejeitados_escala += 1
            continue


        if not produto_nacional(
            titulo,
            trecho,
            loja
        ):

            rejeitados_internacional += 1
            continue


        if not hot_wheels_valido(
            titulo,
            link
        ):

            continue


        marca = identificar_marca(
            titulo,
            link
        )


        # Não queremos marca desconhecida
        if marca == "Outra":
            continue


        preco, fonte_preco = obter_preco(
            item,
            marca
        )


        if preco is None:

            rejeitados_preco += 1
            continue


        desconto = detectar_desconto(
            trecho
        )


        links_vistos.add(
            link
        )


        resultados.append({
            "titulo": titulo,
            "link": link,
            "trecho": trecho,
            "loja": loja,
            "marca": marca,
            "preco": preco,
            "fonte_preco":
                fonte_preco,
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
# MEDIANA / OFERTAS
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


    if registro is None:

        item["tipo_alerta"] = (
            "NOVA_OFERTA"
        )

        para_enviar.append(
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

        para_enviar.append(
            item
        )

        continue


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

        if (
            item["loja"]
            == "Mercado Livre"
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
        ):

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


        corpo.append(
            f"💰 PREÇO À VISTA: "
            f"R$ {item['preco']:.2f}"
        )


        if item["desconto"] is not None:

            corpo.append(
                f"🔥 Desconto informado: "
                f"{item['desconto']:.0f}%"
            )


        corpo.append(
            f"🔎 Motivo: "
            f"{item['status']}"
        )


        corpo.append(
            f"✅ Fonte do preço: "
            f"{item['fonte_preco']}"
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
            f"{item['preco']:.2f} à vista*"
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
        "\n".join(
            corpo
        )
    )


else:

    corpo = f"""
🔎 BUSCADOR DIECAST

Data: {HOJE}

Busca concluída.

Nenhuma nova oferta elegível foi encontrada.

✅ Somente valores em R$
✅ Parcelas ignoradas
✅ Prioridade para preço à vista / Pix
✅ Escala 1:64
✅ Usados e loose bloqueados
✅ Mercado Livre monitorado
✅ Amazon Brasil monitorada

Rejeitados:

Internacional:
{rejeitados_internacional}

Escala errada:
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

    print(
        "TÍTULO:",
        item["titulo"]
    )

    print(
        f"PREÇO À VISTA: "
        f"R$ {item['preco']:.2f}"
    )

    print(
        "FONTE:",
        item["fonte_preco"]
    )


    if item["desconto"] is not None:

        print(
            f"DESCONTO INFORMADO: "
            f"{item['desconto']:.0f}%"
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
    "REJEITADOS - INTERNACIONAL:",
    rejeitados_internacional
)

print(
    "REJEITADOS - ESCALA:",
    rejeitados_escala
)

print(
    "REJEITADOS - PREÇO NÃO CONFIÁVEL:",
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
