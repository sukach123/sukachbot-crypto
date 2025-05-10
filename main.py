# Recriar o conteúdo do script após reinício do ambiente

codigo_execucao_real_unificado = '''
# === SukachBot PRO - Execução Real com LONG Filtrado e SHORT Tradicional ===

import pandas as pd
import numpy as np
from pybit.unified_trading import HTTP
import time

# === Configurações ===
symbols = ["BTCUSDT", "ETHUSDT", "DOGEUSDT", "BNBUSDT", "SOLUSDT"]
interval = "1"
api_key = "TUA_API_KEY"       # <-- Substituir aqui pela tua API key real
api_secret = "TEU_API_SECRET" # <-- Substituir aqui pela tua API secret real
quantidade_usdt = 5

session = HTTP(api_key=api_key, api_secret=api_secret, testnet=False)

def fetch_candles(symbol, interval="1"):
    try:
        data = session.get_kline(category="linear", symbol=symbol, interval=interval, limit=200)
        candles = data['result']['list']
        df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"])
        df = df.astype({"open": float, "high": float, "low": float, "close": float, "volume": float})
        df["timestamp"] = pd.to_datetime(pd.to_numeric(df["timestamp"]), unit="ms")
        return df
    except Exception as e:
        print(f"🚨 Erro a buscar candles de {symbol}: {e}")
        time.sleep(5)
        return fetch_candles(symbol)

def calcular_indicadores(df):
    df["EMA10"] = df["close"].ewm(span=10).mean()
    df["EMA20"] = df["close"].ewm(span=20).mean()
    df["MACD"] = df["close"].ewm(span=12).mean() - df["close"].ewm(span=26).mean()
    df["SINAL"] = df["MACD"].ewm(span=9).mean()
    df["CCI"] = (df["close"] - df["close"].rolling(20).mean()) / (0.015 * df["close"].rolling(20).std())
    df["ADX"] = abs(df["high"] - df["low"]).rolling(14).mean()
    df["volume_medio"] = df["volume"].rolling(20).mean()
    df["volume_explosivo"] = df["volume"] > 1.3 * df["volume_medio"]
    return df

def detectar_padrao_vela(row, prev):
    corpo = abs(row["close"] - row["open"])
    sombra_inferior = row["open"] - row["low"] if row["close"] > row["open"] else row["close"] - row["low"]
    martelo = sombra_inferior > corpo * 2
    engulfing = row["close"] > row["open"] and prev["close"] < prev["open"] and row["close"] > prev["open"] and row["open"] < prev["close"]
    return martelo or engulfing

def verificar_entrada(df):
    row = df.iloc[-1]
    prev = df.iloc[-2]
    ultimos20 = df.iloc[-20:]
    estrutura_reversao = (
        prev["close"] < prev["open"] and
        row["close"] > prev["high"] and
        row["volume"] > ultimos20["volume"].mean()
    )
    padrao_vela = detectar_padrao_vela(row, prev)

    entrar_long = (
        (estrutura_reversao or padrao_vela) and
        row["EMA10"] > row["EMA20"] and
        row["MACD"] > row["SINAL"] and
        row["CCI"] > 0 and
        row["ADX"] > 20 and
        row["volume_explosivo"]
    )

    entrar_short = (
        row["EMA10"] < row["EMA20"] and
        row["MACD"] < row["SINAL"] and
        row["CCI"] < 0 and
        row["ADX"] > 20 and
        row["volume_explosivo"] and
        row["close"] < prev["close"]
    )

    if entrar_long:
        print(f"✅ LONG confirmado em {df.iloc[-1]['timestamp']}")
        return "Buy"
    elif entrar_short:
        print(f"✅ SHORT confirmado em {df.iloc[-1]['timestamp']}")
        return "Sell"
    else:
        return None

def tentar_colocar_sl(symbol, preco_sl, quantidade, tentativas=3):
    sl_colocado = False
    tentativas_feitas = 0
    while not sl_colocado:
        for tentativa in range(tentativas):
            try:
                session.place_order(
                    category="linear",
                    symbol=symbol,
                    side="Sell" if preco_sl < 1 else "Buy",
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
                print(f"🚨 Erro ao colocar SL (tentativa {tentativa+1}): {e}")
                time.sleep(1)
        if not sl_colocado:
            tentativas_feitas += 1
            print(f"⏳ Esperando 15 segundos para tentar novamente colocar SL... ({tentativas_feitas} falhas)")
            time.sleep(15)

def enviar_ordem(symbol, lado):
    try:
        preco_atual = float(session.get_ticker(category="linear", symbol=symbol)["result"]["lastPrice"])
        quantidade = round(quantidade_usdt / preco_atual, 3)
        session.set_leverage(category="linear", symbol=symbol, buyLeverage=10, sellLeverage=10)

        session.place_order(
            category="linear",
            symbol=symbol,
            side=lado,
            orderType="Market",
            qty=quantidade,
            reduceOnly=False
        )
        print(f"🚀 Ordem {lado} executada em {symbol} ao preço de {preco_atual}")

        preco_entrada = preco_atual
        if lado == "Buy":
            sl = preco_entrada * 0.994
        else:
            sl = preco_entrada * 1.006
        tentar_colocar_sl(symbol, sl, quantidade)

    except Exception as e:
        print(f"🚨 Erro ao enviar ordem: {e}")
        time.sleep(5)
        enviar_ordem(symbol, lado)

# === Loop Principal ===
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
            print(f"🚨 Erro geral em {symbol}: {e}")
            time.sleep(5)
    time.sleep(1)
'''

# Salvar novamente
from pathlib import Path
script_path = Path("/mnt/data/sukachbot_execucao_real_LONG_SHORT_PRO_FINAL.py")
script_path.write_text(codigo_execucao_real_unificado)
script_path

