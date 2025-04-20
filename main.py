# --- CONFIGURAÇÕES GERAIS ---
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")

if not BYBIT_API_KEY or not BYBIT_API_SECRET:
    raise EnvironmentError("Erro: As variáveis de ambiente BYBIT_API_KEY e BYBIT_API_SECRET não estão configuradas.")

session = HTTP(
    api_key=BYBIT_API_KEY,
    api_secret=BYBIT_API_SECRET,
    testnet=False
)

# --- TELEGRAM ---
BOT_TOKEN = "7830564079:AAER2NNtWfoF0Nsv94Z_WXdPAXQbdsKdcmk"
CHAT_ID = "1407960941"

if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("Erro: O BOT_TOKEN ou CHAT_ID do Telegram não está configurado corretamente.")

# --- ENVIO DE MENSAGENS PARA O TELEGRAM ---
def enviar_telegram_mensagem(mensagem):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        print("Mensagem enviada ao Telegram com sucesso.")
    except requests.exceptions.RequestException as e:
        print("Erro ao enviar mensagem para Telegram:", e)
        raise

# --- Lógica de Stop Loss e Take Profit ---
def calcular_tp_sl(preco_entrada, direcao):
    try:
        if direcao.lower() == "buy":
            tp = preco_entrada * (1 + TAKE_PROFIT_PORCENTAGEM)
            sl = preco_entrada * (1 - STOP_LOSS_PORCENTAGEM)
        elif direcao.lower() == "sell":
            tp = preco_entrada * (1 - TAKE_PROFIT_PORCENTAGEM)
            sl = preco_entrada * (1 + STOP_LOSS_PORCENTAGEM)
        else:
            raise ValueError("Direção inválida. Use 'buy' ou 'sell'.")
        return round(tp, 4), round(sl, 4)
    except Exception as e:
        print("Erro ao calcular TP e SL:", e)
        raise

# --- EXECUTAR ORDEM NA BYBIT ---
def executar_ordem(par, preco_entrada, direcao, preco_atual):
    try:
        tp, sl = calcular_tp_sl(preco_entrada if preco_entrada else preco_atual, direcao)
        quantidade = round((VALOR_ENTRADA_USDT * ALAVANCAGEM) / (preco_entrada if preco_entrada else preco_atual), 3)

        print(f"Executando ordem {direcao.upper()} em {par} | TP: {tp} | SL: {sl} | Quantidade: {quantidade}")

        response = session.place_order(
            category="linear",
            symbol=par,
            side="Buy" if direcao.lower() == "buy" else "Sell",
            order_type="Market",
            qty=quantidade,
            take_profit=tp,
            stop_loss=sl,
            time_in_force="GoodTillCancel",
            reduce_only=False
        )
        print("Resposta da API:", response)

        hora = datetime.utcnow().strftime("%H:%M:%S")
        mensagem = (
            f"✨ *ENTRADA EXECUTADA!* ✨\n"
            f"🛠 *Par:* `{par}`\n"
            f"📈 *Direção:* `{direcao.upper()}`\n"
            f"💵 *Entrada:* `{preco_entrada:.4f}`\n"
            f"🎯 *TP:* `{tp:.4f}` | 🛡 *SL:* `{sl:.4f}`\n"
            f"💰 *Qtd:* `{quantidade}` | ⚖️ *Alavancagem:* `{ALAVANCAGEM}x`\n"
            f"⏱ *Hora:* `{hora}`"
        )
        enviar_telegram_mensagem(mensagem)
    except ValueError as ve:
        print("Erro de validação:", ve)
        enviar_telegram_mensagem(f"❌ Erro de validação: {ve}")
    except Exception as e:
        print("Erro ao executar ordem:", e)
        enviar_telegram_mensagem(f"❌ Erro ao executar ordem em {par}: {str(e)}")


