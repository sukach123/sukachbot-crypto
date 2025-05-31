import os
import time
import pandas as pd
import ta
from datetime import datetime
from pybit.unified_trading import HTTP
from dotenv import load_dotenv

load_dotenv()

# === Sessão Bybit TESTNET ===
session = HTTP(
    testnet=True,
    api_key=os.getenv("API_KEY"),
    api_secret=os.getenv("API_SECRET")
)

PAIR = "ADAUSDT"
INTERVAL = "1"
USDT_PER_TRADE = 5
LEVERAGE = 10
TP_PERCENT = 1.5 / 100

def get_klines(symbol, interval="1", limit=100):
    try:
        response = session.get_kline(
            category="linear",
            symbol=symbol,
            interval=interval,
            limit=limit
        )
        df = pd.DataFrame(response['result']['list'])
        df.columns = ['timestamp','open','high','low','close','volume','turnover']
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.astype({
            "open": float,
            "high": float,
            "low": float,
            "close": float,
            "volume": float
        })
        df.sort_values("timestamp", inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df
    except Exception as e:
        print("Erro ao buscar candles:", e)
        return None

def avaliar_sinais(df):
    sinais_fortes = 0
    sinais_extras = 0

    df["EMA10"] = ta.trend.ema_indicator(df["close"], window=10)
    df["EMA20"] = ta.trend.ema_indicator(df["close"], window=20)

    if df["EMA10"].iloc[-1] > df["EMA20"].iloc[-1]:
        sinais_fortes += 1
        print("📌 EMA10 vs EMA20: True")
    else:
        print("📌 EMA10 vs EMA20: False")

    corpo = abs(df["close"].iloc[-1] - df["open"].iloc[-1])
    range_total = df["high"].iloc[-1] - df["low"].iloc[-1]
    if corpo > 0.7 * range_total:
        sinais_fortes += 1
        print("📌 Corpo grande: True")
    else:
        print("📌 Corpo grande: False")

    ultimos_closes = df["close"].iloc[-5:]
    if not (ultimos_closes.max() - ultimos_closes.min()) < 0.003 * ultimos_closes.mean():
        sinais_fortes += 1
        print("📌 Não lateral: True")
    else:
        print("📌 Não lateral: False")

    if df["close"].iloc[-2] > df["open"].iloc[-2]:
        sinais_extras += 1
        print("📌 Extra: Vela anterior de alta: True")
    else:
        print("📌 Extra: Vela anterior de alta: False")

    pavio_superior = df["high"].iloc[-1] - max(df["close"].iloc[-1], df["open"].iloc[-1])
    if pavio_superior < 0.25 * (df["high"].iloc[-1] - df["low"].iloc[-1]):
        sinais_extras += 1
        print("📌 Extra: Pequeno pavio superior: True")
    else:
        print("📌 Extra: Pequeno pavio superior: False")

    total = sinais_fortes + sinais_extras
    print(f"\n✔️ Total: {sinais_fortes} fortes + {sinais_extras} extras = {total}/9")

    if sinais_fortes >= 5 or (sinais_fortes == 4 and sinais_extras >= 1):
        print(f"\n🔔 {df['timestamp'].iloc[-1]} | Entrada validada com {sinais_fortes} fortes + {sinais_extras} extras!")
        return True
    return False

def calcular_quantidade(symbol, usdt, preco):
    try:
        qty = round(usdt / preco, 3)
        return qty
    except:
        return None

def enviar_ordem_buy(symbol, preco_entrada):
    qty = calcular_quantidade(symbol, USDT_PER_TRADE, preco_entrada)
    if not qty:
        print("Erro ao calcular quantidade.")
        return

    try:
        print(f"\n📦 Tentando enviar ordem:\n\n    ➤ Par: {symbol}\n    ➤ Direção: Buy\n    ➤ Preço atual: {preco_entrada}\n    ➤ Quantidade calculada: {qty}")

        session.set_leverage(
            category="linear",
            symbol=symbol,
            buyLeverage=LEVERAGE,
            sellLeverage=LEVERAGE
        )

        ordem = session.place_order(
            category="linear",
            symbol=symbol,
            side="Buy",
            order_type="Market",
            qty=qty,
            time_in_force="GoodTillCancel",
            reduce_only=False
        )

        ordem_id = ordem['result']['orderId']
        print(f"✅ Ordem enviada com sucesso! ID: {ordem_id}")

        tp_price = round(preco_entrada * (1 + TP_PERCENT), 4)

        session.set_take_profit(
            category="linear",
            symbol=symbol,
            takeProfit=tp_price,
            positionIdx=1
        )
        print(f"🎯 Take Profit colocado em: {tp_price}")

    except Exception as e:
        print("🚨 Erro ao enviar ordem:", e)

def main():
    while True:
        df = get_klines(PAIR, interval=INTERVAL, limit=100)
        if df is not None:
            if avaliar_sinais(df):
                preco_entrada = df["close"].iloc[-1]
                enviar_ordem_buy(PAIR, preco_entrada)
        time.sleep(60)

if __name__ == "__main__":
    main()

