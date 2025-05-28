# === SukachBot PRO75 - Agora com TP de 1.5% automático e SL de -0.3% ===

import pandas as pd
import numpy as np
import threading
import time
from pybit.unified_trading import WebSocket, HTTP

# Configurações da API
api_key = "SUA_API_KEY"
api_secret = "SEU_API_SECRET"

session = HTTP(testnet=True, api_key=api_key, api_secret=api_secret)

# WebSocket correto com channel_type
ws = WebSocket(
    testnet=True,
    channel_type="linear",
    api_key=api_key,
    api_secret=api_secret
)

# Dados históricos para cálculo dos sinais
historico = []

def calcular_sinais(df):
    sinais = []

    df["EMA10"] = df["close"].ewm(span=10, adjust=False).mean()
    df["EMA20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["MACD"] = df["close"].ewm(span=12, adjust=False).mean() - df["close"].ewm(span=26, adjust=False).mean()
    df["Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["RSI"] = 100 - (100 / (1 + df["close"].pct_change().rolling(14).mean()))

    ultima = df.iloc[-1]

    # Sinais fortes
    if ultima["EMA10"] > ultima["EMA20"]:
        sinais.append("EMA_CROSS")
    if ultima["MACD"] > ultima["Signal"]:
        sinais.append("MACD_CROSS")
    if ultima["RSI"] > 50:
        sinais.append("RSI_POSITIVO")
    if ultima["close"] > df["close"].rolling(20).mean().iloc[-1]:
        sinais.append("PRECO_ACIMA_MEDIA")

    # Extra
    if df["close"].iloc[-1] > df["close"].iloc[-2]:
        sinais.append("EXTRA_SUBIU")

    return sinais

def executar_trade(sinais, preco):
    if len(sinais) >= 5 or (len(sinais) == 4 and "EXTRA_SUBIU" in sinais):
        print(f"📈 Entrada confirmada com sinais: {sinais}")
        try:
            order = session.place_order(
                category="linear",
                symbol="BTCUSDT",
                side="Buy",
                order_type="Market",
                qty=0.01,
                take_profit=round(preco * 1.015, 2),
                stop_loss=round(preco * 0.997, 2),
                time_in_force="GoodTillCancel",
                reduce_only=False
            )
            print("✅ Ordem executada:", order)
        except Exception as e:
            print("❌ Erro ao executar ordem:", e)

def processar_candle(candle):
    try:
        global historico

        # candle é uma lista
        close = float(candle[2])
        timestamp = int(candle[0])

        historico.append({
            "timestamp": timestamp,
            "close": close
        })

        # Limita a 180 candles
        if len(historico) > 180:
            historico = historico[-180:]

        df = pd.DataFrame(historico)
        sinais = calcular_sinais(df)
        executar_trade(sinais, close)

    except Exception as e:
        print("Erro ao processar candle:", e)

def iniciar_ws():
    print("📡 WebSocket iniciado e ouvindo candles a cada segundo...")

    ws.kline_stream(
        interval="1",
        symbol="BTCUSDT",
        callback=lambda msg: processar_candle(msg["data"]["kline"])
    )

# Rodar o WebSocket em uma thread separada
threading.Thread(target=iniciar_ws).start()

