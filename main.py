# === SukachBot PRO75 - TP 1.5% | SL 1% | Loop por segundo ===

import pandas as pd
import numpy as np
import time
from datetime import datetime
from pybit.unified_trading import HTTP
import pytz

# Configurações
API_KEY = "YOUR_API_KEY"
API_SECRET = "YOUR_API_SECRET"
SYMBOLS = ["DOGEUSDT", "SOLUSDT", "ADAUSDT", "ETHUSDT", "BNBUSDT"]
INTERVAL = "1"
QTD_ORDEM = 0.02
TP_PERCENT = 0.015
SL_PERCENT = 0.01

# Sessão Bybit Testnet
session = HTTP(
    testnet=True,
    api_key=API_KEY,
    api_secret=API_SECRET
)

# Calcula indicadores técnicos
def calcular_indicadores(df):
    df["EMA10"] = df["close"].ewm(span=10).mean()
    df["EMA20"] = df["close"].ewm(span=20).mean()

    df["MACD"] = df["close"].ewm(span=12).mean() - df["close"].ewm(span=26).mean()
    df["SINAL"] = df["MACD"].ewm(span=9).mean()

    df["CCI"] = (df["close"] - df["close"].rolling(20).mean()) / (0.015 * df["close"].rolling(20).std())

    df["ATR"] = (df["high"] - df["low"]).rolling(14).mean()

    df["ADX"] = calcular_adx(df, 14)
    return df

# ADX manual
def calcular_adx(df, n):
    plus_dm = df["high"].diff()
    minus_dm = df["low"].diff()
    tr = df[["high", "low", "close"]].max(axis=1) - df[["high", "low", "close"]].min(axis=1)
    tr_smooth = tr.rolling(n).mean()
    plus_di = 100 * (plus_dm.rolling(n).mean() / tr_smooth)
    minus_di = 100 * (minus_dm.rolling(n).mean() / tr_smooth)
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    return dx.rolling(n).mean()

# Busca candles
def buscar_candles(simbolo):
    try:
        dados = session.get_kline(
            category="linear",
            symbol=simbolo,
            interval=INTERVAL,
            limit=100
        )
        candles = dados["result"]["list"]
        df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"])
        df = df.astype(float)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df
    except Exception as e:
        print(f"Erro ao buscar candles de {simbolo}: {e}")
        return None

# Valida sinais
def verificar_sinais(row):
    sinais_fortes = 0
    sinais_extras = 0

    if row["EMA10"] > row["EMA20"]:
        sinais_fortes += 1
    if row["MACD"] > row["SINAL"]:
        sinais_fortes += 1
    if row["CCI"] > 100:
        sinais_fortes += 1
    if row["ADX"] > 20:
        sinais_fortes += 1
    if row["close"] > row["EMA10"]:
        sinais_fortes += 1

    if row["CCI"] > 200:
        sinais_extras += 1
    if row["close"] > row["EMA20"]:
        sinais_extras += 1
    if row["volume"] > row["volume"].mean():
        sinais_extras += 1
    if row["ATR"] > row["ATR"].mean():
        sinais_extras += 1

    return sinais_fortes, sinais_extras

# Envia ordem
def enviar_ordem(simbolo, lado, preco_entrada):
    try:
        sl = round(preco_entrada * (1 - SL_PERCENT if lado == "Buy" else 1 + SL_PERCENT), 4)
        tp = round(preco_entrada * (1 + TP_PERCENT if lado == "Buy" else 1 - TP_PERCENT), 4)

        resposta = session.place_order(
            category="linear",
            symbol=simbolo,
            side=lado,
            order_type="Market",
            qty=QTD_ORDEM,
            take_profit=tp,
            stop_loss=sl,
            time_in_force="GoodTillCancel"
        )
        print(f"🟢 Ordem {lado} enviada para {simbolo} | TP: {tp} | SL: {sl}")
    except Exception as e:
        print(f"❌ Erro ao enviar ordem para {simbolo}: {e}")

# Loop principal
def principal():
    while True:
        for simbolo in SYMBOLS:
            df = buscar_candles(simbolo)
            if df is None or len(df) < 50:
                continue

            df = calcular_indicadores(df)
            row = df.iloc[-1]
            agora = datetime.utcnow().replace(tzinfo=pytz.utc)
            atraso = (agora - row["timestamp"]).total_seconds()

            if atraso > 2:
                continue  # Ignora velas antigas

            fortes, extras = verificar_sinais(row)

            print(f"\n🔍 Analisando {simbolo}")
            print(f"Sinais fortes: {fortes}, extras: {extras}", end='')

            if fortes >= 6 or (fortes >= 5 and extras >= 2):
                print(" → Entrada sugerida: LONG")
                enviar_ordem(simbolo, "Buy", row["close"])
            elif fortes <= 1 and extras >= 3:
                print(" → Entrada sugerida: SHORT")
                enviar_ordem(simbolo, "Sell", row["close"])
            else:
                print(" → Entrada sugerida: NENHUMA")

        time.sleep(1)  # Espera 1 segundo

# Inicia o bot
if __name__ == "__main__":
    principal()


