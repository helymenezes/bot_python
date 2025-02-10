# indicators/Indicators.py
import pandas as pd
import numpy as np
from .rsi import rsi
from .macd import macd

class Indicators:
    @staticmethod
    def getRSI(series, window=14):
        return rsi(series, window, last_only=True)

    @staticmethod
    def getMACD(series, fast_window=12, slow_window=26, signal_window=9):
        return macd(series, fast_window, slow_window, signal_window)

    @staticmethod
    def calculate_ema(prices, period):
        """
        Calcula o EMA (Exponential Moving Average) para uma série de preços
        """
        return prices.ewm(span=period, adjust=False).mean()

    @staticmethod
    def calculate_macd(prices):
        """
        Calcula o MACD (Moving Average Convergence Divergence)
        Retorna: (macd_line, signal_line)
        """
        exp1 = prices.ewm(span=12, adjust=False).mean()
        exp2 = prices.ewm(span=26, adjust=False).mean()
        macd_line = exp1 - exp2
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        return macd_line, signal_line

    @staticmethod
    def calculate_rsi(prices, period=14):
        """
        Calcula o RSI (Relative Strength Index)
        """
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def calculate_ma(prices, period):
        """
        Calcula a Média Móvel Simples
        """
        return prices.rolling(window=period).mean()
