from flask import Flask
import os
import time
import random
import threading
import numpy as np
import pandas as pd
from pybit.unified_trading import HTTP
from datetime import datetime

app = Flask(__name__)

# Conectar à API da Bybit com variáveis de ambiente
api_key = os.getenv("BYBIT_API_KEY")
api_secret = os.getenv("BYBIT_API_SECRET")

session = HTTP(
    api_key=api_key,
    api_secret=api_secret,
    testnet=False
)

@app.route("/")
def home():
    return "SukachBot CRYPTO PRO ativo com 12 indicadores + gestão de risco avançada! 🚀"

@app.route("/saldo")
def saldo():
    try:
        response = session.get_wallet_balance(accountType="UNIFIED")
        coins = response["result"]["list"][0]["coin"]
        output = "<h2>Saldo Atual:</h2><ul>"
        for coin in coins:
            value = coin.get("availableToWithdraw", "0")
            try:
                balance = float(value)
                if balance > 0:
                    output += f"<li>{coin['coin']}: {balance}</li>"
            except ValueError:
                continue
        output += "</ul>"
        return output or "Sem saldo disponível."
    except Exception as e:
        return f"Erro ao obter saldo: {str(e)}"

pares = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "MATICUSDT",
    "AVAXUSDT", "LINKUSDT", "TONUSDT", "FETUSDT", "ADAUSDT",
    "RNDRUSDT", "SHIB1000USDT"  # Corrigido SHIBUSDT para SHIB1000USDT
]

def calcular_indicadores(candles):
    df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"])
    df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].astype(float)

    sinais = []

    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    if rsi.iloc[-1] < 30:
        sinais.append("RSI")

    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    if macd.iloc[-1] > signal.iloc[-1]:
        sinais.append("MACD")

    lowest_low = df["low"].rolling(window=14).min()
    highest_high = df["high"].rolling(window=14).max()
    stoch_k = 100 * ((df["close"] - lowest_low) / (highest_high - lowest_low))
    if stoch_k.iloc[-1] < 20:
        sinais.append("Stoch")

    ema9 = df["close"].ewm(span=9).mean()
    ema21 = df["close"].ewm(span=21).mean()
    if ema9.iloc[-1] > ema21.iloc[-1]:
        sinais.append("EMA")

    df["tr"] = df[["high", "low", "close"]].max(axis=1) - df[["high", "low", "close"]].min(axis=1)
    df["plus_dm"] = df["high"].diff()
    df["minus_dm"] = df["low"].diff()
    tr14 = df["tr"].rolling(14).mean()
    plus_di = 100 * (df["plus_dm"].rolling(14).mean() / tr14)
    minus_di = 100 * (df["minus_dm"].rolling(14).mean() / tr14)
    adx = ((plus_di - minus_di).abs() / (plus_di + minus_di)).rolling(14).mean() * 100
    if adx.iloc[-1] > 25:
        sinais.append("ADX")

    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    cci = (typical_price - typical_price.rolling(20).mean()) / (0.015 * typical_price.rolling(20).std())
    if cci.iloc[-1] < -100:
        sinais.append("CCI")

    sma = df["close"].rolling(window=20).mean()
    std = df["close"].rolling(window=20).std()
    upper = sma + 2 * std
    lower = sma - 2 * std
    if df["close"].iloc[-1] < lower.iloc[-1]:
        sinais.append("Bollinger")

    momentum = df["close"].diff(periods=10)
    if momentum.iloc[-1] > 0:
        sinais.append("Momentum")

    if df["close"].iloc[-1] > df["open"].iloc[-1]:
        sinais.append("PSAR")

    obv = (np.sign(df["close"].diff()) * df["volume"]).fillna(0).cumsum()
    if obv.iloc[-1] > obv.iloc[-2]:
        sinais.append("OBV")

    return sinais

def monitorar_mercado():
    while True:
        try:
            par = random.choice(pares)
            print(f"🔍 Analisando {par}...")

            candles_raw = session.get_kline(
                category="linear",
                symbol=par,
                interval="1",
                limit=50
            )["result"]["list"]

            if not candles_raw or len(candles_raw) < 20:
                print(f"⚠️ Poucos dados em {par}, a ignorar...")
                time.sleep(1)
                continue

            sinais = calcular_indicadores(candles_raw)
            print(f"🔎 Indicadores alinhados: {len(sinais)} ➝ {sinais}")

            if len(sinais) >= 6:
                preco_atual = float(candles_raw[-1][4])
                usdt_alvo = 5
                alavancagem = 4
                qty = round((usdt_alvo * alavancagem) / preco_atual, 3)

                take_profit = round(preco_atual * 1.03, 3)
                stop_loss = round(preco_atual * 0.99, 3)

                session.place_order(
                    category="linear",
                    symbol=par,
                    side="Buy",
                    orderType="Market",
                    qty=qty,
                    takeProfit=take_profit,
                    stopLoss=stop_loss,
                    leverage=alavancagem
                )

                print(f"🚀 ENTRADA REAL: {par} | Qty: {qty} | TP: {take_profit} | SL: {stop_loss} | Sinais: {len(sinais)}")

            time.sleep(1)

        except Exception as e:
            print(f"⚠️ Erro: {str(e)}")
            time.sleep(2)

if __name__ == "__main__":
    threading.Thread(target=monitorar_mercado).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

