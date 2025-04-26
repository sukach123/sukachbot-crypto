# === SukachBot PRO75 - OPERAÇÃO AO VIVO COM 6 PARES ===

import pandas as pd
import numpy as np
from pybit.unified_trading import HTTP
import time

# === Configurações ===
symbols = ["BNBUSDT", "BTCUSDT", "DOGEUSDT", "SOLUSDT", "ADAUSDT", "ETHUSDT"]
interval = "1"
api_key = "TUA_API_KEY"
api_secret = "TEU_API_SECRET"
quantidade_usdt = 2

session = HTTP(api_key=api_key, api_secret=api_secret, testnet=False)

# === Funções auxiliares ===

def fetch_candles(symbol, interval="1"):
    data = session.get_kline(category="linear", symbol=symbol, interval=interval, limit=200)
    candles = data['result']['list']
    df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"])
    df = df.astype({"open": float, "high": float, "low": float, "close": float, "volume": float})
    df["timestamp"] = pd.to_datetime(pd.to_numeric(df["timestamp"]), unit="ms")
    return df

def calcular_indicadores(df):
    df["EMA10"] = df["close"].ewm(span=10).mean()
    df["EMA20"] = df["close"].ewm(span=20).mean()
    df["MACD"] = df["close"].ewm(span=12).mean() - df["close"].ewm(span=26).mean()
    df["SINAL"] = df["MACD"].ewm(span=9).mean()
    df["CCI"] = (df["close"] - df["close"].rolling(20).mean()) / (0.015 * df["close"].rolling(20).std())
    df["ADX"] = abs(df["high"] - df["low"]).rolling(14).mean()
    df["ATR"] = (df["high"] - df["low"]).rolling(14).mean()
    df["volume_medio"] = df["volume"].rolling(20).mean()
    df["volume_explosivo"] = df["volume"] > 1.3 * df["volume_medio"]
    return df

def verificar_entrada(df):
    row = df.iloc[-1]
    prev = df.iloc[-2]
    ultimos5 = df.iloc[-5:]
    ultimos20 = df.iloc[-20:]
    corpo = abs(row["close"] - row["open"])
    volatilidade = ultimos20["high"].max() - ultimos20["low"].min()
    media_atr = ultimos20["ATR"].mean()
    nao_lateral = volatilidade > (2 * media_atr)

    condicoes = [
        row["EMA10"] > row["EMA20"],
        row["MACD"] > row["SINAL"],
        row["CCI"] > 0,
        row["ADX"] > 20,
        row["volume_explosivo"],
        corpo > ultimos5["close"].max() - ultimos5["low"].min(),
        prev["close"] > prev["open"],
        (row["high"] - row["close"]) < corpo,
        nao_lateral
    ]

    confirmados = sum(condicoes)
    print(f"🔎 {df['timestamp'].iloc[-1]} | {confirmados}/9 sinais confirmados")

    return confirmados == 9

def tentar_colocar_sl(symbol, preco_sl, quantidade, tentativas=3):
    sl_colocado = False
    while not sl_colocado:
        for tentativa in range(tentativas):
            try:
                session.place_order(
                    category="linear",
                    symbol=symbol,
                    side="Sell",
                    orderType="Stop",
                    qty=quantidade,
                    price=round(preco_sl, 3),
                    triggerPrice=round(preco_sl, 3),
                    triggerBy="LastPrice",
                    reduceOnly=True
                )
                print(f"🎯 SL colocado na tentativa {tentativa+1} com sucesso!")
                sl_colocado = True
                break
            except Exception as e:
                print(f"Erro ao colocar SL (tentativa {tentativa+1}): {e}")
                time.sleep(1)
        if not sl_colocado:
            print("⏳ Esperando 15 segundos para tentar novamente colocar SL...")
            time.sleep(15)

def enviar_ordem(symbol):
    preco_atual = float(session.get_ticker(category="linear", symbol=symbol)["result"]["lastPrice"])
    quantidade = round(quantidade_usdt / preco_atual, 3)
    session.set_leverage(category="linear", symbol=symbol, buyLeverage=2, sellLeverage=2)

    try:
        session.place_order(
            category="linear",
            symbol=symbol,
            side="Buy",
            orderType="Market",
            qty=quantidade,
            reduceOnly=False
        )
        print(f"🚀 Compra executada em {symbol} ao preço de {preco_atual}")
        preco_entrada = preco_atual
        sl = preco_entrada * 0.985
        tentar_colocar_sl(symbol, sl, quantidade)
    except Exception as e:
        print(f"Erro ao enviar ordem de compra: {e}")

# === Loop Principal ===

while True:
    for symbol in symbols:
        try:
            df = fetch_candles(symbol)
            df = calcular_indicadores(df)
            if verificar_entrada(df):
                enviar_ordem(symbol)
            else:
                print(f"🔹 {symbol} sem entrada confirmada...")
        except Exception as e:
            print(f"Erro no processamento de {symbol}: {e}")
    time.sleep(1)


