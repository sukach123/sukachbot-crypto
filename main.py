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

# --- FUNÇÃO PARA OBTER OS 10 PRIMEIROS PARES DISPONÍVEIS (na categoria 'linear') ---
def obter_top_10_pares():
    try:
        url = "https://api.bybit.com/v5/market/instruments-info?category=linear"
        resposta = requests.get(url)
        if resposta.status_code == 200:
            instrumentos = resposta.json().get("result", {}).get("list", [])
            # Retorna os 10 primeiros pares
            return [inst["symbol"] for inst in instrumentos[:10]]
    except Exception as e:
        print(f"Erro ao buscar pares: {e}")
    return []

# --- CÁLCULOS DOS INDICADORES (RSI, MACD, etc.) ---
def calcular_indicadores(df):
    # Calcular RSI
    df['RSI'] = df['close'].rolling(window=14).apply(lambda x: talib.RSI(x, timeperiod=14)[-1], raw=True)

    # Calcular MACD
    df['macd'], df['signal'], _ = talib.MACD(df['close'], fastperiod=12, slowperiod=26, signalperiod=9)

    # Calcular Média Móvel (SMA)
    df['sma_20'] = df['close'].rolling(window=20).mean()
    
    # Verifica os sinais para RSI, MACD e SMA
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
    # Baixar dados históricos do par
    url = f"https://api.bybit.com/v2/public/kline/list?symbol={par}&interval=1h&limit=200"
    response = requests.get(url)

    if response.status_code == 200:
        try:
            data = response.json()  # Tenta converter a resposta em JSON
            if 'result' in data and data['result']:
                df = pd.DataFrame(data['result'])
                df['close'] = df['close'].astype(float)

                # Calcular indicadores e verificar sinais
                sinais = calcular_indicadores(df)

                # Se 5 ou mais sinais estiverem alinhados
                if len(set(sinais)) >= 5:
                    print(f"✅ Sinal para {par}: {', '.join(sinais)}")
                    return True
                else:
                    print(f"❌ Sinal para {par}: {', '.join(sinais)}")
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

    # Parâmetros da ordem
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

    body_str = str(body).replace("'", '"').replace(" ", "")
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

# --- PROCESSANDO A ANÁLISE NOS PARES --- 
pares = obter_top_10_pares()  # Buscar os 10 pares principais
print(f"✅ Pares para análise: {pares}")

for par in pares:
    print(f"Analisando o par: {par}")
    
    if analisar_entradas(par):
        criar_ordem_market(
            symbol=par,
            qty=VALOR_ENTRADA_USDT,
            tp=TAKE_PROFIT_PORCENTAGEM,  # Exemplo de TP ajustado
            sl=STOP_LOSS_PORCENTAGEM,    # Exemplo de SL ajustado
            side="Buy"                   # Ou "Sell", dependendo do sinal
        )




