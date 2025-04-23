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

api_key = os.getenv("BYBIT_API_KEY")
api_secret = os.getenv("BYBIT_API_SECRET")

session = HTTP(
    api_key=api_key,
    api_secret=api_secret,
    testnet=False
)

historico_resultados = []  # lista para guardar os registos das operações

@app.route("/")
def home():
    return "SukachBot CRYPTO PRO ativo com análise avançada de estrutura, tendência e coerência de sinais! "

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

@app.route("/historico")
def historico():
    html = "<h2>Histórico de Entradas:</h2><ul>"
    for item in historico_resultados[-50:]:
        html += f"<li>{item}</li>"
    html += "</ul>"
    return html

def monitorar_mercado():
    while True:
        try:
            par = random.choice(["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "MATICUSDT",
                                "AVAXUSDT", "LINKUSDT", "TONUSDT", "FETUSDT", "ADAUSDT",
                                "RNDRUSDT", "SHIB1000USDT"])
            print(f"Analisando {par}...")
            candles_raw = session.get_kline(
                category="linear",
                symbol=par,
                interval="1",
                limit=50
            )["result"]["list"]
            if not candles_raw or len(candles_raw) < 20:
                print(f"Poucos dados em {par}, a ignorar...")
                time.sleep(1)
                continue

            sinais, tendencia, candle_confirma, coerente = calcular_indicadores(candles_raw)

            print(f"Indicadores: {len(sinais)} ➝ {sinais} | Tendência: {tendencia} | Candle confirma: {candle_confirma} | Coerente: {coerente}")

            if not (5 <= len(sinais) <= 12):
                print("⛔ Não entrou: número de sinais fora do intervalo (5-12)")
            if tendencia not in ["alta", "baixa", "lateral"]:
                print("⛔ Não entrou: tendência indefinida")
            if not candle_confirma:
                print("⛔ Não entrou: candle não confirma a tendência")
            if not coerente:
                print("⛔ Não entrou: nenhum dos 3 principais indicadores (RSI, MACD, Stoch) presente — exigido mínimo 1")

            if 5 <= len(sinais) <= 12 and candle_confirma and coerente:
                preco_atual = float(candles_raw[-1][4])
                usdt_alvo = 3
                alavancagem = 2
                qty = ajustar_quantidade(par, usdt_alvo, alavancagem, preco_atual)
                if qty is None:
                    print("Quantidade inválida, ignorando entrada.")
                    time.sleep(1)
                    continue
                res = session.place_order(
                    category="linear",
                    symbol=par,
                    side="Buy",
                    orderType="Market",
                    qty=qty,
                    leverage=alavancagem
                )
                historico_resultados.append(
                    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {par} | sinais={len(sinais)} | coerente={coerente} | tendência={tendencia}"
                )
                print(f"🚀 ENTRADA REAL: {par} | Qty: {qty} | Preço: {preco_atual} | Sinais: {len(sinais)} | Tendência: {tendencia}")
                time.sleep(5)
            time.sleep(1)
        except Exception as e:
            print(f"Erro: {str(e)}")
            time.sleep(2)

