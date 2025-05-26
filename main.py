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
    print(f"💰 Saldo disponível (simulado): {saldo_usdt:.4f} USDT")
except Exception as e:
    print(f"❌ Falha ao conectar à API: {e}")

symbols = ["BNBUSDT", "BTCUSDT", "DOGEUSDT", "SOLUSDT", "ADAUSDT", "ETHUSDT"]
interval = "1"
quantidade_usdt = 5

def fetch_candles(symbol, interval="1"):
    try:
        data = session.get_kline(category="linear", symbol=symbol, interval=interval, limit=200)
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
        return fetch_candles(symbol)

def calcular_adx(df, n=14):
    df = df.copy()
    df['TR'] = np.maximum.reduce([
        df['high'] - df['low'],
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    ])
    df['plus_dm'] = np.where(
        (df['high'] - df['high'].shift(1)) > (df['low'].shift(1) - df['low']),
        np.maximum(df['high'] - df['high'].shift(1), 0),
        0
    )
    df['minus_dm'] = np.where(
        (df['low'].shift(1) - df['low']) > (df['high'] - df['high'].shift(1)),
        np.maximum(df['low'].shift(1) - df['low'], 0),
        0
    )
    atr = df['TR'].rolling(n).mean()
    plus_di = 100 * (df['plus_dm'].rolling(n).mean() / atr)
    minus_di = 100 * (df['minus_dm'].rolling(n).mean() / atr)
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(n).mean()
    return adx.fillna(0)

def calcular_indicadores(df):
    print("🧮 Calculando indicadores...")
    df["EMA10"] = df["close"].ewm(span=10, adjust=False).mean()
    df["EMA20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["MACD"] = df["close"].ewm(span=12, adjust=False).mean() - df["close"].ewm(span=26, adjust=False).mean()
    df["SINAL"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["CCI"] = (df["close"] - df["close"].rolling(20).mean()) / (0.015 * df["close"].rolling(20).std())
    df["ADX"] = calcular_adx(df)
    df["volume_explosivo"] = df["volume"] > df["volume"].rolling(20).mean() * 1.5
    print("✅ Indicadores calculados.")
    return df

def avaliar_sinais(df):
    # Exemplo simplificado: sinais fortes se EMA10 > EMA20 + MACD > SINAL + ADX > 25
    sinais_fortes = 0
    extras = 0

    if df["EMA10"].iloc[-1] > df["EMA20"].iloc[-1]:
        sinais_fortes += 1
    if df["MACD"].iloc[-1] > df["SINAL"].iloc[-1]:
        sinais_fortes += 1
    if df["ADX"].iloc[-1] > 25:
        sinais_fortes += 1
    if df["CCI"].iloc[-1] > 100:
        extras += 1
    if df["volume_explosivo"].iloc[-1]:
        extras += 1

    if sinais_fortes >= 3:
        entrada = "LONG"
    elif sinais_fortes == 0 and extras > 0:
        entrada = "SHORT"
    else:
        entrada = "NENHUMA"

    return sinais_fortes, extras, entrada

def enviar_ordem(symbol, side, quantidade_usdt):
    print(f"💡 Enviando ordem para {symbol}: {side}")
    try:
        # Usa o método correto place_active_order com parâmetros atualizados da API v5
        ordem = session.place_active_order(
            symbol=symbol,
            side=side,
            orderType="Market",
            qty=quantidade_usdt,
            timeInForce="GoodTillCancel",
            reduceOnly=False,
            closeOnTrigger=False
        )
        print(f"✅ Ordem enviada para {symbol}: {ordem}")
    except Exception as e:
        print(f"❌ Erro ao enviar pedido para {symbol}: {e}")

def principal():
    while True:
        for symbol in symbols:
            print(f"\n🔍 Analisando {symbol}")
            df = fetch_candles(symbol, interval)
            df = calcular_indicadores(df)
            sinais_fortes, extras, entrada = avaliar_sinais(df)
            print(f"Sinais fortes: {sinais_fortes}, extras: {extras}, entrada sugerida: {entrada}")

            if entrada in ["LONG", "SHORT"]:
                enviar_ordem(symbol, entrada, quantidade_usdt)
            else:
                print("Nenhuma entrada válida no momento.")

            time.sleep(1)  # evitar chamadas muito rápidas
        print("\n--- Fim de ciclo, aguardando 30 segundos para próxima rodada ---\n")
        time.sleep(30)

if __name__ == "__main__":
    principal()
