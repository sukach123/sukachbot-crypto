# === SukachBot PRO75 v1.4 - Entrada com 5 fortes ou 4+2 extras ===

import pandas as pd
import numpy as np
import time
from datetime import datetime, timezone
from pybit.unified_trading import HTTP

# === Configuração da API ===
api_key = "SUA_API_KEY"
api_secret = "SEU_API_SECRET"

session = HTTP(
    testnet=True,
    api_key=api_key,
    api_secret=api_secret
)

# === Função: Buscar velas ===
def buscar_candles(symbol="DOGEUSDT", interval="1", limit=100):
    try:
        res = session.get_kline(
            category="linear",
            symbol=symbol,
            interval=interval,
            limit=limit
        )
        df = pd.DataFrame(res['result']['list'])
        df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover']
        df = df.astype(float)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
        df.set_index('timestamp', inplace=True)
        return df
    except Exception as e:
        print(f"❌ Erro ao buscar velas de {symbol}: {e}")
        return None

# === Função: Indicadores Técnicos ===
def calcular_indicadores(df):
    df['EMA10'] = df['close'].ewm(span=10).mean()
    df['EMA20'] = df['close'].ewm(span=20).mean()

    df['MACD'] = df['close'].ewm(span=12).mean() - df['close'].ewm(span=26).mean()
    df['SINAL'] = df['MACD'].ewm(span=9).mean()

    df['CCI'] = (df['close'] - df['close'].rolling(20).mean()) / (0.015 * df['close'].rolling(20).std())

    high = df['high']
    low = df['low']
    close = df['close']

    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.rolling(14).mean()
    df['ATR'] = atr
    df['ADX'] = 100 * (atr / close.rolling(14).mean())
    return df

# === Função: Estratégia de Entrada ===
def verificar_sinais(df):
    row = df.iloc[-1]
    sinais_fortes = 0
    sinais_extras = 0

    # Fortes
    if row["EMA10"] > row["EMA20"]: sinais_fortes += 1
    if row["MACD"] > row["SINAL"]: sinais_fortes += 1
    if row["CCI"] > 100: sinais_fortes += 1
    if row["ADX"] > 20: sinais_fortes += 1
    if row["close"] > row["EMA10"]: sinais_fortes += 1

    # Extras
    if row["close"] > row["close"] - row["ATR"]: sinais_extras += 1
    if row["EMA10"] > row["EMA10"].shift(1): sinais_extras += 1
    if row["volume"] > df['volume'].rolling(10).mean().iloc[-1]: sinais_extras += 1
    if row["CCI"] > 0: sinais_extras += 1

    return sinais_fortes, sinais_extras

# === Função: Enviar Ordem ===
def enviar_ordem(symbol, direcao, quantidade):
    try:
        preco_entrada = float(session.get_ticker(category="linear", symbol=symbol)['result']['list'][0]['lastPrice'])

        if direcao == "LONG":
            tp = round(preco_entrada * 1.015, 4)
            sl = round(preco_entrada * 0.99, 4)
            lado = "Buy"
        else:
            tp = round(preco_entrada * 0.985, 4)
            sl = round(preco_entrada * 1.01, 4)
            lado = "Sell"

        res = session.place_order(
            category="linear",
            symbol=symbol,
            side=lado,
            orderType="Market",
            qty=quantidade,
            takeProfit=str(tp),
            stopLoss=str(sl),
            timeInForce="GoodTillCancel"
        )
        print(f"✅ Ordem {direcao} enviada para {symbol} - Qtd: {quantidade}")
    except Exception as e:
        print(f"❌ Erro ao enviar ordem para {symbol}: {e}")

# === LOOP PRINCIPAL ===
ativos = ["DOGEUSDT", "ADAUSDT", "SOLUSDT"]

while True:
    for ativo in ativos:
        df = buscar_candles(ativo)
        if df is None or len(df) < 20:
            continue

        tempo_ultima_vela = df.index[-1]
        agora = datetime.now(timezone.utc)

        diff = (agora - tempo_ultima_vela).total_seconds()
        if diff > 2:
            continue  # ignora se a vela não está atualizada

        df = calcular_indicadores(df)
        fortes, extras = verificar_sinais(df)

        print(f"\n🔍 Analisando {ativo}")
        print(f"Sinais fortes: {fortes}, extras: {extras}", end='')

        if fortes >= 5 or (fortes >= 4 and extras >= 2):
            direcao = "LONG" if df["EMA10"].iloc[-1] > df["EMA20"].iloc[-1] else "SHORT"
            print(f", entrada sugerida: {direcao}")
            enviar_ordem(ativo, direcao, 0.02)
        else:
            print(", entrada sugerida: NENHUMA")

    time.sleep(1)


