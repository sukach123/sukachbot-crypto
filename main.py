# === SukachBot PRO LIGHT - ENTRADA REAL BNB COM TP/SL AUTOMÁTICO + TRAILING STOP ===

from pybit.unified_trading import HTTP
import pandas as pd
import numpy as np
import time
import os

# === Configurações ===
symbol = "BNBUSDT"
interval = "1"
api_key = "TUA_API_KEY"
api_secret = "TEU_API_SECRET"
quantidade_usdt = 2
trailing_ativo = False
preco_entrada = 0
novo_trailing = 0

session = HTTP(api_key=api_key, api_secret=api_secret, testnet=False)

# === Função para buscar últimos candles ===
def fetch_candles(symbol, interval="1"):
    data = session.get_kline(category="linear", symbol=symbol, interval=interval, limit=200)
    candles = data['result']['list']
    df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"])
    df = df.astype({"open": float, "high": float, "low": float, "close": float, "volume": float})
    df["timestamp"] = pd.to_datetime(pd.to_numeric(df["timestamp"]), unit="ms")
    return df

# === Indicadores ===
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

# === Verificar entrada ===
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

    return all(condicoes)

# === Função para enviar ordem real com TP/SL e ativar trailing ===
def enviar_ordem(symbol, quantidade_usdt):
    global preco_entrada, trailing_ativo
    session.set_leverage(category="linear", symbol=symbol, buyLeverage=2, sellLeverage=2)
    global preco_entrada, trailing_ativo
    preco_atual = session.get_ticker(category="linear", symbol=symbol)["result"]["lastPrice"]
    preco_atual = float(preco_atual)
    quantidade = round(quantidade_usdt / preco_atual, 3)

    try:
        session.place_order(
            category="linear",
            symbol=symbol,
            side="Buy",
            orderType="Market",
            qty=quantidade,
            reduceOnly=False
        )
        preco_entrada = preco_atual
        trailing_ativo = True
        print(f"🚀 ORDEM DE COMPRA ENVIADA! Preço de entrada: {preco_entrada}")
    except Exception as e:
        print(f"Erro ao enviar ordem: {e}")

# === Função para monitorar trailing stop ===
def monitorar_trailing(symbol):
    global preco_entrada, trailing_ativo, novo_trailing
    if not trailing_ativo:
        return

    preco_atual = session.get_ticker(category="linear", symbol=symbol)["result"]["lastPrice"]
    preco_atual = float(preco_atual)

    if preco_atual >= preco_entrada * 1.01:
        novo_trailing = preco_atual * 0.995
        try:
            session.place_order(
                category="linear",
                symbol=symbol,
                side="Sell",
                orderType="Stop",
                qty=round(quantidade_usdt / preco_atual, 3),
                price=round(novo_trailing, 3),
                triggerPrice=round(novo_trailing, 3),
                triggerBy="LastPrice",
                reduceOnly=True
            )
            print(f"🎯 Trailing Stop atualizado para {round(novo_trailing, 3)}")
            preco_entrada = preco_atual
        except Exception as e:
            print(f"Erro ao atualizar trailing stop: {e}")

# === Loop Principal ===
while True:
    df = fetch_candles(symbol)
    df = calcular_indicadores(df)
    if verificar_entrada(df) and not trailing_ativo:
        enviar_ordem(symbol, quantidade_usdt)
    else:
        monitorar_trailing(symbol)
        print("🔹 Sem sinal de entrada novo. A monitorar trailing...")
    time.sleep(1)

