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
    saldo_usdt = balance['result']['list'][0]['totalEquity']
    print(f"💰 Saldo disponível (simulado): {saldo_usdt} USDT")
except Exception as e:
    print(f"❌ Falha ao conectar à API: {e}")

symbols = ["BNBUSDT", "BTCUSDT", "DOGEUSDT", "SOLUSDT", "ADAUSDT", "ETHUSDT"]
interval = "1"
quantidade_usdt = 5
pares_com_erro_leverage = ["ETHUSDT", "ADAUSDT", "BTCUSDT"]

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
        return fetch_candles(symbol)

def calcular_adx(df, n=14):
    high = df['high']
    low = df['low']
    close = df['close']

    plus_dm = high.diff()
    minus_dm = low.diff()

    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.rolling(window=n).mean()

    plus_di = 100 * (plus_dm.rolling(window=n).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=n).mean() / atr)
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    adx = dx.rolling(window=n).mean()

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
    fortes = 0
    extras = 0

    linha = df.iloc[-1]

    # Exemplo simples de condições para sinais
    if linha["EMA10"] > linha["EMA20"]:
        fortes += 1
    if linha["MACD"] > linha["SINAL"]:
        fortes += 1
    if linha["CCI"] > 100:
        fortes += 1
    if linha["ADX"] > 20:
        fortes += 1
    if linha["volume_explosivo"]:
        extras += 1

    # Exemplo de decisão simples para entrada LONG ou SHORT
    entrada = "NENHUMA"
    if fortes >= 4:
        entrada = "LONG"
    elif fortes <= 1:
        entrada = "SHORT"

    return fortes, extras, entrada

def main():
    for symbol in symbols:
        print(f"🔍 Analisando {symbol}")
        df = fetch_candles(symbol, interval)
        df = calcular_indicadores(df)

        fortes, extras, entrada = sinais(df)

        print(f"Sinais fortes: {fortes}, extras: {extras}, entrada sugerida: {entrada}")

        if entrada != "NENHUMA":
            print(f"💡 Enviando ordem para {symbol}: {entrada}")
            # Aqui deve vir a lógica para envio de ordens com session.place_active_order
            # Exemplo fictício:
            try:
                ordem = session.place_active_order(
                    symbol=symbol,
                    side="Buy" if entrada == "LONG" else "Sell",
                    orderType="Market",
                    qty=quantidade_usdt,
                    timeInForce="GoodTillCancel"
                )
                print("✅ Ordem enviada com sucesso!")
            except Exception as e:
                print(f"❌ Erro ao enviar ordem para {symbol}: {e}")

        time.sleep(1)  # Para não bombardear a API

if __name__ == "__main__":
    main()

