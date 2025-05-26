# === SukachBot PRO75 - Agora com TP de 1.5% automático e SL de -0.3% ===

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
interval = "1"
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
    df["EMA10"] = df["close"].ewm(span=10).mean()
    df["EMA20"] = df["close"].ewm(span=20).mean()
    df["MACD"] = df["close"].ewm(span=12).mean() - df["close"].ewm(span=26).mean()
    df["SINAL"] = df["MACD"].ewm(span=9).mean()
    df["CCI"] = (df["close"] - df["close"].rolling(20).mean()) / (0.015 * df["close"].rolling(20).std())
    df["TR"] = np.maximum.reduce([
        df["high"] - df["low"],
        abs(df["high"] - df["close"].shift()),
        abs(df["low"] - df["close"].shift())
    ])
    df["ATR"] = df["TR"].rolling(14).mean()
    df["ADX"] = 100 * (df["ATR"] / df["close"]).rolling(14).mean()
    df["volume_medio"] = df["volume"].rolling(20).mean()
    df["volume_explosivo"] = df["volume"] > df["volume_medio"] * 1.5
    df["corpo_candle"] = abs(df["close"] - df["open"])
    df["corpo_grande"] = df["corpo_candle"] > df["ATR"]
    df["lateral"] = abs(df["EMA10"] - df["EMA20"]) < df["close"].mean() * 0.002
    return df

def sinais(df):
    ultimo = df.iloc[-1]
    anterior = df.iloc[-2]

    sinais_fortes = 0
    extras = 0

    # Condição 1: EMA10 acima EMA20
    ema_cond = ultimo["EMA10"] > ultimo["EMA20"]
    if ema_cond:
        sinais_fortes += 1

    # Condição 2: MACD > SINAL
    macd_cond = ultimo["MACD"] > ultimo["SINAL"]
    if macd_cond:
        sinais_fortes += 1

    # Condição 3: CCI > 0
    cci_cond = ultimo["CCI"] > 0
    if cci_cond:
        sinais_fortes += 1

    # Condição 4: ADX > 20
    adx_cond = ultimo["ADX"] > 20
    if adx_cond:
        sinais_fortes += 1

    # Condição 5: Volume explosivo
    vol_cond = ultimo["volume_explosivo"]
    if vol_cond:
        sinais_fortes += 1

    # Extras 1: Vela anterior de alta (close > open)
    extra1 = anterior["close"] > anterior["open"]
    if extra1:
        extras += 1

    # Extras 2: Pequeno pavio superior na vela atual
    pavio_sup = ultimo["high"] - max(ultimo["close"], ultimo["open"])
    corpo = abs(ultimo["close"] - ultimo["open"])
    extra2 = pavio_sup < corpo * 0.3
    if extra2:
        extras += 1

    # Decisão de entrada:
    # Entrar se 5 fortes ou 4 fortes + 2 extras
    entrada = False
    if sinais_fortes >= 5:
        entrada = True
    elif sinais_fortes >=4 and extras >= 2:
        entrada = True

    return {
        "ema_cond": ema_cond,
        "macd_cond": macd_cond,
        "cci_cond": cci_cond,
        "adx_cond": adx_cond,
        "vol_cond": vol_cond,
        "extra1": extra1,
        "extra2": extra2,
        "sinais_fortes": sinais_fortes,
        "extras": extras,
        "entrada": entrada
    }

def enviar_ordem(symbol, quantidade, lado="Buy"):
    try:
        print(f"📦 Tentando enviar ordem: {lado} para {symbol} - Qtd: {quantidade:.6f}")
        # Exemplo: set leverage antes da ordem
        session.set_leverage(category="linear", symbol=symbol, buyLeverage=10, sellLeverage=10)
        # Enviar ordem de mercado
        order = session.place_active_order(
            category="linear",
            symbol=symbol,
            side=lado,
            orderType="Market",
            qty=quantidade,
            timeInForce="GoodTillCancel",
            reduceOnly=False,
            closeOnTrigger=False
        )
        print("✅ Ordem enviada com sucesso!")
        return order
    except Exception as e:
        print(f"🚨 Erro ao enviar ordem: {e}")
        return None

def main():
    while True:
        for symbol in symbols:
            print(f"\n🔍 Analisando {symbol}...")
            df = fetch_candles(symbol, interval)
            df = calcular_indicadores(df)
            resultado = sinais(df)

            timestamp = df["timestamp"].iloc[-1]
            print(f"\n📊 Diagnóstico de sinais em {timestamp}")
            print(f"📌 EMA10 vs EMA20: {resultado['ema_cond']}")
            print(f"📌 MACD > SINAL: {resultado['macd_cond']}")
            print(f"📌 CCI > 0: {resultado['cci_cond']} (valor: {df['CCI'].iloc[-1]:.2f})")
            print(f"📌 ADX > 20: {resultado['adx_cond']} (valor: {df['ADX'].iloc[-1]:.2f})")
            print(f"📌 Volume explosivo: {resultado['vol_cond']} (volume: {df['volume'].iloc[-1]:.2f})")
            print(f"📌 Extra: Vela anterior de alta: {resultado['extra1']}")
            print(f"📌 Extra: Pequeno pavio superior: {resultado['extra2']}")
            print(f"✔️ Total: {resultado['sinais_fortes']} fortes + {resultado['extras']} extras")

            if resultado["entrada"]:
                print("🔔 Entrada validada com 4 fortes + extras ou 5 fortes + extras!")
                quantidade = quantidade_usdt / df["close"].iloc[-1]
                order = enviar_ordem(symbol, quantidade, lado="Buy")
            else:
                print("⛔ Entrada não validada, aguardando próximos sinais.")

            time.sleep(3)
        print("\n⏳ Aguardando próximo ciclo...\n")
        time.sleep(15)

if __name__ == "__main__":
    main()

