import pandas as pd
import numpy as np
from pybit.unified_trading import HTTP
import time
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

print("🚧 MODO DEMO ATIVO - Bybit Testnet em execução 🚧")

# Configurações
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
        atraso = int((now - df["timestamp"].iloc[-1]).total_seconds())
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
    df["ADX"] = ta_adx(df)  # você deve implementar ou usar uma lib para ADX
    df["volume_explosivo"] = df["volume"] > df["volume"].rolling(20).mean() * 1.5  # Exemplo
    
    return df

# Função para calcular ADX, pode usar ta-lib ou outro método (simplificado aqui)
def ta_adx(df, n=14):
    # Placeholder simples para ADX, implementar corretamente com talib ou manualmente
    # Para manter o exemplo simples, retorna 25 fixo
    return pd.Series([25]*len(df), index=df.index)

def identificar_sinais(df):
    sinais = []
    for i in range(20, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]
        ultimos5 = df.iloc[i-5:i]

        corpo = abs(row["close"] - row["open"])
        nao_lateral = abs(row["EMA10"] - row["EMA20"]) > 0.001  # critério lateralidade simples

        # Sinais fortes
        sinal_1 = (row["EMA10"] > row["EMA20"]) or (row["EMA10"] < row["EMA20"])  # sempre True? ajustar?
        sinal_2 = row["MACD"] > row["SINAL"]
        sinal_3 = row["CCI"] > 0
        sinal_4 = row["ADX"] > 20
        sinal_5 = nao_lateral
        sinais_fortes = [sinal_1, sinal_2, sinal_3, sinal_4, sinal_5]

        # Sinais extras
        sinal_6 = row["volume_explosivo"]
        sinal_7 = corpo > ultimos5["close"].max() - ultimos5["low"].min()
        extra_1 = prev["close"] > prev["open"]
        extra_2 = (row["high"] - row["close"]) < corpo
        sinais_extras = [sinal_6, sinal_7, extra_1, extra_2]

        # Contar sinais
        fortes_count = sum(sinais_fortes)
        extras_count = sum(sinais_extras)

        # Determinar entrada LONG ou SHORT
        # Aqui supomos LONG se EMA10 > EMA20 e MACD > SINAL e SHORT o contrário
        if fortes_count >= 5 or (fortes_count >= 4 and extras_count >= 2):
            if row["EMA10"] > row["EMA20"] and row["MACD"] > row["SINAL"]:
                entrada = "LONG"
            elif row["EMA10"] < row["EMA20"] and row["MACD"] < row["SINAL"]:
                entrada = "SHORT"
            else:
                entrada = "NONE"
        else:
            entrada = "NONE"

        sinais.append({
            "timestamp": row["timestamp"],
            "fortes": fortes_count,
            "extras": extras_count,
            "entrada": entrada
        })

    return sinais

def colocar_ordem(symbol, lado, preco_entrada, quantidade):
    try:
        # Calcular TP e SL baseado no preço de entrada
        if lado == "LONG":
            tp_price = preco_entrada * 1.015  # +1.5%
            sl_price = preco_entrada * 0.99   # -1%
        elif lado == "SHORT":
            tp_price = preco_entrada * 0.985  # -1.5%
            sl_price = preco_entrada * 1.01   # +1%
        else:
            print(f"⚠️ Ordem não executada. Lado inválido: {lado}")
            return

        # Criar ordem de mercado com TP e SL (exemplo básico)
        print(f"🟢 Enviando ordem {lado} para {symbol} - Qtd: {quantidade} USDT")
        print(f"   Preço entrada: {preco_entrada:.4f}, TP: {tp_price:.4f}, SL: {sl_price:.4f}")

        # Aqui você deve usar os endpoints corretos da API Bybit para abrir posição e colocar TP/SL
        # Exemplo simplificado:
        ordem = session.place_active_order(
            symbol=symbol,
            side=lado,
            orderType="Market",
            qty=quantidade,
            timeInForce="GoodTillCancel",
            reduceOnly=False,
            closeOnTrigger=False,
            takeProfit=tp_price,
            stopLoss=sl_price
        )
        print(f"✅ Ordem enviada: {ordem}")
    except Exception as e:
        print(f"❌ Erro ao enviar ordem para {symbol}: {e}")

def main():
    while True:
        for symbol in symbols:
            print(f"\n🔍 Analisando {symbol}")
            df = fetch_candles(symbol, interval)
            df = calcular_indicadores(df)
            sinais = identificar_sinais(df)
            if not sinais:
                print("Sem sinais suficientes para analisar.")
                continue

            ultimo_sinal = sinais[-1]
            print(f"Sinais fortes: {ultimo_sinal['fortes']}, extras: {ultimo_sinal['extras']}, entrada sugerida: {ultimo_sinal['entrada']}")

            if ultimo_sinal['entrada'] in ["LONG", "SHORT"]:
                preco_entrada = df.iloc[-1]["close"]
                quantidade = quantidade_usdt / preco_entrada
                colocar_ordem(symbol, ultimo_sinal['entrada'], preco_entrada, quantidade)
            else:
                print("⏸️ Entrada bloqueada - sinais insuficientes ou sem tendência clara.")

        time.sleep(60)  # espera 1 minuto para próxima checagem

if __name__ == "__main__":
    main()

