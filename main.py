from flask import Flask
import os
from pybit.unified_trading import HTTP

app = Flask(__name__)

# Lê as variáveis da Railway (já colocaste lá)
api_key = os.getenv("BYBIT_API_KEY")
api_secret = os.getenv("BYBIT_API_SECRET")

# Conexão com a Bybit
session = HTTP(
    api_key=api_key,
    api_secret=api_secret
)

@app.route("/")
def home():
    try:
        balance = session.get_wallet_balance(accountType="UNIFIED")
        return f"SukachBot CRYPTO ligado à Bybit! 🚀<br><br>Saldo atual: {balance}"
    except Exception as e:
        return f"Erro ao ligar à Bybit: {e}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
