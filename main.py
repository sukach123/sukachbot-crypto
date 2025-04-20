from flask import Flask
import os
import time
import threading
import requests
import numpy as np
from datetime import datetime
from pybit.unified_trading import HTTP

app = Flask(__name__)

api_key = os.getenv("BYBIT_API_KEY")
api_secret = os.getenv("BYBIT_API_SECRET")

session = HTTP(api_key=api_key, api_secret=api_secret, testnet=False)

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
    return "✅ SukachBot CRYPTO ativo com Telegram + SL/TP baseados no preço real!"

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

                if total_sinais >= 6:
                    preco_atual = velas[-1]["close"]
                    usdt_alvo = 10
                    alavancagem = 10
                    raw_qty = (usdt_alvo * alavancagem) / preco_atual
                    qty = round(raw_qty, 1)

                    ordem = session.place_order(
                        category="linear",
                        symbol=par,
                        side="Buy",
                        orderType="Market",
                        qty=qty,
                        leverage=alavancagem
                    )

                    if ordem["retCode"] == 0:
                        preco_exec = float(ordem["result"].get("orderPrice", preco_atual))
                        tp = round(preco_exec * 1.03, 4)
                        sl = round(preco_exec * 0.985, 4)

                        stop = session.set_trading_stop(
                            category="linear",
                            symbol=par,
                            takeProfit=tp,
                            stopLoss=sl
                        )

                        print(f"📉 SL/TP aplicado → TP: {tp}, SL: {sl}")

                        entradas += 1
                        mensagem = (
                            f"*🚀 ENTRADA EXECUTADA*
Par: {par}
Qtd: {qty}
Preço entrada: {preco_exec}
🎯 TP: {tp} | 🛡️ SL: {sl}
Sinais: {total_sinais}/12
Alavancagem: 10x"
                        )
                        enviar_telegram_mensagem(mensagem)

                time.sleep(0.1)

            if time.time() - ultimo_log >= 60:
                agora = datetime.now().strftime("%H:%M:%S")
                print(f"\n🟢 [{agora}] Bot ativo — últimos 60s:")
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
