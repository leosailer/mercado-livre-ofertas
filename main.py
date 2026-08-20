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
print("TAMANHO:", len(resposta.text))

if resposta.status_code != 200:
    print("ERRO AO ACESSAR")
    exit()

soup = BeautifulSoup(resposta.text, "html.parser")

links_encontrados = []

for a in soup.find_all("a", href=True):
    link = a["href"]

    if "mercadolivre.com.br" in link:
        texto = a.get_text(" ", strip=True)

        if texto and link not in [x[1] for x in links_encontrados]:
            links_encontrados.append((texto, link))

print("\nLINKS ENCONTRADOS:", len(links_encontrados))
print("\nPRIMEIROS RESULTADOS:\n")

for texto, link in links_encontrados[:20]:
    print("TEXTO:", texto[:150])
    print("LINK:", link)
    print("-" * 70)
