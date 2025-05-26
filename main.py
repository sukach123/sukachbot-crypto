import pandas as pd
import numpy as np
from pybit.unified_trading import HTTP
import time
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

print("🚧 MODO DEMO ATIVO - Bybit Testnet em execução 🚧")

# === Configurações ===
api_key = os.getenv("BYBIT_API_KEY")
api_secret = os.getenv("BYBIT_API_SECRET")
session = HTTP(api_key=api_key, api_secret=api_secret, testnet=True)

print("🔐 Verificando acesso à API...")
try:
    balance = session.get_wallet_balance(accountType="UNIFIED")
    print("✅ API conectada com sucesso!")
    saldo_usdt = balance['result']['list'][0]['totalEquity']
    print(f"💰 Saldo disponível (simulado): {saldo_usdt} USDT")
except Exception as e:
    print(f"❌ Falha ao conectar à API: {e}")

symbols = ["BNBUSDT", "BTCUSDT", "DOGEUSDT", "SOLUSDT", "ADAUSDT", "ETHUSDT"]
interval = "1"
quantidade_usdt = 5

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
        return fetch_candles(symbol)

def calcular_indicadores(df):
    # EMA
    df["EMA10"] = df["close"].ewm(span=10, adjust=False).mean()
    df["EMA20"] = df["close"].ewm(span=20, adjust=False).mean()

    # MACD
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = ema12 - ema26
    df["SINAL"] = df["MACD"].ewm(span=9, adjust=False).mean()

    # CCI
    tp = (df["high"] + df["low"] + df["close"]) / 3
    ma_tp = tp.rolling(window=20).mean()
    md = tp.rolling(window=20).apply(lambda x: np.mean(np.abs(x - np.mean(x))), raw=True)
    df["CCI"] = (tp - ma_tp) / (0.015 * md)

    # ADX
    high = df["high"]
    low = df["low"]
    close = df["close"]

    plus_dm = high.diff()
    minus_dm = low.diff().abs()

    plus_dm = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0)
    minus_dm = np.where((minus_dm > plus_dm) & (minus_dm > 0), minus_dm, 0)

    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.rolling(window=14).mean()

    plus_di = 100 * (pd.Series(plus_dm).rolling(window=14).mean() / atr)
    minus_di = 100 * (pd.Series(minus_dm).rolling(window=14).mean() / atr)

    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    df["ADX"] = dx.rolling(window=14).mean()

    # Volume explosivo (exemplo simples)
    df["volume_explosivo"] = df["volume"] > df["volume"].rolling(20).mean() * 1.5

    return df

def sinais(df):
    row = df.iloc[-1]
    prev = df.iloc[-2]
    ultimos5 = df.iloc[-5:]

    corpo = abs(row["close"] - row["open"])

    # Critérios fortes
    sinal_1 = row["EMA10"] > row["EMA20"]  # EMA10 acima EMA20
    sinal_2 = row["MACD"] > row["SINAL"]  # MACD > SINAL
    sinal_3 = row["CCI"] > 0               # CCI positivo
    sinal_4 = row["ADX"] > 20              # ADX forte
    # Não lateral: corpo maior que 0.1% candle médio dos últimos 20 (exemplo)
    candle_medio = df["close"].rolling(window=20).apply(lambda x: np.mean(abs(x - x.shift())), raw=False).iloc[-1]
    nao_lateral = corpo > (candle_medio * 0.1)
    sinal_5 = nao_lateral

    sinais_fortes = [sinal_1, sinal_2, sinal_3, sinal_4, sinal_5]

    # Critérios extras
    sinal_6 = row["volume_explosivo"]
    sinal_7 = corpo > (ultimos5["close"].max() - ultimos5["low"].min())
    extra_1 = prev["close"] > prev["open"]
    extra_2 = (row["high"] - row["close"]) < corpo

    sinais_extras = [sinal_6, sinal_7, extra_1, extra_2]

    return sinais_fortes, sinais_extras

def calcular_quantidade(symbol, saldo_usdt, preco):
    quantidade = quantidade_usdt / preco
    return quantidade

def colocar_ordem(symbol, lado, quantidade, preco_entrada, tp_perc=1.5, sl_perc=0.3):
    try:
        take_profit = round(preco_entrada * (1 + tp_perc / 100) if lado == "BUY" else preco_entrada * (1 - tp_perc / 100), 8)
        stop_loss = round(preco_entrada * (1 - sl_perc / 100) if lado == "BUY" else preco_entrada * (1 + sl_perc / 100), 8)

        side_str = "Buy" if lado == "BUY" else "Sell"
        print(f"🟢 Enviando ordem {side_str} para {symbol} - Qtd: {quantidade} USDT")
        print(f"   Preço entrada: {preco_entrada}, TP: {take_profit}, SL: {stop_loss}")

        order = session.place_order(
            category="linear",
            symbol=symbol,
            side=lado,
            orderType="Market",
            qty=quantidade,
            timeInForce="GoodTillCancel",
            takeProfit=take_profit,
            stopLoss=stop_loss,
            reduceOnly=False,
            closeOnTrigger=False
        )
        print(f"✅ Ordem enviada: {order}")
    except Exception as e:
        print(f"❌ Erro ao enviar pedido para {symbol}: {e}")

def main():
    for symbol in symbols:
        print(f"\n🔍 Analisando {symbol}")
        df = fetch_candles(symbol, interval)
        df = calcular_indicadores(df)
        fortes, extras = sinais(df)

        n_fortes = sum(fortes)
        n_extras = sum(extras)

        entrada = "NONE"
        if n_fortes >= 6 or (n_fortes >= 5 and n_extras >= 2):
            entrada = "BUY"
        elif n_fortes <= 2 and n_extras == 0:
            entrada = "SELL"

        print(f"Sinais fortes: {n_fortes}, extras: {n_extras}, entrada sugerida: {entrada}")

        if entrada == "BUY":
            preco_entrada = df["close"].iloc[-1]
            quantidade = calcular_quantidade(symbol, saldo_usdt, preco_entrada)
            colocar_ordem(symbol, "BUY", quantidade, preco_entrada)
        elif entrada == "SELL":
            preco_entrada = df["close"].iloc[-1]
            quantidade = calcular_quantidade(symbol, saldo_usdt, preco_entrada)
            colocar_ordem(symbol, "SELL", quantidade, preco_entrada)
        else:
            print("Nenhuma entrada válida no momento.")

        time.sleep(1)

if __name__ == "__main__":
    main()

