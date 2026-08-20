import requests

URL = "https://lista.mercadolivre.com.br/iphone"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    )
}

resposta = requests.get(
    URL,
    headers=headers,
    timeout=30
)

print("STATUS:", resposta.status_code)
print("TAMANHO DA PAGINA:", len(resposta.text))

if resposta.status_code == 200:
    print("PAGINA ACESSADA COM SUCESSO")
else:
    print("NAO FOI POSSIVEL ACESSAR")
