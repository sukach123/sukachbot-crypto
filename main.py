# === SukachBot PRO75 - Agora com TP de 1.5% automático e SL de -0.3% ===

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
pares_com_erro_leverage = ["ETHUSDT", "ADAUSDT", "BTCUSDT"]

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

def enviar_ordem(symbol, lado):
    try:
        if symbol not in pares_com_erro_leverage:
            try:
                session.set_leverage(category="linear", symbol=symbol, buyLeverage=10, sellLeverage=10)
            except Exception as e:
                print(f"⚠️ Aviso: alavancagem não definida para {symbol}: {e}")

        dados_ticker = session.get_tickers(category="linear", symbol=symbol)
        preco_atual = float(dados_ticker['result']['list'][0]['lastPrice'])

        min_qty_map = {
            "BTCUSDT": 0.001,
            "ETHUSDT": 0.01,
            "BNBUSDT": 0.1,
            "DOGEUSDT": 10,
            "SOLUSDT": 0.1,
            "ADAUSDT": 1
        }
        min_qty = min_qty_map.get(symbol, 0.1)
        quantidade = round(max(quantidade_usdt / preco_atual, min_qty), 6)

        if quantidade < min_qty:
            print(f"🚫 Quantidade {quantidade} é inferior ao mínimo permitido para {symbol} ({min_qty}). Ordem não enviada.")
            return

        print(f"📦 Tentando enviar ordem:\n\n    ➤ Par: {symbol}\n    ➤ Direção: {lado}\n    ➤ Preço atual: {preco_atual}\n    ➤ Quantidade calculada: {quantidade}")

        response = session.place_order(
            category="linear",
            symbol=symbol,
            side=lado,
            orderType="Market",
            qty=quantidade,
            reduceOnly=False,
            isIsolated=False,
            takeProfit=round(preco_atual * 1.015, 3) if lado == "Buy" else round(preco_atual * 0.985, 3),
            stopLoss=round(preco_atual - df["ATR"].iloc[-1], 3) if lado == "Buy" else round(preco_atual + df["ATR"].iloc[-1], 3)
        )

        if response.get("retCode") == 0:
            print(f"🚀 Ordem {lado} executada com sucesso!")
            print("📋 Resposta da API:", response)
        else:
            print(f"❌ Ordem falhou: {response.get('retMsg', 'Erro desconhecido')}")
            print("📋 Resposta da API:", response)

    except Exception as e:
        print(f"❌ Erro ao enviar ordem: {e}")

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
    sinal_5 = nao_lateral

    sinais_fortes = [sinal_1, sinal_2, sinal_3, sinal_4, sinal_5]

    sinal_6 = row["volume_explosivo"]
    sinal_7 = corpo > ultimos5["close"].max() - ultimos5["low"].min()
    extra_1 = prev["close"] > prev["open"]
    extra_2 = (row["high"] - row["close"]) < corpo
    sinais_extras = [sinal_6, sinal_7, extra_1, extra_2]

    total_confirmados = sum(sinais_fortes) + sum(sinais_extras)

    print(f"\n📊 Diagnóstico de sinais em {row['timestamp']}")
    print(f"✔️ Total: {sum(sinais_fortes)} fortes + {sum(sinais_extras)} extras = {total_confirmados}/9")

    if sum(sinais_fortes) >= 5 or (sum(sinais_fortes) == 4 and sum(sinais_extras) >= 1):
        preco_atual = row["close"]
        diferenca_ema = abs(row["EMA10"] - row["EMA20"])
        limite_colisao = preco_atual * 0.0001

        print(f"🔔 Entrada validada com 6 sinais ou 5+2 extras!")

        if diferenca_ema < limite_colisao:
            print(f"🚫 Entrada bloqueada ❌ - Colisão de EMAs")
            return None
        else:
            direcao = "Buy" if row["EMA10"] > row["EMA20"] else "Sell"
            print(f"✅ Entrada confirmada! {direcao}")
            return direcao
    elif sum(sinais_fortes) == 4 and sum(sinais_extras) >= 3:
        print(f"🔔 ⚠️ ALERTA: 4 sinais fortes + 3 extras detectados (verificação manual sugerida)")
        return None
    else:
        print(f"🔎 Apenas {total_confirmados}/9 sinais confirmados | Entrada bloqueada ❌")
        return None

print("🔁 Iniciando análise contínua de pares (a cada 1 segundo)...")

while True:
    for symbol in symbols:
        print(f"\n🔍 Analisando par: {symbol}")
        try:
            df = fetch_candles(symbol)
            df = calcular_indicadores(df)
            direcao = verificar_entrada(df)
            if direcao:
                enviar_ordem(symbol, direcao)
        except Exception as e:
            print(f"⚠️ Erro ao processar {symbol}: {e}")
    print("⏳ Aguardando próximo ciclo...")
    time.sleep(1)

