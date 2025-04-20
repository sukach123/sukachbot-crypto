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
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            print("Erro ao enviar para Telegram:", response.text)
    except Exception as e:
        print("Exceção ao enviar Telegram:", e)

# --- Executar ordem na Bybit ---
def executar_ordem(par="LINKUSDT", direcao="Buy"):
    try:
        # Obter preço de entrada atual
        preco_atual = float(session.get_ticker(symbol=par)["result"]["lastPrice"])
        
        # Definir valor de entrada e calcular quantidade
        valor_usdt = 10
        alavancagem = 10
        quantidade = round((valor_usdt / preco_atual) * alavancagem, 3)

        # TP e SL com base em 3% e 1.5%
        take_profit = round(preco_atual * 1.03, 4)
        stop_loss = round(preco_atual * 0.985, 4)

        # Enviar ordem à mercado com TP e SL
        resposta = session.place_order(
            category="linear",
            symbol=par,
            side=direcao,
            order_type="Market",
            qty=quantidade,
            take_profit=take_profit,
            stop_loss=stop_loss,
            time_in_force="GoodTillCancel"
        )

        print("✅ Ordem enviada:", resposta)
        
        # Enviar para Telegram
        mensagem = (
            f"🚀 *ENTRADA EXECUTADA*\n"
            f"Par: {par}\n"
            f"Direção: {direcao.upper()}\n"
            f"Preço Entrada: {preco_atual}\n"
            f"TP: {take_profit} | SL: {stop_loss}\n"
            f"Qtd: {quantidade} | Alavancagem: 10x"
        )
        enviar_telegram_mensagem(mensagem)

    except Exception as e:
        print("Erro ao executar ordem:", e)
        enviar_telegram_mensagem(f"❌ Erro ao entrar em {par}: {e}")

# --- Apenas para teste manual via servidor Flask ---
@app.route("/")
def home():
    return "SukachBot CRYPTO ativo"

@app.route("/testar")
def testar_entrada():
    threading.Thread(target=executar_ordem).start()
    return "✅ Ordem de teste enviada"

# --- Iniciar servidor (Railway ou local) ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
