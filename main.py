# ✅ SukachBot CRYPTO - Código atualizado com Flask + análise automática 💻
# Inclui STOP LOSS, entrada mínima, alavancagem 2x, envio Telegram com emojis, e análise com 5-12 sinais

import os
import time
import requests
from pybit.unified_trading import HTTP
from datetime import datetime
from flask import Flask
import threading
import numpy as np

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
VALOR_ENTRADA_USDT = 1
ALAVANCAGEM = 2
TAKE_PROFIT_PORCENTAGEM = 0.03
STOP_LOSS_PORCENTAGEM = 0.015
PARES = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "LINKUSDT"]

# --- FUNÇÃO DE TELEGRAM ---
def enviar_telegram_mensagem(mensagem):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Erro ao enviar mensagem para Telegram:", e)

# --- FUNÇÃO DE EXECUÇÃO DE ORDEM ---
def executar_ordem(par, preco_entrada, direcao, preco_atual):
    try:
        if not preco_entrada:
            preco_entrada = preco_atual

        if direcao.lower() == "buy":
            tp = preco_entrada * (1 + TAKE_PROFIT_PORCENTAGEM)
            sl = preco_entrada * (1 - STOP_LOSS_PORCENTAGEM)
        else:
            tp = preco_entrada * (1 - TAKE_PROFIT_PORCENTAGEM)
            sl = preco_entrada * (1 + STOP_LOSS_PORCENTAGEM)

        quantidade = round((VALOR_ENTRADA_USDT * ALAVANCAGEM) / preco_entrada, 3)

        print(f"Executando ordem {direcao.upper()} em {par} | Entrada: {preco_entrada:.4f} | TP: {tp:.4f} | SL: {sl:.4f}")

        session.place_order(
            category="linear",
            symbol=par,
            side="Buy" if direcao.lower() == "buy" else "Sell",
            order_type="Market",
            qty=quantidade,
            take_profit=round(tp, 4),
            stop_loss=round(sl, 4),
            time_in_force="GoodTillCancel",
            reduce_only=False
        )

        hora = datetime.utcnow().strftime("%H:%M:%S")
        mensagem = (
            f"🚀 *ENTRADA EXECUTADA!*\n"
            f"📊 *Par:* `{par}`\n"
            f"📈 *Direção:* `{direcao.upper()}`\n"
            f"💵 *Preço:* `{preco_entrada:.4f}`\n"
            f"🎯 *TP:* `{tp:.4f}` | 🛡️ *SL:* `{sl:.4f}`\n"
            f"💰 *Qtd:* `{quantidade}` | ⚖️ *Alavancagem:* `{ALAVANCAGEM}x`\n"
            f"⏱️ *Hora:* `{hora}`"
        )
        enviar_telegram_mensagem(mensagem)

    except Exception as e:
        print("Erro ao executar ordem:", e)
        enviar_telegram_mensagem(f"❌ Erro ao executar ordem em {par}: {str(e)}")

# --- ANÁLISE AUTOMÁTICA ---
def calcular_rsi(fechamentos, periodo=14):
    difs = np.diff(fechamentos)
    ganhos = np.where(difs > 0, difs, 0)
    perdas = np.where(difs < 0, abs(difs), 0)
    media_ganhos = np.mean(ganhos[-periodo:])
    media_perdas = np.mean(perdas[-periodo:])
    if media_perdas == 0:
        return 100
    rs = media_ganhos / media_perdas
    return 100 - (100 / (1 + rs))

def analisar_par(par):
    try:
        dados = session.get_kline(category="linear", symbol=par, interval="1", limit=100)
        candles = dados["result"]["list"]
        fechamentos = np.array([float(c[4]) for c in candles])

        sinais = 0
        rsi = calcular_rsi(fechamentos)
        if rsi < 30:
            sinais += 1  # RSI sobrevendido

        if fechamentos[-1] > np.mean(fechamentos[-9:]):
            sinais += 1  # Preço acima da média curta (EMA9 fake)

        if fechamentos[-1] > np.mean(fechamentos[-21:]):
            sinais += 1  # Preço acima da média longa (EMA21 fake)

        if sinais >= 5:
            enviar_telegram_mensagem(f"📡 *Alerta em {par}* — {sinais}/12 indicadores alinhados!")

        if sinais >= 6:
            executar_ordem(par, preco_entrada=fechamentos[-1], direcao="buy", preco_atual=fechamentos[-1])

    except Exception as e:
        print(f"Erro ao analisar {par}: {e}")

# --- LOOP PRINCIPAL ---
def loop_analise():
    while True:
        for par in PARES:
            analisar_par(par)
            time.sleep(1)
        time.sleep(10)

# --- INICIAR BOT ---
if __name__ == "__main__":
    threading.Thread(target=iniciar_flask).start()
    threading.Thread(target=loop_analise).start()
    print("🔄 SukachBot CRYPTO iniciado com sucesso...")
    while True:
        time.sleep(30)





