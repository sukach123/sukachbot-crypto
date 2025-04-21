# ✅ SukachBot CRYPTO - Código com 12 indicadores + análise PRO + execução automática + registo de resultados 💻
# Entradas reais com 5 ou mais indicadores, TP/SL incluídos, Flask, Telegram e estatísticas ativas

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
PARES = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "LINKUSDT", "XRPUSDT", "DOGEUSDT",
    "MATICUSDT", "ADAUSDT", "BNBUSDT", "DOTUSDT", "TONUSDT", "SHIBUSDT"
]

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

# --- RESTANTE DO CÓDIGO PERMANECE IGUAL (já inclui lógica com qty correta e 12 indicadores) ---






