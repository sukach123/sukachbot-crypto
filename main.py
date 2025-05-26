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
    # Calcula ADX - Mantém método conforme versão anterior, corrigindo numpy -> pandas
    df['TR'] = np.maximum.reduce([
        df['high'] - df['low'],
        abs(df['high'] - df['close'].shift()),
        abs(df['low'] - df['close'].shift())
    ])
    df['ATR'] = df['TR'].rolling(n).mean()
    df['+DM'] = np.where((df['high'] - df['high'].shift()) > (df['low'].shift() - df['low']),
                         np.maximum(df['high'] - df['high'].shift(), 0), 0)
    df['-DM'] = np.where((df['low'].shift() - df['low']) > (df['high'] - df['high'].shift()),
                         np.maximum(df['low'].shift() - df['low'], 0), 0)

    df['+DI'] = 100 * (df['+DM'].rolling(n).sum() / df['ATR'])
    df['-DI'] = 100 * (df['-DM'].rolling(n).sum() / df['ATR'])
    df['DX'] = 100 * (abs(df['+DI'] - df['-DI']) / (df['+DI'] + df['-DI']))
    adx = df['DX'].rolling(n).mean()
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

def analisar_sinais(df):
    fortes = 0
    extras = 0
    entrada = "NENHUMA"

    # Exemplo simples: sinal forte se EMA10 > EMA20 e MACD > SINAL
    if (df["EMA10"].iloc[-1] > df["EMA20"].iloc[-1]) and (df["MACD"].iloc[-1] > df["SINAL"].iloc[-1]):
        fortes += 1
    # Outro sinal forte: CCI > 100 e ADX > 20
    if (df["CCI"].iloc[-1] > 100) and (df["ADX"].iloc[-1] > 20):
        fortes += 1
    # Sinal extra: volume explosivo
    if df["volume_explosivo"].iloc[-1]:
        extras += 1

    if fortes >= 3:
        entrada = "LONG"
    elif fortes == 2:
        entrada = "NENHUMA"
    elif fortes <= 1:
        entrada = "SHORT"

    return fortes, extras, entrada

def enviar_ordem(symbol, side, quantidade_usdt):
    try:
        # Quantidade em quantidade de contratos / quantidade mínima? Aqui está simplificado
        # Preço de mercado (ordem mercado)
        ordem = session.place_active_order(
            symbol=symbol,
            side=side.upper(),
            orderType="Market",
            qty=quantidade_usdt,
            timeInForce="GoodTillCancel",
            reduceOnly=False,
            closeOnTrigger=False
        )
        print(f"💡 Enviando ordem para {symbol}: {side.upper()}")
        return ordem
    except Exception as e:
        print(f"❌ Erro ao enviar pedido para {symbol}: {e}")
        return None

def main():
    while True:
        for symbol in symbols:
            print(f"\n🔍 Analisando {symbol}")

            print("🧮 Calculando indicadores...")
            df = fetch_candles(symbol, interval)
            df = calcular_indicadores(df)
            print("✅ Indicadores calculados.")

            fortes, extras, entrada = analisar_sinais(df)
            print(f"Sinais fortes: {fortes}, extras: {extras}, entrada sugerida: {entrada}")

            if entrada != "NENHUMA":
                enviar_ordem(symbol, entrada, quantidade_usdt)
            else:
                print("Nenhuma entrada válida no momento.")

            # Retira o sleep para analisar a cada segundo
            # time.sleep(30)

if __name__ == "__main__":
    main()
