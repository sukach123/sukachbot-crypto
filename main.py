# === SukachBot PRO75 - Agora com TP de 1.5% automático e SL de -0.3% ===

import pandas as pd
import numpy as np
from pybit.unified_trading import HTTP, WebSocket
import threading

# Configuração da conta e mercado
api_key = "SUA_API_KEY"
api_secret = "SEU_API_SECRET"
symbol = "BTCUSDT"
interval = "1"

session = HTTP(api_key=api_key, api_secret=api_secret)

ws = WebSocket(
    testnet=False,
    api_key=api_key,
    api_secret=api_secret,
    channel_type="linear"
)

# Variáveis de controle
position_open = False
entry_price = 0.0

def calcular_sinais(df):
    sinais = []

    df['EMA10'] = df['close'].ewm(span=10).mean()
    df['EMA20'] = df['close'].ewm(span=20).mean()
    df['MACD'] = df['EMA10'] - df['EMA20']
    df['Signal'] = df['MACD'].ewm(span=9).mean()
    df['RSI'] = 100 - (100 / (1 + df['close'].pct_change().rolling(14).mean()))

    ultimo = df.iloc[-1]

    # 4 sinais fortes
    if ultimo['EMA10'] > ultimo['EMA20']: sinais.append("EMA")
    if ultimo['MACD'] > ultimo['Signal']: sinais.append("MACD")
    if ultimo['RSI'] > 50: sinais.append("RSI")
    if ultimo['close'] > df['close'].rolling(20).mean().iloc[-1]: sinais.append("Preço acima da média")

    # 1 sinal extra
    if df['volume'].iloc[-1] > df['volume'].rolling(20).mean().iloc[-1]: sinais.append("Volume extra")

    return sinais

def abrir_ordem_longa(preco):
    global position_open, entry_price
    print(f"📈 Abrindo LONG em {preco}")
    position_open = True
    entry_price = preco

def verificar_tp_sl(preco_atual):
    global position_open, entry_price
    if not position_open:
        return

    lucro_percentual = (preco_atual - entry_price) / entry_price * 100
    if lucro_percentual >= 1.5:
        print(f"✅ Take Profit alcançado! ({lucro_percentual:.2f}%) — Fechando posição.")
        position_open = False
    elif lucro_percentual <= -0.3:
        print(f"🛑 Stop Loss acionado! ({lucro_percentual:.2f}%) — Fechando posição.")
        position_open = False

def handle_message(message):
    try:
        if 'data' not in message:
            return

        kline = message['data']['k']
        if not kline['confirm']:  # Ignora candles ainda não fechados
            return

        df = pd.DataFrame([{
            'open': float(kline['o']),
            'high': float(kline['h']),
            'low': float(kline['l']),
            'close': float(kline['c']),
            'volume': float(kline['v'])
        }])

        # Guardar últimas 180 velas
        if not hasattr(handle_message, 'historico'):
            handle_message.historico = df.copy()
        else:
            handle_message.historico = pd.concat([handle_message.historico, df]).tail(180)

        if len(handle_message.historico) < 20:
            return  # Aguarda mais dados

        sinais = calcular_sinais(handle_message.historico)

        print(f"Sinais detectados: {sinais}")

        if not position_open and (len(sinais) >= 5 or (len(sinais) == 5 and "Volume extra" in sinais)):
            abrir_ordem_longa(float(kline['c']))

        if position_open:
            verificar_tp_sl(float(kline['c']))

    except Exception as e:
        print(f"❌ Erro ao processar candle: {e}")

# Inicia WebSocket
def iniciar_stream():
    ws.kline_stream(
        symbol=symbol,
        interval=interval,
        callback=handle_message
    )
    print("📡 WebSocket iniciado e ouvindo candles a cada segundo...")

threading.Thread(target=iniciar_stream).start()
