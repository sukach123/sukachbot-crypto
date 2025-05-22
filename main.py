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

# ... (outras funções iguais)

def enviar_ordem(symbol, lado):
    try:
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
            isIsolated=True,
            takeProfit=round(preco_atual * 1.015, 3) if lado == "Buy" else round(preco_atual * 0.985, 3),
            stopLoss=round(preco_atual * 0.997, 3) if lado == "Buy" else round(preco_atual * 1.003, 3)
        )

        if response.get("retCode") == 0:
            print(f"🚀 Ordem {lado} executada com sucesso!")
        else:
            print(f"❌ Ordem falhou: {response.get('retMsg', 'Erro desconhecido')}")

    except Exception as e:
        print(f"❌ Erro ao enviar ordem: {e}")

