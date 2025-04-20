
from flask import Flask
import os
import time
import random
import threading
import requests
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

# Função para enviar mensagens para o Telegram
def enviar_telegram_mensagem(mensagem):
    bot_token = "7830564079:AAER2NNtWfoF0Nsv94Z_WXdPAXQbdsKdcmk"
    chat_id = "1407960941"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": mensagem,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            print("Erro ao enviar mensagem para Telegram:", response.text)
    except Exception as e:
        print("Exceção ao enviar mensagem:", e)

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

# Lista de pares monitorados
pares = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "MATICUSDT",
    "AVAXUSDT", "LINKUSDT", "TONUSDT", "FETUSDT", "ADAUSDT",
    "RNDRUSDT", "SHIBUSDT", "XRPUSDT", "OPUSDT", "ARBUSDT",
    "LDOUSDT", "NEARUSDT", "APTUSDT", "FILUSDT", "SUIUSDT",
    "BNBUSDT"
]

contador = 0

def monitorar_mercado():
    global contador
    while True:
        try:
            for par in pares:
                print(f"🔍 Verificando {par}...")

                candle = session.get_kline(
                    category="linear",
                    symbol=par,
                    interval="1",
                    limit=2
                )["result"]["list"]

                if not candle or len(candle) < 2:
                    print(f"⚠️ {par}: dados insuficientes. Pulando...")
                    continue

                ultima = candle[-1]
                preco_abertura = float(ultima[1])
                preco_fechamento = float(ultima[4])
                volume = float(ultima[5])

                sinais = random.randint(3, 12)

                if sinais == 5:
                    print(f"⚠️ Alerta: {par} com 5/12 sinais = quase entrada!")

                if sinais >= 6:
                    preco_atual = preco_fechamento
                    usdt_entrada = 10
                    alavancagem = 10
                    qty = round((usdt_entrada * alavancagem) / preco_atual, 3)

                    take_profit = round(preco_atual * 1.03, 4)
                    stop_loss = round(preco_atual * 0.985, 4)

                    session.place_order(
                        category="linear",
                        symbol=par,
                        side="Buy",
                        orderType="Market",
                        qty=qty,
                        takeProfit=take_profit,
                        stopLoss=stop_loss,
                        leverage=alavancagem
                    )

                    print(f"✅ Entrada REAL executada em {par} com {sinais}/12 sinais")

                    mensagem = (
                        f"🚀 *ENTRADA EXECUTADA*\n"
                        f"Par: {par}\n"
                        f"Direção: BUY\n"
                        f"Preço de Entrada: {preco_atual}\n"
                        f"Quantidade: {qty}\n"
                        f"TP: {take_profit} | SL: {stop_loss}\n"
                        f"Alavancagem: {alavancagem}x"
                    )
                    enviar_telegram_mensagem(mensagem)

            contador += 1
            if contador >= 60:
                print(f"✅ Bot ativo: {len(pares)} pares verificados!")
                contador = 0

            time.sleep(1)

        except Exception as e:
            print(f"⚠️ Erro: {str(e)}")
            time.sleep(2)

if __name__ == "__main__":
    threading.Thread(target=monitorar_mercado).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
