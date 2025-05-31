from pybit.unified_trading import HTTP
import time
import datetime
import pytz

# Configurações
API_KEY = "SUA_API_KEY"
API_SECRET = "SEU_API_SECRET"
PAIR = "BTCUSDT"
QTY = 0.01  # quantidade para ordem
TP_PERC = 0.015  # 1.5% take profit
SL_PERC = 0.003  # 0.3% stop loss
INTERVALO = 60  # segundos

# Sessão Bybit (Testnet)
session = HTTP(
    testnet=True,
    api_key=API_KEY,
    api_secret=API_SECRET,
)

def analisar_mercado(symbol):
    """
    Simples análise: entra sempre que rodar (só para fins de teste).
    Aqui você pode incluir lógica real com indicadores.
    """
    try:
        ticker = session.get_ticker(category="linear", symbol=symbol)
        price = float(ticker["result"]["list"][0]["lastPrice"])
        print(f"\n🔎 Sinal BUY detectado em {symbol} - Preço: {price}")
        return True, price
    except Exception as e:
        print(f"Erro ao buscar preço: {e}")
        return False, 0

def colocar_ordem_compra(symbol, qty, tp_perc, sl_perc):
    try:
        ticker = session.get_ticker(category="linear", symbol=symbol)
        price = float(ticker["result"]["list"][0]["lastPrice"])

        tp_price = price * (1 + tp_perc)
        sl_price = price * (1 - sl_perc)

        ordem = session.place_order(
            category="linear",
            symbol=symbol,
            side="Buy",
            order_type="Market",
            qty=qty,
            take_profit=round(tp_price, 8),
            stop_loss=round(sl_price, 8),
            time_in_force="GoodTillCancel"
        )
        print(f"✅ Ordem de COMPRA enviada: {ordem}")
    except Exception as e:
        print(f"❌ Erro ao enviar ordem: {e}")

def main():
    while True:
        agora = datetime.datetime.now(pytz.UTC)
        print(f"\n⏳ Analisando {PAIR} - {agora.isoformat()}")

        sinal, preco = analisar_mercado(PAIR)

        if sinal:
            colocar_ordem_compra(PAIR, QTY, TP_PERC, SL_PERC)
        else:
            print(f"🔎 Sem sinal de compra no momento em {PAIR}.")

        print(f"\n⏰ Aguardando {INTERVALO} segundos para próxima análise...\n")
        time.sleep(INTERVALO)

if __name__ == "__main__":
    main()

