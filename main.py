# === SukachBot PRO75 - Com TP, SL dinâmico com ATR, quantidade ajustável e trailing stop ===

import pandas as pd
import numpy as np
from pybit.unified_trading import HTTP
import time
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
SESSION = HTTP(api_key=API_KEY, api_secret=API_SECRET, testnet=True)

PERIODO_ATR = 14
MULT_ATR = 1.8
QUANTIDADE = 0.02  # Quantidade de ETH ou BTC por operação
TP_PERCENTUAL = 0.015  # 1.5%
TRAILING_ATIVO = True
TRAILING_OFFSET = 0.005  # 0.5%

# === Função para calcular ATR ===
def calcular_atr(df, periodo=PERIODO_ATR):
    df['H-L'] = df['high'] - df['low']
    df['H-PC'] = abs(df['high'] - df['close'].shift(1))
    df['L-PC'] = abs(df['low'] - df['close'].shift(1))
    df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
    df['ATR'] = df['TR'].rolling(window=periodo).mean()
    return df

# === Calcular SL dinâmico com base no ATR ===
def obter_sl_dinamico(symbol, lado, preco_atual):
    try:
        candles = SESSION.get_kline(
            category="linear",
            symbol=symbol,
            interval="1",
            limit=PERIODO_ATR + 1
        )

        df = pd.DataFrame(candles['result']['list'], columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume', '_1', '_2'
        ])
        df[['high', 'low', 'close']] = df[['high', 'low', 'close']].astype(float)
        df = calcular_atr(df)

        atr = df.iloc[-1]['ATR']
        if lado == "Buy":
            sl = round(preco_atual - (atr * MULT_ATR), 3)
        else:
            sl = round(preco_atual + (atr * MULT_ATR), 3)

        return sl
    except Exception as e:
        print(f"Erro ao calcular SL dinâmico: {e}")
        return None

# === Enviar ordem com SL, TP e Trailing Stop ===
def enviar_ordem(symbol, lado, preco_atual):
    sl = obter_sl_dinamico(symbol, lado, preco_atual)
    if lado == "Buy":
        tp = round(preco_atual * (1 + TP_PERCENTUAL), 3)
    else:
        tp = round(preco_atual * (1 - TP_PERCENTUAL), 3)

    ordem = {
        "category": "linear",
        "symbol": symbol,
        "side": "Buy" if lado == "Buy" else "Sell",
        "orderType": "Market",
        "qty": QUANTIDADE,
        "takeProfit": tp,
        "stopLoss": sl,
    }

    if TRAILING_ATIVO:
        ordem["trailingStop"] = round(preco_atual * TRAILING_OFFSET, 3)

    print(f"Enviando ordem: {ordem}")
    # Descomente para executar de verdade:
    # resposta = SESSION.place_order(**ordem)
    # print(resposta)

# Exemplo de chamada
# enviar_ordem("ETHUSDT", "Buy", 2200.0)  # Simulação de compra

# Script completo com:
# - SL dinâmico via ATR (período 14, mult. 1.8)
# - TP fixo de +1.5%
# - Trailing Stop opcional
# - Quantidade ajustável

