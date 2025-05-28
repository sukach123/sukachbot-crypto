# === SukachBot PRO75 - Agora com TP de 1.5% automático e SL de -0.3% ===

import pandas as pd
import numpy as np
from pybit.unified_trading import HTTP, WebSocket
import threading
import time

# Configuração da conta
api_key = "SUA_API_KEY"
api_secret = "SEU_API_SECRET"

session = HTTP(api_key=api_key, api_secret=api_secret, testnet=True)

symbol = "BTCUSDT"
interval = "1"
limit = 180
tp_percent = 1.5
sl_percent = -0.3
active_position = False
entry_price = 0

# === Função de Análise Técnica ===
def calcular_sinais(df):
    sinais = []

    df['EMA10'] = df['close'].ewm(span=10).mean()
    df['EMA20'] = df['close'].ewm(span=20).mean()

    df['MACD'] = df['close'].ewm(span=12).mean() - df['close'].ewm(span=26).mean()
    df['Signal'] = df['MACD'].ewm(span=9).mean()

    df['RSI'] = 100 - (100 / (1 + df['close'].pct_change().add(1).rolling(window=14).apply(lambda x: (x[x > 1].sum() / x[x <= 1].sum()) if x[x <= 1].sum() != 0 else 0)))

    close = df['close']
    delta = close.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))

    df['Volume MA'] = df['volume'].rolling(window=20).mean()

    # Verificações de sinais
    if df['EMA10'].iloc[-1] > df['EMA20'].iloc[-1]:
        sinais.append("EMA10>EMA20")
    if df['MACD'].iloc[-1] > df['Signal'].iloc[-1]:
        sinais.append("MACD>Signal")
    if df['RSI'].iloc[-1] > 50:
        sinais.append("RSI>50")
    if df['close'].iloc[-1] > df['EMA10'].iloc[-1]:
        sinais.append("Preço>EMA10")
    if df['volume'].iloc[-1] > df['Volume MA'].iloc[-1]:
        sinais.append("Volume>Media")

    return sinais

# === Execução de Ordem ===
def executar_ordem(direcao, preco):
    global active_position, entry_price
    print(f"📈 Executando ORDEM {direcao} a {preco}")
    active_position = True
    entry_price = preco

def verificar_tp_sl(preco_atual):
    global active_position, entry_price
    if not active_position:
        return
    variacao = (preco_atual - entry_price) / entry_price * 100
    if variacao >= tp_percent:
        print(f"✅ TP alcançado: Lucro de {variacao:.2f}%")
        active_position = False
    elif variacao <= sl_percent:
        print(f"🛑 SL acionado: Perda de {variacao:.2f}%")
        active_position = False

# === Callback do WebSocket ===
df_candles = pd.DataFrame()

def handle_candle(message):
    global df_candles

    try:
        if 'data' in message and isinstance(message['data'], dict):
            k = message['data']
            new_candle = {
                'timestamp': pd.to_datetime(k['timestamp'], unit='ms'),
                'open': float(k['open']),
                'high': float(k['high']),
                'low': float(k['low']),
                'close': float(k['close']),
                'volume': float(k['volume'])
            }
            df_candles = pd.concat([df_candles, pd.DataFrame([new_candle])]).drop_duplicates('timestamp')
            df_candles = df_candles.sort_values('timestamp').tail(limit).reset_index(drop=True)

            if len(df_candles) >= 20:
                sinais = calcular_sinais(df_candles)
                preco_atual = df_candles['close'].iloc[-1]

                if len(sinais) >= 4:
                    print(f"📊 Sinais detectados: {sinais}")
                    if not active_position:
                        print("🟢 Entrada com base nos sinais.")
                        executar_ordem("COMPRA", preco_atual)

                verificar_tp_sl(preco_atual)

    except Exception as e:
        print(f"Erro ao processar candle: {e}")

# === Início do WebSocket ===
def iniciar_ws():
    ws = WebSocket(
        testnet=True,
        api_key=api_key,
        api_secret=api_secret,
        channel_type="linear"
    )
    ws.kline_stream(
        interval="1",
        symbol=symbol,
        callback=handle_candle
    )
    print("📡 WebSocket iniciado e ouvindo candles a cada segundo...")

# Iniciar WebSocket em thread separada
threading.Thread(target=iniciar_ws).start()

# Manter script vivo
while True:
    time.sleep(1)
