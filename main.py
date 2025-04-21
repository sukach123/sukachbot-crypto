def analisar_entradas(par):
    url = f"https://api.bybit.com/v5/market/kline"
    params = {
        "category": "linear",
        "symbol": par,
        "interval": "1",  # 1 minuto
        "limit": 200
    }
    response = requests.get(url, params=params)

    if response.status_code == 200:
        try:
            # Obter os dados e criar DataFrame dinamicamente
            data = response.json().get("result", {}).get("list", [])
            if data:
                df = pd.DataFrame(data)

                # Exibir colunas para depuração
                print(f"Colunas disponíveis: {df.columns}")

                # Verificar se a coluna 'close' está disponível
                if 'close' in df.columns:
                    df['close'] = df['close'].astype(float)

                    # Calcular indicadores
                    sinais = calcular_indicadores(df)

                    # Avaliar os sinais
                    if len(sinais) >= 2:
                        print(f"✅ Sinal para {par}: {', '.join(sinais)}")
                        return True
                    else:
                        print(f"❌ Sinal para {par}: {', '.join(sinais)}")
                        return False
                else:
                    print(f"❌ Coluna 'close' não encontrada para {par}. Verifique os dados retornados.")
                    return False
            else:
                print(f"❌ Dados indisponíveis para {par}.")
                return False
        except Exception as e:
            print(f"Erro ao processar dados de {par}: {e}")
            return False
    else:
        print(f"❌ Erro na requisição para {par}. Status: {response.status_code}")
        return False
