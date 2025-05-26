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

session = HTTP(
    testnet=True,
    api_key=os.getenv("API_KEY"),
    api_secret=os.getenv("API_SECRET")
)

ativos = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT", "DOGEUSDT"]
INTERVALO = 1  # minuto
VELAS = 1000

def obter_dados(simbolo):
    try:
        resposta = session.get_kline(
            category="linear",
            symbol=simbolo,
            interval=str(INTERVALO),
            limit=VELAS
        )
        dados = resposta['result']['list']
        df = pd.DataFrame(dados, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'
        ])
        df = df.astype(float)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        print(f"Erro ao obter velas de {simbolo}: {e}")
        return None

def calcular_indicadores(df):
    df["EMA10"] = df["close"].ewm(span=10, adjust=False).mean()
    df["EMA20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["MACD"] = df["close"].ewm(span=12).mean() - df["close"].ewm(span=26).mean()
    df["SINAL"] = df["MACD"].ewm(span=9).mean()
    df["CCI"] = (df["close"] - df["close"].rolling(20).mean()) / (0.015 * df["close"].rolling(20).std())
    df["ADX"] = abs(df["high"] - df["low"]).rolling(14).mean()
    df["RSI"] = 100 - (100 / (1 + df["close"].diff().clip(lower=0).rolling(14).mean() /
                              -df["close"].diff().clip(upper=0).rolling(14).mean()))
    df["STOCHK"] = ((df["close"] - df["low"].rolling(14).min()) /
                    (df["high"].rolling(14).max() - df["low"].rolling(14).min())) * 100
    df["STOCHD"] = df["STOCHK"].rolling(3).mean()
    return df

def sinais(df):
    ult = df.iloc[-1]
    sinais_fortes = [
        ult["EMA10"] > ult["EMA20"],
        ult["MACD"] > ult["SINAL"],
        ult["CCI"] > 0,
        ult["ADX"] > 20,
        ult["RSI"] > 50
    ]
    sinais_extras = [
        ult["STOCHK"] > ult["STOCHD"],
        ult["EMA10"] > df["EMA10"].shift(1).iloc[-1],
        ult["close"] > ult["EMA10"],
        ult["STOCHK"] > 50
    ]
    return sinais_fortes.count(True), sinais_extras.count(True)

def calcular_quantidade(symbol, usdt=20):
    try:
        preco = float(obter_dados(symbol)['close'].iloc[-1])
        return round(usdt / preco, 8)
    except:
        return 0

def enviar_ordem(simbolo, lado, quantidade, preco):
    try:
        tp = round(preco * 1.015, 4)
        sl = round(preco * 0.997, 4)
        print(f"🟢 Enviando ordem {lado} para {simbolo} - Qtd: {quantidade}")
        print(f"   Preço entrada: {preco}, TP: {tp}, SL: {sl}")
        session.place_order(
            category="linear",
            symbol=simbolo,
            side=lado,
            order_type="Market",
            qty=quantidade,
            take_profit=tp,
            stop_loss=sl,
            time_in_force="GoodTillCancel"
        )
    except Exception as e:
        print(f"❌ Erro ao enviar ordem para {simbolo}: {e}")

def analisar(simbolo):
    print(f"\n🔍 Analisando {simbolo}")
    df = obter_dados(simbolo)
    if df is None or len(df) < 50:
        print(f"❌ Dados insuficientes para {simbolo}")
        return
    print("🧮 Calculando indicadores...")
    df = calcular_indicadores(df)
    fortes, extras = sinais(df)
    print(f"Sinais fortes: {fortes}, extras: {extras}", end='')

    if fortes >= 6 or (fortes >= 5 and extras >= 2):
        lado = "Buy"
    elif fortes <= 1 and extras <= 2:
        lado = "Sell"
    else:
        print(", entrada sugerida: NENHUMA\nNenhuma entrada válida no momento.")
        return

    preco_entrada = float(df["close"].iloc[-1])
    quantidade = calcular_quantidade(simbolo)
    enviar_ordem(simbolo, lado, quantidade, preco_entrada)

def principal():
    while True:
        for simbolo in ativos:
            analisar(simbolo)
        time.sleep(1)

if __name__ == "__main__":
    try:
        print("🔐 Verificando acesso à API...")
        saldo = session.get_wallet_balance(accountType="UNIFIED")['result']['list'][0]['totalEquity']
        print(f"✅ API conectada com sucesso!\n💰 Saldo disponível (simulado): {saldo} USDT")
        principal()
    except Exception as e:
        print(f"Erro crítico: {e}")
