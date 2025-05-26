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
    df["ADX"] = adx_indicator(df)
    # Volume explosivo: volume do candle atual > média dos últimos 20 candles * 1.5
    df["volume_explosivo"] = df["volume"] > (df["volume"].rolling(20).mean() * 1.5)
    return df

def adx_indicator(df, n=14):
    # Calcula ADX básico
    high = df["high"]
    low = df["low"]
    close = df["close"]

    plus_dm = high.diff()
    minus_dm = low.diff().abs()

    plus_dm = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0)
    minus_dm = np.where((minus_dm > plus_dm) & (minus_dm > 0), minus_dm, 0)

    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)

    atr = tr.rolling(n).mean()

    plus_di = 100 * (pd.Series(plus_dm).rolling(n).sum() / atr)
    minus_di = 100 * (pd.Series(minus_dm).rolling(n).sum() / atr)

    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    adx = dx.rolling(n).mean()
    return adx

def sinais(df):
    row = df.iloc[-1]
    prev = df.iloc[-2]
    ultimos5 = df.iloc[-6:-1]

    corpo = abs(row["close"] - row["open"])
    nao_lateral = abs(row["close"] - row["open"]) / (row["high"] - row["low"]) > 0.5 if (row["high"] - row["low"]) != 0 else False

    # Sinais fortes
    sinal_1 = row["EMA10"] > row["EMA20"]
    sinal_2 = row["MACD"] > row["SINAL"]
    sinal_3 = row["CCI"] > 0
    sinal_4 = row["ADX"] > 20
    sinal_5 = nao_lateral
    fortes = [sinal_1, sinal_2, sinal_3, sinal_4, sinal_5]

    # Sinais extras
    sinal_6 = row["volume_explosivo"]
    sinal_7 = corpo > (ultimos5["close"].max() - ultimos5["low"].min())
    extra_1 = prev["close"] > prev["open"]
    extra_2 = (row["high"] - row["close"]) < corpo
    extras = [sinal_6, sinal_7, extra_1, extra_2]

    fortes_count = sum(bool(x) for x in fortes)
    extras_count = sum(bool(x) for x in extras)

    return fortes_count, extras_count

def colocar_ordem(symbol, side, quantidade, preco_entrada, tp, sl):
    try:
        # Ajuste do formato dos números para o API
        quantidade_str = f"{quantidade:.8f}".replace(',', '.')
        preco_entrada_str = f"{preco_entrada:.8f}".replace(',', '.')
        tp_str = f"{tp:.8f}".replace(',', '.')
        sl_str = f"{sl:.8f}".replace(',', '.')

        params = {
            "symbol": symbol,
            "side": side,
            "orderType": "Market",
            "qty": quantidade_str,
            "timeInForce": "GoodTillCancel",
            "takeProfit": tp_str,
            "stopLoss": sl_str
        }
        response = session.post_order_create(**params)
        print(f"✅ Ordem {side} enviada para {symbol} com quantidade {quantidade_str}")
        return response
    except Exception as e:
        print(f"❌ Erro ao enviar pedido para {symbol}: {e}")

def main():
    while True:
        for symbol in symbols:
            df = fetch_candles(symbol, interval)
            df = calcular_indicadores(df)

            now = datetime.now(timezone.utc)
            ultimo_candle_time = df["timestamp"].iloc[-1]
            atraso = (now - ultimo_candle_time).total_seconds()

            if atraso > 3:
                print(f"⚠️ ALERTA: Último candle de {symbol} está atrasado {atraso:.0f} segundos.")
                continue  # Pula símbolo até candle atualizado

            fortes_count, extras_count = sinais(df)

            entrada = "NONE"
            if fortes_count >= 6 or (fortes_count >= 5 and extras_count >= 2):
                entrada = "LONG"
            elif fortes_count <= 1 and extras_count >= 2:
                entrada = "SHORT"

            print(f"🔍 Analisando {symbol}")
            print(f"Sinais fortes: {fortes_count}, extras: {extras_count}, entrada sugerida: {entrada}")

            if entrada == "NONE":
                print("Nenhuma entrada válida no momento.\n")
                continue

            preco_entrada = df["close"].iloc[-1]
            if entrada == "LONG":
                tp = preco_entrada * 1.015  # +1.5%
                sl = preco_entrada * 0.99   # -1%
                side = "Buy"
            else:
                tp = preco_entrada * 0.985  # -1.5%
                sl = preco_entrada * 1.01   # +1%
                side = "Sell"

            quantidade = quantidade_usdt / preco_entrada
            print(f"🟢 Enviando ordem {entrada} para {symbol} - Qtd: {quantidade} USDT")
            print(f"   Preço entrada: {preco_entrada:.6f}, TP: {tp:.6f}, SL: {sl:.6f}")

            colocar_ordem(symbol, side, quantidade, preco_entrada, tp, sl)

        time.sleep(1)

if __name__ == "__main__":
    main()

