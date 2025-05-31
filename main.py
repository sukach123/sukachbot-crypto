import pandas as pd
import numpy as np
import ta

def calcular_indicadores(df):
    # Calcular EMAs
    df['EMA10'] = ta.trend.EMAIndicator(df['close'], window=10).ema_indicator()
    df['EMA20'] = ta.trend.EMAIndicator(df['close'], window=20).ema_indicator()
    # MACD e Sinal
    macd = ta.trend.MACD(df['close'])
    df['MACD'] = macd.macd()
    df['SINAL'] = macd.macd_signal()
    # CCI
    df['CCI'] = ta.trend.CCIIndicator(df['high'], df['low'], df['close'], window=20).cci()
    # ADX
    df['ADX'] = ta.trend.ADXIndicator(df['high'], df['low'], df['close'], window=14).adx()
    # ATR
    df['ATR'] = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'], window=14).average_true_range()
    # Volume explosivo (volume > 1.5 média 20)
    df['volume_media20'] = df['volume'].rolling(window=20).mean()
    df['volume_explosivo'] = df['volume'] > 1.5 * df['volume_media20']
    return df

def verificar_entrada_por_candle(df, idx):
    # Para candle índice idx, checar sinais:
    if idx < 20:
        return None  # não tem dados suficientes

    row = df.iloc[idx]
    prev = df.iloc[idx - 1]
    ultimos5 = df.iloc[idx-5:idx+1]
    ultimos20 = df.iloc[idx-20:idx+1]

    corpo = abs(row["close"] - row["open"])
    volatilidade = ultimos20["high"].max() - ultimos20["low"].min()
    media_atr = ultimos20["ATR"].mean()
    nao_lateral = volatilidade > (2 * media_atr)

    sinal_1 = row["EMA10"] > row["EMA20"]  # direção ema
    sinal_2 = row["MACD"] > row["SINAL"]
    sinal_3 = row["CCI"] > 0
    sinal_4 = row["ADX"] > 20
    sinal_5 = row["volume_explosivo"]
    sinal_6 = corpo > (ultimos5["close"].max() - ultimos5["low"].min())
    sinal_7 = nao_lateral

    sinais_fortes = [sinal_1, sinal_2, sinal_3, sinal_4, sinal_7]

    extra_1 = prev["close"] > prev["open"]
    extra_2 = (row["high"] - row["close"]) < corpo
    sinais_extras = [sinal_5, sinal_6, extra_1, extra_2]

    total_fortes = sum(sinais_fortes)
    total_extras = sum(sinais_extras)

    # Regras de entrada
    if total_fortes >= 5 or (total_fortes >= 4 and total_extras >= 1):
        # Bloquear colisão das EMAs (diferença menor que 0.01% do preço)
        preco_atual = row["close"]
        diferenca_ema = abs(row["EMA10"] - row["EMA20"])
        limite_colisao = preco_atual * 0.0001
        if diferenca_ema < limite_colisao:
            return None  # Bloqueado
        else:
            return "Buy" if row["EMA10"] > row["EMA20"] else "Sell"
    else:
        return None

def main():
    # Simulação: gerar 300 candles fictícios (substituir por dados reais)
    np.random.seed(42)
    tamanho = 300
    timestamps = pd.date_range(start='2025-01-01', periods=tamanho, freq='H')
    openp = np.random.uniform(100, 110, tamanho)
    highp = openp + np.random.uniform(0, 5, tamanho)
    lowp = openp - np.random.uniform(0, 5, tamanho)
    closep = lowp + np.random.uniform(0, (highp - lowp), tamanho)
    volume = np.random.uniform(1000, 5000, tamanho)

    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': openp,
        'high': highp,
        'low': lowp,
        'close': closep,
        'volume': volume
    })

    df = calcular_indicadores(df)

    # Para cada candle, aplicar a função de decisão
    df['entrada'] = [verificar_entrada_por_candle(df, i) for i in range(len(df))]

    # Resultados
    entradas_totais = df['entrada'].notnull().sum()
    buys = (df['entrada'] == 'Buy').sum()
    sells = (df['entrada'] == 'Sell').sum()

    print(f"\nTotal de candles: {len(df)}")
    print(f"Entradas totais encontradas: {entradas_totais}")
    print(f"Buy: {buys} | Sell: {sells}")

    # Mostrar últimas entradas detectadas
    print("\nÚltimas entradas detectadas:")
    print(df.loc[df['entrada'].notnull(), ['timestamp', 'close', 'entrada']].tail(10))

if __name__ == "__main__":
    main()


