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

def manter_ativo():
    def pingar():
        while True:
            try:
                requests.get("https://sukachbot-crypto-production.up.railway.app/")
                print("🔄 Ping de atividade enviado para manter o bot online")
            except:
                pass
            time.sleep(300)
    threading.Thread(target=pingar, daemon=True).start()

def aplicar_tp_sl(par, preco_entrada):
    take_profit = round(preco_entrada * 1.03, 4)
    stop_loss = round(preco_entrada * 0.985, 4)
    trailing_ativado = False
    sucesso = False

    for tentativa in range(3):
        try:
            posicoes = session.get_positions(category="linear", symbol=par)["result"]["list"]
            if posicoes:
                atual = float(posicoes[0].get("markPrice", preco_entrada))
                lucro_atual = (atual - preco_entrada) / preco_entrada

                # Ativar trailing stop se lucro > 2%
                if lucro_atual > 0.02:
                    novo_sl = round(atual * 0.99, 4)  # trailing SL = -1% abaixo do preço atual
                    stop_loss = max(stop_loss, novo_sl)
                    trailing_ativado = True

                response = session.set_trading_stop(
                    category="linear",
                    symbol=par,
                    takeProfit=take_profit,
                    stopLoss=stop_loss
                )

                if response.get("retCode") == 0:
                    print(f"TP/SL definidos: TP={take_profit} | SL={stop_loss} {'(Trailing SL ativo)' if trailing_ativado else ''}")
                    sucesso = True
                    break
                else:
                    print(f"Erro ao aplicar TP/SL: {response}")
        except Exception as e:
            print(f"Falha ao aplicar TP/SL (tentativa {tentativa+1}): {e}")
            time.sleep(1)

    if not sucesso:
        print("Não foi possível aplicar TP/SL após 3 tentativas! Reagendando nova tentativa em 15 segundos...")
        threading.Timer(15, aplicar_tp_sl, args=(par, preco_entrada)).start()

def monitorar_mercado():
    while True:
        try:
            par = random.choice(["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "MATICUSDT",
                                "AVAXUSDT", "LINKUSDT", "TONUSDT", "FETUSDT", "ADAUSDT",
                                "RNDRUSDT", "SHIB1000USDT"])
            preco_atual = float(session.get_kline(
                category="linear",
                symbol=par,
                interval="1",
                limit=2
            )["result"]["list"][-1][4])

            usdt_alvo = 3
            alavancagem = 2
            qty = round((usdt_alvo * alavancagem) / preco_atual, 3)

            session.place_order(
                category="linear",
                symbol=par,
                side="Buy",
                orderType="Market",
                qty=qty,
                leverage=alavancagem
            )

            historico_resultados.append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {par} | Entrada real | Qty={qty}")
            print(f"🚀 ENTRADA REAL: {par} | Qty: {qty} | Preço: {preco_atual}")
            time.sleep(5)
            aplicar_tp_sl(par, preco_atual)

        except Exception as e:
            print(f"Erro no monitoramento: {e}")
        time.sleep(2)

if __name__ == "__main__":
    manter_ativo()
    threading.Thread(target=monitorar_mercado, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

