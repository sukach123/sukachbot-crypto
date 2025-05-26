# === SukachBot PRO75 - Análise por segundo com TP/SL e checagem de velas ===

import time
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from pybit.unified_trading import HTTP

# Configurações de API
api_key = "SUA_API_KEY"
api_secret = "SEU_API_SECRET"

session = HTTP(
    testnet=True,
    api_key=api_key,
    api_secret=api_secret,
)

symbols = ["DOGEUSDT", "SOLUSDT", "ADAUSDT", "ETHUSDT", "BNBUSDT"]

def buscar_velas(symbol, interval="1", limit=1000):
    try:
        response = session.get_kline(
            category="linear",
            symbol=symbol,
            interval=interval,
            limit=limit,
        )
        df = pd.DataFrame(response["result"]["list"], columns=[
            "timestamp", "open", "high", "low", "close", "volume", "turnover"
        ])
        df = df.astype(float)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df.set_index("timestamp", inplace=True)
        return df
    except Exception as e:
        print(f"Erro ao buscar velas de {symbol}: {e}")
        return None

def calcular_indicadores(df):
    df["EMA10"] = df["close"].ewm(span=10).mean()
    df["EMA20"] = df["close"].ewm(span=20).mean()
    df["MACD"] = df["close"].ewm(12).mean() - df["close"].ewm(26).mean()
    df["SINAL"] = df["MACD"].ewm(9).mean()
    df["CCI"] = (df["close"] - df["close"].rolling(20).mean()) / (0.015 * df["close"].rolling(20).std())
    df["ADX"] = calcular_adx(df)
    df["ATR"] = calcular_atr(df)
    return df

def calcular_adx(df, period=14):
    high = df["high"]
    low = df["low"]
    close = df["close"]

    plus_dm = high.diff()
    minus_dm = low.diff()
    tr = pd.concat([
        high - low,
        abs(high - close.shift()),
        abs(low - close.shift())
    ], axis=1).max(axis=1)

    atr = tr.rolling(period).mean()
    plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    adx = dx.rolling(period).mean()
    return adx

def calcular_atr(df, period=14):
    tr = pd.concat([
        df["high"] - df["low"],
        abs(df["high"] - df["close"].shift()),
        abs(df["low"] - df["close"].shift())
    ], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    return atr

def gerar_sinais(row):
    sinais_fortes = 0
    sinais_extras = 0

    if row["EMA10"] > row["EMA20"]:
        sinais_fortes += 1
    if row["MACD"] > row["SINAL"]:
        sinais_fortes += 1
    if row["CCI"] > 100:
        sinais_fortes += 1
    if row["ADX"] > 20:
        sinais_fortes += 1
    if row["close"] > row["EMA10"]:
        sinais_fortes += 1

    if row["EMA10"] > row["EMA20"] and row["CCI"] > 100:
        sinais_extras += 1
    if row["MACD"] > row["SINAL"] and row["ADX"] > 20:
        sinais_extras += 1

    return sinais_fortes, sinais_extras

def enviar_ordem(symbol, side, qty, price, sl_percent=1.0, tp_percent=1.5):
    try:
        sl_price = price * (1 - sl_percent / 100) if side == "Buy" else price * (1 + sl_percent / 100)
        tp_price = price * (1 + tp_percent / 100) if side == "Buy" else price * (1 - tp_percent / 100)

        response = session.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            order_type="Market",
            qty=qty,
            take_profit=round(tp_price, 4),
            stop_loss=round(sl_price, 4),
            time_in_force="GoodTillCancel",
        )
        print(f"🟢 Ordem enviada: {side} {symbol} - Qtd: {qty}")
    except Exception as e:
        print(f"❌ Erro ao enviar ordem para {symbol}: {e}")

def principal():
    while True:
        for symbol in symbols:
            df = buscar_velas(symbol)
            if df is None or len(df) < 50:
                continue

            df = calcular_indicadores(df)
            ultima = df.iloc[-1]

            # Verifica se candle é atual (máx 2s de atraso)
            agora = datetime.now(timezone.utc)
            atraso = (agora - ultima.name).total_seconds()
            if atraso > 2:
                continue  # Pula esse símbolo se a vela estiver atrasada

            fortes, extras = gerar_sinais(ultima)
            print(f"\n🔍 Analisando {symbol}")
            print(f"Sinais fortes: {fortes}, extras: {extras}", end="")

            if fortes >= 6 or (fortes == 5 and extras >= 2):
                side = "Buy"
                price = ultima["close"]
                enviar_ordem(symbol, side, qty=0.02, price=price)
            else:
                print(" | Nenhuma entrada válida.")

        time.sleep(1)

if __name__ == "__main__":
    principal()

