# === SukachBot PRO75 - Agora com TP de 1.5% automático e SL de -0.3% ===

import pandas as pd
import numpy as np
from pybit.unified_trading import HTTP
import time

# Configurações da API
api_key = "SUA_API_KEY"
api_secret = "SEU_API_SECRET"

session = HTTP(
    testnet=True,  # False para conta real
    api_key=api_key,
    api_secret=api_secret,
)

# Par de trading e timeframe
symbol = "BTCUSDT"
intervalo = "15"  # minutos

# Função para buscar dados de candles
def get_ohlcv(symbol, interval="15", limit=100):
    klines = session.get_kline(
        category="linear",
        symbol=symbol,
        interval=interval,
        limit=limit
    )
    df = pd.DataFrame(klines["result"]["list"])
    df.columns = [
        "timestamp", "open", "high", "low", "close", "volume",
        "_", "_", "_", "_", "_", "_"
    ]
    df["close"] = df["close"].astype(float)
    df["open"] = df["open"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit='ms')
    return df

# Indicadores
def calcular_indicadores(df):
    df["EMA20"] = df["close"].ewm(span=20).mean()
    df["EMA50"] = df["close"].ewm(span=50).mean()

    # MACD
    ema12 = df["close"].ewm(span=12).mean()
    ema26 = df["close"].ewm(span=26).mean()
    df["MACD"] = ema12 - ema26
    df["SINAL"] = df["MACD"].ewm(span=9).mean()

    # CCI
    TP = (df["high"] + df["low"] + df["close"]) / 3
    df["CCI"] = (TP - TP.rolling(20).mean()) / (0.015 * TP.rolling(20).std())

    # ADX
    df["+DM"] = df["high"].diff()
    df["-DM"] = df["low"].diff()
    df["+DM"] = np.where((df["+DM"] > df["-DM"]) & (df["+DM"] > 0), df["+DM"], 0)
    df["-DM"] = np.where((df["-DM"] > df["+DM"]) & (df["-DM"] > 0), df["-DM"], 0)
    tr1 = df["high"] - df["low"]
    tr2 = abs(df["high"] - df["close"].shift())
    tr3 = abs(df["low"] - df["close"].shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df["TR"] = tr
    df["+DI"] = 100 * (df["+DM"].rolling(14).sum() / df["TR"].rolling(14).sum())
    df["-DI"] = 100 * (df["-DM"].rolling(14).sum() / df["TR"].rolling(14).sum())
    df["DX"] = (abs(df["+DI"] - df["-DI"]) / (df["+DI"] + df["-DI"])) * 100
    df["ADX"] = df["DX"].rolling(14).mean()

    return df

# Lógica de entrada
def verificar_entrada(row):
    sinal_1 = row["EMA20"] > row["EMA50"]
    sinal_2 = row["MACD"] > row["SINAL"]
    sinal_3 = row["CCI"] > 0
    sinal_4 = row["ADX"] > 20
    sinal_5 = row["+DI"] > row["-DI"]

    sinais_fortes = [sinal_1, sinal_2, sinal_3, sinal_4, sinal_5]
    total_fortes = sum(sinais_fortes)

    # Sinal extra opcional (ex: candle de alta)
    candle_alta = row["close"] > row["open"]

    if total_fortes == 5:
        return True
    elif total_fortes == 4 and candle_alta:
        return True
    else:
        return False

# Enviar ordem
def enviar_ordem_compra(preco_entrada, capital_total):
    risco_pct = 0.01  # 1% do capital
    risco_valor = capital_total * risco_pct
    qtd = round(risco_valor / preco_entrada, 3)

    tp = round(preco_entrada * 1.015, 2)
    sl = round(preco_entrada * 0.997, 2)

    try:
        ordem = session.place_active_order(
            category="linear",
            symbol=symbol,
            side="Buy",
            order_type="Market",
            qty=qtd,
            take_profit=tp,
            stop_loss=sl,
            time_in_force="GoodTillCancel",
        )
        print("✅ Ordem executada!")
        print("🎯 TP:", tp, "| 🛑 SL:", sl)
    except Exception as e:
        print("❌ Erro ao enviar ordem:", e)

# Loop principal
capital_simulado = 1000  # simulação de capital

while True:
    try:
        df = get_ohlcv(symbol, intervalo)
        df = calcular_indicadores(df)

        ultima_linha = df.iloc[-1]

        if verificar_entrada(ultima_linha):
            preco_atual = ultima_linha["close"]
            enviar_ordem_compra(preco_atual, capital_simulado)
        else:
            print("⏳ Aguardando sinais...")

    except Exception as e:
        print("⚠️ Erro no loop principal:", e)

    time.sleep(60 * int(intervalo))  # Espera o tempo do candle

