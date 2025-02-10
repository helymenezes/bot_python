import pandas as pd
import numpy as np
from indicators.Indicators import Indicators

# Estratégia de Média Móvel Exponencial (EMA) e MACD

def getEMAMACDTradeStrategy(stock_data: pd.DataFrame, fast_window = 7, slow_window = 25, signal_window = 7):#stock_data
    """
    Estratégia de negociação baseada em EMA e MACD
    """
    # Cria instância dos indicadores
    indicators = Indicators()
    
    # Calcula EMA de 9 e 21 períodos
    stock_data['ema_9'] = indicators.calculate_ema(stock_data['close_price'], 9)
    stock_data['ema_21'] = indicators.calculate_ema(stock_data['close_price'], 21)
    
    # Calcula MACD
    stock_data['macd_line'], stock_data['signal_line'] = indicators.calculate_macd(stock_data['close_price'])
    
    # Inicializa pontos de sinal
    stock_data["point_signal"] = 0
    
    # Define sinais de compra e venda
    stock_data.loc[(stock_data['ema_9'] > stock_data['ema_21']) & 
                   (stock_data['macd_line'] > stock_data['signal_line']), "point_signal"] = 1
    
    stock_data.loc[(stock_data['ema_9'] < stock_data['ema_21']) & 
                   (stock_data['macd_line'] < stock_data['signal_line']), "point_signal"] = -1
    
    # Preenche valores nulos
    stock_data["point_signal"] = stock_data["point_signal"].replace(0, np.nan).bfill().fillna(0)
    
    # Retorna True (bool nativo) para sinal de compra no último período
    return bool(stock_data["point_signal"].iloc[-1] == 1)


