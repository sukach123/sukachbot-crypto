# === SukachBot PRO75 - Agora com TP de 1.5% automático e SL de -0.3% ===

import pandas as pd
import numpy as np
from pybit.unified_trading import HTTP, WebSocket
import time
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

# === Configurações ===
symbols = ["BNBUSDT", "BTCUSDT", "DOGEUSDT", "SOLUSDT", "ADAUSDT", "ETHUSDT"]
interval = "1"  # 1 minuto para cálculo de candles (mas atualização será em tempo real via WebSocket)
api_key = os.getenv("BYBIT_API_KEY")
api_secret = os.getenv("BYBIT_API_SECRET")
quantidade_usdt = 5

session = HTTP(api_key=api_key, api_secret=api_secret, testnet=False)

# WebSocket com channel_type obrigatório
ws = WebSocket(
    channel_type="linear",
    testnet=False,
    api_key=api_key,
    api_secret=api_secret
)

# Dicionário para armazenar candles atualizados por símbolo
candles_data = {symbol: None for symbol in symbols}

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

def analisar_sinais(df):
    # Exemplo simplificado de 5 sinais, ajusta conforme sua lógica real
    sinais = 0
    # Sinal 1: EMA10 > EMA20
    if df["EMA10"].iloc[-1] > df["EMA20"].iloc[-1]:
        sinais += 1
    # Sinal 2: MACD cruza acima da SINAL
    if df["MACD"].iloc[-2] < df["SINAL"].iloc[-2] and df["MACD"].iloc[-1] > df["SINAL"].iloc[-1]:
        sinais += 1
    # Sinal 3: CCI < -100 (exemplo)
    if df["CCI"].iloc[-1] < -100:
        sinais += 1
    # Sinal 4: ADX > 25 indicando tendência forte
    if df["ADX"].iloc[-1] > 25:
        sinais += 1
    # Sinal 5: volume explosivo
    if df["volume_explosivo"].iloc[-1]:
        sinais += 1
    return sinais

def abrir_posicao(symbol):
    print(f"✅ Abrindo posição em {symbol} com {quantidade_usdt} USDT")
    # Aqui entra sua lógica de ordem via API, por exemplo:
    # session.place_active_order(...)
    # Implementar Take Profit de 1.5% e Stop Loss de -0.3%
    pass

def on_candle_update(data):
    symbol = data['topic'].split(".")[1]
    candle = data['data']
    
    # Atualizar candles no dicionário
    df_candle = pd.DataFrame([{
        "timestamp": pd.to_datetime(candle['start'], utc=True),
        "open": float(candle['open']),
        "high": float(candle['high']),
        "low": float(candle['low']),
        "close": float(candle['close']),
        "volume": float(candle['volume']),
    }])
    
    if candles_data[symbol] is None:
        # Para inicializar, pegar candles históricos para os últimos 200 candles
        historical = session.get_kline(category="linear", symbol=symbol, interval=interval, limit=200)
        hist_candles = historical['result']['list']
        df_hist = pd.DataFrame(hist_candles, columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"])
        df_hist = df_hist.astype({"open": float, "high": float, "low": float, "close": float, "volume": float})
        df_hist["timestamp"] = pd.to_datetime(pd.to_numeric(df_hist["timestamp"]), unit="ms", utc=True)
        candles_data[symbol] = df_hist
    
    # Substituir último candle pelo novo ou adicionar se for um candle novo
    if candle['start'] == candles_data[symbol]["timestamp"].iloc[-1].isoformat():
        candles_data[symbol].iloc[-1] = df_candle.iloc[0]
    else:
        candles_data[symbol] = pd.concat([candles_data[symbol], df_candle], ignore_index=True)
        # Manter apenas últimos 200 candles
        candles_data[symbol] = candles_data[symbol].iloc[-200:]
    
    # Recalcular indicadores e analisar sinais
    df_atual = calcular_indicadores(candles_data[symbol])
    sinais = analisar_sinais(df_atual)
    
    # Abrir posição se tiver pelo menos 5 sinais fortes (4 + 1 extra)
    if sinais >= 5:
        abrir_posicao(symbol)

def main():
    # Subscrever candles em tempo real via WebSocket para cada símbolo
    for symbol in symbols:
        ws.subscribe(f"kline.{symbol}.1")
    
    print("🚀 Iniciando SukachBot PRO75 com atualização a cada segundo via WebSocket...")
    
    # Loop para manter conexão aberta e processar mensagens
    while True:
        try:
            msg = ws.receive()
            if msg and 'topic' in msg and 'data' in msg:
                if msg['topic'].startswith("kline"):
                    on_candle_update(msg)
        except Exception as e:
            print(f"Erro no loop principal: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()


