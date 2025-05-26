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
interval = "1"  # 1 minuto
quantidade_usdt = 5

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
    # Cálculo simples do ADX - para demo, sem tratar NaNs
    high = df['high']
    low = df['low']
    close = df['close']

    plus_dm = high.diff()
    minus_dm = low.diff().abs()

    plus_dm = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0)
    minus_dm = np.where((minus_dm > plus_dm) & (minus_dm > 0), minus_dm, 0)

    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.rolling(n).mean()

    plus_di = 100 * (plus_dm.rolling(n).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(n).mean() / atr)

    dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di))
    adx = dx.rolling(n).mean()
    return adx.fillna(0)

def calcular_indicadores(df):
    df["EMA10"] = df["close"].ewm(span=10, adjust=False).mean()
    df["EMA20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["MACD"] = df["close"].ewm(span=12, adjust=False).mean() - df["close"].ewm(span=26, adjust=False).mean()
    df["SINAL"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["CCI"] = (df["close"] - df["close"].rolling(20).mean()) / (0.015 * df["close"].rolling(20).std())
    df["ADX"] = calcular_adx(df)
    df["volume_explosivo"] = df["volume"] > df["volume"].rolling(20).mean() * 1.5
    return df

def sinais(df):
    fortes = 0
    extras = 0

    # Sinais fortes
    if df["EMA10"].iloc[-1] > df["EMA20"].iloc[-1]:
        fortes += 1
    if df["MACD"].iloc[-1] > df["SINAL"].iloc[-1]:
        fortes += 1
    if df["CCI"].iloc[-1] > 100:
        fortes += 1
    if df["ADX"].iloc[-1] > 20:
        fortes += 1
    if df["volume_explosivo"].iloc[-1]:
        fortes += 1

    # Sinais extras
    if df["CCI"].iloc[-1] > 0:
        extras += 1
    if df["MACD"].iloc[-1] > 0:
        extras += 1

    if fortes >= 4:
        entrada = "LONG"
    elif fortes <= 1:
        entrada = "SHORT"
    else:
        entrada = "NENHUMA"

    return fortes, extras, entrada

def main():
    for symbol in symbols:
        df = fetch_candles(symbol, interval)
        df = calcular_indicadores(df)
        fortes, extras, entrada = sinais(df)

        print(f"🔍 Analisando {symbol}")
        print(f"Sinais fortes: {fortes}, extras: {extras}, entrada sugerida: {entrada}\n")

        # Exemplo envio de ordem (comentado por segurança)
        # if entrada == "LONG":
        #     try:
        #         qty = quantidade_usdt / df["close"].iloc[-1]
        #         session.place_active_order(
        #             symbol=symbol,
        #             side="Buy",
        #             orderType="Market",
        #             qty=round(qty, 6),
        #             timeInForce="GoodTillCancel"
        #         )
        #         print(f"✅ Ordem LONG enviada para {symbol}")
        #     except Exception as e:
        #         print(f"❌ Erro ao enviar ordem LONG para {symbol}: {e}")
        # elif entrada == "SHORT":
        #     # Lógica para SHORT, se aplicável
        #     pass
        # else:
        #     print("Nenhuma entrada válida no momento.\n")

if __name__ == "__main__":
    while True:
        main()
        time.sleep(1)


