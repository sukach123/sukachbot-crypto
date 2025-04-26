# === SukachBot PRO75 - BACKTEST BNBUSDT - PERÍODO ESPECÍFICO COM SL REPEAT ===

import pandas as pd
import numpy as np
from pybit.unified_trading import HTTP
import time

# === Configurações ===
symbols = ["BNBUSDT", "BTCUSDT", "DOGEUSDT", "SOLUSDT", "ADAUSDT", "ETHUSDT"]
interval = "1"
api_key = "TUA_API_KEY"
api_secret = "TEU_API_SECRET"
quantidade_usdt = 2
saldo_inicial = 500

start_date = "2025-04-01 00:00:00"
end_date = "2025-04-25 00:00:00"

start_timestamp = int(pd.Timestamp(start_date).timestamp() * 1000)
end_timestamp = int(pd.Timestamp(end_date).timestamp() * 1000)

session = HTTP(api_key=api_key, api_secret=api_secret, testnet=False)

# === Funções auxiliares ===

def fetch_historico(symbol):
    candles = []
    start = start_timestamp
    while True:
        data = session.get_kline(category="linear", symbol=symbol, interval=interval, limit=1000, start=start)
        batch = data['result']['list']
        if not batch:
            break
        candles.extend(batch)
        start = int(batch[-1][0]) + 60_000
        if start > end_timestamp:
            break
        time.sleep(0.2)
    df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"])
    df = df.astype({"open": float, "high": float, "low": float, "close": float, "volume": float})
    df["timestamp"] = pd.to_datetime(pd.to_numeric(df["timestamp"]), unit="ms")
    return df

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

def verificar_entrada(df, i):
    row = df.iloc[i]
    prev = df.iloc[i-1]
    ultimos5 = df.iloc[i-5:i]
    ultimos20 = df.iloc[i-20:i]
    corpo = abs(row["close"] - row["open"])
    volatilidade = ultimos20["high"].max() - ultimos20["low"].min()
    media_atr = ultimos20["ATR"].mean()
    nao_lateral = volatilidade > (2 * media_atr)

    condicoes = [
        row["EMA10"] > row["EMA20"],
        row["MACD"] > row["SINAL"],
        row["CCI"] > 0,
        row["ADX"] > 20,
        row["volume_explosivo"],
        corpo > ultimos5["close"].max() - ultimos5["low"].min(),
        prev["close"] > prev["open"],
        (row["high"] - row["close"]) < corpo,
        nao_lateral
    ]
    return all(condicoes)

def tentar_colocar_sl(symbol, preco_sl, quantidade, tentativas=3):
    sl_colocado = False
    while not sl_colocado:
        for tentativa in range(tentativas):
            try:
                session.place_order(
                    category="linear",
                    symbol=symbol,
                    side="Sell",
                    orderType="Stop",
                    qty=quantidade,
                    price=round(preco_sl, 3),
                    triggerPrice=round(preco_sl, 3),
                    triggerBy="LastPrice",
                    reduceOnly=True
                )
                print(f"🎯 SL colocado na tentativa {tentativa+1} com sucesso!")
                sl_colocado = True
                break
            except Exception as e:
                print(f"Erro ao colocar SL (tentativa {tentativa+1}): {e}")
                time.sleep(1)
        if not sl_colocado:
            print("⏳ Esperando 15 segundos para tentar novamente colocar SL...")
            time.sleep(15)

def simular(df, symbol):
    saldo = saldo_inicial
    historico = []
    win = 0
    loss = 0

    for i in range(30, len(df)-20):
        if verificar_entrada(df, i):
            preco_entrada = df.iloc[i]["close"]
            tp = preco_entrada * 1.025
            sl = preco_entrada * 0.985
            trailing = preco_entrada * 1.01
            quantidade = (quantidade_usdt * 2) / preco_entrada

            tentar_colocar_sl(symbol, sl, quantidade)

            for j in range(i+1, min(i+20, len(df))):
                high = df.iloc[j]["high"]
                low = df.iloc[j]["low"]

                if high >= tp:
                    saldo += quantidade_usdt * 2 * 0.025
                    win += 1
                    break
                elif low <= sl:
                    saldo -= quantidade_usdt * 2 * 0.015
                    loss += 1
                    break
                elif high >= trailing:
                    trailing = high * 0.995

            historico.append(saldo)

    return win, loss, saldo, historico

# === Execução ===

print("📥 Buscando histórico específico...")

for symbol in symbols:
    print(f"\n=== Testando par: {symbol} ===")
    df = fetch_historico(symbol)
    print("📊 Calculando indicadores...")
    df = calcular_indicadores(df)
    print("🚀 Iniciando simulação...")
    win, loss, saldo_final, historico = simular(df, symbol)

    print("\n=== RESULTADO DO BACKTEST ===")
    print(f"Entradas simuladas: {win + loss}")
    print(f"✅ WIN: {win}")
    print(f"❌ LOSS: {loss}")
    print(f"🎯 Taxa de acerto: {round(100 * win / (win + loss), 2)}%")
    print(f"💰 Saldo final: {round(saldo_final, 2)} USDT")

    # Removido gráfico para ambientes sem matplotlib
