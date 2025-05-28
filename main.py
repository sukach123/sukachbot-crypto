# === SukachBot PRO75 - Agora com TP de 1.5% automático e SL de -0.3% ===

import pandas as pd
import numpy as np
from pybit.unified_trading import HTTP, WebSocket
import threading
import time

# Configuração de API
api_key = "SUA_API_KEY"
api_secret = "SEU_API_SECRET"

session = HTTP(testnet=True, api_key=api_key, api_secret=api_secret)

# Dados globais
df = pd.DataFrame()
symbol = "BTCUSDT"
interval = "1"  # 1 minuto (ainda usamos isso para o candle base)
limit = 180

# Função para processar candles recebidos via WebSocket
def process_candle(data):
    global df

    if data["topic"] == f"kline.{interval}.{symbol}":
        k = data["data"]
        new_row = {
            'timestamp': pd.to_datetime(k["start"]),
            'open': float(k["open"]),
            'high': float(k["high"]),
            'low': float(k["low"]),
            'close': float(k["close"]),
            'volume': float(k["volume"]),
        }

        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.drop_duplicates(subset='timestamp', keep='last', inplace=True)
        df = df.sort_values(by='timestamp').reset_index(drop=True)
        df = df.tail(limit)

        if len(df) >= 55:
            checar_sinais(df)

# Função de sinais
def checar_sinais(df):
    close = df['close']

    df['EMA10'] = close.ewm(span=10, adjust=False).mean()
    df['EMA20'] = close.ewm(span=20, adjust=False).mean()
    df['MACD'] = close.ewm(span=12).mean() - close.ewm(span=26).mean()
    df['Signal'] = df['MACD'].ewm(span=9).mean()
    df['RSI'] = calcular_rsi(close)
    df['ATR'] = calcular_atr(df)

    ultima = df.iloc[-1]

    # 5 sinais fortes (4 + 1 extra)
    sinais = [
        ultima['EMA10'] > ultima['EMA20'],               # sinal 1
        ultima['MACD'] > ultima['Signal'],               # sinal 2
        ultima['RSI'] < 30,                              # sinal 3
        ultima['close'] > df['EMA10'].iloc[-2],          # sinal 4
        ultima['ATR'] > df['ATR'].iloc[-2],              # extra
    ]

    total = sum(sinais)

    if total >= 5:
        print("🔔 ENTRADA DE COMPRA: 5 sinais confirmados!")
        executar_ordem('Buy', ultima['close'])

    elif total == 4 and sinais[-1]:
        print("🔔 ENTRADA DE COMPRA (4+1 extra) confirmada!")
        executar_ordem('Buy', ultima['close'])

def calcular_rsi(close, period=14):
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calcular_atr(df, period=14):
    high = df['high']
    low = df['low']
    close = df['close']
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    return atr

# Função para executar ordem com TP/SL automáticos
def executar_ordem(lado, preco_entrada):
    tp = preco_entrada * 1.015
    sl = preco_entrada * 0.997

    print(f"🔹 Ordem {lado.upper()} executada a {preco_entrada:.2f}")
    print(f"🎯 TP: {tp:.2f} | 🛑 SL: {sl:.2f}")

    # Aqui iria a chamada real para enviar a ordem via API
    # Exemplo:
    # session.place_order(...)

# Conectando ao WebSocket
def iniciar_websocket():
    ws = WebSocket(
        testnet=True,
        channel_type="linear",  # necessário!
        api_key=api_key,
        api_secret=api_secret
    )

    ws.kline_stream(callback=process_candle, symbol=symbol, interval=interval)
    print("📡 WebSocket iniciado e ouvindo candles a cada segundo...")

# Início da execução
if __name__ == "__main__":
    print("🚀 SukachBot PRO75 Iniciado.")
    iniciar_websocket()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("🛑 Bot finalizado manualmente.")

