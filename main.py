from flask import Flask
import os
import time
import threading
from pybit.unified_trading import HTTP
import numpy as np
from datetime import datetime

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
    return "✅ SukachBot CRYPTO (TESTE 5+ sinais) | 10 USDT | 10x | TP 3% | SL 1.5%"

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

def calcular_rsi(fechamentos, periodo=14):
    diffs = np.diff(fechamentos)
    ganhos = np.where(diffs > 0, diffs, 0)
    perdas = np.where(diffs < 0, -diffs, 0)
    media_ganhos = np.mean(ganhos[-periodo:])
    media_perdas = np.mean(perdas[-periodo:])
    rs = media_ganhos / media_perdas if media_perdas != 0 else 0
    rsi = 100 - (100 / (1 + rs))
    return rsi

def contar_sinais(velas):
    if len(velas) < 21:
        return 0
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
    return sum(condicoes)

# ✅ 20 pares (PEPEUSDT removido)

pares = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "MATICUSDT",
    "AVAXUSDT", "LINKUSDT", "TONUSDT", "FETUSDT", "ADAUSDT",
    "RNDRUSDT", "BNBUSDT", "XRPUSDT", "OPUSDT", "APTUSDT",
    "NEARUSDT", "SUIUSDT", "ARBUSDT", "LDOUSDT", "FILUSDT"
]

def monitorar_mercado():
    verificados = 0
    entradas = 0
    ultimo_log = time.time()

    while True:
        try:
            for par in pares:
                verificados += 1
                print(f"🔍 Verificando {par}...")

                velas_raw = session.get_kline(
                    category="linear",
                    symbol=par,
                    interval="1",
                    limit=50
                )["result"]["list"]

                if not velas_raw or len(velas_raw) < 30:
                    print(f"⚠️ {par}: dados insuficientes. Pulando...")
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

                total_sinais = contar_sinais(velas)

                if total_sinais >= 5:
                    entradas += 1
                    preco_atual = velas[-1]["close"]
                    tp = round(preco_atual * 1.03, 4)
                    sl = round(preco_atual * 0.985, 4)
                    usdt_alvo = 10
                    alavancagem = 10
                    qty = round((usdt_alvo * alavancagem) / preco_atual, 3)

                    print(f"✅ Entrada TESTE: {par} com {total_sinais}/12 sinais")
                    print(f"🚀 Ordem: {par} | Qty: {qty} | TP: {tp} | SL: {sl}")

                    session.place_order(
                        category="linear",
                        symbol=par,
                        side="Buy",
                        orderType="Market",
                        qty=qty,
                        takeProfit=tp,
                        stopLoss=sl,
                        leverage=alavancagem
                    )

                time.sleep(0.1)

            if time.time() - ultimo_log >= 60:
                agora = datetime.now().strftime("%H:%M:%S")
                print(f"\n🟢 [{agora}] Bot TESTE ativo — últimos 60s:")
                print(f"🔹 Pares verificados: {verificados}")
                print(f"🔹 Entradas executadas: {entradas}\n")
                verificados = entradas = 0
                ultimo_log = time.time()

        except Exception as e:
            print(f"⚠️ Erro ao monitorar mercado: {str(e)}")
            time.sleep(2)

if __name__ == "__main__":
    threading.Thread(target=monitorar_mercado).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
