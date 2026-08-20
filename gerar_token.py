import os
import requests

client_id = os.getenv("ML_CLIENT_ID")
client_secret = os.getenv("ML_CLIENT_SECRET")
auth_code = os.getenv("ML_AUTH_CODE")

url = "https://api.mercadolibre.com/oauth/token"

dados = {
    "grant_type": "authorization_code",
    "client_id": client_id,
    "client_secret": client_secret,
    "code": auth_code,
    "redirect_uri": "https://github.com/leosailer/mercado-livre-ofertas"
}

resposta = requests.post(url, data=dados, timeout=30)

print("STATUS:", resposta.status_code)
print(resposta.text)
