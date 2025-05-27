# === SukachBot PRO75 - Agora com TP de 1.5% automático e SL de -0.3% e análise em tempo real por WebSocket ===

import pandas as pd
import numpy as np
from pybit.unified_trading import HTTP, WebSocket
import time
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

# === Configurações ===
symbols = ["BNBUSDT", "BTCUSDT", "DOGEUSDT", "SOLUSDT", "ADAUSDT", "ETHUSDT"]
interval = "1"
api_key = os.getenv("BYBIT_API_KEY")
api_secret = os.getenv("BYBIT_API_SECRET")
quantidade_usdt = 5

session = HTTP(api_key=api_key, api_secret=api_secret, testnet=False)

# WebSocket para streaming de dados em tempo real
ws = WebSocket(testnet=False, api_key=api_key, api_secret=api_secret)

# Dicionário para armazenar candles por símbolo
candles_data = {symbol: pd.DataFrame() for symbol in symbols}

def calcular_indicadores(df):
    df["EMA10"] = df["close"].ewm(span=10).mean()
    df["EMA20"] = df["close"].ewm(span=20).mean()
    df["MACD"] = df["close"].ewm(span=12).mean() - df["close"].ewm(span=26).mean()
    df["SINAL"] = df["MACD"].ewm(span=9).mean()
    df["CCI"] = (df["close"] - df["close"].rolling(20).mean()) / (0.015 * df["close"].rolling(20).std())
    df["TR"] = np.maximum.reduce([
        df["high"] - df["low"],
        abs(df["high"] - df["close"].shift()),
        abs(df["low"] - df["close"].shift())
    ])
    df["ATR"] = df["TR"].rolling(14).mean()
    df["ADX"] = 100 * (df["ATR"] / df["close"]).rolling(14).mean()
    df["volume_medio"] = df["volume"].rolling(20).mean()
    df["volume_explosivo"] = df["volume"] > df["volume_medio"]
    return df

def avaliar_sinais(df):
    sinais = 0

    # Exemplo de sinais (ajuste conforme sua lógica original)
    if df["EMA10"].iloc[-1] > df["EMA20"].iloc[-1]:
        sinais += 1
    if df["MACD"].iloc[-1] > df["SINAL"].iloc[-1]:
        sinais += 1
    if df["CCI"].iloc[-1] > 100:
        sinais += 1
    if df["ADX"].iloc[-1] > 25:
        sinais += 1
    if df["volume_explosivo"].iloc[-1]:
        sinais += 1

    return sinais

def abrir_posicao(symbol, side):
    try:
        # Busca preço atual para calcular quantidade
        ticker = session.get_ticker(symbol=symbol)
        preco_atual = float(ticker['result'][0]['lastPrice'])
        quantidade = quantidade_usdt / preco_atual

        # Envia ordem de mercado
        order = session.place_active_order(
            symbol=symbol,
            side=side,
            order_type="Market",
            qty=round(quantidade, 3),
            time_in_force="GoodTillCancel",
            reduce_only=False,
            close_on_trigger=False
        )
        print(f"Ordem {side} aberta para {symbol} qty={round(quantidade, 3)}")
        return preco_atual, round(quantidade, 3)
    except Exception as e:
        print(f"Erro ao abrir posição: {e}")
        return None, None

def gerenciar_posicao(symbol, preco_entrada, quantidade, side):
    # TP 1.5%, SL -0.3%
    tp = preco_entrada * (1 + 0.015) if side == "Buy" else preco_entrada * (1 - 0.015)
    sl = preco_entrada * (1 - 0.003) if side == "Buy" else preco_entrada * (1 + 0.003)

    while True:
        try:
            ticker = session.get_ticker(symbol=symbol)
            preco_atual = float(ticker['result'][0]['lastPrice'])

            if (side == "Buy" and (preco_atual >= tp or preco_atual <= sl)) or \
               (side == "Sell" and (preco_atual <= tp or preco_atual >= sl)):
                # Fecha posição
                close_side = "Sell" if side == "Buy" else "Buy"
                session.place_active_order(
                    symbol=symbol,
                    side=close_side,
                    order_type="Market",
                    qty=quantidade,
                    time_in_force="GoodTillCancel",
                    reduce_only=True,
                    close_on_trigger=False
                )
                print(f"Posição {side} de {symbol} fechada em {preco_atual:.4f}")
                break

            time.sleep(1)
        except Exception as e:
            print(f"Erro no gerenciamento de posição: {e}")
            time.sleep(1)

def on_candle_update(message):
    # Recebe dados atualizados do candle em tempo real por WebSocket
    symbol = message['topic'].split('.')[1]
    candle = message['data']

    new_row = {
        "timestamp": pd.to_datetime(candle['start'], utc=True),
        "open": float(candle['open']),
        "high": float(candle['high']),
        "low": float(candle['low']),
        "close": float(candle['close']),
        "volume": float(candle['volume'])
    }

    df = candles_data[symbol]
    df = df.append(new_row, ignore_index=True)
    if len(df) > 180:  # mantém últimas 180 barras para cálculo
        df = df.iloc[-180:]

    candles_data[symbol] = df

    df = calcular_indicadores(df)
    sinais = avaliar_sinais(df)

    if sinais >= 5:
        side = "Buy"
    elif sinais <= 0:
        side = "Sell"
    else:
        return  # Sem sinal claro, não abre posição

    preco_entrada, quantidade = abrir_posicao(symbol, side)
    if preco_entrada:
        gerenciar_posicao(symbol, preco_entrada, quantidade, side)

# Assinar os tópicos websocket para candles 1s (Bybit não fornece 1s oficial, usa 1m com atualização real-time)
for symbol in symbols:
    topic = f"candle.1.{symbol}"
    ws.subscribe(topic, callback=on_candle_update)

# Iniciar websocket e manter rodando
ws.run_forever()

