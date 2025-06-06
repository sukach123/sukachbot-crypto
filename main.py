import time
from datetime import datetime, timezone
from pybit.unified_trading import HTTP
import math

# === CONFIGURAÇÕES ===
API_KEY = "SUA_API_KEY_TESTNET"
API_SECRET = "SUA_API_SECRET_TESTNET"
BASE_URL = "https://api-testnet.bybit.com"
PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
QTY_USDT = 5
LEVERAGE = 10
TP_PORC = 1.5
SL_PORC = 0.3
INTERVALO = 1  # segundos
MIN_SINAIS = 7

# === CONEXÃO COM API ===
session = HTTP(api_key=API_KEY, api_secret=API_SECRET, testnet=True)

# === FUNÇÃO DE ARREDONDAMENTO DE QTY ===
def ajustar_qty(symbol, usdt_qty):
    try:
        info = session.get_instruments_info(category="linear", symbol=symbol)
        price = float(info["result"]["list"][0]["lastPrice"])
        step = float(info["result"]["list"][0]["lotSizeFilter"]["qtyStep"])
        qty = (usdt_qty * LEVERAGE) / price
        return str(round(math.floor(qty / step) * step, 3))
    except Exception as e:
        print(f"Erro ao ajustar qty para {symbol}: {e}")
        return "0"

# === FUNÇÃO DE VERIFICAÇÃO DE POSIÇÃO ABERTA ===
def tem_posicao_aberta(symbol):
    try:
        posicoes = session.get_positions(category="linear", symbol=symbol)
        for p in posicoes["result"]["list"]:
            if abs(float(p["size"])) > 0:
                return True
    except:
        pass
    return False

# === FUNÇÃO DE ANÁLISE DE SINAIS (SIMULADA) ===
def analisar_sinais(symbol):
    # Exemplo simplificado com sinal aleatório simulado
    from random import randint
    sinais_alinhados = randint(3, 9)
    direcao = "LONG" if randint(0, 1) == 1 else "SHORT"
    return sinais_alinhados, direcao

# === FUNÇÃO DE ENVIO DE ORDEM ===
def enviar_ordem(symbol, direcao):
    try:
        preco_atual = float(session.get_tickers(category="linear", symbol=symbol)["result"]["list"][0]["lastPrice"])
        qty = ajustar_qty(symbol, QTY_USDT)

        if direcao == "LONG":
            tp = round(preco_atual * (1 + TP_PORC / 100), 2)
            sl = round(preco_atual * (1 - SL_PORC / 100), 2)
            side = "Buy"
        else:
            tp = round(preco_atual * (1 - TP_PORC / 100), 2)
            sl = round(preco_atual * (1 + SL_PORC / 100), 2)
            side = "Sell"

        ordem = session.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            order_type="Market",
            qty=qty,
            take_profit=str(tp),
            stop_loss=str(sl),
            time_in_force="GoodTillCancel"
        )

        print(f"✅ Ordem {direcao} enviada para {symbol} | QTY: {qty} | TP: {tp} | SL: {sl}")
    except Exception as e:
        print(f"❌ Erro ao enviar ordem para {symbol}: {e}")

# === LOOP PRINCIPAL ===
while True:
    agora = datetime.now(timezone.utc).isoformat()
    print(f"\n🕒 {agora} - Analisando pares...")

    for pair in PAIRS:
        if tem_posicao_aberta(pair):
            print(f"⛔ {pair} já tem posição aberta. Ignorando...")
            continue

        sinais, direcao = analisar_sinais(pair)
        print(f"🔍 {pair} | Sinais: {sinais} | Direção: {direcao}")

        if sinais >= MIN_SINAIS:
            enviar_ordem(pair, direcao)
        else:
            print(f"📉 {pair}: Sinais insuficientes ({sinais}/{MIN_SINAIS})")

    time.sleep(INTERVALO)
