import time
import requests
import pandas as pd
from ta.trend import EMAIndicator
from datetime import datetime, timezone

API_KEY = "A_TUA_API_KEY_TESTNET"
API_SECRET = "A_TUA_API_SECRET_TESTNET"
TELEGRAM_TOKEN = "7830564079:AAER2NNtWfoF0Nsv94Z_WXdPAXQbdsKdcmk"
CHAT_ID = "1407960941"

SYMBOL = "ADAUSDT"
QTD_USDT = 5
LEVERAGE = 10

BASE_URL = "https://api-testnet.bybit.com"  # <- Testnet ✅

def enviar_mensagem(texto):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": texto, "parse_mode": "Markdown"})

def obter_candles():
    url = f"{BASE_URL}/v5/market/kline"
    params = {
        "category": "linear",
        "symbol": SYMBOL,
        "interval": "1",
        "limit": 200
    }
    r = requests.get(url, params=params)
    df = pd.DataFrame(r.json()["result"]["list"])
    df.columns = ["timestamp", "open", "high", "low", "close", "volume", "turnover"]
    df = df.iloc[::-1]
    df["close"] = df["close"].astype(float)
    df["open"] = df["open"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    return df

def analisar(df):
    df["ema10"] = EMAIndicator(df["close"], window=10).ema_indicator()
    df["ema20"] = EMAIndicator(df["close"], window=20).ema_indicator()
    
    ultima = df.iloc[-1]
    anterior = df.iloc[-2]
    
    sinais_fortes = 0
    extras = 0
    sinais = []

    if ultima["ema10"] > ultima["ema20"]:
        sinais_fortes += 1
        sinais.append("📌 EMA10 vs EMA20: True")
    else:
        sinais.append("📌 EMA10 vs EMA20: False")
    
    corpo = abs(ultima["close"] - ultima["open"])
    range_total = ultima["high"] - ultima["low"]
    if range_total > 0 and corpo / range_total > 0.5:
        sinais_fortes += 1
        sinais.append("📌 Corpo grande: True")
    else:
        sinais.append("📌 Corpo grande: False")
    
    if abs(ultima["close"] - anterior["close"]) > 0.001:
        sinais_fortes += 1
        sinais.append("📌 Não lateral: True")
    else:
        sinais.append("📌 Não lateral: False")

    # Extras
    if anterior["close"] > anterior["open"]:
        extras += 1
        sinais.append("📌 Extra: Vela anterior de alta: True")
    else:
        sinais.append("📌 Extra: Vela anterior de alta: False")
    
    pavio_sup = ultima["high"] - max(ultima["close"], ultima["open"])
    if pavio_sup < 0.001:
        extras += 1
        sinais.append("📌 Extra: Pequeno pavio superior: True")
    else:
        sinais.append("📌 Extra: Pequeno pavio superior: False")
    
    total = sinais_fortes + extras
    sinais.append(f"✔️ Total: {sinais_fortes} fortes + {extras} extras = {total}/9")

    entrada_confirmada = False
    if sinais_fortes >= 5 or (sinais_fortes == 4 and extras >= 1):
        entrada_confirmada = True
        sinais.append(f"🔔 {datetime.now(timezone.utc)} | Entrada validada com 4 fortes + 1 ou mais extras!")
    
    return entrada_confirmada, sinais

def enviar_ordem():
    try:
        # Leverage
        r = requests.post(f"{BASE_URL}/v5/position/set-leverage", json={
            "category": "linear",
            "symbol": SYMBOL,
            "buyLeverage": LEVERAGE,
            "sellLeverage": LEVERAGE
        }, headers={"X-BAPI-API-KEY": API_KEY})
        
        # Preço
        r_price = requests.get(f"{BASE_URL}/v5/market/tickers", params={
            "category": "linear",
            "symbol": SYMBOL
        })
        price = float(r_price.json()["result"]["list"][0]["lastPrice"])
        qty = round(QTD_USDT * LEVERAGE / price, 3)

        # Ordem
        ordem = {
            "category": "linear",
            "symbol": SYMBOL,
            "side": "Buy",
            "orderType": "Market",
            "qty": str(qty),
            "timeInForce": "IOC"
        }

        r_ordem = requests.post(f"{BASE_URL}/v5/order/create", json=ordem, headers={"X-BAPI-API-KEY": API_KEY})
        return r_ordem.json()
    except Exception as e:
        return {"error": str(e)}

def loop():
    while True:
        try:
            df = obter_candles()
            entrada, sinais = analisar(df)
            msg = f"📊 Diagnóstico de sinais em {datetime.now(timezone.utc)}\n\n" + "\n".join(sinais)
            enviar_mensagem(msg)
            if entrada:
                enviar_mensagem("✅ Entrada confirmada! Buy")
                resultado = enviar_ordem()
                enviar_mensagem(f"📦 Resultado ordem: {resultado}")
        except Exception as e:
            enviar_mensagem(f"❌ Erro no bot: {str(e)}")
        time.sleep(60)

if __name__ == "__main__":
    loop()


