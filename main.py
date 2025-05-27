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
        data = session.get_kline(category="linear", symbol=symbol, interval=interval, limit=180)
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
    df["volume_explosivo"] = df["volume"] > df["volume_medio"]
    return df

def sinais_forca(df):
    sinais = []
    
    # EMA cruzamento
    if df["EMA10"].iloc[-1] > df["EMA20"].iloc[-1]:
        sinais.append("EMA_COMPRA")
    elif df["EMA10"].iloc[-1] < df["EMA20"].iloc[-1]:
        sinais.append("EMA_VENDA")
    
    # MACD cruzamento
    if df["MACD"].iloc[-1] > df["SINAL"].iloc[-1]:
        sinais.append("MACD_COMPRA")
    elif df["MACD"].iloc[-1] < df["SINAL"].iloc[-1]:
        sinais.append("MACD_VENDA")
    
    # CCI
    if df["CCI"].iloc[-1] > 100:
        sinais.append("CCI_COMPRA")
    elif df["CCI"].iloc[-1] < -100:
        sinais.append("CCI_VENDA")
    
    # ADX força tendência
    if df["ADX"].iloc[-1] > 25:
        sinais.append("ADX_FORTE")
    else:
        sinais.append("ADX_FRACO")
    
    # Volume explosivo
    if df["volume_explosivo"].iloc[-1]:
        sinais.append("VOLUME_ALTO")
    else:
        sinais.append("VOLUME_BAIXO")
    
    return sinais

def avaliar_entrada(sinais):
    # Contar sinais de compra e venda fortes
    compra = sum(1 for s in sinais if "COMPRA" in s)
    venda = sum(1 for s in sinais if "VENDA" in s)
    extra = 1 if "ADX_FORTE" in sinais or "VOLUME_ALTO" in sinais else 0
    
    # Regra: 4 sinais fortes + 1 extra
    if compra >= 4 and extra == 1:
        return "ENTRAR_COMPRA"
    elif venda >= 4 and extra == 1:
        return "ENTRAR_VENDA"
    else:
        return "AGUARDAR"

def executar_trade(symbol, direcao):
    print(f"Executando trade {direcao} para {symbol} com {quantidade_usdt} USDT")
    # Aqui você colocaria a lógica para abrir posição com TP 1.5% e SL -0.3%
    # Exemplo simplificado:
    # session.place_active_order(symbol=symbol, side="Buy" if direcao=="ENTRAR_COMPRA" else "Sell", qty=quantidade_usdt, tp=..., sl=...)
    pass

def main():
    while True:
        for symbol in symbols:
            df = fetch_candles(symbol, interval)
            df = calcular_indicadores(df)
            sinais = sinais_forca(df)
            decisao = avaliar_entrada(sinais)
            if decisao in ["ENTRAR_COMPRA", "ENTRAR_VENDA"]:
                executar_trade(symbol, decisao)
        time.sleep(60)

if __name__ == "__main__":
    main()


