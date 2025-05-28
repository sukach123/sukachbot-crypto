import pandas as pd
import numpy as np
from pybit.unified_trading import HTTP
from datetime import datetime, timezone
import time

# Configurações API - Testnet Bybit
API_KEY = "SUA_API_KEY"
API_SECRET = "SEU_API_SECRET"

session = HTTP(
    testnet=True,
    api_key=API_KEY,
    api_secret=API_SECRET
)

symbol = "ETHUSDT"
interval = "1"  # 1 minuto
quantidade_usdt = 5  # Valor fixo para trade em USDT

def fetch_candles(symbol, interval="1", limit=200):
    try:
        response = session.get_kline(
            category="linear",
            symbol=symbol,
            interval=interval,
            limit=limit
        )
        candles = response['result']['list']
        df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"])
        df["open"] = df["open"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["close"] = df["close"].astype(float)
        df["volume"] = df["volume"].astype(float)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        return df
    except Exception as e:
        print(f"Erro ao buscar candles: {e}")
        time.sleep(1)
        return fetch_candles(symbol, interval, limit)

def calcular_indicadores(df):
    df["EMA10"] = df["close"].ewm(span=10, adjust=False).mean()
    df["EMA20"] = df["close"].ewm(span=20, adjust=False).mean()

    df["EMA50"] = df["close"].ewm(span=50, adjust=False).mean()

    df["12ema"] = df["close"].ewm(span=12, adjust=False).mean()
    df["26ema"] = df["close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = df["12ema"] - df["26ema"]
    df["SINAL"] = df["MACD"].ewm(span=9, adjust=False).mean()

    tp = (df["high"] + df["low"] + df["close"]) / 3
    ma_tp = tp.rolling(window=20).mean()
    md_tp = tp.rolling(window=20).std()
    df["CCI"] = (tp - ma_tp) / (0.015 * md_tp)

    # ADX simplificado
    df["+DM"] = df["high"].diff()
    df["-DM"] = df["low"].diff()
    df["+DM"] = np.where((df["+DM"] > df["-DM"]) & (df["+DM"] > 0), df["+DM"], 0)
    df["-DM"] = np.where((df["-DM"] > df["+DM"]) & (df["-DM"] > 0), df["-DM"], 0)
    tr1 = df["high"] - df["low"]
    tr2 = abs(df["high"] - df["close"].shift())
    tr3 = abs(df["low"] - df["close"].shift())
    df["TR"] = tr1.combine(tr2, max).combine(tr3, max)
    atr = df["TR"].rolling(14).mean()
    plus_di = 100 * (df["+DM"].rolling(14).sum() / atr)
    minus_di = 100 * (df["-DM"].rolling(14).sum() / atr)
    dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    df["ADX"] = dx.rolling(14).mean()

    df["volume_medio"] = df["volume"].rolling(20).mean()
    df["volume_explosivo"] = df["volume"] > 1.3 * df["volume_medio"]

    return df

def verificar_sinais(df):
    row = df.iloc[-1]
    prev = df.iloc[-2]
    ultimos5 = df.iloc[-6:-1]

    corpo = abs(row["close"] - row["open"])
    corpo_prev = abs(prev["close"] - prev["open"])

    # Sinais fortes
    sinal_1 = row["EMA10"] > row["EMA20"]
    sinal_2 = row["MACD"] > row["SINAL"]
    sinal_3 = row["CCI"] > 0
    sinal_4 = row["ADX"] > 20
    sinal_7 = (row["close"] > row["EMA50"])  # não lateral (exemplo)

    # Sinais extras
    sinal_5 = row["volume_explosivo"]
    sinal_6 = corpo > (ultimos5["close"].max() - ultimos5["low"].min())
    extra_1 = prev["close"] > prev["open"]  # vela anterior de alta
    extra_2 = (row["high"] - row["close"]) < corpo  # pequeno pavio superior

    sinais_fortes = [sinal_1, sinal_2, sinal_3, sinal_4, sinal_7]
    sinais_extras = [sinal_5, sinal_6, extra_1, extra_2]

    total_fortes = sum(sinais_fortes)
    total_extras = sum(sinais_extras)

    print(f"\n📊 Diagnóstico de sinais em {row['timestamp']}")
    print(f"📌 EMA10 > EMA20: {sinal_1}")
    print(f"📌 MACD > SINAL: {sinal_2}")
    print(f"📌 CCI > 0: {sinal_3} (valor: {row['CCI']:.2f})")
    print(f"📌 ADX > 20: {sinal_4} (valor: {row['ADX']:.2f})")
    print(f"📌 Volume explosivo: {sinal_5} (volume: {row['volume']:.2f})")
    print(f"📌 Corpo grande: {sinal_6}")
    print(f"📌 Não lateral: {sinal_7}")
    print(f"📌 Extra: Vela anterior de alta: {extra_1}")
    print(f"📌 Extra: Pequeno pavio superior: {extra_2}")
    print(f"✔️ Total: {total_fortes} fortes + {total_extras} extras = {total_fortes + total_extras}/9")

    # Lógica de entrada conforme pedido
    entrar = False
    if total_fortes >= 5:
        entrar = True
    elif total_fortes == 4 and total_extras >= 1:
        entrar = True

    if entrar:
        print(f"🔔 {row['timestamp']} | Entrada validada com {total_fortes} fortes + {total_extras} extras!")
    else:
        print(f"🔎 {row['timestamp']} | Apenas {total_fortes + total_extras}/9 sinais confirmados | Entrada bloqueada ❌")

    return entrar, row["close"]

def enviar_ordem_compra(symbol, quantidade, preco_entrada):
    try:
        # Calcula TP e SL
        tp_price = preco_entrada * 1.015  # +1.5%
        sl_price = preco_entrada * 0.997  # -0.3%

        print(f"Enviando ordem de compra para {symbol} | Preço entrada: {preco_entrada:.4f}")
        print(f"Take Profit: {tp_price:.4f} | Stop Loss: {sl_price:.4f}")

        order = session.place_active_order(
            category="linear",
            symbol=symbol,
            side="Buy",
            orderType="Market",
            qty=quantidade,
            timeInForce="GoodTillCancel",
            reduceOnly=False,
            closeOnTrigger=False,
            takeProfit=tp_price,
            stopLoss=sl_price
        )
        print("Ordem enviada com sucesso:", order)
    except Exception as e:
        print(f"Erro ao enviar ordem: {e}")

def main():
    while True:
        df = fetch_candles(symbol, interval)
        df = calcular_indicadores(df)
        entrar, preco = verificar_sinais(df)

        if entrar:
            # Pega quantidade em unidades (exemplo simples: compra $5 em moeda)
            quantidade_moeda = quantidade_usdt / preco
            enviar_ordem_compra(symbol, quantidade_moeda, preco)
        else:
            print(f"Sem entrada para {symbol} no momento.")

        time.sleep(60)  # Espera 1 minuto antes de próxima checagem

if __name__ == "__main__":
    main()


