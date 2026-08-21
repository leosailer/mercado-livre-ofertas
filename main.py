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
# MARCAS DE DIECAST ACEITAS
# =========================================================

MARCAS_DIECAST = [
    "Hot Wheels",
    "Mini GT",
    "Kaido House",
    "Tarmac Works",
    "Pop Race",
    "Inno64",
    "Matchbox",
    "Majorette",
    "Greenlight",
    "M2 Machines",
    "Tomica"
]


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
# BUSCAS
#
# IMPORTANTE:
# Não usamos mais números como "R$ 59" no termo da busca.
# Isso fazia o Google casar com PARCELAS.
# =========================================================

BUSCAS = [

    # HOT WHEELS PREMIUM
    '"Hot Wheels Premium" '
    '(Ferrari OR Porsche OR Lamborghini OR McLaren OR BMW OR '
    'Mercedes OR Audi OR Skyline OR Supra OR RX-7)',

    # SILVER / CAR CULTURE / BOULEVARD
    '("Hot Wheels Silver Series" OR '
    '"Hot Wheels Car Culture" OR '
    '"Hot Wheels Boulevard" OR '
    '"Hot Wheels Pop Culture") '
    '(Ferrari OR Porsche OR Skyline OR Supra OR RX-7 OR Lamborghini)',

    # FERRARI E PORSCHE
    '("Hot Wheels Premium" OR "Hot Wheels Car Culture") '
    '(Ferrari OR Porsche)',

    # MINI GT
    '"Mini GT" '
    '(Ferrari OR Porsche OR Lamborghini OR McLaren OR '
    'Skyline OR GT-R OR Supra OR RX-7 OR BMW)',

    # KAIDO
    '"Kaido House" '
    '(Skyline OR Nissan OR Honda OR Datsun)',

    # TARMAC / POP RACE / INNO
    '("Tarmac Works" OR "Pop Race" OR Inno64) '
    '(Ferrari OR Porsche OR Skyline OR Supra OR '
    'RX-7 OR Koenigsegg OR McLaren)',

    # OUTRAS PREMIUM
    '("Majorette Premium" OR "Tomica Premium" OR '
    'Greenlight OR "M2 Machines" OR '
    '"Matchbox Collectors" OR "Matchbox Moving Parts") '
    '(Ferrari OR Porsche OR Lamborghini OR Skyline OR '
    'Supra OR BMW OR Mustang)',

    # MODELOS QUENTES / 2026
    '("Hot Wheels Premium" OR "Mini GT" OR "Tarmac Works") '
    '("Ferrari F40" OR "Ferrari Testarossa" OR '
    '"Porsche 911 GT3" OR "Skyline R32" OR '
    '"Skyline R34" OR "Mazda RX-7" OR Koenigsegg)'
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
    "damaged",
    "refurbished",
    "recondicionado",
    "expositor",
    "display para",
    "diorama",
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
    "importado",
    "importação",
    "importacao",
    "taxa de importação",
    "taxas de importação",
    "import fees",
    "enviado do exterior",
    "envio do exterior",
    "enviado dos estados unidos",
    "envio dos estados unidos",
    "ships from china",
    "envio da china"
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
    "anniversary",
    "aniversário",
    "aniversario",
    "edição especial",
    "edicao especial"
]


# =========================================================
# FAIXAS PLAUSÍVEIS
#
# Não determinam se é oferta.
# Só bloqueiam preço obviamente impossível.
# =========================================================

FAIXAS_VALIDAS = {
    "Hot Wheels": (35, 600),
    "Mini GT": (65, 500),
    "Kaido House": (100, 600),
    "Tarmac Works": (80, 600),
    "Pop Race": (80, 600),
    "Inno64": (80, 600),
    "Matchbox": (25, 400),
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
        "amazon" in texto
        or "amazon.com.br" in texto
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
# CARROS TOP
# =========================================================

def identificar_carros_top(titulo):

    texto = normalizar(titulo)

    encontrados = []

    for carro in CARROS_TOP:

        if normalizar(carro) in texto:
            encontrados.append(carro)

    return encontrados


# =========================================================
# ESCALA
# =========================================================

def escala_valida(titulo, snippet):

    texto = normalizar(
        f"{titulo} {snippet}"
    )

    # bloqueia explicitamente escalas erradas
    for escala in ESCALAS_PROIBIDAS:

        if escala in texto:
            return False

    # se existir escala explícita, ela precisa ser 1:64
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
# NOVO / NÃO INTERNACIONAL
# =========================================================

def produto_valido(
    titulo,
    snippet,
    extensions,
    condition,
    delivery
):

    combinado = normalizar(
        " ".join([
            titulo or "",
            snippet or "",
            " ".join(
                str(x)
                for x in (extensions or [])
            ),
            condition or "",
            delivery or ""
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
# HOT WHEELS
# =========================================================

def hot_wheels_valido(titulo):

    texto = normalizar(titulo)

    if "hot wheels" not in texto:
        return True

    return any(
        termo in texto
        for termo in HOT_WHEELS_PERMITIDOS
    )


# =========================================================
# PREÇO
#
# AQUI ESTÁ A PRINCIPAL CORREÇÃO.
#
# extracted_price = preço do produto
# installment = parcela
#
# NÃO usamos installment.
# =========================================================

def obter_preco_shopping(item, marca):

    preco = item.get(
        "extracted_price"
    )


    # Sem preço estruturado = descarta
    if preco is None:
        return None


    try:

        preco = float(preco)

    except:
        return None


    # Campo textual deve estar em Real
    preco_texto = str(
        item.get(
            "price",
            ""
        )
    )


    if preco_texto:

        texto = preco_texto.upper()

        if (
            "R$" not in texto
            and "BRL" not in texto
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
    # NÃO FAZEMOS NADA COM:
    #
    # item["installment"]
    #
    # Ela existe, mas é ignorada propositalmente.
    # =====================================================

    return preco


# =========================================================
# PREÇO ANTIGO / DESCONTO REAL
# =========================================================

def calcular_desconto_real(
    item,
    preco_atual
):

    antigo = item.get(
        "extracted_old_price"
    )


    if antigo is None:
        return None, None


    try:

        antigo = float(
            antigo
        )

    except:
        return None, None


    if antigo <= preco_atual:
        return None, None


    # evita dados absurdos
    if antigo > preco_atual * 3:
        return None, None


    desconto = (
        (
            antigo
            - preco_atual
        )
        / antigo
    ) * 100


    if not (
        1
        <= desconto
        <= 80
    ):
        return None, None


    return (
        antigo,
        desconto
    )


# =========================================================
# RANKING
# =========================================================

def classificar(
    marca,
    preco,
    desconto
):

    # =====================================================
    # HOT WHEELS
    # =====================================================

    if (
        marca == "Hot Wheels"
        and preco < 69
    ):

        return (
            "🚨 IMPERDÍVEL",
            0,
            "HOT WHEELS PREMIUM/SILVER ABAIXO DE R$69"
        )


    if (
        marca == "Hot Wheels"
        and preco < 89
    ):

        return (
            "🔥 BOA OFERTA",
            1,
            "HOT WHEELS PREMIUM/SILVER ABAIXO DE R$89"
        )


    if (
        marca == "Hot Wheels"
        and preco < 99
    ):

        return (
            "👀 INTERESSANTE",
            2,
            "HOT WHEELS PREMIUM/SILVER ABAIXO DE R$99"
        )


    # =====================================================
    # MINI GT
    # =====================================================

    if (
        marca == "Mini GT"
        and preco < 110
    ):

        return (
            "🚨 IMPERDÍVEL",
            0,
            "MINI GT ABAIXO DE R$110"
        )


    if (
        marca == "Mini GT"
        and preco < 130
    ):

        return (
            "🔥 BOA OFERTA",
            1,
            "MINI GT ABAIXO DE R$130"
        )


    if (
        marca == "Mini GT"
        and preco < 150
    ):

        return (
            "👀 INTERESSANTE",
            2,
            "MINI GT ABAIXO DE R$150"
        )


    # =====================================================
    # QUALQUER MARCA COM DESCONTO REAL
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
# RESULTADOS
# =========================================================

resultados = []

chaves_vistas = set()

total_shopping = 0
rejeitados_loja = 0
rejeitados_marca = 0
rejeitados_escala = 0
rejeitados_condicao = 0
rejeitados_preco = 0


# =========================================================
# EXECUTAR BUSCAS
#
# Usamos engine=google porque os blocos inline Shopping
# trazem LINK DIRETO + extracted_price.
# =========================================================

for numero, termo in enumerate(
    BUSCAS,
    start=1
):

    print(
        f"Executando busca Shopping "
        f"{numero}/{len(BUSCAS)}..."
    )


    parametros = {
        "engine": "google",
        "q": termo,
        "hl": "pt-br",
        "gl": "br",
        "location": "Brazil",
        "num": 100,
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
            "ERRO NA BUSCA:",
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
        "Resultados Shopping estruturados:",
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

        link = item.get(
            "link",
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

        condition = item.get(
            "second_hand_condition",
            ""
        )

        delivery = (
            item.get(
                "delivery",
                ""
            )
            or item.get(
                "shipping",
                ""
            )
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
        # MARCA
        # =================================================

        marca = identificar_marca(
            titulo
        )


        if marca is None:

            rejeitados_marca += 1
            continue


        # =================================================
        # HOT WHEELS SÓ PREMIUM / ESPECIAIS
        # =================================================

        if not hot_wheels_valido(
            titulo
        ):
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
        # NOVO / NÃO INTERNACIONAL
        # =================================================

        if not produto_valido(
            titulo,
            snippet,
            extensions,
            condition,
            delivery
        ):

            rejeitados_condicao += 1
            continue


        # =================================================
        # PREÇO TOTAL
        #
        # NÃO USA installment.
        # =================================================

        preco = obter_preco_shopping(
            item,
            marca
        )


        if preco is None:

            rejeitados_preco += 1
            continue


        # =================================================
        # PREÇO ANTIGO / DESCONTO REAL
        # =================================================

        preco_antigo, desconto = (
            calcular_desconto_real(
                item,
                preco
            )
        )


        # =================================================
        # CLASSIFICA
        # =================================================

        classificacao = classificar(
            marca,
            preco,
            desconto
        )


        if classificacao is None:
            continue


        ranking, ranking_ordem, status = (
            classificacao
        )


        # =================================================
        # ID PARA ELIMINAR REPETIDOS
        # =================================================

        chave = normalizar(
            f"{loja}|{titulo}|{preco}"
        )


        if chave in chaves_vistas:
            continue


        chaves_vistas.add(
            chave
        )


        resultados.append({
            "titulo": titulo,
            "link": link,
            "loja": loja,
            "source": source,
            "marca": marca,
            "preco": preco,
            "preco_antigo":
                preco_antigo,
            "desconto":
                desconto,
            "ranking":
                ranking,
            "ranking_ordem":
                ranking_ordem,
            "status":
                status,
            "carros_top":
                identificar_carros_top(
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

    # Preferimos usar o link.
    # Se eventualmente Shopping não fornecer,
    # usa loja + título como identificador.
    chave_historico = (
        item["link"]
        if item["link"]
        else normalizar(
            f"{item['loja']}|"
            f"{item['titulo']}"
        )
    )


    item["chave_historico"] = (
        chave_historico
    )


    registro = historico.get(
        chave_historico
    )


    # NOVO PRODUTO
    if registro is None:

        item["tipo_alerta"] = (
            "NOVA_OFERTA"
        )

        para_enviar.append(
            item
        )

        continue


    # NOVO DIA:
    # reapresenta mesmo preço
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
    # só se o preço TOTAL cair
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
            and item["link"]
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

    for item in para_enviar:

        if (
            item["loja"]
            == "Amazon"
            and item["link"]
        ):

            arquivo.write(
                item["link"]
                + "\n"
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
        "IMPORTANTE:"
    )

    corpo.append(
        "Os preços abaixo vêm do campo "
        "estruturado do Google Shopping."
    )

    corpo.append(
        "Parcelas foram ignoradas."
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
                f"❌ Preço anterior: "
                f"R$ "
                f"{item['preco_antigo']:.2f}"
            )


        corpo.append(
            f"💰 PREÇO TOTAL: "
            f"R$ {item['preco']:.2f}"
        )


        if (
            item["desconto"]
            is not None
        ):

            corpo.append(
                f"🔥 DESCONTO REAL: "
                f"{item['desconto']:.0f}%"
            )


        corpo.append(
            f"🔎 Motivo: "
            f"{item['status']}"
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
            or "Link direto não disponível"
        )


        corpo.append("")

        corpo.append(
            "📲 MENSAGEM PARA WHATSAPP"
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
            or "LINK"
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

✅ Preço estruturado do Google Shopping
✅ Parcelas ignoradas
✅ Preço antigo estruturado
✅ Desconto calculado com preço antigo real
✅ Hot Wheels básicos bloqueados
✅ Escalas erradas bloqueadas
✅ Usados/loose bloqueados
✅ Mercado Livre monitorado
✅ Amazon Brasil monitorada

DADOS DA BUSCA

Resultados Shopping encontrados:
{total_shopping}

Rejeitados por loja:
{rejeitados_loja}

Rejeitados por marca:
{rejeitados_marca}

Rejeitados por escala:
{rejeitados_escala}

Rejeitados por condição/importação:
{rejeitados_condicao}

Rejeitados por preço:
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

        chave = item[
            "chave_historico"
        ]

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
        f"PREÇO TOTAL: "
        f"R$ {item['preco']:.2f}"
    )


    installment = None

    # Apenas para diagnóstico.
    # NÃO é usado como preço.
    # Mantemos escrito explicitamente
    # que parcela está sendo ignorada.

    print(
        "PARCELAMENTO: IGNORADO"
    )


    if (
        item["preco_antigo"]
        is not None
    ):

        print(
            f"PREÇO ANTIGO: "
            f"R$ "
            f"{item['preco_antigo']:.2f}"
        )


    if (
        item["desconto"]
        is not None
    ):

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
    "TOTAL SHOPPING:",
    total_shopping
)

print(
    "REJEITADOS LOJA:",
    rejeitados_loja
)

print(
    "REJEITADOS MARCA:",
    rejeitados_marca
)

print(
    "REJEITADOS ESCALA:",
    rejeitados_escala
)

print(
    "REJEITADOS CONDIÇÃO/IMPORTAÇÃO:",
    rejeitados_condicao
)

print(
    "REJEITADOS PREÇO:",
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
