# main.py atualizado com módulo de indicadores e detecção de candle
from flask import Flask
import os
import time
import random
import threading
import numpy as np
import pandas as pd
from pybit.unified_trading import HTTP
from datetime import datetime
import requests

app = Flask(__name__)

api_key = os.getenv("BYBIT_API_KEY")
api_secret = os.getenv("BYBIT_API_SECRET")

session = HTTP(api_key=api_key, api_secret=api_secret, testnet=False)
historico_resultados = []

# === indicadores integrados ===
def analisar_indicadores(df):
    sinais = []
    df["EMA_10"] = df["close"].ewm(span=10).mean()
    df["EMA_20"] = df["close"].ewm(span=20).mean()
    if df["EMA_10"].iloc[-1] > df["EMA_20"].iloc[-1]:
        sinais.append("EMA")
    delta = df["close"].diff()
    ganho = delta.where(delta > 0, 0)
    perda = -delta.where(delta < 0, 0)
    media_ganho = ganho.rolling(14).mean()
    media_perda = perda.rolling(14).mean()
    rs = media_ganho / media_perda
    rsi = 100 - (100 / (1 + rs))
    if rsi.iloc[-1] < 30:
        sinais.append("RSI")
    exp1 = df["close"].ewm(span=12).mean()
    exp2 = df["close"].ewm(span=26).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9).mean()
    if macd.iloc[-1] > signal.iloc[-1]:
        sinais.append("MACD")
    df["CCI"] = (df["close"] - df["close"].rolling(20).mean()) / (0.015 * df["close"].rolling(20).std())
    if df["CCI"].iloc[-1] > 100:
        sinais.append("CCI")
    df["ADX"] = df["close"].rolling(14).std()
    if df["ADX"].iloc[-1] > df["ADX"].mean():
        sinais.append("ADX")
    return sinais

# === estrutura candle integrada ===
def detectar_direcao_candle(candle_anterior, candle_atual):
    open_price = float(candle_atual[1])
    close_price = float(candle_atual[4])
    if abs(close_price - open_price) < 0.0001:
        return "Neutro"
    elif close_price > open_price:
        return "Alta"
    else:
        return "Baixa"

# função corrigida para SL

def aplicar_tp_sl(par, preco_entrada):
    take_profit = round(preco_entrada * 1.01, 4)
    stop_loss = round(preco_entrada * 0.997, 4)
    trailing_ativado = False
    sucesso = False
    for tentativa in range(3):
        try:
            posicoes = session.get_positions(category="linear", symbol=par)["result"]["list"]
            if posicoes and (
                posicoes[0].get("takeProfit") == str(take_profit) and
                posicoes[0].get("stopLoss") == str(stop_loss)
            ):
                print("TP/SL já definidos corretamente, sem alterações.")
                sucesso = True
                break
            atual = float(posicoes[0].get("markPrice", preco_entrada))
            lucro_atual = (atual - preco_entrada) / preco_entrada
            if lucro_atual > 0.006:
                novo_sl = round(atual * 0.997, 4)
                stop_loss = max(stop_loss, novo_sl)
                trailing_ativado = True
            if stop_loss >= preco_entrada:
                stop_loss = preco_entrada - 0.0001
            response = session.set_trading_stop(
                category="linear",
                symbol=par,
                takeProfit=take_profit,
                stopLoss=stop_loss
            )
            if response.get("retCode") == 0:
                print(f"✅ TP/SL definidos: TP={take_profit} | SL={stop_loss} {'(Trailing SL ativo)' if trailing_ativado else ''}")
                sucesso = True
                break
            else:
                print(f"Erro ao aplicar TP/SL: {response}")
        except Exception as e:
            print(f"Falha ao aplicar TP/SL (tentativa {tentativa+1}): {e}")
            time.sleep(1)
    if not sucesso:
        print("⚠️ Não foi possível aplicar TP/SL após 3 tentativas. Nova tentativa em 15 segundos...")
        threading.Timer(15, aplicar_tp_sl, args=(par, preco_entrada)).start()

# ⚙️ Commit: Correção final aplicada. Indicadores e vela integrados, SL garantido abaixo do preço base
