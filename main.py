# SukachBot CRYPTO PRO com entrada baseada em 4 a 12 indicadores + validação de direção
# Entradas apenas se houver pelo menos 1 indicador "forte" confirmado (RSI, EMAs, MACD, CCI ou ADX)
# Direção da vela confirmada como "Alta" ou "Baixa"

from flask import Flask
import os
import time
import random
import threading
import numpy as np
import pandas as pd
from pybit.unified_trading import HTTP
from datetime import datetime
import requests
from indicadores import analisar_indicadores
from estrutura_candle import detectar_direcao_candle

app = Flask(__name__)

api_key = os.getenv("BYBIT_API_KEY")
api_secret = os.getenv("BYBIT_API_SECRET")

session = HTTP(
    api_key=api_key,
    api_secret=api_secret,
    testnet=False
)

historico_resultados = []

MIN_INDICADORES = 4
INDICADORES_OBRIGATORIOS = ["RSI", "EMAs", "MACD", "CCI", "ADX"]

def ajustar_quantidade(par, usdt_alvo, alavancagem, preco_atual):
    try:
        info = session.get_instruments_info(category="linear", symbol=par)
        filtro = info["result"]["list"][0]["lotSizeFilter"]
        step = float(filtro["qtyStep"])
        min_qty = float(filtro["minOrderQty"])
        qty_bruta = (usdt_alvo * alavancagem) / preco_atual
        precisao = abs(int(round(-np.log10(step), 0)))
        qty_final = round(qty_bruta, precisao)
        if qty_final < min_qty:
            print(f"Quantidade abaixo do mínimo ({qty_final} < {min_qty})")
            return None
        return qty_final
    except Exception as e:
        print(f"Erro ao ajustar quantidade: {e}")
        return None

def aplicar_tp_sl(par, preco_entrada):
    take_profit = round(preco_entrada * 1.01, 4)
    stop_loss = round(preco_entrada * 0.997, 4)
    trailing_ativado = False
    sucesso = False

    for tentativa in range(3):
        try:
            posicoes = session.get_positions(category="linear", symbol=par)["result"]["list"]
            if posicoes and (
                posicoes[0].get("takeProfit") == str(take_profit) and
                posicoes[0].get("stopLoss") == str(stop_loss)
            ):
                print("TP/SL já definidos corretamente, sem alterações.")
                sucesso = True
                break

            atual = float(posicoes[0].get("markPrice", preco_entrada))
            lucro_atual = (atual - preco_entrada) / preco_entrada

            if lucro_atual > 0.006:
                novo_sl = round(atual * 0.997, 4)
                stop_loss = max(stop_loss, novo_sl)
                trailing_ativado = True

            response = session.set_trading_stop(
                category="linear",
                symbol=par,
                takeProfit=take_profit,
                stopLoss=stop_loss
            )

            if response.get("retCode") == 0:
                print(f"✅ TP/SL definidos: TP={take_profit} | SL={stop_loss} {'(Trailing SL ativo)' if trailing_ativado else ''}")
                sucesso = True
                break
            else:
                print(f"Erro ao aplicar TP/SL: {response}")
        except Exception as e:
            print(f"Falha ao aplicar TP/SL (tentativa {tentativa+1}): {e}")
            time.sleep(1)

    if not sucesso:
        print("⚠️ Não foi possível aplicar TP/SL após 3 tentativas. Nova tentativa em 15 segundos...")
        threading.Timer(15, aplicar_tp_sl, args=(par, preco_entrada)).start()


def verificar_condicoes_entrada(par, candles):
    resultado = analisar_indicadores(par, candles)
    total_confirmados = sum(resultado.values())
    confirmados = [k for k, v in resultado.items() if v]
    obrigatorios_ok = any(ind in confirmados for ind in INDICADORES_OBRIGATORIOS)

    direcao = detectar_direcao_candle(candles[-2], candles[-1])

    if direcao == "Neutro":
        print("⚪ Candle neutro detectado — ignorado.")
        return False, 0, direcao, resultado

    if total_confirmados >= MIN_INDICADORES and obrigatorios_ok:
        print(f"📈 Direção: {direcao} ({total_confirmados}/12 sinais confirmados)")
        return True, total_confirmados, direcao, resultado
    else:
        print(f"❌ Sinais insuficientes ou sem confirmador forte: {total_confirmados}/12")
        return False, total_confirmados, direcao, resultado


def monitorar_mercado():
    while True:
        try:
            pares_disponiveis = [
                "BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT", "MATICUSDT",
                "AVAXUSDT", "LINKUSDT", "TONUSDT", "FETUSDT", "ADAUSDT",
                "RNDRUSDT", "SHIB1000USDT"
            ]

            par = random.choice(pares_disponiveis)

            dados = session.get_kline(category="linear", symbol=par, interval="1", limit=100)
            candles = dados["result"]["list"]
            if not candles or len(candles) < 2:
                print(f"⚠️ Nenhum candle válido retornado para {par}, a saltar...")
                time.sleep(2)
                continue

            preco_atual = float(candles[-1][4])

            pode_entrar, confirmados, direcao, sinais = verificar_condicoes_entrada(par, candles)
            if not pode_entrar:
                time.sleep(2)
                continue

            usdt_alvo = 3
            alavancagem = 2

            try:
                wallet = session.get_wallet_balance(accountType="UNIFIED")
                coins = wallet.get("result", {}).get("list", [])[0].get("coin", [])

                saldo_total = 0
                for c in coins:
                    nome_moeda = c.get("moeda") or c.get("coin")
                    if nome_moeda == "USDT":
                        saldo_str = c.get("availableToWithdraw") or c.get("walletBalance") or c.get("equity") or "0"
                        saldo_total = float(saldo_str.replace(",", "."))
                        break

                print(f"💰 Saldo USDT aprovado: {saldo_total}")

            except Exception as e:
                print(f"❌ Erro ao obter saldo disponível em USDT: {e}")
                saldo_total = 0

            if saldo_total < usdt_alvo:
                print(f"❌ Saldo insuficiente ({saldo_total} < {usdt_alvo}) — não vai entrar.")
                time.sleep(2)
                continue

            qty = ajustar_quantidade(par, usdt_alvo, alavancagem, preco_atual)
            if qty is None:
                time.sleep(2)
                continue

            session.place_order(
                category="linear",
                symbol=par,
                side="Buy" if direcao == "Alta" else "Sell",
                orderType="Market",
                qty=qty,
                leverage=alavancagem
            )

            historico_resultados.append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {par} | Entrada {direcao} | Qty={qty}")
            print(f"🚀 ENTRADA REAL: {par} | Qty: {qty} | Preço: {preco_atual} | Direção: {direcao}")
            time.sleep(5)
            aplicar_tp_sl(par, preco_atual)

        except Exception as e:
            print(f"Erro no monitoramento: {e}")
        time.sleep(2)

if __name__ == "__main__":
    threading.Thread(target=monitorar_mercado, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

