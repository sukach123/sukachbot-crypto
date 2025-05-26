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
    # ADX - cálculo simplificado
    df['TR'] = np.maximum(df['high'] - df['low'], np.maximum(abs(df['high'] - df['close'].shift()), abs(df['low'] - df['close'].shift())))
    df['+DM'] = np.where((df['high'] - df['high'].shift()) > (df['low'].shift() - df['low']), np.maximum(df['high'] - df['high'].shift(), 0), 0)
    df['-DM'] = np.where((df['low'].shift() - df['low']) > (df['high'] - df['high'].shift()), np.maximum(df['low'].shift() - df['low'], 0), 0)
    tr14 = df['TR'].rolling(14).sum()
    plus_dm14 = df['+DM'].rolling(14).sum()
    minus_dm14 = df['-DM'].rolling(14).sum()
    plus_di = 100 * (plus_dm14 / tr14)
    minus_di = 100 * (minus_dm14 / tr14)
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    df["ADX"] = dx.rolling(14).mean()
    # Indicador lateralidade (simples) - True se mercado não lateral
    df["nao_lateral"] = df["close"].rolling(10).std() > 0.0005
    # Volume explosivo simples (exemplo)
    df["volume_explosivo"] = df["volume"] > df["volume"].rolling(20).mean() * 1.5
    return df

def identificar_sinais(row, ultimos5, prev):
    corpo = abs(row["close"] - row["open"])
    # Sinais fortes (5)
    sinal_1 = (row["EMA10"] > row["EMA20"]) or (row["EMA10"] < row["EMA20"])
    sinal_2 = row["MACD"] > row["SINAL"]
    sinal_3 = row["CCI"] > 0
    sinal_4 = row["ADX"] > 20
    sinal_5 = row["nao_lateral"]
    sinais_fortes = [sinal_1, sinal_2, sinal_3, sinal_4, sinal_5]
    # Sinais extras (4)
    sinal_6 = row["volume_explosivo"]
    sinal_7 = corpo > ultimos5["close"].max() - ultimos5["low"].min()
    extra_1 = prev["close"] > prev["open"]
    extra_2 = (row["high"] - row["close"]) < corpo
    sinais_extras = [sinal_6, sinal_7, extra_1, extra_2]
    return sinais_fortes, sinais_extras

def calcular_quantidade(symbol, preco_entrada):
    global saldo_usdt
    qtd_usdt = quantidade_usdt
    if symbol in pares_com_erro_leverage:
        qtd_usdt = quantidade_usdt / 10  # reduzir exposição para pares com problema
    quantidade = qtd_usdt / preco_entrada
    return quantidade

def colocar_ordem(symbol, lado, quantidade, preco_entrada):
    tp_percent = 0.015
    sl_percent = 0.003
    if lado == "LONG":
        tp_price = round(preco_entrada * (1 + tp_percent), 6)
        sl_price = round(preco_entrada * (1 - sl_percent), 6)
        side = "Buy"
    else:
        tp_price = round(preco_entrada * (1 - tp_percent), 6)
        sl_price = round(preco_entrada * (1 + sl_percent), 6)
        side = "Sell"
    try:
        order = session.place_active_order_v3(
            symbol=symbol,
            side=side,
            orderType="Market",
            qty=round(quantidade, 6),
            price=None,
            timeInForce="GoodTillCancel",
            reduceOnly=False,
            closeOnTrigger=False,
            takeProfit=tp_price,
            stopLoss=sl_price,
            positionIdx=0
        )
        print(f"🟢 Ordem {lado} enviada para {symbol} - Qtd: {quantidade}")
        print(f"   Preço entrada: {preco_entrada}, TP: {tp_price}, SL: {sl_price}")
        return True
    except Exception as e:
        print(f"❌ Erro ao enviar pedido para {symbol}: {e}")
        return False

def main():
    while True:
        for symbol in symbols:
            df = fetch_candles(symbol, interval)
            df = calcular_indicadores(df)
            row = df.iloc[-1]
            ultimos5 = df.iloc[-6:-1]
            prev = df.iloc[-2]

            sinais_fortes, sinais_extras = identificar_sinais(row, ultimos5, prev)
            total_fortes = sum(sinais_fortes)
            total_extras = sum(sinais_extras)
            total_sinais = total_fortes + total_extras

            entrada = None
            if total_fortes >= 6 or (total_fortes >= 5 and total_extras >= 2):
                if row["EMA10"] > row["EMA20"]:
                    entrada = "LONG"
                else:
                    entrada = "SHORT"

            print(f"\n🔍 Analisando {symbol}")
            print(f"Sinais fortes: {total_fortes}, extras: {total_extras}, entrada sugerida: {entrada if entrada else 'NENHUMA'}")

            if entrada:
                preco_entrada = row["close"]
                quantidade = calcular_quantidade(symbol, preco_entrada)
                colocar_ordem(symbol, entrada, quantidade, preco_entrada)
            else:
                print(f"🔎 Entrada bloqueada para {symbol} | Sinais insuficientes.")

            time.sleep(3)  # delay entre símbolos para evitar excesso de chamadas

        print("\n⏳ Esperando próximo ciclo...\n")
        time.sleep(15)  # delay geral antes de novo ciclo

if __name__ == "__main__":
    main()

