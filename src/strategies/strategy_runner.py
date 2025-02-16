#from .moving_average_antecipation import getMovingAverageAntecipationTradeStrategy
from .moving_average import getMovingAverageTradeStrategy
from .talib import getEMAMACDtalib

def runStrategies(stock_data, volatility_factor=0.5, fallback_activated=True):
    """
    Executa todas as estratégias disponíveis na ordem:
    1. EMA MACD (principal)
    2. MA Antecipation (secundária)
    3. Moving Average (fallback)
    """
    # Primeira estratégia: EMA MACD
    ema_macd_decision = getEMAMACDtalib(stock_data) 
    if ema_macd_decision is not None:
        print('Decisão baseada na estratégia EMA MACD')
        return ema_macd_decision
        
    # Segunda estratégia: MA Antecipation
    # maant_trade_decision = getMovingAverageAntecipationTradeStrategy(stock_data, volatility_factor)
    # if maant_trade_decision is not None:
    #     print('Decisão baseada na estratégia MA Antecipation')
    #     return maant_trade_decision

    
    # Fallback strategy
    if fallback_activated:
        print('Estratégias principais inconclusivas\nExecutando estratégia de fallback...')
        ma_trade_decision = getMovingAverageTradeStrategy(stock_data)
        return ma_trade_decision
    
    return None

def run_all_strategies(bot):
    """
    Função auxiliar para executar todas as estratégias a partir do objeto bot
    """
    return runStrategies(
        stock_data=bot.stock_data,
        volatility_factor=bot.volatility_factor,
        fallback_activated=bot.fallback_activated
    )

