# ✅ SukachBot CRYPTO - Código atualizado com correções avançadas
# Corrigido: STOP LOSS funcional, entradas de 1 USDT com alavancagem 2x, alerta Telegram com emojis e tratamento de exceções

import os
import time
import requests
from pybit.unified_trading import HTTP
from datetime import datetime

# --- CONFIGURAÇÕES GERAIS ---
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("Erro: O BOT_TOKEN ou CHAT_ID do Telegram não estão configurados corretamente.")

session = HTTP(
    api_key=BYBIT_API_KEY,
    api_secret=BYBIT_API_SECRET,
    testnet=False
)

# --- CONFIGURAÇÕES DO BOT ---
VALOR_ENTRADA_USDT = 1
ALAVANCAGEM = 2
TAKE_PROFIT_PORCENTAGEM = 0.03  # 3%
STOP_LOSS_PORCENTAGEM = 0.015   # 1.5%

# --- FUNÇÃO TELEGRAM ---
def enviar_telegram_mensagem(mensagem):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Erro ao enviar mensagem para Telegram:", e)

# --- EXECUTAR ORDEM ---
def executar_ordem(par, preco_entrada, direcao, preco_atual):
    try:
        if direcao.lower() == "buy":
            tp = preco_entrada * (1 + TAKE_PROFIT_PORCENTAGEM)
            sl = preco_entrada * (1 - STOP_LOSS_PORCENTAGEM)
        else:
            tp = preco_entrada * (1 - TAKE_PROFIT_PORCENTAGEM)
            sl = preco_entrada * (1 + STOP_LOSS_PORCENTAGEM)

        if not preco_entrada:
            preco_entrada = preco_atual

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
            f"🚀 *ENTRADA EXECUTADA!*
"
            f"📊 *Par:* `{par}`
"
            f"📈 *Direção:* `{direcao.upper()}`
"
            f"💵 *Preço:* `{preco_entrada:.4f}`
"
            f"🎯 *TP:* `{tp:.4f}` | 🛡️ *SL:* `{sl:.4f}`
"
            f"💰 *Qtd:* `{quantidade}` | ⚖️ *Alavancagem:* `{ALAVANCAGEM}x`
"
            f"⏱️ *Hora:* `{hora}`"
        )

        enviar_telegram_mensagem(mensagem)

    except Exception as e:
        print("Erro ao executar ordem:", e)
        enviar_telegram_mensagem(f"❌ Erro ao executar ordem em {par}: {str(e)}")



