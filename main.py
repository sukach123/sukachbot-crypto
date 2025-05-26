# === SukachBot PRO75 - Agora com TP de 1.5% automático e SL de -0.3% ===

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
    df["ADX"] = calcular_adx(df)  # Função para calcular ADX precisa ser implementada

    return df

def calcular_adx(df, n=14):
    # Cálculo simplificado do ADX
    df['TR'] = np.maximum.reduce([
        df['high'] - df['low'],
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    ])
    df['+DM'] = np.where((df['high'] - df['high'].shift(1)) > (df['low'].shift(1) - df['low']), 
                         np.maximum(df['high'] - df['high'].shift(1), 0), 0)
    df['-DM'] = np.where((df['low'].shift(1) - df['low']) > (df['high'] - df['high'].shift(1)), 
                         np.maximum(df['low'].shift(1) - df['low'], 0), 0)

    df['TRn'] = df['TR'].rolling(n).sum()
    df['+DMn'] = df['+DM'].rolling(n).sum()
    df['-DMn'] = df['-DM'].rolling(n).sum()

    df['+DI'] = 100 * (df['+DMn'] / df['TRn'])
    df['-DI'] = 100 * (df['-DMn'] / df['TRn'])
    df['DX'] = 100 * abs(df['+DI'] - df['-DI']) / (df['+DI'] + df['-DI'])

    df['ADX'] = df['DX'].rolling(n).mean()
    return df['ADX']

def analisar_sinais(df):
    row = df.iloc[-1]
    ultimos5 = df.iloc[-6:-1]
    prev = df.iloc[-2]

    corpo = abs(row["close"] - row["open"])

    # Sinais Fortes (5)
    sinal_1 = row["EMA10"] > row["EMA20"]
    sinal_2 = row["MACD"] > row["SINAL"]
    sinal_3 = row["CCI"] > 0
    sinal_4 = row["ADX"] > 20
    nao_lateral = (row["EMA10"] - row["EMA20"]) > 0.01  # Exemplo, pode ajustar
    sinal_5 = nao_lateral

    sinais_fortes = [sinal_1, sinal_2, sinal_3, sinal_4, sinal_5]

    # Sinais Extras (4)
    sinal_6 = row["volume"] > ultimos5["volume"].mean() * 1.5
    sinal_7 = corpo > (ultimos5["close"].max() - ultimos5["low"].min())
    extra_1 = prev["close"] > prev["open"]
    extra_2 = (row["high"] - row["close"]) < corpo
    sinais_extras = [sinal_6, sinal_7, extra_1, extra_2]

    count_fortes = sum(sinais_fortes)
    count_extras = sum(sinais_extras)

    entrada = None
    if count_fortes >= 6:
        entrada = "LONG"
    elif count_fortes >= 5 and count_extras >= 2:
        entrada = "LONG"
    elif count_fortes <= 2:  # exemplo para SHORT, ajustar conforme lógica
        entrada = "SHORT"
    else:
        entrada = "NONE"

    return count_fortes, count_extras, entrada

def colocar_ordem(symbol, side, quantidade, preco_entrada):
    tp_percent = 0.015  # 1.5%
    sl_percent = 0.003  # 0.3%

    if side == "LONG":
        tp_price = preco_entrada * (1 + tp_percent)
        sl_price = preco_entrada * (1 - sl_percent)
    else:  # SHORT
        tp_price = preco_entrada * (1 - tp_percent)
        sl_price = preco_entrada * (1 + sl_percent)

    try:
        order = session.post_active_order(
            symbol=symbol,
            side=side,
            orderType="Market",
            qty=quantidade,
            price=None,
            timeInForce="GoodTillCancel",
            takeProfit=round(tp_price, 8),
            stopLoss=round(sl_price, 8),
            reduceOnly=False,
            closeOnTrigger=False
        )
        print(f"🟢 Ordem {side} enviada para {symbol} - Qtd: {quantidade}")
        print(f"   Preço entrada: {preco_entrada}, TP: {tp_price}, SL: {sl_price}")
    except Exception as e:
        print(f"❌ Erro ao enviar pedido para {symbol}: {e}")

def main():
    while True:
        for symbol in symbols:
            df = fetch_candles(symbol, interval)
            df = calcular_indicadores(df)
            fortes, extras, entrada = analisar_sinais(df)

            print(f"🔍 Analisando {symbol}")
            print(f"Sinais fortes: {fortes}, extras: {extras}, entrada sugerida: {entrada}")

            if entrada in ["LONG", "SHORT"]:
                preco_entrada = df["close"].iloc[-1]
                quantidade = quantidade_usdt / preco_entrada
                colocar_ordem(symbol, entrada, quantidade, preco_entrada)

            time.sleep(1)
        time.sleep(30)

if __name__ == "__main__":
    main()
