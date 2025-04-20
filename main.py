from flask import Flask
import os
import time
import random
import threading
from pybit.unified_trading import HTTP
import numpy as np

app = Flask(__name__)

api_key = os.getenv("BYBIT_API_KEY")
api_secret = os.getenv("BYBIT_API_SECRET")

session = HTTP(
    api_key=api_key,
    api_secret=api_secret,
    testnet=False
)

@app.route("/")
def home():
    return "SukachBot CRYPTO online com Fibonacci + RSI/EMA/MACD 🚀"

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

def calcular_fibonacci_tp_sl(velas, direcao="compra"):
    if len(velas) < 5:
        return None

    ultimas = velas[-5:]
    swing_high = max(ultimas, key=lambda x: x['high'])['high']
    swing_low = min(ultimas, key=lambda x: x['low'])['low']

    if direcao == "compra":
        fib_618 = swing_high - (swing_high - swing_low) * 0.618
        tp1 = swing_high + (swing_high - swing_low) * 1.272
        sl = fib_618
    else:
        fib_618 = swing_low + (swing_high - swing_low) * 0.618
        tp1 = swing_low - (swing_high - swing_low) * 1.272
        sl = fib_618

    return {
        "tp": round(tp1, 3),
        "sl": round(sl, 3)
    }

def calcular_rsi(fechamentos, periodo=14):
    diffs = np.diff(fechamentos)
    ganhos = np.where(diffs > 0, diffs, 0)
    perdas = np.where(diffs < 0, -diffs, 0)
    media_ganhos = np.mean(ganhos[-periodo:])
    media_perdas = np.mean(perdas[-periodo:])
    rs = media_ganhos / media_perdas if media_perdas != 0 else 0
    rsi = 100 - (100 / (1 + rs))
    return rsi

def verificar_confluencia(velas):
    if len(velas) < 21:
        return False

    fechamentos = [v["close"] for v in velas]
    closes = np.array(fechamentos)

    ema9 = np.mean(closes[-9:])
    ema21 = np.mean(closes[-21:])
    rsi = calcular_rsi(closes)

    macd_line = np.mean(closes[-12:]) - np.mean(closes[-26:])
    signal_line = np.mean(closes[-9:])
    macd_ok = macd_line > signal_line

    ultima = velas[-1]
    candle_verde = ultima["close"] > ultima["open"]
    volume_ok = ultima["volume"] > 1000
    preco_acima_media = ultima["close"] > np.mean(closes)

    condicoes = [
        rsi < 70 and rsi > 50,
        ema9 > ema21,
        macd_ok,
        candle_verde,
        volume_ok,
        preco_acima_media
    ]

    return sum(condicoes) >= 6

pares = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "MATICUSDT",
    "AVAXUSDT", "LINKUSDT", "TONUSDT", "FETUSDT", "ADAUSDT",
    "RNDRUSDT", "1000SHIBUSDT"
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
                limit=50
            )["result"]["list"]

            if not velas_raw or len(velas_raw) < 30:
                print(f"⚠️ {par}: dados insuficientes. Pulando...")
                time.sleep(1)
                continue

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

            if verificar_confluencia(velas):
                print(f"✅ Confluência detectada em {par} (RSI, EMA, MACD...)")

                preco_atual = velas[-1]["close"]
                fib = calcular_fibonacci_tp_sl(velas, direcao="compra")
                if not fib:
                    print("❌ Fibonacci falhou.")
                    continue

                usdt_alvo = 5
                alavancagem = 4
                qty = round((usdt_alvo * alavancagem) / preco_atual, 2)

                session.place_order(
                    category="linear",
                    symbol=par,
                    side="Buy",
                    orderType="Market",
                    qty=qty,
                    takeProfit=fib["tp"],
                    stopLoss=fib["sl"],
                    leverage=alavancagem
                )

                print(f"🚀 Ordem enviada: {par} | Qty: {qty} | TP: {fib['tp']} | SL: {fib['sl']}")

            time.sleep(1)

        except Exception as e:
            print(f"⚠️ Erro ao analisar {par}: {str(e)}")
            time.sleep(2)

if __name__ == "__main__":
    threading.Thread(target=monitorar_mercado).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
