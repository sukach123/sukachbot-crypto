from flask import Flask
import os
from pybit.unified_trading import HTTP

app = Flask(__name__)

# TESTE DIRETO: Inserir chaves diretamente no código (vamos apagar depois!)
api_key = "SA4LOLcNBxaNbL1SJ6"
api_secret = "MMJjpHKUr9Hb94cpZ87ysTd4yQLm0VvL2al4"

session = HTTP(
    api_key=api_key,
    api_secret=api_secret,
    testnet=False
)

@app.route("/")
def home():
    return "SukachBot CRYPTO online e pronto para enviar sinais! 🚀"

@app.route("/saldo")
def saldo():
    try:
        response = session.get_wallet_balance(accountType="UNIFIED")
        coins = response["result"]["list"][0]["coin"]
        output = "<h2>Saldo Atual:</h2><ul>"
        for coin in coins:
            balance = float(coin["availableToWithdraw"])
            if balance > 0:
                output += f"<li>{coin['coin']}: {balance}</li>"
        output += "</ul>"
        return output or "Sem saldo disponível."
    except Exception as e:
        return f"Erro ao obter saldo: {str(e)}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# Lista de pares para análise futura
pares = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "MATICUSDT",
    "AVAXUSDT", "LINKUSDT", "TONUSDT", "FETUSDT", "ADAUSDT",
    "RNDRUSDT", "SHIBUSDT"
]
