# === SukachBot PRO75 - Agora com TP de 1.5%, SL de 1% e análise por segundo ===

import pandas as pd
import numpy as np
import time
from datetime import datetime
from pybit.unified_trading import HTTP

# === Configuração ===
api_key = "SUA_API_KEY"
api_secret = "SEU_API_SECRET"

session = HTTP(
    api_key=api_key,
    api_secret=api_secret,
    testnet=True,
)

symbolos = ["DOGEUSDT", "SOLUSDT", "ADAUSDT", "ETHUSDT", "BNBUSDT"]
quantidade_ordem = 0.02
tempo_candle = 1  # minutos

def buscar_candles(symbol):
    try:
        dados = session.get_kline(
            category="linear",
            symbol=symbol,
            interval=str(tempo_candle),
            limit=100
        )["result"]["list"]
        df = pd.DataFrame(dados, columns=["timestamp", "open", "high", "low", "close", "volume", "_", "__"])
        df["timestamp"] = pd.to_datetime(df["timestamp"].astype(float), unit="ms")
        df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].astype(float)
        return df
    except Exception as e:
        print(f"Erro ao buscar candles de {symbol}: {e}")
        return None

def calcular_indicadores(df):
    df["EMA10"] = df["close"].ewm(span=10, adjust=False).mean()
    df["EMA20"] = df["close"].ewm(span=20, adjust=False).mean()
    
    # MACD
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["SINAL"] = df["MACD"].ewm(span=9, adjust=False).mean()

    # CCI
    tp = (df["high"] + df["low"] + df["close"]) / 3
    cci = (tp - tp.rolling(20).mean()) / (0.015 * tp.rolling(20).std())
    df["CCI"] = cci

    # ADX
    df["TR"] = df[["high", "low", "close"]].max(axis=1) - df[["high", "low"]].min(axis=1)
    df["+DM"] = np.where((df["high"].diff() > df["low"].diff()) & (df["high"].diff() > 0), df["high"].diff(), 0)
    df["-DM"] = np.where((df["low"].diff() > df["high"].diff()) & (df["low"].diff() > 0), df["low"].diff(), 0)
    df["+DI"] = 100 * (df["+DM"].rolling(14).sum() / df["TR"].rolling(14).sum())
    df["-DI"] = 100 * (df["-DM"].rolling(14).sum() / df["TR"].rolling(14).sum())
    dx = (abs(df["+DI"] - df["-DI"]) / (df["+DI"] + df["-DI"])) * 100
    df["ADX"] = dx.rolling(14).mean()

    return df

def contar_sinais(row):
    sinais_fortes = 0
    extras = 0

    # Fortes
    if row["EMA10"] > row["EMA20"]: sinais_fortes += 1
    if row["MACD"] > row["SINAL"]: sinais_fortes += 1
    if row["CCI"] > 100: sinais_fortes += 1
    if row["ADX"] > 20: sinais_fortes += 1
    if row["close"] > row["EMA20"]: sinais_fortes += 1

    # Extras
    if row["EMA10"] > row["EMA20"] and row["MACD"] > row["SINAL"]: extras += 1
    if row["CCI"] > 0 and row["ADX"] > 25: extras += 1
    if row["volume"] > df["volume"].rolling(20).mean().iloc[-1]: extras += 1
    if row["close"] > row["EMA10"]: extras += 1

    return sinais_fortes, extras

def colocar_ordem(symbol, direcao, preco_entrada):
    tp = round(preco_entrada * 1.015, 4)
    sl = round(preco_entrada * 0.99, 4)
    side = "Buy" if direcao == "LONG" else "Sell"

    try:
        session.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            order_type="Market",
            qty=quantidade_ordem,
            take_profit=str(tp),
            stop_loss=str(sl),
            time_in_force="GoodTillCancel",
            reduce_only=False
        )
        print(f"✅ Ordem {direcao} enviada para {symbol} - Qtd: {quantidade_ordem} | TP: {tp} | SL: {sl}")
    except Exception as e:
        print(f"❌ Erro ao enviar ordem para {symbol}: {e}")

def analisar_mercado():
    for symbol in symbolos:
        df = buscar_candles(symbol)
        if df is None or len(df) < 50:
            continue

        df = calcular_indicadores(df)
        row = df.iloc[-1]

        # Verifica atraso da vela
        agora = pd.Timestamp.utcnow()
        delta = (agora - row["timestamp"]).total_seconds()
        if delta > 2:
            continue  # Pula se candle atrasado

        fortes, extras = contar_sinais(row)

        direcao = "NENHUMA"
        if fortes >= 5:
            direcao = "LONG"
        elif fortes == 4 and extras >= 2:
            direcao = "LONG"

        if fortes <= -5:
            direcao = "SHORT"
        elif fortes <= -4 and extras >= 2:
            direcao = "SHORT"

        print(f"\n🔍 Analisando {symbol}")
        print(f"Sinais fortes: {fortes}, extras: {extras}, entrada sugerida: {direcao}")

        if direcao in ["LONG", "SHORT"]:
            colocar_ordem(symbol, direcao, row["close"])

# === Loop principal ===
while True:
    analisar_mercado()
    time.sleep(1)


