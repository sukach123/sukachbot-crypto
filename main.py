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

def calcular_indicadores(candles):
    df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"])
    df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].astype(float)
    sinais = []
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -1 * delta.clip(upper=0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    if rsi.iloc[-1] < 30:
        sinais.append("RSI")
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    if macd.iloc[-1] > signal.iloc[-1]:
        sinais.append("MACD")
    lowest_low = df["low"].rolling(window=14).min()
    highest_high = df["high"].rolling(window=14).max()
    stoch_k = 100 * ((df["close"] - lowest_low) / (highest_high - lowest_low))
    if stoch_k.iloc[-1] < 20:
        sinais.append("Stoch")
    ema9 = df["close"].ewm(span=9).mean()
    ema21 = df["close"].ewm(span=21).mean()
    if ema9.iloc[-1] > ema21.iloc[-1]:
        sinais.append("EMA")
    df["tr"] = df[["high", "low", "close"]].max(axis=1) - df[["high", "low", "close"]].min(axis=1)
    df["plus_dm"] = df["high"].diff()
    df["minus_dm"] = df["low"].diff()
    tr14 = df["tr"].rolling(14).mean()
    plus_di = 100 * (df["plus_dm"].rolling(14).mean() / tr14)
    minus_di = 100 * (df["minus_dm"].rolling(14).mean() / tr14)
    adx = ((plus_di - minus_di).abs() / (plus_di + minus_di)).rolling(14).mean() * 100
    if adx.iloc[-1] > 25:
        sinais.append("ADX")
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    cci = (typical_price - typical_price.rolling(20).mean()) / (0.015 * typical_price.rolling(20).std())
    if cci.iloc[-1] < -100:
        sinais.append("CCI")
    sma = df["close"].rolling(window=20).mean()
    std = df["close"].rolling(window=20).std()
    lower = sma - 2 * std
    if df["close"].iloc[-1] < lower.iloc[-1]:
        sinais.append("Bollinger")
    momentum = df["close"].diff(periods=10)
    if momentum.iloc[-1] > 0:
        sinais.append("Momentum")
    if df["close"].iloc[-1] > df["open"].iloc[-1]:
        sinais.append("PSAR")
    obv = (np.sign(df["close"].diff()) * df["volume"]).fillna(0).cumsum()
    if obv.iloc[-1] > obv.iloc[-2]:
        sinais.append("OBV")

    highs = df['high']
    lows = df['low']
    hh = highs.iloc[-1] > highs.iloc[-2] and highs.iloc[-2] > highs.iloc[-3]
    hl = lows.iloc[-1] > lows.iloc[-2] and lows.iloc[-2] > lows.iloc[-3]
    ll = lows.iloc[-1] < lows.iloc[-2] and lows.iloc[-2] < lows.iloc[-3]
    lh = highs.iloc[-1] < highs.iloc[-2] and highs.iloc[-2] < highs.iloc[-3]

    if hh and hl:
        tendencia = "alta"
    elif ll and lh:
        tendencia = "baixa"
    else:
        tendencia = "lateral"

    candle_confirma = (
        (tendencia == "alta" and df["close"].iloc[-1] > df["open"].iloc[-1]) or
        (tendencia == "baixa" and df["close"].iloc[-1] < df["open"].iloc[-1])
    )

    coerente = sum(indicador in sinais for indicador in ["RSI", "MACD", "Stoch"]) >= 1

    return sinais, tendencia, candle_confirma, coerente

def monitorar_mercado():
    while True:
        try:
            par = random.choice(["BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "MATICUSDT",
                                "AVAXUSDT", "LINKUSDT", "TONUSDT", "FETUSDT", "ADAUSDT",
                                "RNDRUSDT", "SHIB1000USDT"])
            print(f"Analisando {par}...")
            candles_raw = session.get_kline(
                category="linear",
                symbol=par,
                interval="1",
                limit=50
            )["result"]["list"]
            if not candles_raw or len(candles_raw) < 20:
                print(f"Poucos dados em {par}, a ignorar...")
                time.sleep(1)
                continue

            sinais, tendencia, candle_confirma, coerente = calcular_indicadores(candles_raw)

            print(f"Indicadores: {len(sinais)} ➝ {sinais} | Tendência: {tendencia} | Candle confirma: {candle_confirma} | Coerente: {coerente}")

            if not (4 <= len(sinais) <= 12):
                print("⛔ Não entrou: número de sinais fora do intervalo (4-12)")
            if tendencia not in ["alta", "baixa"]:
                print("⛔ Não entrou: tendência é lateral")
            if len(sinais) != 5 and not candle_confirma:
                print("⛔ Não entrou: candle não confirma a tendência")
            if not coerente:
                print("⛔ Não entrou: nenhum dos 3 principais indicadores (RSI, MACD, Stoch) presente — exigido mínimo 1")

            if 4 <= len(sinais) <= 12 and tendencia in ["alta", "baixa"] and (candle_confirma or len(sinais) == 5) and coerente:
                preco_atual = float(candles_raw[-1][4])
                usdt_alvo = 3
                alavancagem = 2
                qty = ajustar_quantidade(par, usdt_alvo, alavancagem, preco_atual)
                if qty is None:
                    print("Quantidade inválida, ignorando entrada.")
                    time.sleep(1)
                    continue
                res = session.place_order(
                    category="linear",
                    symbol=par,
                    side="Buy",
                    orderType="Market",
                    qty=qty,
                    leverage=alavancagem
                )
                historico_resultados.append(
                    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {par} | sinais={len(sinais)} | coerente={coerente} | tendência={tendencia}"
                )
                print(f"🚀 ENTRADA REAL: {par} | Qty: {qty} | Preço: {preco_atual} | Sinais: {len(sinais)} | Tendência: {tendencia}")
                time.sleep(5)
                aplicar_tp_sl(par, preco_atual)
            time.sleep(1)
        except Exception as e:
            print(f"Erro: {str(e)}")
            time.sleep(2)

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

def aplicar_tp_sl(par, preco_atual):
    take_profit = round(preco_atual * 1.03, 4)
    stop_loss = round(preco_atual * 0.985, 4)
    sucesso = False
    for tentativa in range(3):
        try:
            posicoes = session.get_positions(category="linear", symbol=par)["result"]["list"]
            if posicoes and posicoes[0].get("takeProfit") == str(take_profit) and posicoes[0].get("stopLoss") == str(stop_loss):
                print("TP/SL já definidos corretamente, sem alterações.")
                sucesso = True
                break
            session.set_trading_stop(
                category="linear",
                symbol=par,
                takeProfit=take_profit,
                stopLoss=stop_loss
            )
            print(f"TP/SL definidos: TP={take_profit} | SL={stop_loss}")
            sucesso = True
            break
        except Exception as e:
            print(f"Falha ao aplicar TP/SL (tentativa {tentativa+1}): {e}")
            time.sleep(1)
    if not sucesso:
        print("Não foi possível aplicar TP/SL após 3 tentativas!")

if __name__ == "__main__":
    manter_ativo()
    threading.Thread(target=monitorar_mercado).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


