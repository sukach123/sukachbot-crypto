from flask import Flask
import os
import time
import random
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

# ✅ Função Fibonacci
def calcular_fibonacci_tp_sl(velas, direcao="compra"):
    if len(velas) < 5:
        return None

    # Extrair as últimas 5 velas
    ultimas = velas[-5:]

    swing_high = max(ultimas, key=lambda x: x['high'])['high']
    swing_low = min(ultimas, key=lambda x: x['low'])['low']

    if direcao == "compra":
        fib_618 = swing_high - (swing_high - swing_low) * 0.618
        tp1 = swing_high + (swing_high - swing_low) * 1.272
        tp2 = swing_high + (swing_high - swing_low) * 1.618
        sl = fib_618
    else:
        fib_618 = swing_low + (swing_high - swing_low) * 0.618
        tp1 = swing_low - (swing_high - swing_low) * 1.272
        tp2 = swing_low - (swing_high - swing_low) * 1.618
        sl = fib_618

    return {
        "tp_1.272": round(tp1, 3),
        "tp_1.618": round(tp2, 3),
        "sl_fib_0.618": round(sl, 3),
        "swing_high": swing_high,
        "swing_low": swing_low
    }

# Lista de pares monitorados
pares = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "MATICUSDT",
    "AVAXUSDT", "LINKUSDT", "TONUSDT", "FETUSDT", "ADAUSDT",
    "RNDRUSDT", "SHIBUSDT"
]

def monitorar_mercado():
    while True:
        try:
            par = random.choice(pares)
            print(f"🔍 Verificando oportunidade em {par}")

            velas_raw = session.get_kline(
                category="linear",
                symbol=par,
                interval="1",
                limit=20
            )["result"]["list"]

            velas = []
            for v in velas_raw:
                velas.append({
                    "timestamp": v[0],
                    "open": float(v[1]),
                    "high": float(v[2]),
                    "low": float(v[3]),
                    "close": float(v[4]),
                    "volume": float(v[5])
                })

            ultima = velas[-1]
            preco_abertura = ultima["open"]
            preco_fechamento = ultima["close"]
            volume = ultima["volume"]

            if preco_fechamento > preco_abertura and volume > 1000:
                print(f"✅ Sinal de COMPRA detectado em {par}")

                preco_atual = preco_fechamento
                usdt_alvo = 5
                alavancagem = 4
                qty = round((usdt_alvo * alavancagem) / preco_atual, 3)

                fib = calcular_fibonacci_tp_sl(velas, direcao="compra")

                if not fib:
                    print("❌ Não foi possível calcular Fibonacci. Pulando.")
                    time.sleep(1)
                    continue

                take_profit = fib["tp_1.272"]
                stop_loss = fib["sl_fib_0.618"]

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

                print(f"🚀 Ordem enviada: {par}, qty: {qty}, TP: {take_profit}, SL: {stop_loss}, alavancagem: {alavancagem}x")

            time.sleep(1)

        except Exception as e:
            print(f"⚠️ Erro ao analisar {par}: {str(e)}")
            time.sleep(2)

if __name__ == "__main__":
    threading.Thread(target=monitorar_mercado).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
