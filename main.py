# === SukachBot PRO75 - Agora com TP de 1.5% automático ===

import pandas as pd
import numpy as np
from pybit.unified_trading import HTTP
import time
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# === Configurações ===
symbols = ["BNBUSDT", "BTCUSDT", "DOGEUSDT", "SOLUSDT", "ADAUSDT", "ETHUSDT"]
interval = "1"
api_key = os.getenv("BYBIT_API_KEY")
api_secret = os.getenv("BYBIT_API_SECRET")
quantidade_usdt = 5

session = HTTP(api_key=api_key, api_secret=api_secret, testnet=False)

def fetch_candles(symbol, interval="1"):
    try:
        data = session.get_kline(category="linear", symbol=symbol, interval=interval, limit=200)
        candles = data['result']['list']
        df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"])
        df = df.astype({"open": float, "high": float, "low": float, "close": float, "volume": float})
        df["timestamp"] = pd.to_datetime(pd.to_numeric(df["timestamp"]), unit="ms")
        return df
    except Exception as e:
        print(f"🚨 Erro ao buscar candles de {symbol}: {e}")
        time.sleep(1)
        return fetch_candles(symbol)

def calcular_indicadores(df):
    df["EMA10"] = df["close"].ewm(span=10).mean()
    df["EMA20"] = df["close"].ewm(span=20).mean()
    df["MACD"] = df["close"].ewm(span=12).mean() - df["close"].ewm(span=26).mean()
    df["SINAL"] = df["MACD"].ewm(span=9).mean()
    df["CCI"] = (df["close"] - df["close"].rolling(20).mean()) / (0.015 * df["close"].rolling(20).std())
    df["ADX"] = abs(df["high"] - df["low"]).rolling(14).mean()
    df["ATR"] = (df["high"] - df["low"]).rolling(14).mean()
    df["volume_medio"] = df["volume"].rolling(20).mean()
    df["volume_explosivo"] = df["volume"] > 1.3 * df["volume_medio"]
    return df

def verificar_entrada(df):
    row = df.iloc[-1]
    prev = df.iloc[-2]
    ultimos5 = df.iloc[-5:]
    ultimos20 = df.iloc[-20:]

    corpo = abs(row["close"] - row["open"])
    volatilidade = ultimos20["high"].max() - ultimos20["low"].min()
    media_atr = ultimos20["ATR"].mean()
    nao_lateral = volatilidade > (2 * media_atr)

    sinal_1 = row["EMA10"] > row["EMA20"] or row["EMA10"] < row["EMA20"]
    sinal_2 = row["MACD"] > row["SINAL"]
    sinal_3 = row["CCI"] > 0
    sinal_4 = row["ADX"] > 20
    sinal_5 = row["volume_explosivo"]
    sinal_6 = corpo > ultimos5["close"].max() - ultimos5["low"].min()
    sinal_7 = nao_lateral

    sinais_fortes = [sinal_1, sinal_2, sinal_3, sinal_4, sinal_5, sinal_6, sinal_7]

    extra_1 = prev["close"] > prev["open"]
    extra_2 = (row["high"] - row["close"]) < corpo
    sinais_extras = [extra_1, extra_2]

    total_confirmados = sum(sinais_fortes) + sum(sinais_extras)

    print(f"\n📊 Diagnóstico de sinais em {row['timestamp']}")
    print(f"📌 EMA10 vs EMA20: {sinal_1}")
    print(f"📌 MACD > SINAL: {sinal_2}")
    print(f"📌 CCI > 0: {sinal_3} (valor: {row['CCI']:.2f})")
    print(f"📌 ADX > 20: {sinal_4} (valor: {row['ADX']:.2f})")
    print(f"📌 Volume explosivo: {sinal_5} (volume: {row['volume']:.2f})")
    print(f"📌 Corpo grande: {sinal_6}")
    print(f"📌 Não lateral: {sinal_7}")
    print(f"📌 Extra: Vela anterior de alta: {extra_1}")
    print(f"📌 Extra: Pequeno pavio superior: {extra_2}")
    print(f"✔️ Total: {sum(sinais_fortes)} fortes + {sum(sinais_extras)} extras = {total_confirmados}/9")

    if sum(sinais_fortes) >= 7:
        preco_atual = row["close"]
        diferenca_ema = abs(row["EMA10"] - row["EMA20"])
        limite_colisao = preco_atual * 0.0001

        print(f"🔔 {row['timestamp']} | 7/9 sinais fortes confirmados!")

        if diferenca_ema < limite_colisao:
            print(f"🚫 Entrada bloqueada ❌")
            return None
        else:
            direcao = "Buy" if row["EMA10"] > row["EMA20"] else "Sell"
            print(f"✅ Entrada confirmada! {direcao}")
            return direcao
    else:
        print(f"🔎 {row['timestamp']} | Apenas {total_confirmados}/9 sinais confirmados | Entrada bloqueada ❌")
        return None

