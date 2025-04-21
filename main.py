import os
import time
import requests
from pybit.unified_trading import HTTP
from datetime import datetime
from flask import Flask
import threading
import numpy as np
import pandas as pd

# --- FLASK SETUP ---
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ SukachBot CRYPTO está online!"

def iniciar_flask():
    app.run(host="0.0.0.0", port=8080)

# --- CONFIGURAÇÕES GERAIS ---
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Verificar se variáveis estão configuradas
if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("Erro: O BOT_TOKEN ou CHAT_ID do Telegram não estão configurados corretamente.")

session = HTTP(api_key=BYBIT_API_KEY, api_secret=BYBIT_API_SECRET, testnet=False)

# --- CONFIGURAÇÕES DO BOT ---
VALOR_ENTRADA_USDT = 5
ALAVANCAGEM = 2
TAKE_PROFIT_PORCENTAGEM = 0.03
STOP_LOSS_PORCENTAGEM = 0.015

# --- VARIÁVEIS DE REGISTO DE RESULTADOS ---
estatisticas = {
    "total_entradas": 0,
    "total_wins": 0,
    "total_losses": 0,
    "lucro_total": 0.0,
    "ordens_ativas": []
}

# --- FUNÇÃO DE TELEGRAM ---
def enviar_telegram_mensagem(mensagem):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Erro ao enviar mensagem para Telegram:", e)

# --- PARES FIXOS PARA ANÁLISE ---
PARES = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "BNBUSDT", 
    "XRPUSDT", "DOGEUSDT", "MATICUSDT", "ADAUSDT", "DOTUSDT"
]

# --- CÁLCULOS DOS INDICADORES (RSI, MACD, etc.) ---

# Calcular RSI
def calcular_rsi(df, period=14):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Calcular MACD
def calcular_macd(df, fastperiod=12, slowperiod=26, signalperiod=9):
    df['ema_fast'] = df['close'].ewm(span=fastperiod, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=slowperiod, adjust=False).mean()
    df['macd'] = df['ema_fast'] - df['ema_slow']
    df['signal'] = df['macd'].ewm(span=signalperiod, adjust=False).mean()
    return df['macd'], df['signal']

# Calcular Média Móvel Simples (SMA)
def calcular_sma(df, period=20):
    df['sma'] = df['close'].rolling(window=period).mean()
    return df['sma']

# Função de cálculo de indicadores
def calcular_indicadores(df):
    df['RSI'] = calcular_rsi(df)
    df['macd'], df['signal'] = calcular_macd(df)
    df['sma_20'] = calcular_sma(df)
    
    sinais = []
    if df['RSI'].iloc[-1] < 30:
        sinais.append('RSI Buy')
    elif df['RSI'].iloc[-1] > 70:
        sinais.append('RSI Sell')

    if df['macd'].iloc[-1] > df['signal'].iloc[-1]:
        sinais.append('MACD Buy')
    else:
        sinais.append('MACD Sell')

    if df['close'].iloc[-1] > df['sma_20'].iloc_

