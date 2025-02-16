import unittest
import pandas as pd
import sys
import os
import logging

# Configura logging para testes
logging.basicConfig(level=logging.ERROR)  # Apenas erros serão mostrados durante os testes

# Adiciona o diretório src ao path para poder importar os módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.BinanceRobot import BinanceTraderBot
from strategies.ema_macd import getEMAMACDTradeStrategy
from indicators.Indicators import Indicators
from strategies.talib import getEMAMACDtalib

class TestBinanceTraderBot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Configuração executada uma vez antes de todos os testes"""
        # Verifica se as variáveis de ambiente necessárias estão configuradas
        if not os.getenv("BINANCE_API_KEY") or not os.getenv("BINANCE_SECRET_KEY"):
            print("\nAviso: Chaves da API Binance não encontradas. Alguns testes podem falhar.")

    def setUp(self):
        """Configuração inicial para cada teste"""
        self.bot = BinanceTraderBot(
            stock_code="BTC",
            operation_code="BTCUSDT",
            traded_quantity=0.001,
            traded_percentage=100,
            candle_period="5m",
            volatility_factor=0.5,
            time_to_trade=300,
            delay_after_order=900,
            acceptable_loss_percentage=0.5,
            stop_loss_percentage=3,
            fallback_activated=True
        )

    def test_bot_initialization(self):
        """Testa se o bot foi inicializado corretamente com os parâmetros"""
        self.assertEqual(self.bot.stock_code, "BTC")
        self.assertEqual(self.bot.operation_code, "BTCUSDT")
        self.assertEqual(self.bot.traded_quantity, 0.001)
        self.assertEqual(self.bot.volatility_factor, 0.5)
        print("\n✅ Bot inicializado corretamente")

    def test_adjust_to_step(self):
        """Testa o ajuste de valores para step size"""
        # Teste com step size de 0.00001
        self.assertEqual(self.bot.adjust_to_step(0.123456, 0.00001), 0.12345)
        # Teste com step size de 0.001
        self.assertEqual(self.bot.adjust_to_step(0.123456, 0.001), 0.123)
        print("\n✅ Ajuste de step size funcionando corretamente")

    def test_ema_macd_strategy(self):
        """Testa a estratégia EMA MACD"""
        # Cria dados de teste simulando um mercado em tendência de alta
        test_data = pd.DataFrame({
            'close_price': pd.Series([100.0 + i for i in range(30)], dtype='float64'),  # Preços em tendência de alta
            'open_time': pd.date_range(start='2024-01-01', periods=30, freq='5min')
        })
        
        # Testa se a função retorna um valor booleano
        result = getEMAMACDtalib(test_data)
        self.assertIsInstance(result, bool)
        print("\n✅ Estratégia EMA MACD funcionando corretamente")

    def test_stop_loss_calculation(self):
        """Testa o cálculo do stop loss"""
        self.bot.last_buy_price = 100
        stop_loss_price = self.bot.last_buy_price * (1 - self.bot.stop_loss_percentage)
        self.assertEqual(stop_loss_price, 97)  # 100 - 3%
        print("\n✅ Cálculo de Stop Loss correto")

    def test_minimum_sell_price_calculation(self):
        """Testa o cálculo do preço mínimo de venda"""
        self.bot.last_buy_price = 100
        min_sell_price = self.bot.getMinimumPriceToSell()
        expected_price = 100 * (1 - self.bot.acceptable_loss_percentage)
        self.assertEqual(min_sell_price, expected_price)
        print("\n✅ Cálculo do preço mínimo de venda correto")

    def test_position_tracking(self):
        """Testa o rastreamento de posição"""
        # Inicialmente deve estar vendido (False)
        self.assertFalse(self.bot.actual_trade_position)
        print("\n✅ Rastreamento de posição funcionando")

if __name__ == '__main__':
    print("\n🔄 Iniciando testes do Bot Trader...")
    unittest.main(verbosity=2)