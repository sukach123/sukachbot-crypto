import pandas as pd
import numpy as np
from pybit.unified_trading import HTTP
import time
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

print("🚧 MODO DEMO ATIVO - Bybit Testnet em execução 🚧")

# === Configurações ===
api_key = os.getenv("BYBIT_API_KEY")
api_secret = os.getenv("BYBIT_API_SECRET")
session = HTTP(api_key=api_key, api_secret=api_secret, testnet=True)

print("🔐 Verificando acesso à API...")
try:
    balance = session.get_wallet_balance(accountType="UNIFIED")
    print("✅ API conectada com sucesso!")
    saldo_usdt = float(balance['result']['list'][0]['totalEquity'])
    print(f"💰 Saldo disponível (simulado): {saldo_usdt} USDT")
except Exception as e:
    print(f"❌ Falha ao conectar à API: {e}")
    saldo_usdt = 0

symbols = ["BNBUSDT", "BTCUSDT", "DOGEUSDT", "SOLUSDT", "ADAUSDT", "ETHUSDT"]
interval = "1"
quantidade_usdt = 5  # quantidade fixa por ordem (pode adaptar)
pares_com_erro_leverage = ["ETHUSDT", "ADAUSDT", "BTCUSDT"]  # Exemplo, ajustar se precisar

def fetch_candles(symbol, interval="1"):
    try:
        data = session.get_kline(category="linear", symbol=symbol, interval=interval, limit=200)
        candles = data['result']['list']
        df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"])
        df = df.astype({"open": float, "high": float, "low": float, "close": float, "volume": float})
        df["timestamp"] = pd.to_datetime(pd.to_numeric(df["timestamp"]), unit="ms", utc=True)
        return df
    except Exception as e:
        print(f"🚨 Erro ao buscar candles de {symbol}: {e}")
        time.sleep(1)
        return fetch_candles(symbol, interval)

def calcular_adx(df, n=14):
    high = df['high']
    low = df['low']
    close = df['close']

    plus_dm = high.diff()
    minus_dm = low.diff() * -1

    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0

    tr1 = pd.Series(high - low)
    tr2 = pd.Series(abs(high - close.shift()))
    tr3 = pd.Series(abs(low - close.shift()))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=n).mean()

    plus_di = 100 * (plus_dm.rolling(n).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(n).mean() / atr)

    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    adx = dx.rolling(n).mean()

    return adx

def calcular_indicadores(df):
    df["EMA10"] = df["close"].ewm(span=10).mean()
    df["EMA20"] = df["close"].ewm(span=20).mean()
    df["MACD"] = df["close"].ewm(span=12).mean() - df["close"].ewm(span=26).mean()
    df["SINAL"] = df["MACD"].ewm(span=9).mean()
    df["CCI"] = (df["close"] - df["close"].rolling(20).mean()) / (0.015 * df["close"].rolling(20).std())
    df["ADX"] = calcular_adx(df)
    df["volume_explosivo"] = df["volume"] > df["volume"].rolling(20).mean() * 1.5
    return df

def sinais(df):
    # Simples regra exemplo para sinal LONG ou SHORT, pode adaptar conforme estratégia
    fortes = 0
    extras = 0
    entrada = "NENHUMA"

    if df["EMA10"].iloc[-1] > df["EMA20"].iloc[-1]:
        fortes += 1
    if df["MACD"].iloc[-1] > df["SINAL"].iloc[-1]:
        fortes += 1
    if df["CCI"].iloc[-1] > 100:
        extras += 1
    if df["ADX"].iloc[-1] > 20:
        extras += 1

    # Decidir entrada baseado em indicadores
    if fortes >= 2 and extras >= 1:
        entrada = "LONG"
    elif fortes == 0 and extras == 0:
        entrada = "SHORT"

    return fortes, extras, entrada

def enviar_ordem(symbol, lado, quantidade):
    try:
        resposta = session.place_active_order_v2(
            symbol=symbol,
            side="Buy" if lado == "LONG" else "Sell",
            orderType="Market",
            qty=quantidade,
            timeInForce="GoodTillCancel",
            reduceOnly=False,
            closeOnTrigger=False
        )
        print(f"💡 Ordem enviada para {symbol}: {lado}")
        return resposta
    except Exception as e:
        print(f"❌ Erro ao enviar pedido para {symbol}: {e}")

def main():
    while True:
        for simbolo in symbols:
            df = fetch_candles(simbolo, interval)
            df = calcular_indicadores(df)
            fortes, extras, entrada_sugerida = sinais(df)

            print(f"🔍 Analisando {simbolo}")
            print(f"Sinais fortes: {fortes}, extras: {extras}, entrada sugerida: {entrada_sugerida}")

            if entrada_sugerida in ["LONG", "SHORT"]:
                enviar_ordem(simbolo, entrada_sugerida, quantidade_usdt)
            else:
                print("Nenhuma entrada válida no momento.")

            time.sleep(1)  # delay entre pares para não sobrecarregar API

if __name__ == "__main__":
    main()

