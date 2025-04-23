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

PARES_PRIORITARIOS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT"]
PARES_ADICIONAIS = ["MATICUSDT", "AVAXUSDT", "LINKUSDT", "TONUSDT", "FETUSDT", "ADAUSDT", "RNDRUSDT", "SHIB1000USDT"]

@app.route("/")
def home():
    return "SukachBot CRYPTO PRO ATUALIZADO: Estratégia dinâmica ativa com entrada estendida!"

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
            par = random.choices(PARES_PRIORITARIOS + PARES_ADICIONAIS, weights=[5]*len(PARES_PRIORITARIOS) + [1]*len(PARES_ADICIONAIS))[0]
            print(f"Analisando {par}...")
            candles_raw = session.get_kline(category="linear", symbol=par, interval="1", limit=50)["result"]["list"]
            if not candles_raw or len(candles_raw) < 20:
                print(f"Poucos dados em {par}, a ignorar...")
                time.sleep(1)
                continue

            sinais, tendencia, candle_confirma, coerente = calcular_indicadores(candles_raw)

            print(f"Indicadores: {len(sinais)} ➝ {sinais} | Tendência: {tendencia} | Candle confirma: {candle_confirma} | Coerente: {coerente}")

            if not (3 <= len(sinais) <= 12):
                print("⛔ Não entrou: número de sinais fora do intervalo (3-12)")
            if tendencia not in ["alta", "baixa"]:
                print("⛔ Não entrou: tendência é lateral")
            if not candle_confirma:
                print("⛔ Não entrou: candle não confirma a tendência")

            pode_entrar = False
            usdt_alvo = 2

            if len(sinais) >= 9:
                pode_entrar = True
                usdt_alvo = 4
            elif 6 <= len(sinais) <= 8 and coerente:
                pode_entrar = True
            elif len(sinais) == 5 and all(ind in sinais for ind in ["RSI", "MACD", "Stoch"]):
                pode_entrar = True
            elif len(sinais) == 4 and sum(ind in sinais for ind in ["RSI", "MACD", "Stoch"]) >= 2:
                pode_entrar = True
            elif len(sinais) == 3 and tendencia in ["alta", "baixa"] and candle_confirma and "OBV" in sinais:
                pode_entrar = True

            if pode_entrar and tendencia in ["alta", "baixa"] and candle_confirma:
                preco_atual = float(candles_raw[-1][4])
                alavancagem = 2
                qty = ajustar_quantidade(par, usdt_alvo, alavancagem, preco_atual)
                if qty is None:
                    print("Quantidade inválida, ignorando entrada.")
                    time.sleep(1)
                    continue
                session.place_order(
                    category="linear",
                    symbol=par,
                    side="Buy",
                    orderType="Market",
                    qty=qty,
                    leverage=alavancagem
                )
                historico_resultados.append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {par} | sinais={len(sinais)} | coerente={coerente} | tendência={tendencia}")
                print(f"🚀 ENTRADA EXECUTADA: {par} | Qty: {qty} | Valor: ${usdt_alvo} | Sinais: {len(sinais)} | Tendência: {tendencia}")
                aplicar_tp_sl(par, preco_atual)
                time.sleep(5)
            time.sleep(1)
        except Exception as e:
            print(f"Erro: {str(e)}")
            time.sleep(2)

# As outras funções continuam (calcular_indicadores, aplicar_tp_sl, etc.)
