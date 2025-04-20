from flask import Flask
import os
import threading
from pybit.unified_trading import HTTP

app = Flask(__name__)

# Conectar à API da Bybit com variáveis de ambiente
api_key = os.getenv("BYBIT_API_KEY")
api_secret = os.getenv("BYBIT_API_SECRET")

session = HTTP(
    api_key=api_key,
    api_secret=api_secret,
    testnet=False
)

@app.route("/")
def home():
    return "SukachBot CRYPTO online e pronto para enviar sinais! 🚀"

@app.route("/saldo")
def saldo():
    try:
        response = session.get_wallet_balance(accountType="UNIFIED")
        coins = response["result"]["list"][0]["coin"]
        output = "<h2>Saldo Atual:</h2><ul>"
        for coin in coins:
            value = coin.get("availableToWithdraw", "0")
            try:
                balance = float(value)
                if balance > 0:
                    output += f"<li>{coin['coin']}: {balance}</li>"
            except ValueError:
                continue
        output += "</ul>"
        return output or "Sem saldo disponível."
    except Exception as e:
        return f"Erro ao obter saldo: {str(e)}"

if __name__ == "__main__":
    # Iniciar o loop automático em background
    threading.Thread(target=monitorar_mercado).start()

    # Iniciar o servidor Flask
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# Lista de pares monitorados
pares = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "MATICUSDT",
    "AVAXUSDT", "LINKUSDT", "TONUSDT", "FETUSDT", "ADAUSDT",
    "RNDRUSDT", "SHIBUSDT"
]


import time
import random
import threading

def monitorar_mercado():
    while True:
        try:
            par = random.choice(pares)
            print(f"🔍 Verificando oportunidade em {par}")

            # Obter os dados das últimas velas (1 minuto)
            candle = session.get_kline(
                category="linear",
                symbol=par,
                interval="1",
                limit=2
            )["result"]["list"]

            ultima = candle[-1]
            preco_abertura = float(ultima[1])
            preco_fechamento = float(ultima[4])
            volume = float(ultima[5])

            # Lógica de entrada simples (vela verde com bom volume)
            if preco_fechamento > preco_abertura and volume > 1000:
                print(f"✅ Sinal de COMPRA detectado em {par}")

                # Enviar ordem de mercado real com 2 USDT
                session.place_order(
                    category="linear",
                    symbol=par,
                    side="Buy",
                    orderType="Market",
                    qty=2,
                    leverage=2
                )

                print(f"🚀 Ordem enviada: {par}, valor: 2 USDT, alavancagem: 2x")

            time.sleep(1)

        except Exception as e:
            print(f"⚠️ Erro ao analisar {par}: {str(e)}")
            time.sleep(2)

# Iniciar o loop automático em background
threading.Thread(target=monitorar_mercado).start()
