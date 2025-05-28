import pandas as pd
import numpy as np
from pybit.unified_trading import HTTP
import time
from datetime import datetime, timezone

# === Configuração da API Testnet ===
API_KEY = "SUA_API_KEY_AQUI"
API_SECRET = "SEU_API_SECRET_AQUI"

session = HTTP(
    testnet=True,
    api_key=API_KEY,
    api_secret=API_SECRET
)

symbol = "BTCUSDT"
interval = "1"
qty = 0.01  # Quantidade para abrir a ordem

# === Função para buscar candles ===
def fetch_candles(symbol, interval="1"):
    try:
        data = session.get_kline(
            category="linear",
            symbol=symbol,
            interval=interval,
            limit=100
        )
        df = pd.DataFrame(data['result']['list'], columns=[
            "timestamp", "open", "high", "low", "close", "volume", "turnover"])
        df["timestamp"] = pd.to_datetime(df["timestamp"].astype(np.int64), unit='ms')
        df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].astype(float)
        return df
    except Exception as e:
        print(f"Erro ao buscar candles: {e}")
        return None

# === Função para calcular indicadores ===
def aplicar_indicadores(df):
    df["EMA10"] = df["close"].ewm(span=10, adjust=False).mean()
    df["EMA20"] = df["close"].ewm(span=20, adjust=False).mean()

    # MACD
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["SINAL"] = df["MACD"].ewm(span=9, adjust=False).mean()

    # CCI
    tp = (df["high"] + df["low"] + df["close"]) / 3
    sma = tp.rolling(20).mean()
    mad = tp.rolling(20).apply(lambda x: np.mean(np.abs(x - np.mean(x))))
    df["CCI"] = (tp - sma) / (0.015 * mad)

    # ADX
    df["TR"] = df[["high", "low", "close"]].max(axis=1) - df[["high", "low"]].min(axis=1)
    df["+DM"] = df["high"].diff()
    df["-DM"] = df["low"].diff()
    df["+DM"] = np.where((df["+DM"] > df["-DM"]) & (df["+DM"] > 0), df["+DM"], 0)
    df["-DM"] = np.where((df["-DM"] > df["+DM"]) & (df["-DM"] > 0), df["-DM"], 0)
    tr14 = df["TR"].rolling(window=14).sum()
    plus_dm14 = df["+DM"].rolling(window=14).sum()
    minus_dm14 = df["-DM"].rolling(window=14).sum()
    plus_di14 = 100 * (plus_dm14 / tr14)
    minus_di14 = 100 * (minus_dm14 / tr14)
    dx = 100 * np.abs(plus_di14 - minus_di14) / (plus_di14 + minus_di14)
    df["ADX"] = dx.rolling(window=14).mean()

    return df

# === Função de decisão e envio de ordem ===
def analisar_e_executar(df):
    row = df.iloc[-1]
    agora = row["timestamp"]

    sinais_fortes = []
    sinais_extras = []

    # Sinais fortes
    if row["EMA10"] > row["EMA20"]:
        sinais_fortes.append("EMA10 > EMA20")

    if row["MACD"] > row["SINAL"]:
        sinais_fortes.append("MACD > SINAL")

    if row["CCI"] > 0:
        sinais_fortes.append("CCI > 0")

    if row["ADX"] > 20:
        sinais_fortes.append("ADX > 20")

    if row["close"] > df["close"].rolling(50).mean().iloc[-1]:
        sinais_fortes.append("Preço acima da média 50")

    # Extras
    if row["ADX"] < 50:
        sinais_extras.append("Tendência não exagerada")

    if row["volume"] > df["volume"].rolling(20).mean().iloc[-1]:
        sinais_extras.append("Volume acima da média")

    # Diagnóstico
    print(f"\n📊 Diagnóstico de sinais em {agora}")
    for s in sinais_fortes:
        print(f"✅ {s}")
    for e in sinais_extras:
        print(f"➕ Extra: {e}")

    total = len(sinais_fortes)
    extra = len(sinais_extras)

    print(f"\n✔️ Total: {total} fortes + {extra} extras = {total + extra}/9")

    if total >= 5 or (total == 4 and extra >= 1):
        print(f"\n🔔 Entrada validada em {agora}")
        enviar_ordem(row["close"])

# === Enviar ordem de mercado com TP e SL ===
def enviar_ordem(preco_entrada):
    tp = round(preco_entrada * 1.015, 2)
    sl = round(preco_entrada * 0.997, 2)

    try:
        ordem = session.place_order(
            category="linear",
            symbol=symbol,
            side="Buy",
            order_type="Market",
            qty=qty,
            take_profit=str(tp),
            stop_loss=str(sl),
            time_in_force="GoodTillCancel"
        )
        print("✅ Ordem enviada:", ordem)
    except Exception as e:
        print("🚨 Erro ao enviar ordem:", e)

# === Loop principal ===
while True:
    df = fetch_candles(symbol)
    if df is not None:
        df = aplicar_indicadores(df)
        analisar_e_executar(df)
    time.sleep(60)
