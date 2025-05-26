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
        # Sem alerta de atraso de vela
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
    df["ADX"] = calcular_adx(df)
    df["volume_explosivo"] = df["volume"] > df["volume"].rolling(20).mean() * 1.5
    # Aqui você pode incluir outros indicadores necessários
    return df

def calcular_adx(df, n=14):
    # Cálculo simplificado do ADX, para exemplo
    df['TR'] = np.maximum.reduce([
        df['high'] - df['low'],
        abs(df['high'] - df['close'].shift()),
        abs(df['low'] - df['close'].shift())
    ])
    df['plus_dm'] = np.where((df['high'] - df['high'].shift()) > (df['low'].shift() - df['low']), 
                              np.maximum(df['high'] - df['high'].shift(), 0), 0)
    df['minus_dm'] = np.where((df['low'].shift() - df['low']) > (df['high'] - df['high'].shift()), 
                              np.maximum(df['low'].shift() - df['low'], 0), 0)
    tr_smooth = df['TR'].rolling(n).sum()
    plus_dm_smooth = df['plus_dm'].rolling(n).sum()
    minus_dm_smooth = df['minus_dm'].rolling(n).sum()
    plus_di = 100 * plus_dm_smooth / tr_smooth
    minus_di = 100 * minus_dm_smooth / tr_smooth
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(n).mean()
    return adx

def sinais(df):
    row = df.iloc[-1]
    prev = df.iloc[-2]
    ultimos5 = df.iloc[-6:-1]
    corpo = abs(row["close"] - row["open"])

    sinal_1 = (row["EMA10"] > row["EMA20"]) or (row["EMA10"] < row["EMA20"])
    sinal_2 = row["MACD"] > row["SINAL"]
    sinal_3 = row["CCI"] > 0
    sinal_4 = row["ADX"] > 20
    nao_lateral = True  # Pode definir lógica real aqui
    sinal_5 = nao_lateral

    sinais_fortes = [sinal_1, sinal_2, sinal_3, sinal_4, sinal_5]

    sinal_6 = row["volume_explosivo"]
    sinal_7 = corpo > ultimos5["close"].max() - ultimos5["low"].min()
    extra_1 = prev["close"] > prev["open"]
    extra_2 = (row["high"] - row["close"]) < corpo
    sinais_extras = [sinal_6, sinal_7, extra_1, extra_2]

    fortes = sum(sinais_fortes)
    extras = sum(sinais_extras)

    return fortes, extras

def definir_entrada(fortes, extras):
    if fortes >= 6 or (fortes >= 5 and extras >= 2):
        return "LONG"
    elif fortes <= 3 and extras <= 1:
        return "SHORT"
    else:
        return "NENHUMA"

def colocar_ordem(symbol, side, quantidade, preco_entrada, tp, sl):
    try:
        response = session.place_active_order(
            symbol=symbol,
            side=side,
            orderType="Market",
            qty=quantidade,
            timeInForce="GoodTillCancel",
            takeProfit=tp,
            stopLoss=sl,
            reduceOnly=False,
            closeOnTrigger=False
        )
        print(f"🟢 Ordem {side} enviada para {symbol} - Qtd: {quantidade} USDT")
        print(f"   Preço entrada: {preco_entrada}, TP: {tp}, SL: {sl}")
    except Exception as e:
        print(f"❌ Erro ao enviar pedido para {symbol}: {e}")

def main():
    for symbol in symbols:
        df = fetch_candles(symbol, interval)
        df = calcular_indicadores(df)
        fortes, extras = sinais(df)
        entrada = definir_entrada(fortes, extras)

        print(f"\n🔍 Analisando {symbol}")
        print(f"Sinais fortes: {fortes}, extras: {extras}, entrada sugerida: {entrada}")

        if entrada == "NENHUMA":
            print("\nNenhuma entrada válida no momento.\n")
            continue

        preco_entrada = df["close"].iloc[-1]
        sl = round(preco_entrada * 0.99, 6)  # exemplo SL -1%
        tp = round(preco_entrada * 1.015, 6)  # exemplo TP +1.5%

        # Calcular quantidade em tokens baseada na quantidade_usdt (simplificação)
        quantidade = quantidade_usdt / preco_entrada

        side = "Buy" if entrada == "LONG" else "Sell"
        colocar_ordem(symbol, side, quantidade, preco_entrada, tp, sl)

        time.sleep(1)

if __name__ == "__main__":
    while True:
        main()
        time.sleep(30)  # Roda a cada 30 segundos, pode ajustar para menor se quiser


