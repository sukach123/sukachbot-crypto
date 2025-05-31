import time
import os
import pandas as pd
from pybit.unified_trading import HTTP
from datetime import datetime

# Configurar API (usar suas keys e testnet=True)
api_key = os.getenv("BYBIT_API_KEY")
api_secret = os.getenv("BYBIT_API_SECRET")

session = HTTP(api_key=api_key, api_secret=api_secret, testnet=True)

PAIR = "BTCUSDT"
QTY = 0.01
TP_PERCENT = 0.005  # 0.5% take profit
SL_PERCENT = 0.003  # 0.3% stop loss
INTERVAL = "1"

def obter_candles(symbol, interval="1", limit=10):
    resp = session.get_kline(
        category="linear",
        symbol=symbol,
        interval=interval,
        limit=limit
    )
    data = resp["result"]["list"]
    df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"])
    df["timestamp"] = pd.to_datetime(df["timestamp"].astype(int), unit='ms')
    df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].astype(float)
    return df

def eh_candle_bullish(df):
    # Simples: close > open no último candle
    candle = df.iloc[-1]
    return candle["close"] > candle["open"]

def colocar_ordem_compra(symbol, qty, tp_perc, sl_perc):
    try:
        # Buscar preço atual (last price)
        ticker = session.get_ticker(category="linear", symbol=symbol)
        price = float(ticker["result"]["lastPrice"])

        tp_price = price * (1 + tp_perc)
        sl_price = price * (1 - sl_perc)

        ordem = session.place_active_order(
            category="linear",
            symbol=symbol,
            side="Buy",
            order_type="Market",
            qty=qty,
            time_in_force="GoodTillCancel",
            take_profit=round(tp_price, 8),
            stop_loss=round(sl_price, 8)
        )
        print(f"✅ Ordem de COMPRA enviada: {ordem}")
    except Exception as e:
        print(f"❌ Erro ao enviar ordem: {e}")

def main():
    print("🤖 Iniciando robô testnet Bybit...")
    while True:
        print(f"\n⏳ Analisando {PAIR} - {datetime.utcnow()} UTC")
        df = obter_candles(PAIR, INTERVAL, 10)
        if eh_candle_bullish(df):
            print(f"🔎 Sinal BUY detectado em {PAIR} - Preço: {df.iloc[-1]['close']}")
            colocar_ordem_compra(PAIR, QTY, TP_PERCENT, SL_PERCENT)
        else:
            print(f"🔎 Sem sinal de compra no momento em {PAIR}.")
        print("⏰ Aguardando 60 segundos para próxima análise...")
        time.sleep(60)

if __name__ == "__main__":
    main()
