# === SukachBot PRO75 - Agora com TP de 1.5% automático e SL de -1% ===

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

def calcular_indicadores(df):
    df["EMA10"] = df["close"].ewm(span=10).mean()
    df["EMA20"] = df["close"].ewm(span=20).mean()
    df["MACD"] = df["close"].ewm(span=12).mean() - df["close"].ewm(span=26).mean()
    df["SINAL"] = df["MACD"].ewm(span=9).mean()
    df["CCI"] = (df["close"] - df["close"].rolling(20).mean()) / (0.015 * df["close"].rolling(20).std())
    df["ADX"] = calcular_adx(df)  # função ADX que você deve implementar
    df["volume_explosivo"] = df["volume"] > df["volume"].rolling(20).mean() * 1.5
    # Defina seu critério de "não lateral" aqui:
    df["nao_lateral"] = (df["EMA10"] > df["EMA20"]) | (df["EMA10"] < df["EMA20"])
    return df

def calcular_adx(df, period=14):
    # Cálculo simples de ADX (você pode adaptar)
    df['TR'] = np.maximum.reduce([
        df['high'] - df['low'],
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    ])
    df['+DM'] = np.where((df['high'] - df['high'].shift(1)) > (df['low'].shift(1) - df['low']),
                         np.maximum(df['high'] - df['high'].shift(1), 0), 0)
    df['-DM'] = np.where((df['low'].shift(1) - df['low']) > (df['high'] - df['high'].shift(1)),
                         np.maximum(df['low'].shift(1) - df['low'], 0), 0)
    df['TR_smooth'] = df['TR'].rolling(window=period).sum()
    df['+DM_smooth'] = df['+DM'].rolling(window=period).sum()
    df['-DM_smooth'] = df['-DM'].rolling(window=period).sum()
    df['+DI'] = 100 * (df['+DM_smooth'] / df['TR_smooth'])
    df['-DI'] = 100 * (df['-DM_smooth'] / df['TR_smooth'])
    df['DX'] = 100 * (abs(df['+DI'] - df['-DI']) / (df['+DI'] + df['-DI']))
    adx = df['DX'].rolling(window=period).mean()
    return adx

def avaliar_sinais(row, ultimos5, prev):
    corpo = abs(row["close"] - row["open"])

    # Sinais fortes (5)
    sinal_1 = (row["EMA10"] > row["EMA20"]) or (row["EMA10"] < row["EMA20"])
    sinal_2 = row["MACD"] > row["SINAL"]
    sinal_3 = row["CCI"] > 0
    sinal_4 = row["ADX"] > 20
    sinal_5 = row["nao_lateral"]

    sinais_fortes = [sinal_1, sinal_2, sinal_3, sinal_4, sinal_5]

    # Sinais extras (4)
    sinal_6 = row["volume_explosivo"]
    sinal_7 = corpo > ultimos5["close"].max() - ultimos5["low"].min()
    extra_1 = prev["close"] > prev["open"]
    extra_2 = (row["high"] - row["close"]) < corpo

    sinais_extras = [sinal_6, sinal_7, extra_1, extra_2]

    return sinais_fortes, sinais_extras

def colocar_ordem(symbol, side, quantidade, preco_entrada):
    tp_perc = 0.015  # Take Profit 1.5%
    sl_perc = 0.01   # Stop Loss 1%

    if side == "Buy":
        tp = preco_entrada * (1 + tp_perc)
        sl = preco_entrada * (1 - sl_perc)
    else:  # Sell (Short)
        tp = preco_entrada * (1 - tp_perc)
        sl = preco_entrada * (1 + sl_perc)

    try:
        order = session.place_order(
            symbol=symbol,
            side=side,
            orderType="Market",
            qty=quantidade,
            timeInForce="GoodTillCancel",
            takeProfit=tp,
            stopLoss=sl
        )
        print(f"🟢 Ordem {side} enviada para {symbol} - Qtd: {quantidade} USDT")
        print(f"   Preço de entrada: {preco_entrada}, TP: {tp}, SL: {sl}")
        return order
    except Exception as e:
        print(f"❌ Erro ao enviar pedido para {symbol}: {e}")
        return None

def main():
    while True:
        for symbol in symbols:
            print(f"\n🔍 Analisando {symbol}")
            df = fetch_candles(symbol, interval)
            df = calcular_indicadores(df)

            row = df.iloc[-1]
            prev = df.iloc[-2]
            ultimos5 = df.iloc[-6:-1]

            sinais_fortes, sinais_extras = avaliar_sinais(row, ultimos5, prev)

            fortes_count = sum(sinais_fortes)
            extras_count = sum(sinais_extras)

            entrada = "NONE"
            if fortes_count >= 5 and extras_count >= 2:
                entrada = "LONG"
            elif fortes_count == 6:
                entrada = "LONG"
            elif fortes_count >= 5 and extras_count < 2:
                entrada = "LONG"
            else:
                entrada = "NONE"

            print(f"\nSinais fortes: {fortes_count}, extras: {extras_count}, entrada sugerida: {entrada}")

            if entrada == "LONG":
                preco_entrada = row["close"]
                quantidade = quantidade_usdt / preco_entrada
                colocar_ordem(symbol, "Buy", quantidade, preco_entrada)

            elif entrada == "SHORT":
                preco_entrada = row["close"]
                quantidade = quantidade_usdt / preco_entrada
                colocar_ordem(symbol, "Sell", quantidade, preco_entrada)

            else:
                print(f"🔕 Sem sinais suficientes para entrada em {symbol}")

        time.sleep(60)  # Espera 1 minuto entre as análises

if __name__ == "__main__":
    main()

