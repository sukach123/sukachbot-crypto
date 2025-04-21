import os
import time
import requests
from pybit.unified_trading import HTTP
from datetime import datetime
from flask import Flask
import threading
import numpy as np
import pandas as pd

# --- FLASK SETUP ---
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ SukachBot CRYPTO está online!"

def iniciar_flask():
    app.run(host="0.0.0.0", port=8080)

# --- CONFIGURAÇÕES GERAIS ---
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Verificar se variáveis estão configuradas
if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("Erro: O BOT_TOKEN ou CHAT_ID do Telegram não estão configurados corretamente.")

session = HTTP(api_key=BYBIT_API_KEY, api_secret=BYBIT_API_SECRET, testnet=False)

# --- CONFIGURAÇÕES DO BOT ---
VALOR_ENTRADA_USDT = 5
ALAVANCAGEM = 2
TAKE_PROFIT_PORCENTAGEM = 0.03
STOP_LOSS_PORCENTAGEM = 0.015

# --- VARIÁVEIS DE REGISTO DE RESULTADOS ---
estatisticas = {
    "total_entradas": 0,
    "total_wins": 0,
    "total_losses": 0,
    "lucro_total": 0.0,
    "ordens_ativas": []
}

# --- FUNÇÃO DE TELEGRAM ---
def enviar_telegram_mensagem(mensagem):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Erro ao enviar mensagem para Telegram:", e)

# --- PARES FIXOS PARA ANÁLISE ---
PARES = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "BNBUSDT", 
    "XRPUSDT", "DOGEUSDT", "MATICUSDT", "ADAUSDT", "DOTUSDT"
]

# --- CÁLCULOS DOS INDICADORES (RSI, MACD, etc.) ---

# Calcular RSI
def calcular_rsi(df, period=14):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Calcular MACD
def calcular_macd(df, fastperiod=12, slowperiod=26, signalperiod=9):
    df['ema_fast'] = df['close'].ewm(span=fastperiod, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=slowperiod, adjust=False).mean()
    df['macd'] = df['ema_fast'] - df['ema_slow']
    df['signal'] = df['macd'].ewm(span=signalperiod, adjust=False).mean()
    return df['macd'], df['signal']

# Calcular Média Móvel Simples (SMA)
def calcular_sma(df, period=20):
    df['sma'] = df['close'].rolling(window=period).mean()
    return df['sma']

# Função de cálculo de indicadores
def calcular_indicadores(df):
    df['RSI'] = calcular_rsi(df)
    df['macd'], df['signal'] = calcular_macd(df)
    df['sma_20'] = calcular_sma(df)
    
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

# --- FUNÇÃO PARA ANÁLISE COMPLETA E ENTRADA NO MERCADO ---
def analisar_entradas(par):
    if par not in PARES:
        print(f"❌ Par {par} não encontrado na lista de pares válidos.")
        return False

    url = f"https://api.bybit.com/v5/market/kline"  # Alterado para o endpoint V5
    params = {
        "symbol": par,
        "interval": "15m",  # Intervalo de 15 minutos (tentei um intervalo menor)
        "limit": 200
    }
    response = requests.get(url, params=params)

    if response.status_code == 200:
        try:
            data = response.json()
            print(f"Dados retornados para {par}: {data}")  # Verifique os dados recebidos

            if 'result' in data and data['result']:
                if data['result']['list']:  # Verifique se a lista de dados não está vazia
                    df = pd.DataFrame(data['result']['list'])  # Corrigir a chave 'list'
                    print(f"DataFrame para {par}: {df.head()}")  # Verifique as primeiras linhas do DataFrame
                    
                    # Verifica se a coluna 'close' está presente
                    if 'close' in df.columns:
                        df['close'] = df['close'].astype(float)
                        sinais = calcular_indicadores(df)
                        if len(set(sinais)) >= 5:
                            print(f"✅ Sinal para {par}: {', '.join(sinais)}")
                            return True
                        else:
                            print(f"❌ Sinal para {par}: {', '.join(sinais)}")
                            return False
                    else:
                        print(f"❌ Coluna 'close' não encontrada nos dados para {par}.")
                        return False
                else:
                    print(f"❌ Lista de dados vazia para {par}.")
                    return False
            else:
                print(f"❌ Dados de {par} não disponíveis.")
                return False
        except ValueError as e:
            print(f"Erro ao processar dados de {par}: {e}")
            return False
    else:
        print(f"❌ Erro na requisição para {par}. Status: {response.status_code}")
        return False

# --- FUNÇÃO PARA CRIAR ORDENS DE MERCADO --- 
def criar_ordem_market(symbol, qty, tp, sl, side="Buy"):
    timestamp = str(int(time.time() * 1000))
    url = f"https://api.bybit.com/v5/order/create"

    body = {
        "category": "linear",
        "symbol": symbol,
        "side": side,
        "order_type": "Market",
        "qty": qty,
        "take_profit": tp,
        "stop_loss": sl,
        "time_in_force": "GoodTillCancel"
    }

    # Criação da assinatura de forma segura, sem o uso de str(body) direto
    body_str = f'{{"category":"linear","symbol":"{symbol}","side":"{side}","order_type":"Market","qty":{qty},"take_profit":{tp},"stop_loss":{sl},"time_in_force":"GoodTillCancel"}}'

    sign_payload = timestamp + BYBIT_API_KEY + "5000" + body_str
    signature = gerar_assinatura(BYBIT_API_SECRET, sign_payload)

    headers = {
        "X-BYBIT-API-KEY": BYBIT_API_KEY,
        "X-BYBIT-SIGN": signature,
        "X-BYBIT-TIMESTAMP": timestamp,
        "X-BYBIT-RECV-WINDOW": "5000",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=body, headers=headers)
        resposta = response.json()

        if response.status_code == 200 and resposta.get("retCode") == 0:
            print(f"✅ Ordem executada: {symbol} | {side} | {qty} USDT")
            enviar_telegram_mensagem(f"✅ Ordem executada para {symbol}: {side} | Quantidade: {qty} USDT")
        else:
            print(f"❌ Ordem falhou: {resposta.get('retMsg')}")
            enviar_telegram_mensagem(f"❌ Falha ao executar ordem para {symbol}: {resposta.get('retMsg')}")
        
        return resposta
    except Exception as e:
        print(f"Erro ao enviar ordem: {e}")
        enviar_telegram_mensagem(f"❌ Erro ao enviar ordem para {symbol}: {e}")
        return None

# --- PROCESSANDO A ANÁLISE NOS PARES FIXOS ---
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
