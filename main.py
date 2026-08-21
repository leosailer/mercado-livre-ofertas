import re
import json
import requests


# =========================================================
# TESTE DIRETO - MERCADO LIVRE
# =========================================================

URL = (
    "https://lista.mercadolivre.com.br/"
    "hot-wheels-car-culture"
)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/avif,"
        "image/webp,*/*;q=0.8"
    ),
}


print("=" * 80)
print("TESTE MERCADO LIVRE DIRETO")
print("=" * 80)

print()
print("Acessando:")
print(URL)
print()


try:

    resposta = requests.get(
        URL,
        headers=HEADERS,
        timeout=30
    )

except Exception as erro:

    print("ERRO DE CONEXÃO:")
    print(erro)

    raise SystemExit(1)


print("STATUS:", resposta.status_code)
print("TAMANHO HTML:", len(resposta.text))
print()


if resposta.status_code != 200:

    print("NÃO CONSEGUIMOS ACESSAR A BUSCA.")

    print()
    print(
        resposta.text[:1000]
    )

    raise SystemExit(1)


html = resposta.text


# =========================================================
# TESTE 1
# VER SE REALMENTE VEIO CONTEÚDO DO MERCADO LIVRE
# =========================================================

html_lower = html.lower()


if "mercado livre" in html_lower:

    print("✅ Página do Mercado Livre carregada.")

else:

    print("⚠️ Não encontrei identificação normal da página.")


# =========================================================
# TESTE 2
# PROCURAR LINKS DE PRODUTOS
# =========================================================

links = re.findall(
    r'https://www\.mercadolivre\.com\.br/[^"\'<> ]+',
    html
)


# Limpa caracteres HTML
links_limpos = []


for link in links:

    link = (
        link
        .replace("&amp;", "&")
        .replace("\\u0026", "&")
        .replace("\\/", "/")
    )


    # Queremos páginas de produto/anúncio.
    if (
        "/p/" not in link
        and "/up/" not in link
        and "MLB-" not in link
        and "MLB" not in link
    ):
        continue


    if link not in links_limpos:

        links_limpos.append(
            link
        )


print()
print(
    "LINKS DE PRODUTOS ENCONTRADOS:",
    len(links_limpos)
)


print()
print("=" * 80)
print("PRIMEIROS LINKS")
print("=" * 80)


for numero, link in enumerate(
    links_limpos[:10],
    start=1
):

    print()
    print(numero, link)


# =========================================================
# TESTE 3
# PROCURAR TÍTULOS HOT WHEELS
# =========================================================

print()
print("=" * 80)
print("PROCURANDO HOT WHEELS NO HTML")
print("=" * 80)


ocorrencias = len(
    re.findall(
        r"hot\s*wheels",
        html,
        flags=re.IGNORECASE
    )
)


print(
    "OCORRÊNCIAS DE HOT WHEELS:",
    ocorrencias
)


# =========================================================
# TESTE 4
# PROCURAR VALORES EM R$
# =========================================================

precos = re.findall(
    r'R\$\s*[\d\.\,]+',
    html
)


precos_unicos = []


for preco in precos:

    if preco not in precos_unicos:

        precos_unicos.append(
            preco
        )


print()
print(
    "VALORES R$ ENCONTRADOS:",
    len(precos_unicos)
)


print()
print("EXEMPLOS:")


for preco in precos_unicos[:20]:

    print(preco)


# =========================================================
# TESTE 5
# TENTAR ENCONTRAR JSON EMBUTIDO
# =========================================================

print()
print("=" * 80)
print("PROCURANDO DADOS ESTRUTURADOS")
print("=" * 80)


scripts_json = re.findall(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    html,
    flags=re.IGNORECASE | re.DOTALL
)


print(
    "BLOCOS JSON-LD:",
    len(scripts_json)
)


produtos_json = []


for bloco in scripts_json:

    try:

        dados = json.loads(
            bloco.strip()
        )

    except:

        continue


    if isinstance(dados, dict):

        tipo = dados.get(
            "@type"
        )


        if tipo:

            print(
                "JSON-LD TYPE:",
                tipo
            )


        if tipo == "ItemList":

            elementos = dados.get(
                "itemListElement",
                []
            )


            for elemento in elementos:

                if not isinstance(
                    elemento,
                    dict
                ):
                    continue


                produto = elemento.get(
                    "item",
                    elemento
                )


                if isinstance(
                    produto,
                    dict
                ):

                    produtos_json.append(
                        produto
                    )


# =========================================================
# MOSTRAR PRODUTOS JSON
# =========================================================

print()
print(
    "PRODUTOS ESTRUTURADOS ENCONTRADOS:",
    len(produtos_json)
)


print()
print("=" * 80)
print("PRODUTOS")
print("=" * 80)


for numero, produto in enumerate(
    produtos_json[:10],
    start=1
):

    print()

    print(
        f"PRODUTO {numero}"
    )

    print(
        "NOME:",
        produto.get("name")
    )

    print(
        "URL:",
        produto.get("url")
    )


    offers = produto.get(
        "offers",
        {}
    )


    if isinstance(
        offers,
        dict
    ):

        print(
            "PREÇO:",
            offers.get("price")
        )

        print(
            "MOEDA:",
            offers.get("priceCurrency")
        )


    print("-" * 80)


# =========================================================
# RESULTADO FINAL
# =========================================================

print()
print("=" * 80)
print("RESULTADO DO TESTE")
print("=" * 80)


if (
    len(links_limpos) > 0
    or len(produtos_json) > 0
):

    print()
    print(
        "🔥 SUCESSO: CONSEGUIMOS LER "
        "RESULTADOS DO MERCADO LIVRE."
    )

    print()
    print(
        "PODEMOS CONSTRUIR O BUSCADOR "
        "SEM SERPAPI."
    )


else:

    print()
    print(
        "❌ A PÁGINA ABRIU, MAS NÃO "
        "CONSEGUIMOS EXTRAIR OS PRODUTOS."
    )

    print()
    print(
        "PRECISAMOS USAR OUTRA ESTRATÉGIA."
    )
