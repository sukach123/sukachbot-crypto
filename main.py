import time
from datetime import datetime, timezone
from pybit.unified_trading import HTTP

# === CONFIGURAÇÕES ===
API_KEY = "SUA_API_KEY_TESTNET"
API_SECRET = "SUA_API_SECRET_TESTNET"
BASE_URL = "https://api-testnet.bybit.com"
PAIR = "BTCUSDT"
QTY = 0.01  # Quantidade de entrada
TP_PORC = 0.5   # Take Profit (0.5%)
SL_PORC = 0.3   # Stop Loss (0.3%)
INTERVALO = 60  # Tempo entre análises (em segundos)

# === CONEXÃO COM API UNIFICADA (TESTNET) ===
session = HTTP(
    api_key=API_KEY,
    api_secret=API_SECRET,
    testnet=True
)

# === FUNÇÃO DE ANÁLISE DE MERCADO ===
def analisar_mercado(symbol):
    try:
        ticker = session.get_tickers(category="linear", symbol=symbol)
        price = float(ticker["result"]["list"][0]["lastPrice"])
        print(f"🔎 Sinal BUY detectado em {symbol} - Preço: {price}")
        return True, price
    except Exception as e:
        print(f"❌ Erro ao buscar preço: {e}")
        return False, 0

# === FUNÇÃO DE ENVIO DE ORDEM ===
def enviar_ordem(symbol, price):
    try:
        tp = round(price * (1 + TP_PORC / 100), 2)
        sl = round(price * (1 - SL_PORC / 100), 2)

        print(f"📈 Enviando ordem: QTY {QTY}, TP {tp}, SL {sl}")

        ordem = session.place_order(
            category="linear",
            symbol=symbol,
            side="Buy",
            order_type="Market",
            qty=str(QTY),
            take_profit=str(tp),
            stop_loss=str(sl),
            time_in_force="GoodTillCancel"
        )

        print(f"✅ Ordem enviada com sucesso: {ordem}")
    except Exception as e:
        print(f"❌ Erro ao enviar ordem: {e}")

# === LOOP PRINCIPAL ===
while True:
    agora = datetime.now(timezone.utc).isoformat()
    print(f"\n⏳ Analisando {PAIR} - {agora}")

    sinal, preco = analisar_mercado(PAIR)

    if sinal and preco > 0:
        enviar_ordem(PAIR, preco)
    else:
        print(f"📉 Nenhum sinal detectado ou erro no preço para {PAIR}.")

    print(f"\n⏰ Aguardando {INTERVALO} segundos para próxima análise...\n")
    time.sleep(INTERVALO)


