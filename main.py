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

URL = "https://serpapi.com/search.json"

ARQUIVO_HISTORICO = Path("ofertas_vistas.json")
ARQUIVO_ML = Path("links_para_afiliado.txt")
ARQUIVO_AMAZON = Path("links_amazon.txt")

FUSO_BRASIL = ZoneInfo("America/Sao_Paulo")

AGORA = datetime.now(FUSO_BRASIL)
HOJE = AGORA.date().isoformat()


# =========================================================
# LOJAS
# =========================================================

DOMINIOS = (
    "(site:mercadolivre.com.br OR site:amazon.com.br)"
)

EXCLUSAO_INTERNACIONAL_BUSCA = (
    '-"compra internacional" '
    '-"envio internacional" '
    '-"frete internacional" '
    '-"international shopping" '
    '-"taxas de importação" '
)


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


# =========================================================
# TERMOS QUENTES / RECENTES
# =========================================================

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
    "Koenigsegg Agera RS",
    "Koenigsegg One:1",
    "Lamborghini Countach",
    "Lamborghini Huracan",
    "Ford Mustang GTD",
    "Porsche 928",
    "Toyota GR Corolla",
    "Mazda RX-7 VeilSide",
    "Skyline R32 Widebody"
]


# =========================================================
# BUSCAS REFINADAS
# =========================================================

BUSCAS = [

    # 1 - HOT WHEELS PREMIUM BARATOS
    f'{DOMINIOS} '
    '"Hot Wheels Premium" '
    '("Ferrari" OR "Porsche" OR "Lamborghini" OR "McLaren" OR '
    '"BMW" OR "Mercedes" OR "Audi" OR "Skyline" OR "Supra") '
    '("R$ 49" OR "R$ 55" OR "R$ 59" OR "R$ 65" OR "R$ 69" '
    'OR promoção OR oferta OR desconto) '
    '-usado -loose '
    f'{EXCLUSAO_INTERNACIONAL_BUSCA}',

    # 2 - LINHAS ESPECIAIS HOT WHEELS
    f'{DOMINIOS} '
    '("Hot Wheels Silver Series" OR "Hot Wheels Car Culture" OR '
    '"Hot Wheels Boulevard" OR "Hot Wheels Pop Culture") '
    '("Ferrari" OR "Porsche" OR "Skyline" OR "Supra" OR '
    '"RX-7" OR "Lamborghini") '
    '(oferta OR promoção OR desconto OR "R$ 69" OR "R$ 79") '
    '-usado -loose '
    f'{EXCLUSAO_INTERNACIONAL_BUSCA}',

    # 3 - FERRARI / PORSCHE
    f'{DOMINIOS} '
    '("Hot Wheels Premium" OR "Silver Series") '
    '("Ferrari" OR "Porsche") '
    '(oferta OR promoção OR desconto OR barato OR "15% OFF" OR "20% OFF") '
    '-usado -loose '
    f'{EXCLUSAO_INTERNACIONAL_BUSCA}',

    # 4 - MINI GT BARATO
    f'{DOMINIOS} '
    '"Mini GT" '
    '("Ferrari" OR "Porsche" OR "Lamborghini" OR "McLaren" OR '
    '"Skyline" OR "GT-R" OR "Supra" OR "RX-7" OR "BMW") '
    '("R$ 99" OR "R$ 109" OR "R$ 119" OR "R$ 129" OR '
    '"R$ 139" OR "R$ 149" OR oferta OR promoção) '
    '-usado -loose '
    f'{EXCLUSAO_INTERNACIONAL_BUSCA}',

    # 5 - DESCONTOS FORTES
    f'{DOMINIOS} '
    '("Hot Wheels Premium" OR "Mini GT" OR "Kaido House" OR '
    '"Tarmac Works" OR "Pop Race" OR "Inno64") '
    '("15% OFF" OR "20% OFF" OR "25% OFF" OR "30% OFF" OR '
    '"40% OFF" OR promoção OR desconto OR oferta relâmpago) '
    '-usado -loose '
    f'{EXCLUSAO_INTERNACIONAL_BUSCA}',

    # 6 - TARMAC / POP RACE / INNO64
    f'{DOMINIOS} '
    '("Tarmac Works" OR "Pop Race" OR "Inno64") '
    '("Ferrari" OR "Porsche" OR "Skyline" OR "Supra" OR '
    '"RX-7" OR "Koenigsegg" OR "McLaren") '
    '(oferta OR promoção OR desconto OR barato) '
    '-usado -loose '
    f'{EXCLUSAO_INTERNACIONAL_BUSCA}',

    # 7 - LANÇAMENTOS / MODELOS QUENTES
    f'{DOMINIOS} '
    '("Hot Wheels Premium" OR "Mini GT" OR "Tarmac Works") '
    '("Ferrari F40" OR "Ferrari Testarossa" OR "Porsche 911 GT3" OR '
    '"Skyline R32" OR "Skyline R34" OR "Mazda RX-7 VeilSide" OR '
    '"Koenigsegg" OR "Toyota GR Corolla") '
    '(2026 OR lançamento OR novidade OR oferta) '
    '-usado -loose '
    f'{EXCLUSAO_INTERNACIONAL_BUSCA}',

    # 8 - OUTRAS MARCAS PREMIUM
    f'{DOMINIOS} '
    '("Majorette Premium" OR "Tomica Premium" OR "Greenlight" OR '
    '"M2 Machines" OR "Matchbox Collectors" OR "Matchbox Moving Parts") '
    '("Ferrari" OR "Porsche" OR "Lamborghini" OR "Skyline" OR '
    '"Supra" OR "BMW" OR "Mustang") '
    '(oferta OR promoção OR desconto OR barato) '
    '-usado -loose '
    f'{EXCLUSAO_INTERNACIONAL_BUSCA}'
]


# =========================================================
# FILTROS
# =========================================================

PALAVRAS_EXCLUIR = [
    "usado",
    "loose",
    "aberto",
    "sem blister",
    "sem embalagem",
    "avariado",
    "expositor",
    "display",
    "diorama",
    "garagem",
    "estante",
    "prateleira",
    "adesivo",
    "roda avulsa",
    "pneu avulso",
    "suporte",
    "protetor blister"
]


TERMOS_INTERNACIONAIS = [
    "compra internacional",
    "envio internacional",
    "frete internacional",
    "produto internacional",
    "international shopping",
    "taxas de importação",
    "taxa de importação",
    "enviado dos estados unidos",
    "enviado do exterior",
    "envio do exterior"
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
    "Hot Wheels": (20, 1000),
    "Matchbox": (20, 600),
    "Mini GT": (40, 500),
    "Kaido House": (70, 700),
    "Tarmac Works": (50, 700),
    "Pop Race": (50, 700),
    "Inno64": (50, 700),
    "Majorette": (20, 500),
    "Greenlight": (40, 600),
    "M2 Machines": (40, 700),
    "Tomica": (30, 600)
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


def eh_internacional(titulo, trecho):

    combinado = normalizar(
        f"{titulo} {trecho}"
    )

    return any(
        termo in combinado
        for termo in TERMOS_INTERNACIONAIS
    )


def deve_excluir(titulo):

    t = normalizar(titulo)

    return any(
        palavra in t
        for palavra in PALAVRAS_EXCLUIR
    )


def identificar_marca(titulo, link):

    combinado = normalizar(
        f"{titulo} {link}"
    )

    if "kaido house" in combinado:
        return "Kaido House"

    if "mini gt" in combinado:
        return "Mini GT"

    if "tarmac works" in combinado:
        return "Tarmac Works"

    if "pop race" in combinado:
        return "Pop Race"

    if "inno64" in combinado or "inno 64" in combinado:
        return "Inno64"

    if "matchbox" in combinado:
        return "Matchbox"

    if "hot wheels" in combinado:
        return "Hot Wheels"

    if "majorette" in combinado:
        return "Majorette"

    if "greenlight" in combinado:
        return "Greenlight"

    if "m2 machines" in combinado:
        return "M2 Machines"

    if "tomica" in combinado:
        return "Tomica"

    return "Outra"


def hot_wheels_valido(titulo, link):

    combinado = normalizar(
        f"{titulo} {link}"
    )

    if "hot wheels" not in combinado:
        return True

    return any(
        termo in combinado
        for termo in HOT_WHEELS_PERMITIDOS
    )


def identificar_carros_top(titulo):

    t = normalizar(titulo)

    return [
        carro
        for carro in CARROS_TOP
        if carro.lower() in t
    ]


def identificar_tendencia(titulo):

    t = normalizar(titulo)

    for modelo in MODELOS_QUENTES:

        palavras = normalizar(modelo).split()

        if len(palavras) >= 2:

            encontrados = sum(
                1
                for palavra in palavras
                if palavra in t
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

    minimo, maximo = FAIXAS_VALIDAS[marca]

    return minimo <= preco <= maximo


def extrair_precos_texto(texto):

    encontrados = re.findall(
        r"R\$\s*([\d\.]+,\d{2})",
        texto or ""
    )

    precos = []

    for valor in encontrados:

        try:

            precos.append(
                float(
                    valor
                    .replace(".", "")
                    .replace(",", ".")
                )
            )

        except:
            pass

    return precos


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

        if preco is not None:

            try:
                return float(preco)

            except:
                pass

    return None


def detectar_desconto(
    trecho,
    preco_atual
):

    if not preco_atual:
        return None

    padroes = [
        r"(\d{1,2})%\s*(?:OFF|off)",
        r"(\d{1,2})%\s*de\s*desconto",
        r"desconto\s*de\s*(\d{1,2})%"
    ]

    for padrao in padroes:

        resultado = re.search(
            padrao,
            trecho or "",
            re.IGNORECASE
        )

        if resultado:

            valor = float(
                resultado.group(1)
            )

            if 0 < valor <= 80:
                return valor


    precos = extrair_precos_texto(
        trecho
    )

    candidatos = [
        p for p in precos
        if preco_atual < p <= preco_atual * 2.2
    ]

    if not candidatos:
        return None

    anterior = max(candidatos)

    desconto = (
        (anterior - preco_atual)
        / anterior
    ) * 100

    if 5 <= desconto <= 80:
        return desconto

    return None


# =========================================================
# COMPARAÇÃO DE PREÇO
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

        if len(comuns) >= 2:
            precos.append(
                outro["preco"]
            )

    if len(precos) < 2:
        return None

    # remove valores muito fora do conjunto
    mediana = statistics.median(
        precos
    )

    filtrados = [
        preco
        for preco in precos
        if (
            mediana * 0.45
            <= preco
            <= mediana * 2
        )
    ]

    if len(filtrados) < 2:
        return None

    return statistics.median(
        filtrados
    )


# =========================================================
# CLASSIFICAÇÃO / RANKING
# =========================================================

def classificar(item):

    marca = item["marca"]
    preco = item["preco"]
    desconto = item["desconto"]
    mediana = item.get("mediana")

    status = None

    # Hot Wheels muito barato
    if (
        marca == "Hot Wheels"
        and preco is not None
        and preco < 69
    ):

        status = (
            "HOT WHEELS PREMIUM/SILVER "
            "ABAIXO DE R$69"
        )

    # desconto forte
    elif (
        desconto is not None
        and desconto >= 15
    ):

        status = (
            "DESCONTO DE 15% OU MAIS"
        )

    # Hot Wheels até 99
    elif (
        marca == "Hot Wheels"
        and preco is not None
        and preco < 99
    ):

        status = (
            "HOT WHEELS PREMIUM/SILVER "
            "ABAIXO DE R$99"
        )

    # Mini GT
    elif (
        marca == "Mini GT"
        and preco is not None
        and preco < 150
    ):

        status = (
            "MINI GT ABAIXO DE R$150"
        )

    # abaixo do mercado
    elif (
        mediana is not None
        and preco is not None
        and preco <= mediana * 0.85
    ):

        status = (
            "PREÇO 15%+ ABAIXO DE "
            "ANÚNCIOS SEMELHANTES"
        )

    if status is None:
        return None


    # RANKING

    if (
        marca == "Hot Wheels"
        and preco < 69
    ):

        ranking = "🚨 IMPERDÍVEL"
        ordem = 0

    elif (
        marca == "Mini GT"
        and preco < 110
    ):

        ranking = "🚨 IMPERDÍVEL"
        ordem = 0

    elif (
        desconto is not None
        and desconto >= 30
    ):

        ranking = "🚨 IMPERDÍVEL"
        ordem = 0

    elif (
        desconto is not None
        and desconto >= 20
    ):

        ranking = "🔥 BOA OFERTA"
        ordem = 1

    elif (
        mediana is not None
        and preco <= mediana * 0.80
    ):

        ranking = "🔥 BOA OFERTA"
        ordem = 1

    elif (
        marca == "Hot Wheels"
        and preco < 89
    ):

        ranking = "🔥 BOA OFERTA"
        ordem = 1

    elif (
        marca == "Mini GT"
        and preco < 130
    ):

        ranking = "🔥 BOA OFERTA"
        ordem = 1

    else:

        ranking = "👀 INTERESSANTE"
        ordem = 2


    item["status"] = status
    item["ranking"] = ranking
    item["ranking_ordem"] = ordem

    return item


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
# BUSCAR
# =========================================================

links_vistos = set()
resultados = []


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
            URL,
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


        # Remove internacional
        if eh_internacional(
            titulo,
            trecho
        ):
            continue


        if not hot_wheels_valido(
            titulo,
            link
        ):
            continue


        links_vistos.add(
            link
        )


        loja = identificar_loja(
            link
        )


        marca = identificar_marca(
            titulo,
            link
        )


        preco = preco_rich_snippet(
            item
        )


        if preco is None:

            precos = extrair_precos_texto(
                trecho
            )

            validos = [
                p
                for p in precos
                if preco_valido(
                    marca,
                    p
                )
            ]

            if validos:
                preco = validos[0]


        if not preco_valido(
            marca,
            preco
        ):

            preco = None


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

    if item["preco"] is None:
        continue


    chave = item["link"]

    registro = historico.get(
        chave
    )


    # nunca enviado
    if registro is None:

        item["tipo_alerta"] = (
            "NOVA_OFERTA"
        )

        para_enviar.append(
            item
        )

        continue


    ultima_data = registro.get(
        "ultima_data_enviada"
    )


    # novo dia = reapresenta
    if ultima_data != HOJE:

        item["tipo_alerta"] = (
            "OFERTA_DO_DIA"
        )

        para_enviar.append(
            item
        )

        continue


    # mesmo dia, só se preço cair
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
        if x["preco"] is not None
        else 999999
    )
)


# =========================================================
# ARQUIVOS DE LINKS
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
# MONTAR E-MAIL
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


    for numero, item in enumerate(
        para_enviar,
        start=1
    ):

        corpo.append(
            "=" * 60
        )

        corpo.append(
            f"{numero}. {item['ranking']}"
        )

        corpo.append(
            f"🛍️ Loja: {item['loja']}"
        )

        corpo.append(
            f"🏷️ Marca: {item['marca']}"
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
            f"Produto: {item['titulo']}"
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


        if item["mediana"] is not None:

            corpo.append(
                f"📊 Mediana encontrada: "
                f"R$ {item['mediana']:.2f}"
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
            f"💰 *R$ {item['preco']:.2f}*"
        )


        if item["desconto"] is not None:

            corpo.append(
                f"🔥 {item['desconto']:.0f}% OFF"
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
            "⚠️ Preço pode mudar a qualquer momento."
        )

        corpo.append("")


    assunto = (
        f"🚨 {len(para_enviar)} oferta(s) "
        f"Diecast - ML + Amazon"
    )


    email_ok = enviar_email(
        assunto,
        "\n".join(corpo)
    )


else:

    corpo = f"""
🔎 BUSCADOR DIECAST

Data: {HOJE}

Busca concluída com sucesso.

Nenhuma nova oferta elegível foi encontrada nesta rodada.

✅ Mercado Livre monitorado
✅ Amazon Brasil monitorada
✅ Produtos internacionais ignorados
✅ Produtos usados/loose ignorados
✅ Ofertas já enviadas hoje ignoradas

O buscador continuará monitorando automaticamente.
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
                    preco,
                    antigo.get(
                        "menor_preco_historico",
                        preco
                    )
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
        f"PREÇO: R$ "
        f"{item['preco']:.2f}"
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


if email_ok:

    print(
        "📧 E-MAIL ENVIADO COM SUCESSO."
    )

else:

    print(
        "❌ E-MAIL NÃO FOI ENVIADO."
    )
