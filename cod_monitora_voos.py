
import os
import requests
from datetime import date, timedelta, datetime
from email.message import EmailMessage
import smtplib
import time

# ===============================
# CONFIGURAÇÕES DO USUÁRIO
# ===============================

AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY")
AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET")

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

EMAIL_FROM = EMAIL_USER
EMAIL_TO = ["leosarkisj@gmail.com"]  # adicione outros e-mails se quiser

ORIGENS = ["GRU"]          # Apenas Guarulhos
DESTINO = "FCO"            # Roma Fiumicino

DUR_MIN = 9
DUR_MAX = 11

ANO = date.today().year
MESES = [9]                # Apenas setembro

MAX_RESULTS = 10
TIME_BUDGET_SECONDS = 240

CARRIER_NAME_FALLBACK = {
    "AZ": "ITA Airways",
    "TP": "TAP Air Portugal",
    "AF": "Air France",
    "KL": "KLM",
    "IB": "Iberia",
    "LH": "Lufthansa",
    "LX": "SWISS",
    "TK": "Turkish Airlines",
    "UA": "United Airlines",
    "BA": "British Airways",
    "AA": "American Airlines",
    "DL": "Delta Air Lines",
    "QR": "Qatar Airways",
    "EK": "Emirates",
    "EY": "Etihad Airways"
}

# ===============================
# 1) TOKEN OAUTH2 (AMADEUS)
# ===============================

def obter_access_token():
    url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "client_id": AMADEUS_API_KEY,
        "client_secret": AMADEUS_API_SECRET
    }
    # REMOVIDO TIMEOUT
    resp = requests.post(url, headers=headers, data=data)
    resp.raise_for_status()
    return resp.json()["access_token"]

# ===============================
# 2) BUSCAR OFERTAS
# ===============================

def buscar_ofertas(access_token, origem, destino, ida, volta):
    url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "originLocationCode": origem,
        "destinationLocationCode": destino,
        "departureDate": ida.strftime("%Y-%m-%d"),
        "returnDate": volta.strftime("%Y-%m-%d"),
        "adults": 1,
        "currencyCode": "BRL",
        "max": MAX_RESULTS
    }

    # REMOVIDO TIMEOUT
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code != 200:
        print(f"[WARN] {origem}->{destino} {ida} {volta} status={resp.status_code}")
        return None

    payload = resp.json()
    data = payload.get("data", [])
    if not data:
        return None

    melhor = min(data, key=lambda x: float(x["price"]["grandTotal"]))
    preco = float(melhor["price"]["grandTotal"])

    itineraries = melhor.get("itineraries", [])
    if not itineraries:
        return None

    ida_itin = itineraries[0]
    volta_itin = itineraries[1] if len(itineraries) > 1 else itineraries[0]

    ida_segs = ida_itin.get("segments", [])
    volta_segs = volta_itin.get("segments", [])

    # 🔥 MANTER APENAS VOOS DIRETOS
    if len(ida_segs) != 1 or len(volta_segs) != 1:
        return None

    origem_airport_ida = ida_segs[0]["departure"]["iataCode"]
    destino_airport_ida = ida_segs[-1]["arrival"]["iataCode"]

    origem_airport_volta = volta_segs[0]["departure"]["iataCode"]
    destino_airport_volta = volta_segs[-1]["arrival"]["iataCode"]

    ida_data_real = ida_segs[0]["departure"]["at"][:10]
    volta_data_real = volta_segs[-1]["arrival"]["at"][:10]

    dictionaries = payload.get("dictionaries", {}) or {}
    carriers_dict = dictionaries.get("carriers", {}) or {}

    carriers_codes = set()
    for s in ida_segs + volta_segs:
        code = s.get("carrierCode") or s.get("marketingCarrierCode")
        if code:
            carriers_codes.add(code)

    carriers_list = []
    for code in sorted(carriers_codes):
        nome = carriers_dict.get(code) or CARRIER_NAME_FALLBACK.get(code) or "Companhia desconhecida"
        carriers_list.append(f"{nome} ({code})")

    google_link = f"https://www.google.com/flights?hl=pt-BR#flt={origem}.{destino}.{ida_data_real}*{destino}.{origem}.{volta_data_real}"
    skyscanner_link = f"https://www.skyscanner.com/transport/flights/{origem}/{destino}/{ida_data_real}/{volta_data_real}/"
    kiwi_link = f"https://www.kiwi.com/br/search/results/{origem}-{ida_data_real}/{destino}-{volta_data_real}"

    return {
        "preco": preco,
        "ida": ida_data_real,
        "volta": volta_data_real,
        "origem": origem,
        "destino": destino,
        "cia_list": carriers_list,
        "airports": {
            "ida": {"partida": origem_airport_ida, "chegada": destino_airport_ida},
            "volta": {"partida": origem_airport_volta, "chegada": destino_airport_volta}
        },
        "links": {
            "google": google_link,
            "skyscanner": skyscanner_link,
            "kiwi": kiwi_link
        }
    }

# ===============================
# 3) COMPARAR COMBINAÇÕES (SETEMBRO + GRU)
# ===============================

def encontrar_melhor_voo(access_token):
    melhor_global = None
    start_ts = time.time()

    for mes in MESES:          
        for dia in range(1, 29):
            ida = date(ANO, mes, dia)

            for dur in range(DUR_MIN, DUR_MAX + 1):
                volta = ida + timedelta(days=dur)

                for origem in ORIGENS:
                    if time.time() - start_ts > TIME_BUDGET_SECONDS:
                        print("[INFO] Time budget atingido. Encerrando busca com o melhor atual.")
                        return melhor_global

                    print(f"[INFO] Consultando {origem}->{DESTINO} | ida {ida} volta {volta} ...")
                    resultado = buscar_ofertas(access_token, origem, DESTINO, ida, volta)

                    if not resultado:
                        continue

                    if (melhor_global is None) or (resultado["preco"] < melhor_global["preco"]):
                        melhor_global = resultado
                        print(f"[OK] Novo melhor: R$ {resultado['preco']:.2f} | {resultado['ida']} - {resultado['volta']} | cias={', '.join(resultado['cia_list'])}")

    return melhor_global

# ===============================
# 4) ENVIO DE E-MAIL COMPLETO
# ===============================

def enviar_email(resultado):
    msg = EmailMessage()
    msg["Subject"] = "💸 Melhor Preço GRU ⇄ Roma (9–11 dias, setembro) – Amadeus API"
    msg["From"] = EMAIL_FROM
    msg["To"] = ", ".join(EMAIL_TO)

    agora = datetime.now().strftime("%d/%m/%Y %H:%M")

    if resultado is None:
        corpo = f"""
Olá,

Nenhum voo direto encontrado dentro dos critérios.
Origem: GRU → Destino: FCO
Janela analisada: setembro/{ANO}
Permanência: {DUR_MIN}–{DUR_MAX} dias

Execução: {agora}
"""
    else:
        dur = (datetime.fromisoformat(resultado["volta"]) - datetime.fromisoformat(resultado["ida"])).days
        cia_str = ", ".join(resultado["cia_list"]) if resultado["cia_list"] else "—"
        ida_airports = resultado["airports"]["ida"]
        volta_airports = resultado["airports"]["volta"]

        corpo = f"""
MELHOR OPÇÃO ENCONTRADA – AMADEUS API (VOO DIRETO)

🛫 Origem (cidade/airport): {resultado["origem"]} → {ida_airports["partida"]}
🛬 Destino (cidade/airport): {resultado["destino"]} → {ida_airports["chegada"]}

➡️ Ida:   {resultado["ida"]}
⬅️ Volta: {resultado["volta"]}
🕒 Duração: {dur} dias

✈️ Companhia(s): {cia_str}
💰 Preço total: R$ {resultado["preco"]:.2f}

🔗 Links úteis para buscar e comprar:
• Google Flights: {resultado["links"]["google"]}
• Skyscanner:    {resultado["links"]["skyscanner"]}
• Kiwi.com:      {resultado["links"]["kiwi"]}

Observações:
• Filtrados apenas voos 100% diretos (sem conexões).
• Preços mudam rapidamente.

Execução: {agora}
"""

    msg.set_content(corpo)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_USER, EMAIL_PASS)
        smtp.send_message(msg)

    print("Email enviado com sucesso!")

# ===============================
# MAIN
# ===============================

if __name__ == "__main__":
    if not AMADEUS_API_KEY or not AMADEUS_API_SECRET:
        raise Exception("Defina AMADEUS_API_KEY e AMADEUS_API_SECRET nos secrets/ambiente.")
    if not EMAIL_USER or not EMAIL_PASS:
        raise Exception("Defina EMAIL_USER e EMAIL_PASS nos secrets/ambiente.")

    print("Obtendo access token...")
    token = obter_access_token()

    print("Buscando o melhor voo direto (Setembro + GRU → FCO)…")
    melhor_voo = encontrar_melhor_voo(token)

    print("Enviando e-mail…")
    enviar_email(melhor_voo)

    print("Finalizado.")
