import os
import re
import json
import ssl
import smtplib
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
ARQUIVO_LINKS_AFILIADO = Path("links_para_afiliado.txt")


# =========================================================
# CARROS DE INTERESSE
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
    "Corvette"
]


# =========================================================
# MODELOS QUENTES
# =========================================================

TENDENCIAS_QUENTES = [
    ("Ferrari F40 RLC", ["ferrari", "f40", "rlc"]),
    ("Ferrari Testarossa", ["ferrari", "testarossa"]),
    ("Ferrari 250 GTO", ["ferrari", "250", "gto"]),
    ("Ferrari Enzo", ["ferrari", "enzo"]),
    ("Ferrari 499P", ["ferrari", "499p"]),
    ("Ferrari F50", ["ferrari", "f50"]),

    ("Porsche 993 GT2", ["porsche", "993", "gt2"]),
    ("Porsche 917K", ["porsche", "917k"]),
    ("Porsche Carrera GT", ["porsche", "carrera", "gt"]),
    ("Porsche 911 Carrera RS", ["porsche", "911", "carrera", "rs"]),
    ("Porsche 911 GT3 RS", ["porsche", "911", "gt3", "rs"]),

    ("Nissan Skyline BNR32", ["nissan", "skyline", "bnr32"]),
    ("NISMO 270R", ["nismo", "270r"]),
    ("Toyota Supra VeilSide", ["toyota", "supra", "veilside"]),
    ("Lamborghini Countach", ["lamborghini", "countach"]),
    ("Mazda RX-7 RE-Amemiya", ["mazda", "rx-7", "re-amemiya"]),
    ("Nissan Skyline R33", ["nissan", "skyline", "r33"]),
    ("Ford Mustang GTD", ["ford", "mustang", "gtd"]),
    ("Koenigsegg Agera RS", ["koenigsegg", "agera", "rs"])
]


# =========================================================
# BUSCAS
# =========================================================

BUSCAS = [

    'site:mercadolivre.com.br "Hot Wheels Premium" '
    '("Ferrari" OR "Porsche" OR "Lamborghini" OR "McLaren" OR '
    '"BMW" OR "Mercedes" OR "Audi") '
    '("R$ 49" OR "R$ 55" OR "R$ 59" OR "R$ 65" OR "R$ 69" '
    'OR oferta OR desconto) '
    '-usado -loose',

    'site:mercadolivre.com.br '
    '("Hot Wheels Car Culture" OR "Hot Wheels Boulevard" OR '
    '"Hot Wheels Silver Series" OR "Hot Wheels Pop Culture") '
    '("Ferrari" OR "Porsche" OR "Skyline" OR "Supra" OR "RX-7") '
    '("R$ 49" OR "R$ 59" OR "R$ 69" OR oferta) '
    '-usado -loose',

    'site:mercadolivre.com.br "Hot Wheels Premium" "Ferrari" '
    '-usado -loose',

    'site:mercadolivre.com.br "Hot Wheels Premium" "Porsche" '
    '-usado -loose',

    'site:mercadolivre.com.br "Hot Wheels Premium" '
    '("Skyline" OR "Supra" OR "RX-7") '
    '-usado -loose',

    'site:mercadolivre.com.br "Mini GT" '
    '("Ferrari" OR "Porsche" OR "Lamborghini" OR "McLaren" OR '
    '"Skyline" OR "GT-R" OR "Supra" OR "RX-7") '
    '-usado -loose',

    'site:mercadolivre.com.br "Mini GT" '
    '("R$ 99" OR "R$ 109" OR "R$ 119" OR '
    '"R$ 129" OR "R$ 139" OR "R$ 149") '
    '-usado -loose',

    'site:mercadolivre.com.br "Kaido House" '
    '("oferta" OR desconto OR promoção) '
    '-usado -loose',

    'site:mercadolivre.com.br "Tarmac Works" '
    '("oferta" OR desconto OR promoção) '
    '-usado -loose',

    'site:mercadolivre.com.br '
    '("Pop Race" OR "Inno64" OR "Greenlight" OR '
    '"M2 Machines" OR "Tomica Premium" OR "Majorette Premium") '
    '("oferta" OR desconto OR promoção) '
    '-usado -loose'
]


# =========================================================
# FILTROS
# =========================================================

PALAVRAS_EXCLUIR = [
    "expositor",
    "display",
    "estante",
    "prateleira",
    "garagem",
    "diorama",
    "adesivo",
    "roda avulsa",
    "pneu avulso",
    "case",
    "caixa organizadora",
    "suporte",
    "protetor blister",
    "usado",
    "loose",
    "aberto",
    "sem blister",
    "sem embalagem",
    "avariado"
]


HOT_WHEELS_PERMITIDOS = [
    "premium",
    "silver series",
    "boulevard",
    "car culture",
    "team transport",
    "rlc",
    "collector",
    "collectors",
    "pop culture",
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
    "Majorette": (20, 500),
    "Greenlight": (40, 600),
    "M2 Machines": (40, 700),
    "Tomica": (30, 600),
    "Pop Race": (50, 700),
    "Inno64": (50, 700)
}


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

            return json.load(arquivo)

    except Exception as erro:

        print(
            "AVISO: erro ao carregar histórico:",
            erro
        )

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
# FUNÇÕES
# =========================================================

def texto_normalizado(texto):

    return re.sub(
        r"\s+",
        " ",
        (texto or "").lower()
    ).strip()


def identificar_marca(titulo, link):

    combinado = texto_normalizado(
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


def identificar_carros_top(titulo):

    t = texto_normalizado(titulo)

    encontrados = []

    for carro in CARROS_TOP:

        if carro.lower() in t:
            encontrados.append(carro)

    return encontrados


def identificar_tendencia(titulo):

    t = texto_normalizado(titulo)

    for nome, termos in TENDENCIAS_QUENTES:

        if all(
            termo.lower() in t
            for termo in termos
        ):

            return nome

    return None


def link_valido(link):

    formatos = [
        "/p/",
        "/up/",
        "produto.mercadolivre.com.br/MLB-"
    ]

    return (
        bool(link)
        and any(
            formato in link
            for formato in formatos
        )
    )


def deve_excluir(titulo):

    t = texto_normalizado(titulo)

    return any(
        palavra in t
        for palavra in PALAVRAS_EXCLUIR
    )


def hot_wheels_valido(titulo, link):

    combinado = texto_normalizado(
        f"{titulo} {link}"
    )

    if "hot wheels" not in combinado:
        return True

    return any(
        palavra in combinado
        for palavra in HOT_WHEELS_PERMITIDOS
    )


def preco_valido(marca, preco):

    if preco is None:
        return False

    if marca not in FAIXAS_VALIDAS:
        return True

    minimo, maximo = FAIXAS_VALIDAS[marca]

    return minimo <= preco <= maximo


def extrair_precos_texto(texto):

    valores = re.findall(
        r"R\$\s*([\d\.]+,\d{2})",
        texto or ""
    )

    precos = []

    for valor in valores:

        try:

            numero = float(
                valor
                .replace(".", "")
                .replace(",", ".")
            )

            precos.append(numero)

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

            percentual = float(
                resultado.group(1)
            )

            if 0 < percentual <= 80:
                return percentual


    precos = extrair_precos_texto(
        trecho
    )

    candidatos = [
        preco
        for preco in precos
        if (
            preco_atual < preco
            <= preco_atual * 2.5
        )
    ]

    if not candidatos:
        return None


    preco_anterior = max(
        candidatos
    )


    desconto = (
        (
            preco_anterior
            - preco_atual
        )
        / preco_anterior
    ) * 100


    if 5 <= desconto <= 80:
        return desconto

    return None


# =========================================================
# ENVIAR E-MAIL
# =========================================================

def enviar_email(ofertas):

    if not ofertas:
        return True


    if not EMAIL_DESTINO:
        print(
            "ERRO: EMAIL_DESTINO não configurado."
        )

        return False


    if not GMAIL_APP_PASSWORD:
        print(
            "ERRO: GMAIL_APP_PASSWORD não configurado."
        )

        return False


    mensagem = EmailMessage()


    if len(ofertas) == 1:

        assunto = (
            "🚨 Nova oferta Diecast encontrada"
        )

    else:

        assunto = (
            f"🚨 {len(ofertas)} novas ofertas Diecast"
        )


    mensagem["Subject"] = assunto

    mensagem["From"] = EMAIL_DESTINO

    mensagem["To"] = EMAIL_DESTINO


    corpo = []

    corpo.append(
        "🚗 BUSCADOR DIECAST - NOVAS OFERTAS"
    )

    corpo.append("")

    corpo.append(
        f"Foram encontradas {len(ofertas)} "
        "oferta(s) nova(s) ou queda(s) de preço."
    )

    corpo.append("")

    corpo.append("=" * 60)

    corpo.append("")


    for numero, item in enumerate(
        ofertas,
        start=1
    ):

        if (
            item.get("tipo_alerta")
            == "QUEDA_PRECO"
        ):

            corpo.append(
                f"📉 {numero}. PREÇO CAIU!"
            )

        else:

            corpo.append(
                f"🔥 {numero}. NOVA OFERTA"
            )


        corpo.append("")

        corpo.append(
            item["status"]
        )


        corpo.append(
            f"Marca: {item['marca']}"
        )


        if item["carros_top"]:

            corpo.append(
                "Carro top: "
                + ", ".join(
                    item["carros_top"]
                )
            )


        if item["tendencia"]:

            corpo.append(
                "Tendência: "
                + item["tendencia"]
            )


        corpo.append(
            f"Produto: {item['titulo']}"
        )


        if (
            item.get("tipo_alerta")
            == "QUEDA_PRECO"
        ):

            anterior = item.get(
                "preco_anterior_encontrado"
            )

            if anterior is not None:

                corpo.append(
                    f"Preço anterior encontrado: "
                    f"R$ {anterior:.2f}"
                )


        corpo.append(
            f"Preço atual: "
            f"R$ {item['preco']:.2f}"
        )


        if item["desconto"] is not None:

            corpo.append(
                f"Desconto identificado: "
                f"{item['desconto']:.1f}%"
            )


        corpo.append("")

        corpo.append(
            "Link Mercado Livre:"
        )

        corpo.append(
            item["link"]
        )

        corpo.append("")

        corpo.append(
            "-" * 60
        )

        corpo.append("")


    corpo.append(
        "Os links acima também foram salvos "
        "em links_para_afiliado.txt."
    )

    corpo.append("")

    corpo.append(
        "Abra o Gerador de Links do Mercado Livre, "
        "cole os links e gere os links de afiliado."
    )


    mensagem.set_content(
        "\n".join(corpo)
    )


    contexto = ssl.create_default_context()


    try:

        with smtplib.SMTP_SSL(
            "smtp.gmail.com",
            465,
            context=context
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
            "ERRO NA BUSCA:",
            erro
        )

        continue


    if resposta.status_code != 200:

        print(
            "ERRO:",
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


        preco = preco_rich_snippet(
            item
        )


        if preco is None:

            precos = extrair_precos_texto(
                trecho
            )

            validos = [
                preco_encontrado
                for preco_encontrado in precos
                if preco_valido(
                    marca,
                    preco_encontrado
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
                ),
            "link": link
        })


# =========================================================
# CLASSIFICAR OFERTAS
# =========================================================

ofertas = []


for item in resultados:

    preco = item["preco"]

    marca = item["marca"]

    desconto = item["desconto"]

    item["status"] = None


    # HOT WHEELS PREMIUM/SILVER < 69

    if (
        marca == "Hot Wheels"
        and preco is not None
        and preco < 69
    ):

        item["status"] = (
            "🚨 HOT WHEELS PREMIUM/SILVER "
            "ABAIXO DE R$69"
        )


    # DESCONTO >= 15%

    elif (
        desconto is not None
        and desconto >= 15
    ):

        item["status"] = (
            "🔥🔥 DESCONTO DE 15% OU MAIS"
        )


    # HOT WHEELS < 99

    elif (
        marca == "Hot Wheels"
        and preco is not None
        and preco < 99
    ):

        item["status"] = (
            "🔥 HOT WHEELS PREMIUM/SILVER "
            "ABAIXO DE R$99"
        )


    # MINI GT < 150

    elif (
        marca == "Mini GT"
        and preco is not None
        and preco < 150
    ):

        item["status"] = (
            "🔥 MINI GT ABAIXO DE R$150"
        )


    if item["status"]:

        ofertas.append(
            item
        )


# =========================================================
# VERIFICAR HISTÓRICO
# =========================================================

historico = carregar_historico()

ofertas_para_enviar = []


for item in ofertas:

    link = item["link"]

    preco = item["preco"]


    if preco is None:
        continue


    registro_anterior = historico.get(
        link
    )


    # NOVA OFERTA

    if registro_anterior is None:

        item["tipo_alerta"] = (
            "NOVA_OFERTA"
        )

        ofertas_para_enviar.append(
            item
        )

        continue


    menor_preco_anterior = (
        registro_anterior.get(
            "menor_preco"
        )
    )


    # PREÇO CAIU

    if (
        menor_preco_anterior is None
        or preco < menor_preco_anterior
    ):

        item[
            "preco_anterior_encontrado"
        ] = menor_preco_anterior


        item["tipo_alerta"] = (
            "QUEDA_PRECO"
        )


        ofertas_para_enviar.append(
            item
        )


# =========================================================
# ORDENAR
# =========================================================

ordem = {

    "🚨 HOT WHEELS PREMIUM/SILVER ABAIXO DE R$69": 0,

    "🔥🔥 DESCONTO DE 15% OU MAIS": 1,

    "🔥 HOT WHEELS PREMIUM/SILVER ABAIXO DE R$99": 2,

    "🔥 MINI GT ABAIXO DE R$150": 3
}


ofertas_para_enviar.sort(

    key=lambda x: (

        ordem.get(
            x["status"],
            99
        ),

        x["preco"]
        if x["preco"]
        else 999999
    )
)


# =========================================================
# GERAR LINKS PARA AFILIADO
# =========================================================

with open(
    ARQUIVO_LINKS_AFILIADO,
    "w",
    encoding="utf-8"
) as arquivo:

    for item in ofertas_para_enviar:

        arquivo.write(
            item["link"] + "\n"
        )


print()

print(
    "ARQUIVO GERADO:",
    ARQUIVO_LINKS_AFILIADO
)

print(
    "LINKS PARA AFILIADO:",
    len(ofertas_para_enviar)
)


# =========================================================
# ENVIAR E-MAIL
# =========================================================

email_enviado = True


if ofertas_para_enviar:

    email_enviado = enviar_email(
        ofertas_para_enviar
    )


# =========================================================
# SÓ GRAVA NO HISTÓRICO SE O E-MAIL FOI ENVIADO
# =========================================================

if email_enviado:

    for item in ofertas_para_enviar:

        historico[
            item["link"]
        ] = {

            "menor_preco":
                item["preco"],

            "titulo":
                item["titulo"],

            "marca":
                item["marca"]
        }


    salvar_historico(
        historico
    )


else:

    print(
        "ATENÇÃO: o histórico NÃO foi atualizado "
        "porque o e-mail falhou."
    )

    print(
        "A oferta será tentada novamente "
        "na próxima execução."
    )


# =========================================================
# RESULTADO NO GITHUB
# =========================================================

print()

print(
    "=" * 80
)

print(
    "NOVAS OFERTAS / QUEDAS DE PREÇO:",
    len(ofertas_para_enviar)
)

print(
    "=" * 80
)

print()


for item in ofertas_para_enviar:


    if (
        item.get("tipo_alerta")
        == "QUEDA_PRECO"
    ):

        print(
            "📉📉 PREÇO CAIU NOVAMENTE!"
        )


        anterior = item.get(
            "preco_anterior_encontrado"
        )


        if anterior is not None:

            print(
                f"ANTES: "
                f"R$ {anterior:.2f}"
            )


            print(
                f"AGORA: "
                f"R$ {item['preco']:.2f}"
            )


    else:

        print(
            "🆕 NOVA OFERTA"
        )


    print(
        item["status"]
    )


    print(
        "MARCA:",
        item["marca"]
    )


    print(
        "TITULO:",
        item["titulo"]
    )


    print(
        f"PRECO: "
        f"R$ {item['preco']:.2f}"
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


if not ofertas_para_enviar:

    print(
        "Nenhuma oferta nova encontrada."
    )

    print(
        "Nenhum e-mail foi enviado."
    )
