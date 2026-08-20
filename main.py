import requests
from bs4 import BeautifulSoup

URL = "https://lista.mercadolivre.com.br/iphone"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    )
}

resposta = requests.get(URL, headers=headers, timeout=30)

print("STATUS:", resposta.status_code)

if resposta.status_code != 200:
    print("ERRO AO ACESSAR A PAGINA")
    exit()

soup = BeautifulSoup(resposta.text, "html.parser")

produtos = soup.select("li.ui-search-layout__item")

print("\nQUANTIDADE ENCONTRADA:", len(produtos))
print("\nOFERTAS:\n")

for produto in produtos[:10]:

    titulo_elemento = produto.select_one("h2")
    link_elemento = produto.select_one("a")
    preco_elemento = produto.select_one(".andes-money-amount__fraction")

    titulo = titulo_elemento.get_text(strip=True) if titulo_elemento else "Sem titulo"
    link = link_elemento.get("href") if link_elemento else "Sem link"
    preco = preco_elemento.get_text(strip=True) if preco_elemento else "Sem preco"

    print("Produto:", titulo)
    print("Preco: R$", preco)
    print("Link:", link)
    print("-" * 60)
