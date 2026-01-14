
import requests
import smtplib
from email.message import EmailMessage
import os
from datetime import datetime, timedelta

# -------------------------------
# CONFIGURAÇÕES DO USUÁRIO
# -------------------------------

RAPID_API_KEY = os.getenv("RAPID_API_KEY")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

origens = ["GRU-sky", "CGH-sky"]
destino = "FCO-sky"  # Roma Fiumicino

# Meses a serem avaliados
meses = ["2026-09", "2026-10", "2026-11"]

# Duração permitida da viagem
duracao_min = 9
duracao_max = 11

# URL da API
url = "https://skyscanner80.p.rapidapi.com/api/v1/flights/search-live"

headers = {
    "X-RapidAPI-Key": RAPID_API_KEY,
    "X-RapidAPI-Host": "skyscanner80.p.rapidapi.com",
    "Content-Type": "application/json"
}

melhor_preco_global = None
melhor_opcao_global = None


# --------------------------------------------------
# FUNÇÃO PARA CONSULTAR PREÇOS DE IDA E VOLTA
# --------------------------------------------------
def buscar_preco(origem, destino, ida, volta):
    payload = {
        "query": {
            "market": "BR",
            "locale": "pt-BR",
            "currency": "BRL",
            "queryLegs": [
                {
                    "originPlaceId": {"entityId": origem},
                    "destinationPlaceId": {"entityId": destino},
                    "date": {"year": ida.year, "month": ida.month, "day": ida.day}
                },
                {
                    "originPlaceId": {"entityId": destino},
                    "destinationPlaceId": {"entityId": origem},
                    "date": {"year": volta.year, "month": volta.month, "day": volta.day}
                }
            ]
        }
    }

    r = requests.post(url, json=payload, headers=headers)
    data = r.json()

    # API retorna preços em itineraries
    itineraries = data.get("data", {}).get("itineraries", [])

    menor_preco = None

    for item in itineraries:
        preco = item["price"]["raw"]

        if menor_preco is None or preco < menor_preco:
            menor_preco = preco

    return menor_preco


# --------------------------------------------------
# LOOP PARA TESTAR TODAS AS COMBINAÇÕES
# --------------------------------------------------
for mes in meses:
    ano, mes_num = map(int, mes.split("-"))
    data_base = datetime(ano, mes_num, 1)

    # testa todos os dias do mês
    for dia in range(1, 29):  # até 28 para evitar problemas em meses menores
        ida = datetime(ano, mes_num, dia)

        for duracao in range(duracao_min, duracao_max + 1):
            volta = ida + timedelta(days=duracao)

            for origem in origens:
                preco = buscar_preco(origem, destino, ida, volta)

                if preco and (melhor_preco_global is None or preco < melhor_preco_global):
                    melhor_preco_global = preco
                    melhor_opcao_global = {
                        "origem": origem,
                        "destino": destino,
                        "ida": ida.strftime("%Y-%m-%d"),
                        "volta": volta.strftime("%Y-%m-%d"),
                        "duracao": duracao,
                        "preco": preco
                    }


# --------------------------------------------------
# ENVIAR E-MAIL COM O MELHOR RESULTADO
# --------------------------------------------------
msg = EmailMessage()
msg["Subject"] = "💸 Melhor Preço de Passagem SP → Roma Encontrado!"
msg["From"] = EMAIL_USER
msg["To"] = ["leosarkisj@gmail.com"]

texto = f"""
Melhor opção encontrada:

Origem: {melhor_opcao_global["origem"]}
Destino: {melhor_opcao_global["destino"]}

Data de ida: {melhor_opcao_global["ida"]}
Data de volta: {melhor_opcao_global["volta"]}

Duração: {melhor_opcao_global["duracao"]} dias
Preço total: R$ {melhor_opcao_global["preco"]}

Meses analisados: Setembro, Outubro, Novembro.
"""

msg.set_content(texto)

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
    smtp.login(EMAIL_USER, EMAIL_PASS)
    smtp.send_message(msg)

print("E-mail enviado com sucesso!")
