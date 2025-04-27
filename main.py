def verificar_entrada(df):
    row = df.iloc[-1]
    prev = df.iloc[-2]
    ultimos5 = df.iloc[-5:]
    ultimos20 = df.iloc[-20:]

    corpo = abs(row["close"] - row["open"])
    volatilidade = ultimos20["high"].max() - ultimos20["low"].min()
    media_atr = ultimos20["ATR"].mean()
    nao_lateral = volatilidade > (2 * media_atr)

    sinais_fortes = [
        row["EMA10"] > row["EMA20"] or row["EMA10"] < row["EMA20"],
        row["MACD"] > row["SINAL"],
        row["CCI"] > 0,
        row["ADX"] > 20,
        row["volume_explosivo"],
        corpo > ultimos5["close"].max() - ultimos5["low"].min(),
        nao_lateral
    ]
    sinais_extras = [
        prev["close"] > prev["open"],
        (row["high"] - row["close"]) < corpo
    ]

    total_confirmados = sum(sinais_fortes) + sum(sinais_extras)

    if sum(sinais_fortes) >= 7:
        if row["EMA10"] > row["EMA20"]:
            return "Buy"
        elif row["EMA10"] < row["EMA20"]:
            return "Sell"
        else:
            print(f"🔎 {row['timestamp']} | {total_confirmados}/9 sinais confirmados | Entrada bloqueada ❌ | Motivo: EMA10 colada com EMA20 (sem tendência clara)")
            return None
    else:
        print(f"🔎 {row['timestamp']} | {total_confirmados}/9 sinais confirmados | Entrada bloqueada ❌ | Motivo: Menos de 7 sinais fortes")
        return None
