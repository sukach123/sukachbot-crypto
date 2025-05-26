import pandas as pd
import numpy as np
from pybit.unified_trading import HTTP
import time
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

print("🚧 MODO DEMO ATIVO - Bybit Testnet em execução 🚧")

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
    df["ADX"] = ... # calcula ADX (implementa conforme necessário)
    df["volume_explosivo"] = ... # lógica para volume explosivo (implementa conforme necessário)
    # Aqui vai lógica do lateral ou não
    df["nao_lateral"] = ... # lógica que define lateralidade
    
    return df

def sinais(df):
    row = df.iloc[-1]
    prev = df.iloc[-2]
    ultimos5 = df.iloc[-6:-1]

    corpo = abs(row["close"] - row["open"])

    sinal_1 = row["EMA10"] > row["EMA20"]
    sinal_2 = row["MACD"] > row["SINAL"]
    sinal_3 = row["CCI"] > 0
    sinal_4 = row["ADX"] > 20
    sinal_5 = row["nao_lateral"]

    sinais_fortes = [sinal_1, sinal_2, sinal_3, sinal_4, sinal_5]

    sinal_6 = row["volume_explosivo"]
    sinal_7 = corpo > (ultimos5["close"].max() - ultimos5["low"].min())
    extra_1 = prev["close"] > prev["open"]
    extra_2 = (row["high"] - row["close"]) < corpo

    sinais_extras = [sinal_6, sinal_7, extra_1, extra_2]

    fortes_verdadeiros = sum(sinais_fortes)
    extras_verdadeiros = sum(sinais_extras)

    return fortes_verdadeiros, extras_verdadeiros

def colocar_ordem(symbol, lado, quantidade, preco_tp, preco_sl):
    try:
        lado_api = "Buy" if lado == "LONG" else "Sell"
        ordem = session.place_order(
            symbol=symbol,
            side=lado_api,
            orderType="Market",
            qty=str(round(quantidade, 8)),
            timeInForce="GoodTillCancel",
            takeProfit=str(round(preco_tp, 8)),
            stopLoss=str(round(preco_sl, 8)),
        )
        print(f"✅ Ordem {lado} enviada para {symbol} - Qtd: {quantidade} USDT")
        print(f"   Preço entrada: (market), TP: {preco_tp}, SL: {preco_sl}")
        return ordem
    except Exception as e:
        print(f"❌ Erro ao enviar pedido para {symbol}: {e}")

def main():
    for symbol in symbols:
        print(f"\n🔍 Analisando {symbol}")
        df = fetch_candles(symbol, interval)
        df = calcular_indicadores(df)
        fortes, extras = sinais(df)

        if fortes >= 6 or (fortes >= 5 and extras >= 2):
            lado = "LONG"
        elif fortes <= 2 and extras == 0:
            lado = "SHORT"
        else:
            lado = "NONE"

        print(f"Sinais fortes: {fortes}, extras: {extras}, entrada sugerida: {lado}")

        if lado != "NONE":
            preco_entrada = df["close"].iloc[-1]
            tp = preco_entrada * 1.015
            sl = preco_entrada * 0.99

            quantidade = quantidade_usdt / preco_entrada

            colocar_ordem(symbol, lado, quantidade, tp, sl)
        else:
            print("Sem entrada para hoje.")

if __name__ == "__main__":
    while True:
        main()
        time.sleep(60)

