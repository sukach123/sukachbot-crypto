# === SukachBot PRO75 ===
# Entradas com: 5 sinais fortes OU 4 fortes + 1 extra
# TP de +1.5% | SL de -0.3% | Alavancagem: 10x (corrigido erro 110043)

import pandas as pd
import numpy as np
from pybit.unified_trading import HTTP
import time
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

# === Configurações ===
symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "DOGEUSDT", "SOLUSDT"]
interval = "1"
api_key = os.getenv("BYBIT_API_KEY")
api_secret = os.getenv("BYBIT_API_SECRET")
quantidade_usdt = 5

session = HTTP(api_key=api_key, api_secret=api_secret, testnet=True)

def fetch_candles(symbol):
    try:
        data = session.get_kline(category="linear", symbol=symbol, interval=interval, limit=200)
        candles = data['result']['list']
        df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"])
        df = df.astype({"open": float, "high": float, "low": float, "close": float, "volume": float})
        df["timestamp"] = pd.to_datetime(pd.to_numeric(df["timestamp"]), unit="ms", utc=True)

        now = datetime.now(timezone.utc)
        atraso = (now - df["timestamp"].iloc[-1]).total_seconds()
        if 60 < atraso < 300:
            print(f"⚠️ AVISO: Último candle de {symbol} está atrasado {atraso:.0f} segundos!")
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

    sinal_1 = row["EMA10"] > row["EMA20"] or row["EMA10"] < row["EMA20"]
    sinal_2 = row["MACD"] > row["SINAL"]
    sinal_3 = row["CCI"] > 0
    sinal_4 = row["ADX"] > 20
    sinal_5 = row["volume_explosivo"]
    sinal_6 = corpo > ultimos5["close"].max() - ultimos5["low"].min()
    sinal_7 = nao_lateral

    sinais_fortes = [sinal_1, sinal_2, sinal_3, sinal_4, sinal_7]
    sinais_extras = [sinal_5, sinal_6, prev["close"] > prev["open"], (row["high"] - row["close"]) < corpo]

    total_fortes = sum(sinais_fortes)
    total_extras = sum(sinais_extras)

    print(f"\n📊 Diagnóstico de sinais em {row['timestamp']}")
    print(f"📌 EMA10 vs EMA20: {sinal_1}")
    print(f"📌 MACD > SINAL: {sinal_2}")
    print(f"📌 CCI > 0: {sinal_3} (valor: {row['CCI']:.2f})")
    print(f"📌 ADX > 20: {sinal_4} (valor: {row['ADX']:.2f})")
    print(f"📌 Volume explosivo: {sinal_5} (volume: {row['volume']:.2f})")
    print(f"📌 Corpo grande: {sinal_6}")
    print(f"📌 Não lateral: {sinal_7}")
    print(f"📌 Extra: Vela anterior de alta: {prev['close'] > prev['open']}")
    print(f"📌 Extra: Pequeno pavio superior: {(row['high'] - row['close']) < corpo}")
    print(f"✔️ Total: {total_fortes} fortes + {total_extras} extras = {total_fortes + total_extras}/9")

    if total_fortes >= 5 or (total_fortes == 4 and total_extras >= 1):
        preco = row["close"]
        diferenca_ema = abs(row["EMA10"] - row["EMA20"])
        limite = preco * 0.0001
        if diferenca_ema < limite:
            print(f"🚫 Entrada bloqueada ❌ (colisão de EMAs)")
            return None
        lado = "Buy" if row["EMA10"] > row["EMA20"] else "Sell"
        print(f"✅ Entrada confirmada! {lado}")
        return lado
    else:
        print(f"🔎 {row['timestamp']} | Apenas {total_fortes + total_extras}/9 sinais confirmados | Entrada bloqueada ❌")
        return None

def colocar_sl_tp(symbol, lado, preco_entrada, quantidade):
    tp = round(preco_entrada * 1.015, 3)
    sl = round(preco_entrada * 0.997, 3)
    for i in range(3):
        try:
            session.place_order(
                category="linear",
                symbol=symbol,
                side="Sell" if lado == "Buy" else "Buy",
                orderType="Stop",
                qty=quantidade,
                price=sl,
                triggerPrice=sl,
                triggerBy="LastPrice",
                reduceOnly=True,
                isIsolated=True
            )
            session.place_order(
                category="linear",
                symbol=symbol,
                side="Sell" if lado == "Buy" else "Buy",
                orderType="Limit",
                qty=quantidade,
                price=tp,
                reduceOnly=True,
                isIsolated=True
            )
            print("🎯 TP e SL definidos com sucesso!")
            return
        except Exception as e:
            print(f"⚠️ Erro SL/TP tentativa {i+1}: {e}")
            time.sleep(2)

def enviar_ordem(symbol, lado):
    try:
        ticker = session.get_tickers(category="linear", symbol=symbol)
        preco = float(ticker["result"]["list"][0]["lastPrice"])
        qty = round(quantidade_usdt / preco, 3)
        print(f"\n📦 Tentando enviar ordem:")
        print(f"    ➤ Por: {symbol}")
        print(f"    ➤ Direção: {lado}")
        print(f"    ➤ Preço atual: {preco}")
        print(f"    ➤ Quantidade calculada: {qty}")

        if qty <= 0:
            print("🚫 Quantidade inválida! Ordem não enviada")
            return

        try:
            session.set_leverage(
                category="linear",
                symbol=symbol,
                buyLeverage="10",
                sellLeverage="10"
            )
        except Exception as e:
            if "110043" in str(e):
                print("⚠️ Alavancagem já está correta.")
            else:
                print(f"⚠️ Erro ao definir alavancagem: {e}")

        session.place_order(
            category="linear",
            symbol=symbol,
            side=lado,
            orderType="Market",
            qty=qty,
            reduceOnly=False,
            isIsolated=True
        )

        print(f"🚀 Ordem executada com sucesso!")
        colocar_sl_tp(symbol, lado, preco, qty)

    except Exception as e:
        print(f"🚨 Erro ao enviar pedido: {e}")

# === LOOP PRINCIPAL ===
while True:
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
            print(f"❌ Erro geral com {symbol}: {e}")
    time.sleep(1)


