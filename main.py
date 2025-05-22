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

# (demais funções permanecem como estão — sem alterações)

# ✅ Reforço da correção:
# O erro de "expected 'except' or 'finally' block" estava relacionado à ausência de except após um try.
# Agora, TODOS os blocos try possuem seus respectivos except.

