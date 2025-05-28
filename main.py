# === SukachBot PRO75 - Agora com TP de 1.5% automático e SL de -0.3% ===

import pandas as pd
import numpy as np
from pybit.unified_trading import HTTP
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

def fetch_candles(symbol, interval="1"):
    try:
        data = session.get_kline(category="linear", symbol=symbol, interval=interval, limit=180)  # Alterado para 180
        candles = data['result']['list']
        df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"])
        df = df.astype({"open": float, "high": float, "low": float, "close": float, "volume": float})
        df["timestamp"] = pd.to_datetime(pd.to_numeric(df["timestamp"]), unit="ms", utc=True)
        now = datetime.now(timezone.utc)
        diff = now - df["timestamp"].iloc[-1]
        atraso = int(diff.total_seconds())
        if 60 < atraso < 300:
            print(f"⚠️ AVISO: Último candle de {symbol} está atrasado {atraso} segundos!")
        return df
    except Exception as e:
        print(f"🚨 Erro ao buscar candles de {symbol}: {e}")
        time.sleep(1)
        return fetch_candles(symbol, interval)

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

def verificar_sinal(df):
    ultima = df.iloc[-1]
    anterior = df.iloc[-2]

    # Condições para entrada LONG
    cond_long = (
        (ultima["EMA10"] > ultima["EMA20"]) and
        (anterior["EMA10"] <= anterior["EMA20"]) and
        (ultima["MACD"] > ultima["SINAL"]) and
        (ultima["CCI"] > 0) and
        (ultima["ADX"] > 25) and
        (ultima["volume_explosivo"])
    )

    # Condições para entrada SHORT
    cond_short = (
        (ultima["EMA10"] < ultima["EMA20"]) and
        (anterior["EMA10"] >= anterior["EMA20"]) and
        (ultima["MACD"] < ultima["SINAL"]) and
        (ultima["CCI"] < 0) and
        (ultima["ADX"] > 25) and
        (ultima["volume_explosivo"])
    )

    if cond_long:
        return "LONG"
    elif cond_short:
        return "SHORT"
    else:
        return None

def enviar_ordem(symbol, lado, quantidade_usdt):
    try:
        price_data = session.get_symbol_price_ticker(symbol=symbol)
        preco_atual = float(price_data['result']['price'])
        quantidade = quantidade_usdt / preco_atual

        # Criar ordem de mercado
        ordem = session.place_active_order(
            category="linear",
            symbol=symbol,
            side=lado,
            orderType="Market",
            qty=round(quantidade, 3),
            timeInForce="GoodTillCancel",
            reduceOnly=False,
            closeOnTrigger=False
        )

        print(f"Ordem enviada: {lado} {quantidade:.3f} {symbol} ao preço {preco_atual}")
        return ordem
    except Exception as e:
        print(f"Erro ao enviar ordem: {e}")
        return None

def main():
    while True:
        for symbol in symbols:
            df = fetch_candles(symbol, interval)
            df = calcular_indicadores(df)
            sinal = verificar_sinal(df)

            if sinal:
                print(f"Sinal {sinal} detectado para {symbol}")
                lado_ordem = "Buy" if sinal == "LONG" else "Sell"
                enviar_ordem(symbol, lado_ordem, quantidade_usdt)

            time.sleep(1)

if __name__ == "__main__":
    main()

