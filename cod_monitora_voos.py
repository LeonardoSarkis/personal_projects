
import os
import requests
from datetime import date, timedelta, datetime
from email.message import EmailMessage
import smtplib

# ===============================
# CONFIGURAÇÕES DO USUÁRIO
# ===============================

AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY")
AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET")

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

EMAIL_FROM = EMAIL_USER
EMAIL_TO = ["leosarkisj@gmail.com"]  # coloque mais e-mails se quiser

ORIGENS = ["GRU", "CGH"]
DESTINO = "FCO"

DUR_MIN = 9
DUR_MAX = 11

ANO = date.today().year
MESES = [9, 10, 11]  # setembro, outubro, novembro

# ===============================
# FUNÇÃO PARA OBTER ACCESS TOKEN
# ===============================

def obter_access_token():
    url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "client_id": AMADEUS_API_KEY,
        "client_secret": AMADEUS_API_SECRET
    }

    resp = requests.post(url, headers=headers, data=data)
    resp.raise_for_status()
    return resp.json()["access_token"]

# ===============================
# BUSCA DE VOO NA AMADEUS
# ===============================

def buscar_ofertas(access_token, origem, destino, ida, volta):
    url = "https://test.api.amadeus.com/v2/shopping/flight-offers"

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    params = {
        "originLocationCode": origem,
        "destinationLocationCode": destino,
        "departureDate": ida.strftime("%Y-%m-%d"),
        "returnDate": volta.strftime("%Y-%m-%d"),
        "adults": 1,
        "currencyCode": "BRL",
        "max": 20
    }

    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code != 200:
        return None

    data = resp.json().get("data", [])
    if not data:
        return None

    # Ordena pelo menor preço total
    melhor = sorted(data, key=lambda x: float(x["price"]["grandTotal"]))[0]

    return {
        "preco": float(melhor["price"]["grandTotal"]),
        "ida": ida.strftime("%Y-%m-%d"),
        "volta": volta.strftime("%Y-%m-%d"),
        "origem": origem,
        "destino": destino
    }


# ===============================
# ROTINA PARA ACHAR O MELHOR COMBO
# ===============================

def encontrar_melhor_voo(access_token):
    melhor_global = None

    for mes in MESES:
        for dia in range(1, 29):  # evita datas inválidas
            try:
                ida = date(ANO, mes, dia)
            except:
                continue

            for dur in range(DUR_MIN, DUR_MAX + 1):
                volta = ida + timedelta(days=dur)

                for origem in ORIGENS:
                    resultado = buscar_ofertas(access_token, origem, DESTINO, ida, volta)

                    if not resultado:
                        continue

                    if (melhor_global is None) or (resultado["preco"] < melhor_global["preco"]):
                        melhor_global = resultado

    return melhor_global

# ===============================
# ENVIO DE E-MAIL
# ===============================

def enviar_email(resultado):
    msg = EmailMessage()
    msg["Subject"] = "🔔 Melhor Preço SP ⇄ Roma Encontrado (Amadeus API)"
    msg["From"] = EMAIL_FROM
    msg["To"] = ", ".join(EMAIL_TO)

    agora = datetime.now().strftime("%d/%m/%Y %H:%M")

    if resultado is None:
        corpo = f"""
Nenhum voo encontrado dentro dos critérios.

Execução: {agora}
"""
    else:
        corpo = f"""
MELHOR OPÇÃO ENCONTRADA – AMADEUS API

Origem: {resultado["origem"]}
Destino: {resultado["destino"]}

Ida: {resultado["ida"]}
Volta: {resultado["volta"]}

Duração: {(datetime.fromisoformat(resultado["volta"]) - datetime.fromisoformat(resultado["ida"])).days} dias
Preço total: R$ {resultado["preco"]:.2f}

Execução: {agora}
"""

    msg.set_content(corpo)

