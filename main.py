import os
import time
import pandas as pd
from pybit.unified_trading import HTTP
from datetime import datetime, timedelta

# Carregar variáveis ambiente (se usar .env)
from dotenv import load_dotenv
load_dotenv()

# Configurações API
api_key = os.getenv("BYBIT_API_KEY")
api_secret = os.getenv("BYBIT_API_SECRET")
session = HTTP(api_key=api_key, api_secret=api_secret, testnet=True)

PAIRS = ["DOGEUSDT"]  # Pode adicionar mais pares
INTERVAL = "1"        # 1 minuto candles

# Função para obter candles 1m recentes (limit=50)
def obter_candles(symbol, interval="1", limit=50):
    params = {
        "category": "linear",
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }
    res = session.get_kline(**params)
    candles = res["result"]["list"]
    df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"])
    df["timestamp"] = pd.to_datetime(df["timestamp"].astype(int), unit='ms')
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    return df

# Detecta martelo simples (exemplo)
def padrao_vela_bullish(df):
    if len(df) < 2:
        return False
    corpo = abs(df['close'].iloc[-1] - df['open'].iloc[-1])
    sombra_inferior = df['open'].iloc[-1] - df['low'].iloc[-1] if df['close'].iloc[-1] > df['open'].iloc[-1] else df['close'].iloc[-1] - df['low'].iloc[-1]
    sombra_superior = df['high'].iloc[-1] - max(df['open'].iloc[-1], df['close'].iloc[-1])
    martelo = sombra_inferior > corpo * 2 and sombra_superior < corpo
    return martelo

# Função para enviar ordem (corrigida)
def enviar_ordem(session, symbol, side, qty, tp, sl):
    try:
        resp = session.place_order(
            category="linear",
            symbol=symbol,
            side=side,            # "Buy" ou "Sell"
            order_type="Market",
            qty=str(qty),
            take_profit=str(tp),
            stop_loss=str(sl),
            time_in_force="GoodTillCancel"
        )
        print(f"✅ Ordem enviada: {side} {qty} {symbol} TP={tp} SL={sl}")
        print("Resposta da API:", resp)
    except Exception as e:
        print(f"❌ Erro ao enviar ordem: {e}")

def main():
    while True:
        for pair in PAIRS:
            print(f"\n⏳ Analisando {pair} - {datetime.utcnow()} UTC")
            df = obter_candles(pair)
            if padrao_vela_bullish(df):
                preco_entrada = df["close"].iloc[-1]
                qty = 10  # Ajuste quantidade conforme saldo/testnet
                tp = preco_entrada * 1.005  # +0.5% TP
                sl = preco_entrada * 0.995  # -0.5% SL
                print(f"Sinal BUY detectado em {pair} - Preço: {preco_entrada:.6f}")
                enviar_ordem(session, pair, "Buy", qty, tp, sl)
            else:
                print(f"Sem sinal para {pair} no momento.")
        print("Aguardando 60 segundos para próxima análise...\n")
        time.sleep(60)

if __name__ == "__main__":
    main()
