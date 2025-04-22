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

# ... as funções anteriores continuam aqui ...

# Dentro da função monitorar_mercado(), logo após uma entrada real:
# Adiciona esta linha dentro do bloco que executa a entrada real:
# historico_resultados.append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {par} | sinais={len(sinais)} | coerente={coerente} | tendência={tendencia}")

# Substituir o bloco de entrada real por este:
if 5 <= len(sinais) <= 12 and tendencia in ["alta", "baixa"] and candle_confirma and coerente:
    preco_atual = float(candles_raw[-1][4])
    usdt_alvo = 2
    alavancagem = 2
    qty = ajustar_quantidade(par, usdt_alvo, alavancagem, preco_atual)
    if qty is None:
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
    print(f"ENTRADA REAL: {par} | Qty: {qty} | Preço: {preco_atual} | Sinais: {len(sinais)} | Tendência: {tendencia}")
    time.sleep(5)
    aplicar_tp_sl(par, preco_atual)

# Atualizar coerência para exigir apenas 1 dos principais indicadores
coerente = sum(indicador in sinais for indicador in ["RSI", "MACD", "Stoch"]) >= 1

