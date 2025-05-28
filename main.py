# === SukachBot PRO75 - Agora com TP de 1.5% automático e SL de -0.3% ===

import pandas as pd
import numpy as np
import time
import threading
from pybit.unified_trading import HTTP, WebSocket

# Configurações
API_KEY = 'SUA_API_KEY'
API_SECRET = 'SEU_API_SECRET'
SYMBOL = "BTCUSDT"
INTERVAL = "1"  # 1 minuto ainda necessário para candle de referência
TP_PERCENT = 1.5 / 100
SL_PERCENT = 0.3 / 100

session = HTTP(api_key=API_KEY, api_secret=API_SECRET)

# WebSocket com channel_type obrigatório
ws = WebSocket(
    testnet=False,
    channel_type="linear",
    api_key=API_KEY,
    api_secret=API_SECRET
)

# Lógica de 5 sinais fortes
def calcular_sinais(df):
    sinais = {
        "ema10_ema20": False,
        "macd": False,
        "rsi": False,
        "volume": False,
        "extra": False
    }

    # EMA
    df["EMA10"] = df["close"].ewm(span=10).mean()
    df["EMA20"] = df["close"].ewm(span=20).mean()
    if df["EMA10"].iloc[-1] > df["EMA20"].iloc[-1]:
        sinais["ema10_ema20"] = True

    # MACD
    exp1 = df["close"].ewm(span=12, adjust=False).mean()
    exp2 = df["close"].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    if macd.iloc[-1] > signal.iloc[-1]:
        sinais["macd"] = True

    # RSI
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    if rsi.iloc[-1] < 70 and rsi.iloc[-1] > 30:
        sinais["rsi"] = True

    # Volume (comparado com média)
    media_volume = df["volume"].rolling(window=20).mean()
    if df["volume"].iloc[-1] > media_volume.iloc[-1]:
        sinais["volume"] = True

    # Sinal extra: candle de alta
    if df["close"].iloc[-1] > df["open"].iloc[-1]:
        sinais["extra"] = True

    return sinais

# Função de entrada
def verificar_entrada(sinais):
    sinais_ativos = [v for v in sinais.values() if v]
    if len(sinais_ativos) >= 5:
        return True
    elif list(sinais.values()).count(True) == 4 and sinais["extra"]:
        return True
    return False

# Execução da ordem
def executar_ordem(ultimo_preco):
    tp = ultimo_preco * (1 + TP_PERCENT)
    sl = ultimo_preco * (1 - SL_PERCENT)

    print(f"✅ Enviando ordem: TP={tp:.2f}, SL={sl:.2f}")

    order = session.place_order(
        category="linear",
        symbol=SYMBOL,
        side="Buy",
        order_type="Market",
        qty=0.01,
        take_profit=round(tp, 2),
        stop_loss=round(sl, 2),
        time_in_force="GoodTillCancel"
    )

    print(f"📦 Ordem enviada: {order}")

# Callback do WebSocket
def handle_candle(message):
    try:
        if message["type"] != "snapshot" and "data" in message:
            candles = message["data"]
            df = pd.DataFrame(candles)
            df["open"] = df["o"].astype(float)
            df["high"] = df["h"].astype(float)
            df["low"] = df["l"].astype(float)
            df["close"] = df["c"].astype(float)
            df["volume"] = df["v"].astype(float)
            df = df[["open", "high", "low", "close", "volume"]]

            sinais = calcular_sinais(df)

            if verificar_entrada(sinais):
                ultimo_preco = df["close"].iloc[-1]
                executar_ordem(ultimo_preco)
            else:
                print("⚠️  Sinais insuficientes para entrada.")

    except Exception as e:
        print(f"❌ Erro ao processar candle: {e}")

# Iniciar WebSocket para candles de 1 minuto (BTCUSDT)
ws.kline_stream(
    symbol=SYMBOL,
    interval=INTERVAL,
    callback=handle_candle
)

print("📡 WebSocket iniciado e ouvindo candles a cada segundo...")

# Manter o script rodando
while True:
    time.sleep(1)

