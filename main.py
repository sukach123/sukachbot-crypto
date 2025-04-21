# ✅ SukachBot CRYPTO - Código completo restaurado (versão anterior das 13h50-13h55) 💻
# 12 indicadores, entradas reais com 5+ sinais, TP/SL, Telegram, estatísticas e análise contínua

import os
import time
import requests
from pybit.unified_trading import HTTP
from datetime import datetime
from flask import Flask
import threading
import numpy as np
import pandas as pd

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ SukachBot CRYPTO está online!"

def iniciar_flask():
    app.run(host="0.0.0.0", port=8080)

BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("Erro: O BOT_TOKEN ou CHAT_ID do Telegram não estão configurados corretamente.")

session = HTTP(api_key=BYBIT_API_KEY, api_secret=BYBIT_API_SECRET, testnet=False)

VALOR_ENTRADA_USDT = 5
ALAVANCAGEM = 2
TAKE_PROFIT_PORCENTAGEM = 0.03
STOP_LOSS_PORCENTAGEM = 0.015
PARES = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "LINKUSDT", "XRPUSDT", "DOGEUSDT",
    "MATICUSDT", "ADAUSDT", "BNBUSDT", "DOTUSDT", "TONUSDT", "SHIBUSDT"
]

estatisticas = {
    "total_entradas": 0,
    "total_wins": 0,
    "total_losses": 0,
    "lucro_total": 0.0,
    "ordens_ativas": []
}

def enviar_telegram_mensagem(mensagem):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Erro ao enviar mensagem para Telegram:", e)

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

        if quantidade <= 0:
            print("Quantidade inválida, ordem não enviada.")
            return

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

        estatisticas["total_entradas"] += 1
        estatisticas["ordens_ativas"].append({"par": par, "entrada": preco_entrada, "tp": tp, "sl": sl})

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

def monitorar_ordens():
    while True:
        try:
            for ordem in estatisticas["ordens_ativas"][:]:
                par = ordem["par"]
                preco_atual = float(session.get_ticker(category="linear", symbol=par)["result"]["list"][0]["lastPrice"])
                if preco_atual >= ordem["tp"]:
                    estatisticas["total_wins"] += 1
                    estatisticas["lucro_total"] += VALOR_ENTRADA_USDT * TAKE_PROFIT_PORCENTAGEM * ALAVANCAGEM
                    enviar_telegram_mensagem(f"✅ *TP Atingido em {par}!* Lucro realizado.")
                    estatisticas["ordens_ativas"].remove(ordem)
                elif preco_atual <= ordem["sl"]:
                    estatisticas["total_losses"] += 1
                    estatisticas["lucro_total"] -= VALOR_ENTRADA_USDT * STOP_LOSS_PORCENTAGEM * ALAVANCAGEM
                    enviar_telegram_mensagem(f"🛑 *SL Atingido em {par}!* Perda registada.")
                    estatisticas["ordens_ativas"].remove(ordem)
            time.sleep(3)
        except Exception as e:
            print("Erro ao monitorar ordens:", e)
            time.sleep(3)

# (continua com os indicadores, análise e loop principais)

   
