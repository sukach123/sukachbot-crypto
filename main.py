import pandas as pd
import numpy as np
import time
from datetime import datetime, timezone
from pybit.unified_trading import HTTP

# === CONFIGURAÇÕES ===
api_key = "SUA_API"
api_secret = "SEU_SECRET"
symbolos = ["DOGEUSDT", "SOLUSDT", "ADAUSDT", "ETHUSDT", "BNBUSDT"]
quantidade_ordem = 0.02
timeframe = "1m"
limite_velas = 200

tp_percent = 1.5
sl_percent = 1.0

# === CONECTAR COM BYBIT TESTNET ===
sessao = HTTP(
    testnet=True,
    api_key=api_key,
    api_secret=api_secret,
)

def buscar_velas(symbol):
    try:
        resposta = sessao.get_kline(
            category="linear",
            symbol=symbol,
            interval=timeframe,
            limit=limite_velas
        )
        dados = resposta["result"]["list"]
        colunas = ["timestamp", "open", "high", "low", "close", "volume", "turnover"]
        df = pd.DataFrame(dados, columns=colunas)
        df = df.iloc[::-1].copy()  # inverter para ordem crescente
        df["timestamp"] = pd.to_datetime(df["timestamp"].astype(float), unit="ms")
        df.set_index("timestamp", inplace=True)
        df = df.astype(float)
        return df
    except Exception as e:
        print(f"Erro ao buscar velas de {symbol}: {e}")
        return None

def calcular_indicadores(df):
    df["EMA10"] = df["close"].ewm(span=10).mean()
    df["EMA20"] = df["close"].ewm(span=20).mean()
    
    # MACD
    exp1 = df["close"].ewm(span=12, adjust=False).mean()
    exp2 = df["close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = exp1 - exp2
    df["SINAL"] = df["MACD"].ewm(span=9, adjust=False).mean()
    
    # CCI
    tp = (df["high"] + df["low"] + df["close"]) / 3
    ma = tp.rolling(window=20).mean()
    md = tp.rolling(window=20).apply(lambda x: np.mean(np.abs(x - np.mean(x))))
    df["CCI"] = (tp - ma) / (0.015 * md)
    
    # ADX
    df["+DM"] = df["high"].diff()
    df["-DM"] = df["low"].diff()
    df["+DM"] = np.where((df["+DM"] > df["-DM"]) & (df["+DM"] > 0), df["+DM"], 0)
    df["-DM"] = np.where((df["-DM"] > df["+DM"]) & (df["-DM"] > 0), df["-DM"], 0)
    tr = pd.concat([
        df["high"] - df["low"],
        abs(df["high"] - df["close"].shift()),
        abs(df["low"] - df["close"].shift())
    ], axis=1).max(axis=1)
    atr = tr.rolling(window=14).mean()
    df["+DI"] = 100 * (df["+DM"].rolling(window=14).sum() / atr)
    df["-DI"] = 100 * (df["-DM"].rolling(window=14).sum() / atr)
    df["ADX"] = (abs(df["+DI"] - df["-DI"]) / (df["+DI"] + df["-DI"])) * 100
    df["ADX"] = df["ADX"].rolling(window=14).mean()
    
    # ATR
    df["ATR"] = atr

    return df

def avaliar_sinais(df):
    row = df.iloc[-1]
    sinais_fortes = 0
    sinais_extras = 0

    # Fortes
    if row["EMA10"] > row["EMA20"]:
        sinais_fortes += 1
    if row["MACD"] > row["SINAL"]:
        sinais_fortes += 1
    if row["CCI"] > 100:
        sinais_fortes += 1
    if row["+DI"] > row["-DI"]:
        sinais_fortes += 1
    if row["ADX"] > 20:
        sinais_fortes += 1

    # Extras
    if row["close"] > row["EMA10"]:
        sinais_extras += 1
    if row["CCI"] > 0:
        sinais_extras += 1
    if row["MACD"] > 0:
        sinais_extras += 1
    if row["EMA20"] > df["EMA20"].shift(1).iloc[-1]:  # tendência de alta
        sinais_extras += 1

    return sinais_fortes, sinais_extras

def enviar_ordem(symbol, lado, preco_entrada):
    try:
        tp = round(preco_entrada * (1 + (tp_percent / 100)), 5)
        sl = round(preco_entrada * (1 - (sl_percent / 100)), 5)

        resposta = sessao.place_order(
            category="linear",
            symbol=symbol,
            side=lado.upper(),
            order_type="Market",
            qty=quantidade_ordem,
            take_profit=str(tp),
            stop_loss=str(sl),
            time_in_force="GoodTillCancel"
        )

        print(f"✅ Ordem {lado.upper()} enviada para {symbol} | Qtd: {quantidade_ordem}")
    except Exception as e:
        print(f"❌ Erro ao enviar ordem para {symbol}: {e}")

def principal():
    while True:
        agora = datetime.utcnow().replace(tzinfo=timezone.utc)

        for simbolo in symbolos:
            df = buscar_velas(simbolo)
            if df is None or len(df) < 50:
                continue

            ultima_vela = df.index[-1]
            diferenca = (agora - ultima_vela).total_seconds()

            if diferenca > 2:
                continue  # pular se candle estiver atrasado

            df = calcular_indicadores(df)
            fortes, extras = avaliar_sinais(df)

            print(f"\n🔍 Analisando {simbolo}")
            print(f"Sinais fortes: {fortes}, extras: {extras}", end='')

            if fortes >= 6 or (fortes >= 5 and extras >= 2):
                preco_entrada = df["close"].iloc[-1]
                lado = "Buy" if df["EMA10"].iloc[-1] > df["EMA20"].iloc[-1] else "Sell"
                print(f", entrada sugerida: {lado.upper()}")
                enviar_ordem(simbolo, lado, preco_entrada)
            else:
                print(", entrada sugerida: NENHUMA")

        time.sleep(1)

# Iniciar o bot
if __name__ == "__main__":
    principal()


