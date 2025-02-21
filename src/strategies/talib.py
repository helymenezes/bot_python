import pandas as pd
import talib as ta

def sinal_compra_venda(stock_data: pd.DataFrame) -> bool:
    """
    Função para melhorar os sinais de compra e venda utilizando TA-Lib.
    
    Parâmetros:
        stock_data (pd.DataFrame): DataFrame contendo, no mínimo, a coluna 'close_price'.
        
    Retorna:
        bool: True se o último sinal for de compra (1) e False caso contrário.
    """
    # Verificação de entrada: DataFrame não vazio e coluna 'close_price' existente
    if stock_data.empty or 'close_price' not in stock_data.columns:
        print("Erro: DataFrame vazio ou coluna 'close_price' não encontrada.")
        return False

    # Cálculo das médias exponenciais (EMAs)
    stock_data['EMA7'] = ta.EMA(stock_data['close_price'], timeperiod=7)
    stock_data['EMA25'] = ta.EMA(stock_data['close_price'], timeperiod=25)
    stock_data['EMA99'] = ta.EMA(stock_data['close_price'], timeperiod=99)

    # Cálculo do MACD com os parâmetros especificados
    macd, signal_line, _ = ta.MACD(stock_data['close_price'], fastperiod=7, slowperiod=25, signalperiod=7)
    stock_data['MACD'] = pd.Series(macd, index=stock_data.index)
    stock_data['Signal_Line'] = pd.Series(signal_line, index=stock_data.index)

    # Definição da condição de mercado com base na relação entre as EMAs
    # Valorização: EMA7 > EMA25 > EMA99; Desvalorização: EMA7 < EMA25 < EMA99
    stock_data['market_condition'] = None
    cond_valorizacao = (stock_data['EMA7'] > stock_data['EMA25']) & (stock_data['EMA25'] > stock_data['EMA99'])
    cond_desvalorizacao = (stock_data['EMA7'] < stock_data['EMA25']) & (stock_data['EMA25'] < stock_data['EMA99'])
    stock_data.loc[cond_valorizacao, 'market_condition'] = 'valorizacao'
    stock_data.loc[cond_desvalorizacao, 'market_condition'] = 'desvalorizacao'

    # Inicialização da coluna de sinais: 1 para compra, -1 para venda, 0 para sem sinal
    stock_data['signal'] = 0

    # Estratégia para mercado em valorização: cruzamento da EMA7 com a EMA25
    # Sinal de compra: quando EMA7 cruza para cima da EMA25
    compra_valorizacao = cond_valorizacao & (stock_data['EMA7'] > stock_data['EMA25']) & \
                         (stock_data['EMA7'].shift(1) <= stock_data['EMA25'].shift(1))
    stock_data.loc[compra_valorizacao, 'signal'] = 1

    # Sinal de venda: quando EMA7 cruza para baixo da EMA25
    venda_valorizacao = cond_valorizacao & (stock_data['EMA7'] < stock_data['EMA25']) & \
                        (stock_data['EMA7'].shift(1) >= stock_data['EMA25'].shift(1))
    stock_data.loc[venda_valorizacao, 'signal'] = -1

    # Estratégia para mercado em desvalorização: baseada no MACD
    # Sinal de compra: quando EMA7 < EMA25 e MACD > Signal Line
    compra_desvalorizacao = cond_desvalorizacao & (stock_data['EMA7'] < stock_data['EMA25']) & \
                            (stock_data['MACD'] > stock_data['Signal_Line'])
    # Garante que o sinal de compra não se repita consecutivamente
    stock_data.loc[compra_desvalorizacao & ((stock_data['signal'].shift(1) != 1) | (stock_data['signal'].shift(1).isna())), 'signal'] = 1

    # Sinal de venda: quando EMA7 > EMA25 e MACD < Signal Line
    venda_desvalorizacao = cond_desvalorizacao & (stock_data['EMA7'] > stock_data['EMA25']) & \
                           (stock_data['MACD'] < stock_data['Signal_Line'])
    # Garante que o sinal de venda não se repita consecutivamente
    stock_data.loc[venda_desvalorizacao & ((stock_data['signal'].shift(1) != -1) | (stock_data['signal'].shift(1).isna())), 'signal'] = -1

    # Preencher os sinais de forma contínua, propagando o último sinal válido
    stock_data['signal'] = stock_data['signal'].replace(to_replace=0, method='ffill')

    # Retorna True se o último sinal for de compra (1) e False caso contrário
    final_signal = stock_data['signal'].iloc[-1]
    return True if final_signal == 1 else False

# Exemplo de uso:
# df = pd.read_csv("dados_acoes.csv")  # Supondo que 'close_price' esteja presente no CSV
# resultado = sinal_compra_venda(df)
# print("Sinal final é de compra?" , resultado)
