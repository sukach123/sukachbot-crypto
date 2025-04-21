import os
import time
import requests
from pybit.unified_trading import HTTP
from datetime import datetime
from flask import Flask
import threading
import pandas as pd

# --- FLASK SETUP ---
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ SukachBot CRYPTO está online!"

def iniciar_flask():
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=8080)).start()

# --- CONFIGURAÇÕES GERAIS ---
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")

# Verificar se variáveis estão configuradas
if not BYBIT_API_KEY or not BYBIT_API_SECRET:
    raise ValueError("Erro: Configurações de variáveis de ambiente inválidas!")

session = HTTP(api_key=BYBIT_API_KEY, api_secret=BYBIT_API_SECRET, testnet=False)

# --- CONFIGURAÇÕES DO BOT ---
VALOR_ENTRADA_USDT = 5
ALAVANCAGEM = 2
TAKE_PROFIT_PORCENTAGEM = 0.03
STOP_LOSS_PORCENTAGEM = 0.015

PARES = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "BNBUSDT",
    "XRPUSDT", "DOGEUSDT", "MATICUSDT", "ADAUSDT", "DOTUSDT"
]

# --- FUNÇÕES PARA CÁLCULO DE INDICADORES ---
def calcular_rsi(df, period=14):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calcular_indicadores(df):
    df['RSI'] = calcular_rsi(df)
    df['ema_fast'] = df['close'].ewm(span=12, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = df['ema_fast'] - df['ema_slow']
    df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['sma_20'] = df['close'].rolling(window=20).mean()

    sinais = []
    if df['RSI'].iloc[-1] < 30:
        sinais.append('RSI Buy')
    elif df['RSI'].iloc[-1] > 70:
        sinais.append('RSI Sell')

    if df['macd'].iloc[-1] > df['signal'].iloc[-1]:
        sinais.append('MACD Buy')
    else:
        sinais.append('MACD Sell')

    if df['close'].iloc[-1] > df['sma_20'].iloc[-1]:
        sinais.append('SMA Buy')
    else:
        sinais.append('SMA Sell')

    return sinais

# --- ANÁLISE DE PARES ---
def analisar_entradas(par):
    url = f"https://api.bybit.com/v5/market/kline"
    params = {
        "category": "linear",
        "symbol": par,
        "interval": "1",  # 1 minuto
        "limit": 200
    }
    response = requests.get(url, params=params)

    if response.status_code == 200:
        try:
            # Obter os dados e criar DataFrame dinamicamente
            data = response.json().get("result", {}).get("list", [])
            if data:
                # Criar DataFrame e usar as colunas retornadas dinamicamente
                columns = ['start', 'open', 'high', 'low', 'close', 'volume', 'end']
                df = pd.DataFrame(data, columns=columns)
                print(f"Colunas disponíveis: {df.columns}")  # Para depuração

                # Garantir que a coluna 'close' está disponível
                if 'close' in df.columns:
                    df['close'] = df['close'].astype(float)

                    # Calcular indicadores
                    sinais = calcular_indicadores(df)

                    # Avaliar os sinais
                    if len(sinais) >= 2:
                        print(f"✅ Sinal para {par}: {', '.join(sinais)}")
                        return True
                    else:
                        print(f"❌ Sinal para {par}: {', '.join(sinais)}")
                        return False
                else:
                    print(f"❌ Coluna 'close' não encontrada para {par}. Verifique os dados retornados.")
                    return False
            else:
                print(f"❌ Dados indisponíveis para {par}.")
                return False
        except Exception as e:
            print(f"Erro ao processar dados de {par}: {e}")
            return False
    else:
        print(f"❌ Erro na requisição para {par}. Status: {response.status_code}")
        return False

# --- CRIAÇÃO DE ORDENS ---
def criar_ordem_market(symbol, qty, tp, sl, side="Buy"):
    try:
        # Obter o preço atual do símbolo para cálculos
        preco_atual = session.get_latest_price(symbol=symbol).get("price", 0)

        if preco_atual == 0:
            print(f"❌ Não foi possível obter o preço atual para {symbol}. Ordem cancelada.")
            return

        # Calcular Take Profit (TP) e Stop Loss (SL) em valores absolutos
        if side == "Buy":
            tp = round(preco_atual * (1 + tp), 2)
            sl = round(preco_atual * (1 - sl), 2)
        else:
            tp = round(preco_atual * (1 - tp), 2)
            sl = round(preco_atual * (1 + sl), 2)

        # Criar ordem com os parâmetros corrigidos
        session.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            order_type="Market",
            qty=qty,
            take_profit=tp,
            stop_loss=sl,
            time_in_force="GoodTillCancel"
        )

        print(f"✅ Ordem executada: {symbol} | {side} | {qty} USDT | TP: {tp} | SL: {sl}")
    except Exception as e:
        print(f"Erro ao enviar ordem: {e}")

# --- PROCESSAMENTO ---
def iniciar_bot():
    print(f"✅ Pares para análise: {PARES}")
    for par in PARES:
        print(f"Analisando o par: {par}")
        if analisar_entradas(par):
            criar_ordem_market(
                symbol=par,
                qty=VALOR_ENTRADA_USDT,
                tp=TAKE_PROFIT_PORCENTAGEM,
                sl=STOP_LOSS_PORCENTAGEM,
                side="Buy"
            )

# --- INICIAR SERVIDOR E BOT ---
iniciar_flask()
iniciar_bot()
