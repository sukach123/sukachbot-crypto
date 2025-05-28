import pandas as pd
import numpy as np
from pybit.unified_trading import HTTP
import time
from datetime import datetime, timezone

# Configurações API Testnet Bybit
API_KEY = "SUA_API_KEY"
API_SECRET = "SEU_API_SECRET"
session = HTTP(api_key=API_KEY, api_secret=API_SECRET, testnet=True)

symbols = ["BNBUSDT", "BTCUSDT", "DOGEUSDT", "SOLUSDT", "ADAUSDT", "ETHUSDT"]
interval = "1"  # 1 minuto
quantidade_usdt = 5

def fetch_candles(symbol, interval="1"):
    try:
        data = session.get_kline(category="linear", symbol=symbol, interval=interval, limit=200)
        candles = data['result']['list']
        df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"])
        df = df.astype({"open": float, "high": float, "low": float, "close": float, "volume": float})
        df["timestamp"] = pd.to_datetime(pd.to_numeric(df["timestamp"]), unit="ms", utc=True)
        return df
    except Exception as e:
        print(f"🚨 Erro ao buscar candles de {symbol}: {e}")
        time.sleep(1)
        return fetch_candles(symbol)

def calcular_indicadores(df):
    df["EMA10"] = df["close"].ewm(span=10, adjust=False).mean()
    df["EMA20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["MACD"] = df["close"].ewm(span=12, adjust=False).mean() - df["close"].ewm(span=26, adjust=False).mean()
    df["SINAL"] = df["MACD"].ewm(span=9, adjust=False).mean()
    df["CCI"] = (df["close"] - df["close"].rolling(20).mean()) / (0.015 * df["close"].rolling(20).std())
    df["ADX"] = abs(df["high"] - df["low"]).rolling(14).mean()
    df["ATR"] = (df["high"] - df["low"]).rolling(14).mean()
    df["volume_medio"] = df["volume"].rolling(20).mean()
    df["volume_explosivo"] = df["volume"] > 1.3 * df["volume_medio"]
    return df

def verificar_entrada(df):
    row = df.iloc[-1]
    prev = df.iloc[-2]
    ultimos5 = df.iloc[-6:-1]
    
    corpo = abs(row["close"] - row["open"])
    lateral = df.iloc[-10:]
    variacao = lateral["close"].max() - lateral["close"].min()
    nao_lateral = variacao > 0.01 * row["close"]  # exemplo de limiar para definir lateralidade

    sinal_1 = row["EMA10"] > row["EMA20"]
    sinal_2 = row["MACD"] > row["SINAL"]
    sinal_3 = row["CCI"] > 0
    sinal_4 = row["ADX"] > 20
    sinal_5 = row["volume_explosivo"]
    sinal_6 = corpo > (ultimos5["close"].max() - ultimos5["low"].min())
    sinal_7 = nao_lateral

    sinais_fortes = [sinal_1, sinal_2, sinal_3, sinal_4, sinal_7]
    
    extra_1 = prev["close"] > prev["open"]
    extra_2 = (row["high"] - row["close"]) < corpo
    sinais_extras = [sinal_5, sinal_6, extra_1, extra_2]

    total_fortes = sum(sinais_fortes)
    total_extras = sum(sinais_extras)
    total_confirmados = total_fortes + total_extras

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
    print(f"✔️ Total: {total_fortes} fortes + {total_extras} extras = {total_confirmados}/9")

    # Condições para entrada:
    if total_fortes == 5 or (total_fortes == 4 and total_extras >= 1):
        preco_entrada = row["close"]
        tp = preco_entrada * 1.015  # Take Profit 1.5%
        sl = preco_entrada * 0.997  # Stop Loss -0.3%

        print(f"🔔 Entrada validada em {row['timestamp']} | Preço entrada: {preco_entrada:.4f} | TP: {tp:.4f} | SL: {sl:.4f}")

        # Executar ordem de compra (exemplo mercado, quantidade fixa em USDT)
        try:
            quantidade = quantidade_usdt / preco_entrada
            order = session.place_active_order(
                category="linear",
                symbol=symbol,
                side="Buy",
                orderType="Market",
                qty=quantidade,
                timeInForce="GoodTillCancel",
                reduceOnly=False,
                closeOnTrigger=False
            )
            print(f"✅ Ordem de compra enviada: {order}")
        except Exception as e:
            print(f"🚨 Erro ao enviar ordem: {e}")
        return True
    else:
        print(f"🔎 {row['timestamp']} | Entrada bloqueada ❌")
        return False

def main():
    while True:
        for symbol in symbols:
            print(f"\n>>> Analisando {symbol} <<<")
            df = fetch_candles(symbol, interval)
            df = calcular_indicadores(df)
            verificar_entrada(df)
        time.sleep(60)  # Espera 1 minuto para próxima checagem

if __name__ == "__main__":
    main()
