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

# === INÍCIO DE indicadores.py ===
def analisar_indicadores(df):
    sinais = []

    # EMA
    df["EMA_10"] = df["close"].ewm(span=10, adjust=False).mean()
    df["EMA_20"] = df["close"].ewm(span=20, adjust=False).mean()
    if df["EMA_10"].iloc[-1] > df["EMA_20"].iloc[-1]:
        sinais.append("EMA")

    # RSI
    delta = df["close"].diff()
    ganho = delta.where(delta > 0, 0)
    perda = -delta.where(delta < 0, 0)
    media_ganho = ganho.rolling(14).mean()
    media_perda = perda.rolling(14).mean()
    rs = media_ganho / media_perda
    rsi = 100 - (100 / (1 + rs))
    if rsi.iloc[-1] < 30:
        sinais.append("RSI")

    # MACD
    exp1 = df["close"].ewm(span=12, adjust=False).mean()
    exp2 = df["close"].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    if macd.iloc[-1] > signal.iloc[-1]:
        sinais.append("MACD")

    # CCI
    df["CCI"] = (df["close"] - df["close"].rolling(20).mean()) / (0.015 * df["close"].rolling(20).std())
    if df["CCI"].iloc[-1] > 100:
        sinais.append("CCI")

    # ADX (simulado com desvio padrão)
    df["ADX"] = df["close"].rolling(14).std()
    if df["ADX"].iloc[-1] > df["ADX"].mean():
        sinais.append("ADX")

    return sinais
# === FIM DE indicadores.py ===

# === INÍCIO DE estrutura_candle.py ===
def detectar_direcao_candle(candle_anterior, candle_atual):
    open_price = float(candle_atual[1])
    close_price = float(candle_atual[4])

    if abs(close_price - open_price) < 0.0001:
        return "Neutro"
    elif close_price > open_price:
        return "Alta"
    else:
        return "Baixa"
# === FIM DE estrutura_candle.py ===

app = Flask(__name__)

api_key = os.getenv("BYBIT_API_KEY")
api_secret = os.getenv("BYBIT_API_SECRET")

session = HTTP(
    api_key=api_key,
    api_secret=api_secret,
    testnet=False
)

historico_resultados = []

@app.route("/")
def home():
    return "SukachBot CRYPTO PRO ativo com análise avançada de estrutura, tendência e coerência de sinais!"

# (continuação do código principal)

@app.route("/saldo")
def saldo():
    try:
        response = session.get_wallet_balance(accountType="UNIFIED")
        print("🔍 DEBUG saldo:", response)
        coins = response["result"]["list"][0]["coin"]
        output = "<h2>Saldo Atual:</h2><ul>"
        for coin in coins:
            nome_moeda = coin.get("moeda") or coin.get("coin", "???")
            valor_saldo = coin.get("availableToWithdraw") or coin.get("walletBalance") or coin.get("equity") or "0"
            try:
                balance = float(valor_saldo.replace(",", "."))
                if balance > 0:
                    output += f"<li>{nome_moeda}: {balance}</li>"
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

def ajustar_quantidade(par, usdt_alvo, alavancagem, preco_atual):
    try:
        info = session.get_instruments_info(category="linear", symbol=par)
        filtro = info["result"]["list"][0]["lotSizeFilter"]
        step = float(filtro["qtyStep"])
        min_qty = float(filtro["minOrderQty"])
        qty_bruta = (usdt_alvo * alavancagem) / preco_atual
        precisao = abs(int(round(-np.log10(step), 0)))
        qty_final = round(qty_bruta, precisao)
        if qty_final < min_qty:
            print(f"Quantidade abaixo do mínimo ({qty_final} < {min_qty})")
            return None
        return qty_final
    except Exception as e:
        print(f"Erro ao ajustar quantidade: {e}")
        return None

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

def monitorar_mercado():
    while True:
        try:
            pares_disponiveis = [
                "BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "MATICUSDT",
                "AVAXUSDT", "LINKUSDT", "TONUSDT", "FETUSDT", "ADAUSDT",
                "RNDRUSDT", "SHIB1000USDT"
            ]

            par = random.choice(pares_disponiveis)

            kline_data = session.get_kline(
                category="linear",
                symbol=par,
                interval="1",
                limit=50
            )["result"]["list"]

            if len(kline_data) < 30:
                print(f"⚠️ Poucos candles para {par}, a saltar...")
                time.sleep(2)
                continue

            preco_atual = float(kline_data[-1][4])

            df = pd.DataFrame(kline_data, columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"])
            df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].astype(float)

            sinais = analisar_indicadores(df)
            print(f"📊 Indicadores detectados para {par}: {sinais}")

            if len(sinais) < 4 or len(sinais) > 12:
                print("⛔ Número de sinais fora do intervalo 4-12. Ignorado.")
                time.sleep(2)
                continue

            essenciais = ["RSI", "MACD", "EMA", "CCI", "ADX"]
            if not any(sinal in sinais for sinal in essenciais):
                print("⛔ Nenhum indicador essencial presente. Ignorado.")
                time.sleep(2)
                continue

            direcao = detectar_direcao_candle(kline_data[-2], kline_data[-1])
            print(f"🕯️ Direção do candle atual: {direcao}")

            if direcao == "Neutro":
                print("⚠️ Vela neutra detectada. Ignorado.")
                time.sleep(2)
                continue

            try:
                wallet = session.get_wallet_balance(accountType="UNIFIED")
                coins = wallet.get("result", {}).get("list", [])[0].get("coin", [])
                saldo_total = 0
                for c in coins:
                    nome_moeda = c.get("moeda") or c.get("coin")
                    if nome_moeda == "USDT":
                        saldo_str = c.get("availableToWithdraw") or c.get("walletBalance") or c.get("equity") or "0"
                        saldo_total = float(saldo_str.replace(",", "."))
                        break
                print(f"💰 Saldo USDT aprovado: {saldo_total}")
            except Exception as e:
                print(f"❌ Erro ao obter saldo disponível em USDT: {e}")
                saldo_total = 0

            usdt_alvo = 3
            alavancagem = 2

            if saldo_total < usdt_alvo:
                print(f"❌ Saldo insuficiente ({saldo_total} < {usdt_alvo}) — não vai entrar.")
                time.sleep(2)
                continue

            qty = ajustar_quantidade(par, usdt_alvo, alavancagem, preco_atual)
            if qty is None:
                time.sleep(2)
                continue

            session.place_order(
                category="linear",
                symbol=par,
                side="Buy" if direcao == "Alta" else "Sell",
                orderType="Market",
                qty=qty,
                leverage=alavancagem
            )

            historico_resultados.append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {par} | Entrada {direcao} | Qty={qty}")
            print(f"🚀 ENTRADA REAL: {par} | Qty: {qty} | Preço: {preco_atual} | Direção: {direcao}")
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

