import pandas as pd
import numpy as np
from indicators.Indicators import Indicators

def getEMAMACDTradeStrategy(stock_data: pd.DataFrame, volatility_factor: float = 1.0, fast_window=7, slow_window=25, signal_window=7) -> bool:
    """
    Estratégia de negociação antecipada que combina:
      - Indicadores EMA e MACD para identificar cruzamentos.
      - Cálculo de gradientes das EMAs e diferença atual entre elas, 
        permitindo antecipar o momento de compra e venda.
    
    Parâmetros:
      - stock_data: DataFrame contendo pelo menos a coluna 'close_price' 
                    (e opcionalmente 'volatility').
      - volatility_factor: Fator multiplicador para filtrar a diferença atual entre EMAs.
      - fast_window, slow_window, signal_window: janelas para o cálculo dos indicadores.
      
    Retorna:
      - Booleano: True se o sinal final for de compra; False para venda ou nenhum sinal.
    """
    indicators = Indicators()
    
    # --- Cálculo dos Indicadores ---
    # Calcula a EMA rápida e a EMA lenta
    stock_data['ema_fast'] = indicators.calculate_ema(stock_data['close_price'], fast_window)
    stock_data['ema_slow'] = indicators.calculate_ema(stock_data['close_price'], slow_window)
    
    # Calcula MACD e sua linha de sinal
    stock_data['macd_line'], stock_data['signal_line'] = indicators.calculate_macd(stock_data['close_price'])

    
    # --- Condições de Cruzamento ---
    # Sinal básico de compra: EMA rápida acima da lenta e MACD acima da linha de sinal
    buy_condition = (stock_data['ema_fast'] > stock_data['ema_slow']) & (stock_data['macd_line'] > stock_data['signal_line'])
    # Sinal básico de venda: EMA rápida abaixo da lenta e MACD abaixo da linha de sinal
    sell_condition = (stock_data['ema_fast'] > stock_data['ema_slow']) & (stock_data['macd_line'] < stock_data['signal_line'])
    
    # --- Cálculo dos Gradientes das EMAs ---
    # Para calcular o gradiente, garantimos que há linhas suficientes
    if len(stock_data) < 3:
        # Dados insuficientes para gradiente; sem sinal
        return False
    
    # Utiliza o último valor e um valor anterior (a 3 períodos atrás) para suavizar possíveis ruídos
    last_ema_fast = stock_data['ema_fast'].iloc[-1]
    prev_ema_fast = stock_data['ema_fast'].iloc[-3]
    last_ema_slow = stock_data['ema_slow'].iloc[-1]
    prev_ema_slow = stock_data['ema_slow'].iloc[-3]
    
    fast_gradient = last_ema_fast - prev_ema_fast
    slow_gradient = last_ema_slow - prev_ema_slow
    current_difference = abs(last_ema_fast - last_ema_slow)
    
    # --- Obtenção da Volatilidade ---
    # Se a coluna 'volatility' existir, usa o penúltimo valor; caso contrário, define um padrão
    if 'volatility' in stock_data.columns and len(stock_data) >= 2:
        last_volatility = stock_data['volatility'].iloc[-2]
    else:
        # Se não houver volatilidade definida, usa a diferença atual (evitando divisão por zero)
        last_volatility = current_difference if current_difference != 0 else 1.0
    
    # --- Regra de Decisão Integrada ---
    # Apenas considera sinais se as médias estiverem "próximas", isto é,
    # se a diferença atual for menor que (volatilidade * fator)
    trade_signal = 0  # 1 para compra, -1 para venda, 0 para nenhum sinal
    if current_difference < volatility_factor * last_volatility:
        # Sinal de compra: condições de cruzamento e gradiente consistente (subindo)
        if buy_condition.iloc[-1] and (fast_gradient > 0 and fast_gradient > slow_gradient):
            trade_signal = 1
        # Sinal de venda: condições de cruzamento e gradiente consistente (descendo)
        elif sell_condition.iloc[-1] and (fast_gradient < 0 and fast_gradient < slow_gradient):
            trade_signal = -1
        else:
            trade_signal = 0
    else:
        trade_signal = 0

    # --- Registro (Opcional) ---
    # Armazena o sinal final e os valores de gradiente e diferença no DataFrame para referência
    stock_data["point_signal"] = trade_signal
    stock_data["fast_gradient"] = np.nan
    stock_data["slow_gradient"] = np.nan
    stock_data["current_difference"] = np.nan
    stock_data.loc[stock_data.index[-1], "fast_gradient"] = fast_gradient
    stock_data.loc[stock_data.index[-1], "slow_gradient"] = slow_gradient
    stock_data.loc[stock_data.index[-1], "current_difference"] = current_difference
    
    # --- Retorno da Estratégia ---
    # Retorna True se o sinal for de compra (1); caso contrário, retorna False.
    return trade_signal == 1
