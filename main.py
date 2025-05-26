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
    df = df.copy()
    df['TR'] = np.maximum.reduce([
        df['high'] - df['low'],
        abs(df['high'] - df['close'].shift()),
        abs(df['low'] - df['close'].shift())
    ])
    df['+DM'] = np.where((df['high'] - df['high'].shift()) > (df['low'].shift() - df['low']), 
                         np.maximum(df['high'] - df['high'].shift(), 0), 0)
    df['-DM'] = np.where((df['low'].shift() - df['low']) > (df['high'] - df['high'].shift()), 
                         np.maximum(df['low'].shift() - df['low'], 0), 0)
    atr = df['TR'].rolling(n).mean()
    plus_di = 100 * (df['+DM'].rolling(n).mean() / atr)
    minus_di = 100 * (df['-DM'].rolling(n).mean() / atr)
    dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di))
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
    fortes = 0
    extras = 0

    linha = df.iloc[-1]

    # Exemplo de critérios para sinais fortes
    if linha["EMA10"] > linha["EMA20"]:
        fortes += 1
    if linha["MACD"] > linha["SINAL"]:
        fortes += 1
    if linha["CCI"] > 100:
        fortes += 1
    if linha["ADX"] > 20:
        fortes += 1
    if linha["volume_explosivo"]:
        fortes += 1

    # Sinais extras para confirmar ou reforçar
    if linha["EMA10"] < linha["EMA20"]:
        extras += 1
    if linha["MACD"] < linha["SINAL"]:
        extras += 1
    if linha["CCI"] < -100:
        extras += 1

    # Determinar a entrada sugerida
    if fortes >= 4:
        entrada = "LONG"
    elif extras >= 3:
        entrada = "SHORT"
    else:
        entrada = "NENHUMA"

    return fortes, extras, entrada

def enviar_ordem(symbol, side, quantidade):
    try:
        # Converter side para formato aceito pela API
        side_api = "Buy" if side == "LONG" else "Sell"
        resposta = session.place_active_order_v2(
            symbol=symbol,
            side=side_api,
            orderType="Market",
            qty=str(quantidade),
            timeInForce="GoodTillCancel",
            reduceOnly=False,
            closeOnTrigger=False
        )
        print(f"💡 Ordem enviada para {symbol}: {side}")
        print(resposta)
    except Exception as e:
        print(f"❌ Erro ao enviar pedido para {symbol}: {e}")

def main():
    while True:
        for symbol in symbols:
            df = fetch_candles(symbol, interval)
            df = calcular_indicadores(df)
            fortes, extras, entrada = sinais(df)
            print(f"🔍 Analisando {symbol}")
            print(f"Sinais fortes: {fortes}, extras: {extras}, entrada sugerida: {entrada}")

            if entrada != "NENHUMA":
                quantidade = quantidade_usdt / df["close"].iloc[-1]
                enviar_ordem(symbol, entrada, quantidade)
            else:
                print("Nenhuma entrada válida no momento.\n")

            time.sleep(1)  # Para não sobrecarregar API

if __name__ == "__main__":
    main()

