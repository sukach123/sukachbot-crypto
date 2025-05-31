import os
import time
from pybit.unified_trading import HTTP
import pandas as pd

# Pegue suas keys da testnet nos .env ou configure aqui direto:
API_KEY = os.getenv("BYBIT_API_KEY") or "sua_api_key_testnet"
API_SECRET = os.getenv("BYBIT_API_SECRET") or "seu_api_secret_testnet"

# Criar sessão testnet - importante testnet=True para usar ambiente de teste
session = HTTP(api_key=API_KEY, api_secret=API_SECRET, testnet=True)

PAIR = "BTCUSDT"
CATEGORY = "linear"
INTERVAL = "1"  # 1 minuto
QTY = 0.01  # quantidade a operar

def get_latest_candle():
    """Busca o último candle de 1min."""
    response = session.get_kline(
        category=CATEGORY,
        symbol=PAIR,
        interval=INTERVAL,
        limit=1
    )
    data = response["result"]["list"][0]
    df = pd.DataFrame([data], columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"])
    df[["open","high","low","close","volume"]] = df[["open","high","low","close","volume"]].astype(float)
    return df

def padrao_vela_bullish(df):
    """Detecta padrão bullish simples no último candle."""
    corpo = abs(df['close'].iloc[-1] - df['open'].iloc[-1])
    sombra_inferior = df['open'].iloc[-1] - df['low'].iloc[-1] if df['close'].iloc[-1] > df['open'].iloc[-1] else df['close'].iloc[-1] - df['low'].iloc[-1]
    sombra_superior = df['high'].iloc[-1] - max(df['open'].iloc[-1], df['close'].iloc[-1])
    martelo = sombra_inferior > corpo * 2 and sombra_superior < corpo
    return martelo

def enviar_ordem_buy(qty, take_profit, stop_loss):
    """Enviar ordem Market Buy com TP e SL"""
    try:
        ordem = session.place_active_order(
            category=CATEGORY,
            symbol=PAIR,
            side="Buy",
            order_type="Market",
            qty=qty,
            time_in_force="GoodTillCancel",
            take_profit=take_profit,
            stop_loss=stop_loss,
            reduce_only=False,
            close_on_trigger=False
        )
        print("✅ Ordem enviada:", ordem)
    except Exception as e:
        print("❌ Erro ao enviar ordem:", e)

def main():
    while True:
        try:
            df = get_latest_candle()
            print(f"Último candle: open={df['open'].iloc[-1]}, close={df['close'].iloc[-1]}, low={df['low'].iloc[-1]}, high={df['high'].iloc[-1]}")

            # Se padrão bullish detectado, entra buy
            if padrao_vela_bullish(df):
                preco_entrada = df['close'].iloc[-1]
                tp = preco_entrada * 1.005  # TP +0.5%
                sl = preco_entrada * 0.995  # SL -0.5%
                print(f"Sinal BUY detectado - Entrando com QTY {QTY}, TP {tp:.2f}, SL {sl:.2f}")
                enviar_ordem_buy(QTY, take_profit=tp, stop_loss=sl)
            else:
                print("Nenhum sinal de compra detectado.")

        except Exception as e:
            print("Erro geral no loop:", e)

        time.sleep(60)  # espera 1 minuto

if __name__ == "__main__":
    main()
