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
    saldo_usdt = float(balance['result']['list'][0]['totalEquity'])
    print(f"💰 Saldo disponível (simulado): {saldo_usdt} USDT")
except Exception as e:
    print(f"❌ Falha ao conectar à API: {e}")
    exit()

symbols = ["BNBUSDT", "BTCUSDT", "DOGEUSDT", "SOLUSDT", "ADAUSDT", "ETHUSDT"]
interval = "1"
quantidade_usdt = 5  # Valor em USDT para investir por operação

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

def calcular_adx(df, n=14):
    # Função para calcular ADX
    df['up_move'] = df['high'].diff()
    df['down_move'] = df['low'].diff().abs()
    df['plus_dm'] = np.where((df['up_move'] > df['down_move']) & (df['up_move'] > 0), df['up_move'], 0)
    df['minus_dm'] = np.where((df['down_move'] > df['up_move']) & (df['down_move'] > 0), df['down_move'], 0)
    df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(abs(df['high'] - df['close'].shift()), abs(df['low'] - df['close'].shift())))
    atr = df['tr'].rolling(n).mean()
    plus_di = 100 * (df['plus_dm'].rolling(n).mean() / atr)
    minus_di = 100 * (df['minus_dm'].rolling(n).mean() / atr)
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    adx = dx.rolling(n).mean()
    return adx

def calcular_indicadores(df):
    df["EMA10"] = df["close"].ewm(span=10).mean()
    df["EMA20"] = df["close"].ewm(span=20).mean()
    df["MACD"] = df["close"].ewm(span=12).mean() - df["close"].ewm(span=26).mean()
    df["SINAL"] = df["MACD"].ewm(span=9).mean()
    df["CCI"] = (df["close"] - df["close"].rolling(20).mean()) / (0.015 * df["close"].rolling(20).std())
    df["ADX"] = calcular_adx(df)
    df["volume_explosivo"] = df["volume"] > df["volume"].rolling(20).mean() * 1.5
    return df

def gerar_sinais(df):
    sinais_fortes = 0
    sinais_extras = 0
    entrada = "NENHUMA"

    # Sinais fortes - exemplo básico
    if df["EMA10"].iloc[-1] > df["EMA20"].iloc[-1]:
        sinais_fortes += 1
    if df["MACD"].iloc[-1] > df["SINAL"].iloc[-1]:
        sinais_fortes += 1
    if df["CCI"].iloc[-1] > 100:
        sinais_fortes += 1
    if df["ADX"].iloc[-1] > 25:
        sinais_fortes += 1
    if df["volume_explosivo"].iloc[-1]:
        sinais_fortes += 1

    # Sinais extras - exemplo básico
    if df["CCI"].iloc[-1] < -100:
        sinais_extras += 1

    # Definição da entrada
    if sinais_fortes >= 4:
        entrada = "LONG"
    elif sinais_extras >= 1:
        entrada = "SHORT"

    return sinais_fortes, sinais_extras, entrada

def calcular_quantidade(symbol, preco_atual, saldo_usdt=quantidade_usdt):
    # Calcula quantidade para comprar com saldo_usdt valor em USDT
    # Ajuste para preços e lotes mínimos se necessário
    quantidade = saldo_usdt / preco_atual
    return round(quantidade, 4)  # arredonda para 4 casas decimais (ajuste se necessário)

def enviar_ordem(symbol, entrada, preco_atual):
    side = "Buy" if entrada == "LONG" else "Sell"
    quantidade = calcular_quantidade(symbol, preco_atual)
    try:
        response = session.submit_order(
            symbol=symbol,
            side=side,
            orderType="Market",
            qty=quantidade,
            timeInForce="GoodTillCancel",
            reduceOnly=False,
            closeOnTrigger=False,
        )
        print(f"💡 Ordem enviada para {symbol}: {entrada} {quantidade} unidades")
    except Exception as e:
        print(f"❌ Erro ao enviar pedido para {symbol}: {e}")

def main():
    while True:
        for symbol in symbols:
            print(f"\n🔍 Analisando {symbol}")
            df = fetch_candles(symbol, interval)
            print("🧮 Calculando indicadores...")
            df = calcular_indicadores(df)
            print("✅ Indicadores calculados.")

            sinais_fortes, sinais_extras, entrada = gerar_sinais(df)
            print(f"Sinais fortes: {sinais_fortes}, extras: {sinais_extras}, entrada sugerida: {entrada}")

            if entrada != "NENHUMA":
                preco_atual = df["close"].iloc[-1]
                enviar_ordem(symbol, entrada, preco_atual)
            else:
                print("Nenhuma entrada válida no momento.")

            # Removido o sleep entre análises para rodar a cada ciclo sem pausa grande

        # Pequena pausa para evitar excesso de chamadas API (ajuste conforme limite da API)
        time.sleep(1)  # 1 segundo entre rodadas para não sobrecarregar API

if __name__ == "__main__":
    main()
