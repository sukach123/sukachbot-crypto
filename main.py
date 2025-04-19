from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "SukachBot CRYPTO online e pronto para enviar sinais! 🚀"

if __name__ == "__main__":
app.run(host="0.0.0.0", port=3000) 
