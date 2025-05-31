import time
import datetime
from pybit.unified_trading import HTTP

# Configurações
API_KEY = "SUA_API_KEY"
API_SECRET = "SEU_API_SECRET"
PAIR = "BTCUSDT"
QTY = 0.01  # Quantidade fixa
TP_PERC = 0.005  # +0.5%
SL_PERC = 0.005  # -0.5%
INTERVALO = 60  # segundos

# Sessão Testnet
session = HTTP(
    testnet=True,
    api_key=API_KEY,
    api_secret=API_SECRET,
)

def analisar_mercado(symbol):
    """
    Simples análise: entra sempre que rodar (apenas para teste).
    """
    try:
        ticker = session.get_market_ticker(category="linear", symbol=symbol)
        price = float(ticker["result"]["list"][0]["lastPrice"])
        print(f"\n🔎 Sinal BUY detectado em {symbol} - Preço: {price}")
        return True, price
    except Exception as e:
        print(f"Erro ao buscar preço: {e}")
        return False, 0

def colocar_ordem_compra(symbol, qty, price):
    tp = round(price * (1 + TP_PERC), 2)
    sl = round(price * (1 - SL_PERC), 2)

    print(f"\n💼 Enviando ordem de COMPRA ➝ QTY: {qty}, TP: {tp}, SL: {sl}")

    try:
        ordem = session.place_order(
            category="linear",
            symbol=symbol,
            side="Buy",
            order_type="Market",
            qty=str(qty),
            take_profit=str(tp),
            stop_loss=str(sl),
            time_in_force="GoodTillCancel",
        )
        print("✅ Ordem enviada com sucesso:", ordem)
    except Exception as e:
        print(f"❌ Erro ao enviar ordem: {e}")

def main():
    while True:
        agora = datetime.datetime.now(datetime.timezone.utc).isoformat()
        print(f"\n⏳ Analisando {PAIR} - {agora}")

        sinal, preco = analisar_mercado(PAIR)

        if sinal:
            colocar_ordem_compra(PAIR, QTY, preco)
        else:
            print(f"🔎 Sem sinal de compra no momento em {PAIR}.")

        print(f"\n⏰ Aguardando {INTERVALO} segundos para próxima análise...\n")
        time.sleep(INTERVALO)

if __name__ == "__main__":
    main()


