from pybit import HTTP
import time
from datetime import datetime

# Configurações API testnet Bybit
API_KEY = "sua_api_key_aqui"
API_SECRET = "seu_api_secret_aqui"

# Conexão com testnet linear futures
session = HTTP(
    endpoint="https://api-testnet.bybit.com",
    api_key=API_KEY,
    api_secret=API_SECRET,
    spot=False
)

symbol = "DOGEUSDT"
qty = 10  # quantidade de contratos, ajustar conforme saldo
tp_percent = 0.004  # 0.4% de Take Profit
sl_percent = 0.004  # 0.4% de Stop Loss

def analisar_mercado():
    """
    Exemplo simples de análise:
    - Compra se preço fechar maior que abrir (vela de alta)
    - Venda se preço fechar menor que abrir (vela de baixa)
    - Neutro caso contrário
    """
    try:
        # Pega o candle mais recente (1 minuto)
        kline = session.query_kline(symbol=symbol, interval="1", limit=1)
        candle = kline['result'][0]

        open_price = float(candle['open'])
        close_price = float(candle['close'])

        if close_price > open_price:
            return "buy"
        elif close_price < open_price:
            return "sell"
        else:
            return "neutral"

    except Exception as e:
        print("Erro na análise de mercado:", e)
        return "neutral"

def enviar_ordem_buy():
    try:
        ticker = session.latest_information_for_symbol(symbol=symbol)
        last_price = float(ticker['result'][0]['last_price'])
        tp = round(last_price * (1 + tp_percent), 8)
        sl = round(last_price * (1 - sl_percent), 8)

        print(f"[{datetime.utcnow()}] Sinal BUY detectado em {symbol} - Preço: {last_price}")
        print(f"Enviando ordem MARKET Buy: QTY={qty}, TP={tp}, SL={sl}")

        resposta = session.place_active_order(
            category="linear",
            symbol=symbol,
            side="Buy",
            order_type="Market",
            qty=qty,
            take_profit=str(tp),
            stop_loss=str(sl),
            time_in_force="GoodTillCancel"
        )
        print("Ordem enviada com sucesso:", resposta)
    except Exception as e:
        print("Erro ao enviar ordem BUY:", e)

def enviar_ordem_sell():
    try:
        ticker = session.latest_information_for_symbol(symbol=symbol)
        last_price = float(ticker['result'][0]['last_price'])
        tp = round(last_price * (1 - tp_percent), 8)
        sl = round(last_price * (1 + sl_percent), 8)

        print(f"[{datetime.utcnow()}] Sinal SELL detectado em {symbol} - Preço: {last_price}")
        print(f"Enviando ordem MARKET Sell: QTY={qty}, TP={tp}, SL={sl}")

        resposta = session.place_active_order(
            category="linear",
            symbol=symbol,
            side="Sell",
            order_type="Market",
            qty=qty,
            take_profit=str(tp),
            stop_loss=str(sl),
            time_in_force="GoodTillCancel"
        )
        print("Ordem enviada com sucesso:", resposta)
    except Exception as e:
        print("Erro ao enviar ordem SELL:", e)

def main():
    while True:
        sinal = analisar_mercado()

        if sinal == "buy":
            enviar_ordem_buy()
        elif sinal == "sell":
            enviar_ordem_sell()
        else:
            print(f"[{datetime.utcnow()}] Sinal NEUTRO. Nenhuma ordem enviada.")

        print("Aguardando 60 segundos para próxima análise...\n")
        time.sleep(60)

if __name__ == "__main__":
    main()
