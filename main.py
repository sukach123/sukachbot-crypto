import pandas as pd
import numpy as np
from pybit.unified_trading import HTTP
import time
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

# === Configurações ===
symbols = ["BNBUSDT", "BTCUSDT", "DOGEUSDT", "SOLUSDT", "ADAUSDT", "ETHUSDT"]
interval = "1"  # 1 minuto
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
        return fetch_candles(symbol, interval)

def calcular_indicadores(df):
    # EMA
    df["EMA10"] = df["close"].ewm(span=10).mean()
    df["EMA20"] = df["close"].ewm(span=20).mean()

    # MACD e sinal
    ema12 = df["close"].ewm(span=12).mean()
    ema26 = df["close"].ewm(span=26).mean()
    df["MACD"] = ema12 - ema26
    df["SINAL"] = df["MACD"].ewm(span=9).mean()

    # CCI
    tp = (df["high"] + df["low"] + df["close"]) / 3
    sma_tp = tp.rolling(20).mean()
    mad = tp.rolling(20).apply(lambda x: np.fabs(x - x.mean()).mean())
    df["CCI"] = (tp - sma_tp) / (0.015 * mad)

    # TR, ATR, ADX
    df["TR"] = np.maximum.reduce([
        df["high"] - df["low"],
        abs(df["high"] - df["close"].shift()),
        abs(df["low"] - df["close"].shift())
    ])
    df["ATR"] = df["TR"].rolling(14).mean()

    # Calculando +DI e -DI para ADX
    df["up_move"] = df["high"] - df["high"].shift()
    df["down_move"] = df["low"].shift() - df["low"]
    df["+DM"] = np.where((df["up_move"] > df["down_move"]) & (df["up_move"] > 0), df["up_move"], 0)
    df["-DM"] = np.where((df["down_move"] > df["up_move"]) & (df["down_move"] > 0), df["down_move"], 0)
    df["+DI"] = 100 * (df["+DM"].ewm(alpha=1/14).mean() / df["ATR"])
    df["-DI"] = 100 * (df["-DM"].ewm(alpha=1/14).mean() / df["ATR"])
    df["DX"] = (abs(df["+DI"] - df["-DI"]) / (df["+DI"] + df["-DI"])) * 100
    df["ADX"] = df["DX"].ewm(alpha=1/14).mean()

    # RSI
    delta = df["close"].diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    avg_gain = up.rolling(14).mean()
    avg_loss = down.rolling(14).mean()
    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))

    # Volume médio
    df["volume_medio"] = df["volume"].rolling(20).mean()

    return df

def gerar_sinais(df):
    sinais = []

    # 1. EMA10 cruza EMA20
    sinais.append(1 if df["EMA10"].iloc[-1] > df["EMA20"].iloc[-1] else (-1 if df["EMA10"].iloc[-1] < df["EMA20"].iloc[-1] else 0))

    # 2. MACD > sinal
    sinais.append(1 if df["MACD"].iloc[-1] > df["SINAL"].iloc[-1] else (-1 if df["MACD"].iloc[-1] < df["SINAL"].iloc[-1] else 0))

    # 3. CCI
    sinais.append(1 if df["CCI"].iloc[-1] > 100 else (-1 if df["CCI"].iloc[-1] < -100 else 0))

    # 4. ADX > 25 com MACD alinhado
    if df["ADX"].iloc[-1] > 25:
        if df["MACD"].iloc[-1] > df["SINAL"].iloc[-1]:
            sinais.append(1)
        elif df["MACD"].iloc[-1] < df["SINAL"].iloc[-1]:
            sinais.append(-1)
        else:
            sinais.append(0)
    else:
        sinais.append(0)

    # 5. RSI <30 ou >70
    sinais.append(1 if df["RSI"].iloc[-1] < 30 else (-1 if df["RSI"].iloc[-1] > 70 else 0))

    # 6. Volume atual maior que volume médio
    sinais.append(1 if df["volume"].iloc[-1] > df["volume_medio"].iloc[-1] else (-1 if df["volume"].iloc[-1] < df["volume_medio"].iloc[-1] else 0))

    # Você pode adicionar mais indicadores aqui, sempre 1, -1 ou 0
    # Exemplo: Momentum, Bollinger Bands, Stochastic, etc.
    # Por simplicidade, vamos repetir os primeiros para completar 12 sinais:
    sinais += sinais[:6]  # duplicando os primeiros para ter 12

    return sinais

def avaliar_sinais(sinais):
    # Conta os sinais positivos e negativos
    compra = sinais.count(1)
    venda = sinais.count(-1)

    # Critério: 5 sinais fortes (mesmo lado)
    # Ou 4 sinais fortes + 1 extra (mesmo lado)
    if compra >= 5:
        return "compra"
    if venda >= 5:
        return "venda"

    if compra == 4 and sinais.count(1) >= 5:
        return "compra"
    if venda == 4 and sinais.count(-1) >= 5:
        return "venda"

    return "neutro"

def enviar_ordem(symbol, lado, quantidade_usdt):
    try:
        preco = float(session.get_mark_price(symbol=symbol)["result"]["mark_price"])
        quantidade = quantidade_usdt / preco

        print(f"Enviando ordem {lado.upper()} de {quantidade:.6f} {symbol} a preço {preco:.4f}")

        # Exemplo de ordem de mercado (spot)
        order = session.place_active_order(
            symbol=symbol,
            side="Buy" if lado == "compra" else "Sell",
            order_type="Market",
            qty=quantidade,
            time_in_force="GoodTillCancel",
            take_profit=round(preco * 1.015 if lado == "compra" else preco * 0.985, 6),
            stop_loss=round(preco * 0.997 if lado == "compra" else preco * 1.003, 6),
            reduce_only=False,
            close_on_trigger=False,
        )
        print(f"Ordem enviada: {order}")
    except Exception as e:
        print(f"Erro ao enviar ordem: {e}")

def main():
    while True:
        for symbol in symbols:
            df = fetch_candles(symbol, interval)
            df = calcular_indicadores(df)
            sinais = gerar_sinais(df)
            decisao = avaliar_sinais(sinais)

            print(f"{symbol}: sinais={sinais}, decisão={decisao}")

            if decisao in ["compra", "venda"]:
                enviar_ordem(symbol, decisao, quantidade_usdt)
            time.sleep(1)
        print("Ciclo finalizado. Aguardando próximo ciclo...")
        time.sleep(30)

if __name__ == "__main__":
    main()
