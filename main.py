import os
import time
import threading
import requests
from flask import Flask
from pybit.unified_trading import HTTP

app = Flask(__name__)

# --- Configurações principais ---
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")
session = HTTP(api_key=BYBIT_API_KEY, api_secret=BYBIT_API_SECRET, testnet=False)

# --- Telegram ---
BOT_TOKEN = "7830564079:AAER2NNtWfoF0Nsv94Z_WXdPAXQbdsKdcmk"
CHAT_ID = "1407960941"

def enviar_telegram_mensagem(mensagem):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, data=payload)
        if r.status_code != 200:
            print("Erro ao enviar para Telegram:", r.text)
    except Exception as e:
        print("Erro Telegram:", e)

# --- Lista de pares ---
pares = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "MATICUSDT",
    "AVAXUSDT", "LINKUSDT", "TONUSDT", "FETUSDT", "ADAUSDT",
    "RNDRUSDT", "SHIBUSDT", "XRPUSDT", "NEARUSDT", "FILUSDT",
    "LDOUSDT", "OPUSDT", "ARBUSDT", "APTUSDT", "BNBUSDT",
    "SUIUSDT"
]

# --- Função principal ---
def monitorar_mercado():
    while True:
        for par in pares:
            try:
                print(f"🔍 Verificando {par}...")

                # Simula contagem de sinais alinhados (substituir por lógica real)
                sinais_alinhados = checar_sinais(par)

                if sinais_alinhados == 12:
                    preco_atual = pegar_preco_atual(par)
                    valor_usdt = 10
                    alavancagem = 10
                    quantidade = round((valor_usdt * alavancagem) / preco_atual, 3)

                    tp = round(preco_atual * 1.03, 3)
                    sl = round(preco_atual * 0.985, 3)

                    session.place_order(
                        category="linear",
                        symbol=par,
                        side="Buy",
                        orderType="Market",
                        qty=quantidade,
                        takeProfit=tp,
                        stopLoss=sl,
                        leverage=alavancagem
                    )

                    msg = (
                        f"\u2728 *ENTRADA EXECUTADA*
Par: {par}
Sinais: {sinais_alinhados}/12
Entrada: {preco_atual}
Qty: {quantidade}
TP: {tp} | SL: {sl}
Alavancagem: {alavancagem}x"
                    )
                    print(msg)
                    enviar_telegram_mensagem(msg)
                elif sinais_alinhados >= 5:
                    print(f"⚠️ Alerta: {par} com {sinais_alinhados}/12 sinais - quase entrada!")
            except Exception as e:
                print(f"Erro com {par}: {e}")

            time.sleep(0.3)  # evitar excesso de requisições

        print("\u23F3 Aguardando novo ciclo...")
        time.sleep(5)

# --- Funções auxiliares ---
def pegar_preco_atual(par):
    kline = session.get_kline(category="linear", symbol=par, interval=1, limit=1)
    return float(kline["result"]["list"][0][4])  # último preço de fechamento

def checar_sinais(par):
    # Simula os sinais (mudar para tua lógica de indicadores reais)
    import random
    return random.randint(3, 12)

# --- Rota web para verificar status ---
@app.route("/")
def home():
    return "SukachBot CRYPTO ONLINE e a operar com entradas de 12 sinais! 💼"

# --- Inicializa o bot ---
if __name__ == "__main__":
    threading.Thread(target=monitorar_mercado).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
