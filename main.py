import os
import time
import threading
import requests
from flask import Flask
from pybit.unified_trading import HTTP

# --- Flask app ---
app = Flask(__name__)

# --- BYBIT API ---
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
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            print("Erro ao enviar mensagem para Telegram:", response.text)
    except Exception as e:
        print("Exceção ao enviar mensagem:", e)

# --- Função para testar ordem (exemplo simplificado) ---
def executar_ordem_exemplo():
    par = "BTCUSDT"
    direcao = "Buy"
    quantidade = 0.001
    tp = 3  # % lucro
    sl = 1.5  # % perda

    try:
        preco_entrada = session.get_ticker(category="linear", symbol=par)["result"]["list"][0]["lastPrice"]
        preco_entrada = float(preco_entrada)
        take_profit = round(preco_entrada * (1 + tp / 100), 4)
        stop_loss = round(preco_entrada * (1 - sl / 100), 4)

        session.place_order(
            category="linear",
            symbol=par,
            side=direcao,
            order_type="Market",
            qty=quantidade,
            take_profit=take_profit,
            stop_loss=stop_loss,
            time_in_force="GoodTillCancel",
            reduce_only=False
        )

        mensagem = (
            f"\ud83d\ude80 *ENTRADA EXECUTADA*\n"
            f"Par: {par}\n"
            f"Direção: {direcao}\n"
            f"Entrada: {preco_entrada}\n"
            f"TP: {take_profit}\n"
            f"SL: {stop_loss}\n"
            f"Alavancagem: 10x"
        )
        enviar_telegram_mensagem(mensagem)

    except Exception as e:
        print("Erro ao executar ordem:", e)

# --- Thread para simular operação ---
def loop_principal():
    while True:
        print("[Bot ativo] Verificando oportunidades...")
        time.sleep(60)

# --- Início do bot em thread separada ---
th = threading.Thread(target=loop_principal)
th.daemon = True
th.start()

# --- Rota principal do Flask ---
@app.route("/")
def home():
    return "SukachBot está online!"

# --- Roda o servidor Flask ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
