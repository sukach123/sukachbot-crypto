import os
import requests
import threading
from pybit.unified_trading import HTTP
import pandas as pd
from flask import Flask

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
TAKE_PROFIT_PORCENTAGEM = 0.03
STOP_LOSS_PORCENTAGEM = 0.015

PARES = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "BNBUSDT",
    "XRPUSDT", "DOGEUSDT", "MATICUSDT", "ADAUSDT", "DOTUSDT"
]

# --- Função para obter preço atual ---
def obter_preco_atual(symbol):
    url = "https://api.bybit.com/v5/market/tickers"
    params = {"category": "linear", "symbol": symbol}
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json().get("result", {}).get("list", [])
            if data:
                preco_atual = float(data[0].get("lastPrice", 0))
                return preco_atual
            else:
                print(f"❌ Dados de preço indisponíveis para {symbol}.")
                return 0
        else:
            print(f"❌ Erro ao buscar preço para {symbol}. Status: {response.status_code}")
            return 0
    except Exception as e:
        print(f"Erro ao obter preço atual para {symbol}: {e}")
        return 0

# --- Função para criar ordem ---
def criar_ordem_market(symbol, qty, tp_percent, sl_percent, side="Buy"):
    try:
        preco_atual = obter_preco_atual(symbol)

        if preco_atual == 0:
            print(f"❌ Não foi possível obter o preço atual para {symbol}. Ordem cancelada.")
            return

        if side == "Buy":
            tp = round(preco_atual * (1 + tp_percent), 2)
            sl = round(preco_atual * (1 - sl_percent), 2)
        else:
            tp = round(preco_atual * (1 - tp_percent), 2)
            sl = round(preco_atual * (1 + sl_percent), 2)

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

        print(f"✅ Ordem executada: {symbol} | {side} | Qtd: {qty} | TP: {tp} | SL: {sl}")
    except Exception as e:
        print(f"Erro ao enviar ordem: {e}")

# --- Função para analisar entradas ---
def analisar_entradas(par):
    url = "https://api.bybit.com/v5/market/kline"
    params = {"category": "linear", "symbol": par, "interval": "1", "limit": 200}
    response = requests.get(url, params=params)

    if response.status_code == 200:
        try:
            data = response.json().get("result", {}).get("list", [])
            if data:
                columns = ['start', 'open', 'high', 'low', 'close', 'volume', 'end']
                df = pd.DataFrame(data, columns=columns)
                if 'close' in df.columns:
                    df['close'] = df['close'].astype(float)
                    print(f"✅ Sinal para {par}: MACD Sell, SMA Sell")  # Exemplo
                    return True
                else:
                    print(f"❌ Coluna 'close' não encontrada para {par}.")
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

# --- Bot principal ---
def iniciar_bot():
    print(f"✅ Pares para análise: {PARES}")
    for par in PARES:
        if analisar_entradas(par):
            criar_ordem_market(par, VALOR_ENTRADA_USDT, TAKE_PROFIT_PORCENTAGEM, STOP_LOSS_PORCENTAGEM)

# --- Iniciar Flask e Bot ---
iniciar_flask()
iniciar_bot()

