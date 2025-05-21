# === SukachBot PRO75 - Agora com TP de 1.5% automático ===

import pandas as pd
import numpy as np
from pybit.unified_trading import HTTP
import time
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# === Configurações ===
symbols = ["BNBUSDT", "BTCUSDT", "DOGEUSDT", "SOLUSDT", "ADAUSDT", "ETHUSDT"]
interval = "1"
api_key = os.getenv("BYBIT_API_KEY")
api_secret = os.getenv("BYBIT_API_SECRET")
quantidade_usdt = 5

session = HTTP(api_key=api_key, api_secret=api_secret, testnet=False)

def fetch_candles(symbol, interval="1"):
    try:
        data = session.get_kline(category="linear", symbol=symbol, interval=interval, limit=200)
        candles = data['result']['list']
        df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"])
        df = df.astype({"open": float, "high": float, "low": float, "close": float, "volume": float})
        df["timestamp"] = pd.to_datetime(pd.to_numeric(df["timestamp"]), unit="ms")
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

    sinais_fortes = [
        row["EMA10"] > row["EMA20"] or row["EMA10"] < row["EMA20"],
        row["MACD"] > row["SINAL"],
        row["CCI"] > 0,
        row["ADX"] > 20,
        row["volume_explosivo"],
        corpo > ultimos5["close"].max() - ultimos5["low"].min(),
        nao_lateral
    ]

    sinais_extras = [
        prev["close"] > prev["open"],
        (row["high"] - row["close"]) < corpo
    ]

    total_confirmados = sum(sinais_fortes) + sum(sinais_extras)

    print(f"\n📊 Diagnóstico de sinais em {row['timestamp']}")
    print(f"✔️ Total: {sum(sinais_fortes)} fortes + {sum(sinais_extras)} extras = {total_confirmados}/9")

    if sum(sinais_fortes) >= 7:
        preco_atual = row["close"]
        diferenca_ema = abs(row["EMA10"] - row["EMA20"])
        limite_colisao = preco_atual * 0.0001

        print(f"🔔 {row['timestamp']} | 7/9 sinais fortes confirmados!")

        if diferenca_ema < limite_colisao:
            print(f"🚫 Entrada bloqueada ❌ - EMAs muito próximas.")
            return None
        else:
            direcao = "Buy" if row["EMA10"] > row["EMA20"] else "Sell"
            print(f"✅ Entrada confirmada! {direcao}")
            return direcao
    else:
        print(f"🔎 {row['timestamp']} | Apenas {total_confirmados}/9 sinais confirmados | Entrada bloqueada ❌")
        return None

def colocar_sl_tp(symbol, lado, preco_entrada, quantidade):
    preco_sl = preco_entrada * 0.994 if lado == "Buy" else preco_entrada * 1.006
    preco_tp = preco_entrada * 1.015 if lado == "Buy" else preco_entrada * 0.985

    for tentativa in range(5):
        try:
            sl_response = session.place_order(
                category="linear",
                symbol=symbol,
                side="Sell" if lado == "Buy" else "Buy",
                orderType="Stop",
                qty=quantidade,
                price=round(preco_sl, 3),
                triggerPrice=round(preco_sl, 3),
                triggerBy="LastPrice",
                reduceOnly=True,
                isIsolated=True
            )

            tp_response = session.place_order(
                category="linear",
                symbol=symbol,
                side="Sell" if lado == "Buy" else "Buy",
                orderType="Limit",
                qty=quantidade,
                price=round(preco_tp, 3),
                reduceOnly=True,
                isIsolated=True
            )

            print(f"🎯 SL e TP colocados com sucesso!")
            print(f"    🔹 SL: {round(preco_sl, 3)} | TP: {round(preco_tp, 3)}")
            return
        except Exception as e:
            print(f"⚠️ Erro ao colocar SL/TP (tentativa {tentativa+1}): {e}")
            time.sleep(2)

def enviar_ordem(symbol, lado):
    try:
        ticker_data = session.get_tickers(category="linear", symbol=symbol)
        preco_atual = float(ticker_data['result']['list'][0]['lastPrice'])
        quantidade = round(quantidade_usdt / preco_atual, 3)

        print(f"📦 Enviando ordem {lado} para {symbol} | Preço: {preco_atual} | Qtd: {quantidade}")

        if quantidade <= 0:
            print("🚫 Quantidade inválida! Ordem não enviada.")
            return

        session.set_leverage(category="linear", symbol=symbol, buyLeverage=10, sellLeverage=10)

        response = session.place_order(
            category="linear",
            symbol=symbol,
            side=lado,
            orderType="Market",
            qty=quantidade,
            reduceOnly=False,
            isIsolated=True
        )

        print(f"🚀 Ordem {lado} executada com sucesso!")
        print(f"    📄 Resposta: {response}")

        colocar_sl_tp(symbol, lado, preco_atual, quantidade)

    except Exception as e:
        print(f"🚨 Erro ao enviar ordem: {e}")
        time.sleep(1)

# === Loop Principal ===
while True:
    inicio = time.time()
    for symbol in symbols:
        try:
            df = fetch_candles(symbol)
            df = calcular_indicadores(df)
            direcao = verificar_entrada(df)
            if direcao:
                enviar_ordem(symbol, direcao)
            else:
                print(f"🔹 {symbol} sem entrada confirmada...")
        except Exception as e:
            print(f"🚨 Erro geral no processamento de {symbol}: {e}")
            time.sleep(1)
    tempo_execucao = time.time() - inicio
    if tempo_execucao < 1:
        time.sleep(1 - tempo_execucao)
