# ✅ SukachBot CRYPTO - v2025-04-20_1010_estável 💻
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

# --- CONFIGURAÇÕES ---
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

def calcular_rsi(closes, period=14):
    deltas = np.diff(closes)
    seed = deltas[:period]
    up = seed[seed > 0].sum() / period
    down = -seed[seed < 0].sum() / period
    rs = up / down if down != 0 else 0
    rsi = np.zeros_like(closes)
    rsi[:period] = 100. - 100. / (1. + rs)
    for i in range(period, len(closes)):
        delta = deltas[i - 1]
        upval = max(delta, 0)
        downval = -min(delta, 0)
        up = (up * (period - 1) + upval) / period
        down = (down * (period - 1) + downval) / period
        rs = up / down if down != 0 else 0
        rsi[i] = 100. - 100. / (1. + rs)
    return rsi[-1]

def calcular_ema(closes, period):
    return np.array(pd.Series(closes).ewm(span=period, adjust=False).mean())

def calcular_sma(closes, period):
    return np.convolve(closes, np.ones(period)/period, mode='valid')

def calcular_macd(closes):
    ema12 = calcular_ema(closes, 12)
    ema26 = calcular_ema(closes, 26)
    macd_line = ema12 - ema26
    signal_line = np.array(pd.Series(macd_line).ewm(span=9, adjust=False).mean())
    return macd_line, signal_line

def loop_analise():
    while True:
        try:
            hora = datetime.utcnow().strftime("%H:%M:%S")
            print(f"⏱️ {hora} - Análise em andamento...")

            for par in PARES:
                dados = session.get_kline(category="linear", symbol=par, interval=1, limit=100)["result"]["list"]
                closes = [float(c[4]) for c in dados]

                if len(closes) < 50:
                    continue

                sinais = 0

                rsi = calcular_rsi(closes)
                sinais += 1 if rsi > 50 else 0

                ema_fast = calcular_ema(closes, 5)
                ema_slow = calcular_ema(closes, 20)
                sinais += 1 if ema_fast[-1] > ema_slow[-1] else 0

                macd_line, signal_line = calcular_macd(closes)
                sinais += 1 if macd_line[-1] > signal_line[-1] else 0

                sma_20 = calcular_sma(closes, 20)
                sma_50 = calcular_sma(closes, 50)
                sinais += 1 if sma_20[-1] > sma_50[-1] else 0

                ult = closes[-1]
                max_recent = max(closes[-5:])
                min_recent = min(closes[-5:])
                sinais += 1 if ult > max_recent * 0.98 else 0
                sinais += 1 if ult < min_recent * 1.02 else 0

                var = np.var(closes[-10:])
                sinais += 1 if var > 1 else 0

                momentum = closes[-1] - closes[-5]
                sinais += 1 if momentum > 0 else 0

                candles_altas = sum([1 for i in range(-5, -1) if closes[i] < closes[i + 1]])
                sinais += 1 if candles_altas >= 3 else 0

                velas_fortes = sum([1 for i in range(-5, -1) if abs(closes[i] - closes[i+1]) > 0.5])
                sinais += 1 if velas_fortes >= 2 else 0

                if sinais >= 5:
                    preco_atual = closes[-1]
                    direcao = "buy" if ema_fast[-1] > ema_slow[-1] else "sell"
                    executar_ordem(par, preco_atual, direcao, preco_atual)

            time.sleep(10)

        except Exception as e:
            print("Erro na análise:", e)
            time.sleep(10)

if __name__ == "__main__":
    threading.Thread(target=iniciar_flask).start()
    threading.Thread(target=loop_analise).start()
    threading.Thread(target=monitorar_ordens).start()
    print("✅ SukachBot CRYPTO totalmente iniciado com 12 indicadores!")
    while True:
        print(f"💓 Heartbeat: {datetime.utcnow().strftime('%H:%M:%S')} - Bot vivo")
        print(f"📊 Estatísticas: Entradas: {estatisticas['total_entradas']}, WINs: {estatisticas['total_wins']}, LOSSes: {estatisticas['total_losses']}, Lucro: {estatisticas['lucro_total']:.2f} USDT")
        time.sleep(30)


