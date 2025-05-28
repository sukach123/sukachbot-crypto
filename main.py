# === SukachBot PRO75 - Agora com TP de 1.5% automático e SL de -0.3% ===

import pandas as pd
import numpy as np
import threading
from pybit.unified_trading import WebSocket, HTTP

session = HTTP(
    testnet=True,
    api_key="SUA_API_KEY",
    api_secret="SUA_API_SECRET"
)

ws = WebSocket(
    testnet=True,
    channel_type="linear",
    api_key="SUA_API_KEY",
    api_secret="SUA_API_SECRET"
)

df = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

def calcular_sinais(dataframe):
    df = dataframe.copy()

    df["EMA10"] = df["close"].ewm(span=10).mean()
    df["EMA20"] = df["close"].ewm(span=20).mean()

    df["MACD"] = df["close"].ewm(span=12).mean() - df["close"].ewm(span=26).mean()
    df["Signal"] = df["MACD"].ewm(span=9).mean()

    df["RSI"] = 100 - (100 / (1 + df["close"].pct_change().rolling(window=14).mean() /
                              df["close"].pct_change().rolling(window=14).std()))

    df["Momentum"] = df["close"] - df["close"].shift(4)

    sinais = {
        "EMA_Crossover": df["EMA10"].iloc[-1] > df["EMA20"].iloc[-1],
        "MACD": df["MACD"].iloc[-1] > df["Signal"].iloc[-1],
        "RSI": df["RSI"].iloc[-1] < 70 and df["RSI"].iloc[-1] > 30,
        "Momentum": df["Momentum"].iloc[-1] > 0,
        "Extra": df["close"].iloc[-1] > df["open"].iloc[-1]
    }

    total_sinais = sum(sinais.values())
    return total_sinais, sinais

def processar_candle(candle_data):
    global df

    try:
        # Verifica se candle_data["data"] é dict ou list
        candle = candle_data["data"]
        if isinstance(candle, list):
            candle = candle[0]

        novo_candle = {
            "timestamp": candle["start"],
            "open": float(candle["open"]),
            "high": float(candle["high"]),
            "low": float(candle["low"]),
            "close": float(candle["close"]),
            "volume": float(candle["volume"])
        }

        df.loc[len(df)] = novo_candle
        df = df.tail(180)  # Mantém os últimos 180 candles

        if len(df) >= 30:
            total_sinais, sinais = calcular_sinais(df)

            print(f"📊 Sinais detectados: {sinais} (Total: {total_sinais})")

            if total_sinais >= 5:
                print("✅ ENTRADA FORTE IDENTIFICADA (5 SINAIS) — ENTRAR NO MERCADO")
                # Aqui você colocaria a lógica para enviar ordem com TP/SL

    except Exception as e:
        print(f"❌ Erro ao processar candle: {e}")

def iniciar_websocket():
    ws.kline_stream(
        interval="1",
        symbol="BTCUSDT",
        callback=processar_candle
    )
    print("📡 WebSocket iniciado e ouvindo candles a cada segundo...")

# Inicia o WebSocket em uma thread separada
thread = threading.Thread(target=iniciar_websocket)
thread.start()

