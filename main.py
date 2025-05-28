# === SukachBot PRO75 - Agora com TP de 1.5% automático e SL de -0.3% ===

import pandas as pd
import numpy as np
from pybit.unified_trading import WebSocket, HTTP
import threading
import time

# === Configuração ===
symbol = "BTCUSDT"
interval = "1"  # 1 minuto, mas usando streaming a cada segundo
limit = 180
tp_percent = 1.5
sl_percent = -0.3

# === API Keys ===
api_key = "SUA_API_KEY"
api_secret = "SEU_API_SECRET"

# === Sessão HTTP para ordens ===
session = HTTP(
    api_key=api_key,
    api_secret=api_secret,
    testnet=True
)

# === Variável de controle ===
position_opened = False
entry_price = 0.0

# === Função para processar os sinais ===
def process_signals(df):
    global position_opened, entry_price

    # Indicadores
    df["EMA10"] = df["close"].ewm(span=10).mean()
    df["EMA20"] = df["close"].ewm(span=20).mean()
    df["MACD"] = df["close"].ewm(span=12).mean() - df["close"].ewm(span=26).mean()
    df["Signal"] = df["MACD"].ewm(span=9).mean()
    df["RSI"] = compute_rsi(df["close"])

    latest = df.iloc[-1]

    # Sinais
    sinais = [
        latest["EMA10"] > latest["EMA20"],       # Sinal 1: EMA10 > EMA20
        latest["MACD"] > latest["Signal"],       # Sinal 2: MACD > Signal
        latest["RSI"] > 50,                      # Sinal 3: RSI acima de 50
        latest["close"] > latest["EMA10"],       # Sinal 4: Preço acima da EMA10
        latest["close"] > df["close"].mean()     # Sinal Extra: Preço acima da média dos 180 candles
    ]

    sinais_positivos = sum(sinais)

    if not position_opened and sinais_positivos >= 5:
        print("📈 5 sinais fortes detectados: ENTRADA DE COMPRA")
        buy_order(latest["close"])

    if not position_opened and sinais_positivos == 4:
        print("⚠️ 4 sinais fortes + 1 extra detectado: ENTRADA DE COMPRA")
        buy_order(latest["close"])

    if position_opened:
        atual = latest["close"]
        gain = ((atual - entry_price) / entry_price) * 100
        if gain >= tp_percent:
            print("✅ Alvo de lucro alcançado! Fechando posição.")
            close_position()
        elif gain <= sl_percent:
            print("🛑 Stop Loss atingido. Fechando posição.")
            close_position()

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def buy_order(price):
    global position_opened, entry_price
    entry_price = price
    position_opened = True
    print(f"🟢 Compra executada a {price}")

def close_position():
    global position_opened
    position_opened = False
    print("🔴 Posição fechada")

# === WebSocket ===
def start_websocket():
    ws = WebSocket(
        testnet=True,
        api_key=api_key,
        api_secret=api_secret,
        channel_type="linear"
    )

    candles = []

    def handle_message(message):
        if message['type'] != 'snapshot':
            return
        try:
            k = message["data"]
            close = float(k["close"])
            candles.append(close)
            if len(candles) > limit:
                candles.pop(0)
            if len(candles) == limit:
                df = pd.DataFrame({"close": candles})
                process_signals(df)
        except Exception as e:
            print("Erro ao processar candle:", e)

    ws.kline_stream(
        interval=interval,
        symbol=symbol,
        callback=handle_message
    )

    print("📡 WebSocket iniciado e ouvindo candles a cada segundo...")

# === Iniciar Thread ===
t = threading.Thread(target=start_websocket)
t.start()


