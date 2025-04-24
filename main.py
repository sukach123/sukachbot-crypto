# main.py - SukachBot CRYPTO PRO atualizado

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
    # RSI acima de 70 será tratado como possível reversão — não adiciona sinal positivo
    pass
    df["RSI"] = rsi
    exp1 = df["close"].ewm(span=12).mean()
    exp2 = df["close"].ewm(span=26).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9).mean()
    if macd.iloc[-1] > signal.iloc[-1]:
        sinais.append("MACD")
    df["CCI"] = (df["close"] - df["close"].rolling(20).mean()) / (0.015 * df["close"].rolling(20).std())
    cci_valor = df["CCI"].iloc[-1]
    print(f"📉 CCI atual: {cci_valor:.2f}")
    if cci_valor > 100:
        sinais.append("CCI")
    elif cci_valor < -100:
        sinais.append("CCI_SELL")
    df["ADX"] = df["close"].rolling(14).std()
    if df["ADX"].iloc[-1] > df["ADX"].mean():
        sinais.append("ADX")
    if "CCI" in sinais and "RSI" in sinais:
        sinais.append("CCI+RSI BUY")
    if "CCI_SELL" in sinais and "RSI" in sinais:
        sinais.append("CCI+RSI SELL")
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

# === função corrigida para TP/SL ===
def aplicar_tp_sl(par, preco_entrada, direcao):
    if direcao == "Alta":
        take_profit = round(preco_entrada * 1.015, 4)
        stop_loss = round(preco_entrada * 0.997, 4)
    else:
        take_profit = round(preco_entrada * 0.985, 4)
        stop_loss = round(preco_entrada * 1.003, 4)
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

# === ajustar_quantidade ===
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
            print(f"❌ Quantidade {qty_final} abaixo do mínimo permitido {min_qty} para {par}")
            return None
        return qty_final
    except Exception as e:
        print(f"Erro ao ajustar quantidade: {e}")
        return None

# === monitorar_mercado ===
def monitorar_mercado():
    while True:
        try:
            pares = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "MATICUSDT", "AVAXUSDT", "LINKUSDT", "TONUSDT"]
            par = random.choice(pares)
            candles = session.get_kline(category="linear", symbol=par, interval="1", limit=50)["result"]["list"]
            if len(candles) < 30:
                print(f"⚠️ Poucos candles para {par}, a saltar...")
                time.sleep(2)
                continue
            preco_atual = float(candles[-1][4])
            df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"])
            df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].astype(float)
            sinais = analisar_indicadores(df)
            print(f"📊 Indicadores detectados para {par}: {sinais}")
            if len(sinais) < 11 or len(sinais) > 12:
                print("⛔ Número de sinais fora do intervalo 4-12. Ignorado.")
                continue
            essenciais = ["RSI", "EMA", "MACD", "CCI", "ADX"]
            if not any(s in sinais for s in essenciais):
                print("⛔ Nenhum indicador essencial presente. Ignorado.")
                continue
            direcao = detectar_direcao_candle(candles[-2], candles[-1])
            print(f"🕯️ Direção do candle atual: {direcao}")
            if direcao == "Neutro":
                print("⚠️ Vela neutra detectada. Ignorado.")
                continue
            wallet = session.get_wallet_balance(accountType="UNIFIED")
            coins = wallet.get("result", {}).get("list", [])[0].get("coin", [])
            saldo_total = 0
            for c in coins:
                if c.get("coin") == "USDT":
                    saldo_total = float(c.get("equity", "0"))
                    break
            print(f"💰 Saldo USDT aprovado: {saldo_total}")
            if saldo_total < 3:
                print("❌ Saldo insuficiente — não vai entrar.")
                continue
            qty = ajustar_quantidade(par, 3, 2, preco_atual)
            if qty is None:
                continue
            session.place_order(
                category="linear",
                symbol=par,
                side="Buy" if direcao == "Alta" else "Sell",
                orderType="Market",
                qty=qty,
                leverage=2
            )
            historico_resultados.append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {par} | Entrada {direcao} | Qty={qty}")
            print(f"🚀 ENTRADA REAL: {par} | Qty: {qty} | Preço: {preco_atual} | Direção: {direcao}")
            aplicar_tp_sl(par, preco_atual, direcao)
        except Exception as e:
            print(f"Erro no monitoramento: {e}")
        time.sleep(2)

# === manter ativo ===
def manter_ativo():
    def pingar():
        while True:
            try:
                requests.get("https://sukachbot-crypto-production.up.railway.app/")
                print("🔄 Ping enviado para manter online")
            except:
                pass
            time.sleep(300)
    threading.Thread(target=pingar, daemon=True).start()

if __name__ == "__main__":
    manter_ativo()
    threading.Thread(target=monitorar_mercado, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


