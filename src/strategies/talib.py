import pandas as pd
import talib as ta
import numpy as np

def getEMAMACDtalib(stock_data: pd.DataFrame, fast_window=7, slow_window=25, signal_window=7) -> bool:
    """
    Estratégia de negociação antecipada baseada em EMAs, MACD e gradientes utilizando TA-Lib.
    
    A função utiliza o DataFrame stock_data do BinanceRobot, que contém os dados históricos
    com a coluna 'close_price' para os preços de fechamento.
    
    Parâmetros:
        stock_data (pd.DataFrame): DataFrame contendo os dados históricos do BinanceRobot.
        fast_window (int): Janela da EMA rápida. Padrão 7.
        slow_window (int): Janela da EMA lenta. Padrão 25.
        signal_window (int): Janela da linha de sinal do MACD. Padrão 7.
    
    Retorna:
        Booleano: True se o último sinal for de compra (1); False para venda ou nenhum sinal.
    """
    if stock_data is None or stock_data.empty:
        print("Erro: DataFrame stock_data está vazio ou None")
        return False
        
    if 'close_price' not in stock_data.columns:
        print("Erro: Coluna 'close_price' não encontrada no DataFrame")
        return False
        
    df = stock_data.copy()
    # Converter explicitamente para float64
    close_data = df['close_price'].astype('float64').values
    
    # Calcular as EMAs com TA-Lib
    ema_fast = ta.EMA(close_data, timeperiod=fast_window)
    ema_slow = ta.EMA(close_data, timeperiod=slow_window)
    
    # Calcular MACD e a linha de sinal com TA-Lib
    macd, signal_line, _ = ta.MACD(close_data, fastperiod=fast_window, slowperiod=slow_window, signalperiod=signal_window)
    
    # Converter arrays para Series com o mesmo índice do DataFrame original
    ema_fast_series = pd.Series(ema_fast, index=df.index)
    ema_slow_series = pd.Series(ema_slow, index=df.index)
    macd_series = pd.Series(macd, index=df.index)
    signal_line_series = pd.Series(signal_line, index=df.index)
    
    # Calcular gradientes (diferença entre valores consecutivos)
    ema_fast_gradiente = ema_fast_series.diff()
    ema_slow_gradiente = ema_slow_series.diff()
    macd_diff_gradiente = macd_series.diff()
    
    # Adicionar os indicadores ao DataFrame original
    df['EMA_rapida'] = ema_fast_series
    df['EMA_lenta'] = ema_slow_series
    df['MACD'] = macd_series
    df['Signal_Line'] = signal_line_series
    df['EMA_rapida_gradiente'] = ema_fast_gradiente
    df['EMA_lenta_gradiente'] = ema_slow_gradiente
    df['MACD_diff_gradiente'] = macd_diff_gradiente
    
    # Lógica para geração dos sinais
    condicao_compra = (ema_fast_series < ema_slow_series) & (macd_series > signal_line_series)
    condicao_venda = (ema_fast_series > ema_slow_series) & (macd_series < signal_line_series)
    
    # Detecta os cruzamentos únicos
    cruzamento_compra = condicao_compra & ~(condicao_compra.shift(1, fill_value=False))
    cruzamento_venda = condicao_venda & ~(condicao_venda.shift(1, fill_value=False))
    
    # Inicializa a coluna de sinais e aplica os cruzamentos
    df['point_signal'] = 0
    df.loc[cruzamento_compra, 'point_signal'] = 1
    df.loc[cruzamento_venda, 'point_signal'] = -1
    df['point_signal'] = df['point_signal'].replace(0, np.nan).ffill().fillna(0)
    
    # Retorna True se o último sinal for de compra (1), convertendo explicitamente para bool Python
    return bool(df['point_signal'].iloc[-1] == 1)

if __name__ == "__main__":
    # Exemplo de uso:
    # Suponha que 'stock_data' seja um DataFrame com os dados históricos,
    # incluindo a coluna 'close_price' (ou 'close').
    # Exemplo: stock_data = pd.read_csv('seu_arquivo.csv', parse_dates=['open_time'])
    resultado = getEMAMACDtalib(stock_data= pd.DataFrame, fast_window=7, slow_window=25, signal_window=7)
    print("Sinal de compra:", resultado)
