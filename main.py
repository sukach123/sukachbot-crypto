import time
import math
from datetime import datetime, timezone
from pybit.unified_trading import HTTP

# === CONFIGURAÇÕES ===
API_KEY = "SUA_API_KEY_TESTNET"
API_SECRET = "SUA_API_SECRET_TESTNET"
BASE_URL = "https://api-testnet.bybit.com"

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]  # Pares monitorados
USDT_PER_TRADE = 5
LEVERAGE = 10
TP_PORC = 1.5
SL_PORC = 0.3
INTERVALO = 60  # segundos

# === CONEXÃO COM A API ===
session = HTTP(api_key=API_KEY, api_secret=API_SECRET, testnet=True)

# === AJUSTAR QTY COM BASE NO PREÇO E STEP PERMITIDO ===
def ajustar_qty(symbol, usdt_qty):
    try:
        price_data = session.get_tickers(category="linear", symbol=symbol)
        price = float(price_data["result"]["list"][0]["lastPrice"])

        info = session.get_instruments_info(category="linear", symbol=symbol)
        step = float(info["result"]["list"][0]["lotSizeFilter"]["qtyStep"])

        qty = (usdt_qty * LEVERAGE) / price
        qty_arredondado = math.floor(qty / step) * step

        return str(round(qty_arredondado, 3))
    except Exception as e:
        print(f"❌ Erro ao ajustar qty para {symbol}: {e}")
        return "0"

# === FUNÇÃO DE ANÁLISE DE MERCADO (EXEMPLO SIMPLES) ===
def analisar_mercado(symbol):
    try:
        ticker = session.get_tickers(category="linear", symbol=symbol)
        price = float(ticker["result"]["list"][0]["lastPrice"])
        print(f"🔍 {symbol} | Sinal: BUY | Preço: {price}")
        return True, price
    except Exception as e:
        print(f"❌ Erro ao buscar preço de {symbol}: {e}")
        return False, 0

# === ENVIO DE ORDEM MARKET COM TP E SL ===
def enviar_ordem(symbol, price):
    try:
        qty = ajustar_qty(symbol, USDT_PER_TRADE)
        if qty == "0":
            return

        tp = round(price * (1 + TP_PORC / 100), 2)
        sl = round(price * (1 - SL_PORC / 100), 2)

        print(f"📈 Enviando ordem para {symbol}: QTY {qty}, TP {tp}, SL {sl}")

        ordem = session.place_order(
            category="linear",
            symbol=symbol,
            side="Buy",
            order_type="Market",
            qty=qty,
            take_profit=str(tp),
            stop_loss=str(sl),
            time_in_force="GoodTillCancel"
        )

        print(f"✅ Ordem enviada com sucesso para {symbol}: {ordem}")
    except Exception as e:
        print(f"❌ Erro ao enviar ordem para {symbol}: {e}")

# === LOOP PRINCIPAL ===
while True:
    agora = datetime.now(timezone.utc).isoformat()
    print(f"\n⏳ Iniciando análise - {agora}\n")

    for symbol in SYMBOLS:
        sinal, preco = analisar_mercado(symbol)
        if sinal and preco > 0:
            enviar_ordem(symbol, preco)
        else:
            print(f"📉 {symbol}: Nenhum sinal ou erro ao obter preço.")

    print(f"\n⏰ Aguardando {INTERVALO} segundos...\n")
    time.sleep(INTERVALO)

