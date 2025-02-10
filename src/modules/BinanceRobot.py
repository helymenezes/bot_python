import os
import time
from datetime import datetime
import logging
import math
import pandas as pd

from dotenv import load_dotenv
from binance.client import Client
from binance.enums import *
from binance.enums import SIDE_SELL, ORDER_TYPE_STOP_LOSS_LIMIT
from binance.exceptions import BinanceAPIException

# Importações dos módulos customizados
from modules.BinanceClient import BinanceClient
from modules.TraderOrder import TraderOrder
from modules.Logger import createLogOrder  # Função de log das ordens
from indicators import Indicators
from strategies.ema_macd import getEMAMACDTradeStrategy   # Nova importação da estratégia EMA MACD

# Exemplo de implementação da função de estratégia
def runStrategies(bot):
    """
    Executa as estratégias de decisão.
    Verifica se bot.stock_data existe e possui dados; se não, emite aviso e retorna uma decisão padrão.
    """
    if bot.stock_data is None or bot.stock_data.empty:
        print("Erro: stock_data não está definido ou está vazio. Atualize os dados antes de executar a estratégia.")
        # Retorne uma decisão padrão ou None
        return None

    # Exemplo simplificado de estratégia:
    # Calcula a média móvel dos últimos 20 candles e compara com o preço atual.
    moving_average = bot.stock_data["close_price"].rolling(window=20).mean().iloc[-1]
    current_price = bot.stock_data["close_price"].iloc[-1]
    if current_price < moving_average:
        return True   # Decisão: Comprar
    else:
        return False  # Decisão: Vender

load_dotenv()
api_key = os.getenv("BINANCE_API_KEY")
secret_key = os.getenv("BINANCE_SECRET_KEY")


# Classe Principal
class BinanceTraderBot:
    # Parâmetros da classe sem valor inicial
    last_trade_decision = None  # Última decisão (False = Vender | True = Comprar)
    last_buy_price = 0          # Último preço de compra executado
    last_sell_price = 0         # Último preço de venda executado
    open_orders = []
    partial_quantity_discount = 0
    tick_size: float
    step_size: float

    def __init__(self, stock_code, operation_code, traded_quantity, traded_percentage, candle_period,
                 volatility_factor=0.5, time_to_trade=30*60, delay_after_order=60*60,
                 acceptable_loss_percentage=0.5, stop_loss_percentage=5, fallback_activated=True):

        print('------------------------------------------------')
        print('🤖 Robo Trader iniciando...')

        self.stock_code = stock_code                  # Exemplo: 'BTC'
        self.operation_code = operation_code          # Exemplo: 'BTCBRL'
        self.traded_quantity = traded_quantity          # Quantidade inicial a operar
        self.traded_percentage = traded_percentage      # Percentual do total da carteira a negociar
        self.candle_period = candle_period              # Período dos candles (ex: '15m')
        self.volatility_factor = volatility_factor      # Fator de volatilidade para antecipação
        self.fallback_activated = fallback_activated      # Ativa estratégia de fallback
        self.acceptable_loss_percentage = acceptable_loss_percentage / 100
        self.stop_loss_percentage = stop_loss_percentage / 100

        # Tempos de espera
        self.time_to_trade = time_to_trade
        self.delay_after_order = delay_after_order
        self.time_to_sleep = time_to_trade

        self.client_binance = BinanceClient(api_key, secret_key, sync=True, sync_interval=30000, verbose=True)
        self.actual_trade_position = False  # Inicialmente considerado vendido (False)

        # Inicializa stock_data para evitar AttributeError, mesmo que vazio
        self.stock_data = None

        self.setStepSizeAndTickSize()
        self.last_stock_account_balance = 0.0

    def updateAllData(self, verbose=False):
        try:
            self.account_data = self.getUpdatedAccountData()                        # Dados da conta
            self.last_stock_account_balance = self.getLastStockAccountBalance()       # Balanço do ativo
            self.actual_trade_position = self.getActualTradePosition()              # Posição atual (comprado/vendido)
            
            # Obtém os dados de mercado (candles)
            data = self.getStockData_ClosePrice_OpenTime()
            if data is not None and not data.empty:
                self.stock_data = data
            else:
                print("Erro: stock_data retornado vazio. Inicializando com DataFrame vazio.")
                self.stock_data = pd.DataFrame()
                
            self.open_orders = self.getOpenOrders()                                 # Ordens abertas
            self.last_buy_price = self.getLastBuyPrice(verbose)
            self.last_sell_price = self.getLastSellPrice(verbose)
        except BinanceAPIException as e:
            print(f"Erro na atualização de dados: {e}")

    def getUpdatedAccountData(self):
        return self.client_binance.get_account()

    def getLastStockAccountBalance(self):
        in_wallet_amount = 0.0
        for stock in self.account_data['balances']:
            if stock['asset'] == self.stock_code:
                free = float(stock['free'])
                locked = float(stock['locked'])
                in_wallet_amount = free + locked
                break
        return float(in_wallet_amount)

    def getActualTradePosition(self):
        try:
            if self.last_stock_account_balance >= self.step_size:
                return True  # Comprado
            else:
                return False  # Vendido
        except Exception as e:
            print(f"Erro ao determinar a posição atual para {self.operation_code}: {e}")
            return False

    def getStockData_ClosePrice_OpenTime(self, volatility_window=40):
        candles = self.client_binance.get_klines(symbol=self.operation_code, interval=self.candle_period, limit=500)
        prices = pd.DataFrame(candles)
        prices.columns = ["open_time", "open_price", "high_price", "low_price", "close_price",
                          "volume", "close_time", "quote_asset_volume", "number_of_trades",
                          "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "-"]
        prices = prices[["close_price", "open_time", "open_price", "high_price", "low_price", "volume"]]
        prices["close_price"] = pd.to_numeric(prices["close_price"], errors="coerce")
        prices["open_price"] = pd.to_numeric(prices["open_price"], errors="coerce")
        prices["high_price"] = pd.to_numeric(prices["high_price"], errors="coerce")
        prices["low_price"] = pd.to_numeric(prices["low_price"], errors="coerce")
        prices["volume"] = pd.to_numeric(prices["volume"], errors="coerce")
        prices["open_time"] = pd.to_datetime(prices["open_time"], unit="ms").dt.tz_localize("UTC")
        prices["open_time"] = prices["open_time"].dt.tz_convert("America/Sao_Paulo")
        prices["volatility"] = prices["close_price"].rolling(window=volatility_window).std()
        return prices

    def getLastBuyPrice(self, verbose=False):
        try:
            all_orders = self.client_binance.get_all_orders(symbol=self.operation_code, limit=100)
            executed_buy_orders = [
                order for order in all_orders 
                if order['side'] == 'BUY' and order['status'] == 'FILLED'
            ]
            if executed_buy_orders:
                last_executed_order = sorted(executed_buy_orders, key=lambda x: x['time'], reverse=True)[0]
                last_buy_price = float(last_executed_order['cummulativeQuoteQty']) / float(last_executed_order['executedQty'])
                datetime_transact = datetime.utcfromtimestamp(last_executed_order['time'] / 1000).strftime('(%H:%M:%S) %d-%m-%Y')
                if verbose:
                    print(f"\nÚltima ordem de COMPRA executada para {self.operation_code}:")
                    print(f" - Data: {datetime_transact} | Preço: {self.adjust_to_step(last_buy_price, self.tick_size, as_string=True)} | Qnt.: {self.adjust_to_step(float(last_executed_order['origQty']), self.step_size, as_string=True)}")
                return last_buy_price
            else:
                if verbose:
                    print(f"Não há ordens de COMPRA executadas para {self.operation_code}.")
                return 0.0
        except Exception as e:
            if verbose:
                print(f"Erro ao verificar a última ordem de COMPRA executada para {self.operation_code}: {e}")
            return 0.0

    def getLastSellPrice(self, verbose=False):
        try:
            all_orders = self.client_binance.get_all_orders(symbol=self.operation_code, limit=100)
            executed_sell_orders = [
                order for order in all_orders 
                if order['side'] == 'SELL' and order['status'] == 'FILLED'
            ]
            if executed_sell_orders:
                last_executed_order = sorted(executed_sell_orders, key=lambda x: x['time'], reverse=True)[0]
                last_sell_price = float(last_executed_order['cummulativeQuoteQty']) / float(last_executed_order['executedQty'])
                datetime_transact = datetime.utcfromtimestamp(last_executed_order['time'] / 1000).strftime('(%H:%M:%S) %d-%m-%Y')
                if verbose:
                    print(f"Última ordem de VENDA executada para {self.operation_code}:")
                    print(f" - Data: {datetime_transact} | Preço: {self.adjust_to_step(last_sell_price, self.tick_size, as_string=True)} | Qnt.: {self.adjust_to_step(float(last_executed_order['origQty']), self.step_size, as_string=True)}")
                return last_sell_price
            else:
                if verbose:
                    print(f"Não há ordens de VENDA executadas para {self.operation_code}.")
                return 0.0
        except Exception as e:
            if verbose:
                print(f"Erro ao verificar a última ordem de VENDA executada para {self.operation_code}: {e}")
            return 0.0

    def getTimestamp(self):
        try:
            if not hasattr(self, 'time_offset') or self.time_offset is None:
                server_time = self.client_binance.get_server_time()["serverTime"]
                local_time = int(time.time() * 1000)
                self.time_offset = server_time - local_time
            adjusted_timestamp = int(time.time() * 1000) + self.time_offset
            return adjusted_timestamp
        except Exception as e:
            print(f"Erro ao ajustar o timestamp: {e}")
            return int(time.time() * 1000)

    def setStepSizeAndTickSize(self):
        try:
            symbol_info = self.client_binance.get_symbol_info(self.operation_code)
            if symbol_info is None:
                raise ValueError(f"Symbol info não encontrado para {self.operation_code}")
            # Recupera o step_size (quantidade)
            lot_size_filter = next(f for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE')
            self.step_size = float(lot_size_filter['stepSize'])
            # Recupera o tick_size (preço)
            price_filter = next(f for f in symbol_info['filters'] if f['filterType'] == 'PRICE_FILTER')
            self.tick_size = float(price_filter['tickSize'])
            logging.info(f"Step size: {self.step_size}, Tick size: {self.tick_size}")
        except Exception as e:
            logging.error(f"Erro ao configurar step_size e tick_size: {str(e)}")
            self.step_size = 0.00001
            self.tick_size = 0.00001

    def adjust_to_step(self, value, step, as_string=False):
        if step <= 0:
            raise ValueError("O valor de 'step' deve ser maior que zero.")
        decimal_places = max(0, abs(int(math.floor(math.log10(step))))) if step < 1 else 0
        adjusted_value = math.floor(value / step) * step
        adjusted_value = round(adjusted_value, decimal_places)
        if as_string:
            return f"{adjusted_value:.{decimal_places}f}"
        else:
            return adjusted_value

    def printWallet(self):
        for stock in self.account_data["balances"]:
            if float(stock["free"]) > 0:
                print(stock)

    def printStock(self):
        for stock in self.account_data["balances"]:
            if stock['asset'] == self.stock_code:
                print(stock)

    def printBrl(self):
        for stock in self.account_data["balances"]:
            if stock['asset'] == 'BRL':
                print(stock)

    def printOpenOrders(self):
        if self.open_orders:
            print("-------------------------")
            print(f"Ordens abertas para {self.operation_code}:")
            for order in self.open_orders:
                to_print = (
                    f"----\nID {order['orderId']}:\n - Status: {order['status']}\n - Side: {order['side']}\n - Ativo: {order['symbol']}\n - Preço: {order['price']}\n - Quantidade Original: {order['origQty']}\n - Quantidade Executada: {order['executedQty']}\n - Tipo: {order['type']}"
                )
                print(to_print)
            print("-------------------------")
        else:
            print(f"Não há ordens abertas para {self.operation_code}.")

    def getWallet(self):
        for stock in self.account_data["balances"]:
            if float(stock["free"]) > 0:
                return stock

    def getStock(self):
        for stock in self.account_data["balances"]:
            if stock['asset'] == self.stock_code:
                return stock

    def buyMarketOrder(self):
        try:
            if not self.actual_trade_position:  # Se a posição estiver vendida
                quantity = self.adjust_to_step((self.traded_quantity - self.partial_quantity_discount), self.step_size, as_string=True)
                order_buy = self.client_binance.create_order(
                    symbol=self.operation_code,
                    side=SIDE_BUY,
                    type=ORDER_TYPE_MARKET,
                    quantity=quantity
                )
                self.actual_trade_position = True
                createLogOrder(order_buy)
                print(f"\nOrdem de COMPRA a mercado enviada com sucesso:")
                print(order_buy)
                return order_buy
            else:
                logging.warning('Erro ao comprar: Posição já comprada.')
                print('\nErro ao comprar: Posição já comprada.')
                return False
        except Exception as e:
            logging.error(f"Erro ao executar ordem de compra a mercado: {e}")
            print(f"\nErro ao executar ordem de compra a mercado: {e}")
            return False

    def buyLimitedOrder(self, price=0):
        close_price = self.stock_data["close_price"].iloc[-1]
        volume = self.stock_data["volume"].iloc[-1]
        avg_volume = self.stock_data["volume"].rolling(window=20).mean().iloc[-1]
        rsi = Indicators.getRSI(series=self.stock_data["close_price"])
        if price == 0:
            if rsi < 30:
                limit_price = close_price - (0.002 * close_price)
            elif volume < avg_volume:
                limit_price = close_price + (0.002 * close_price)
            else:
                limit_price = close_price + (0.005 * close_price)
        else:
            limit_price = price
        limit_price = self.adjust_to_step(limit_price, self.tick_size, as_string=True)
        quantity = self.adjust_to_step(self.traded_quantity - self.partial_quantity_discount, self.step_size, as_string=True)
        print(f"Enviando ordem limitada de COMPRA para {self.operation_code}:")
        print(f" - RSI: {rsi}")
        print(f" - Quantidade: {quantity}")
        print(f" - Close Price: {close_price}")
        print(f" - Preço Limite: {limit_price}")
        try:
            order_buy = self.client_binance.create_order(
                symbol=self.operation_code,
                side=SIDE_BUY,
                type=ORDER_TYPE_LIMIT,
                timeInForce="GTC",
                quantity=quantity,
                price=limit_price
            )
            self.actual_trade_position = True
            print(f"\nOrdem COMPRA limitada enviada com sucesso:")
            if order_buy is not None:
                createLogOrder(order_buy)
            return order_buy
        except Exception as e:
            logging.error(f"Erro ao enviar ordem limitada de COMPRA: {e}")
            print(f"\nErro ao enviar ordem limitada de COMPRA: {e}")
            return False

    def sellMarketOrder(self):
        try:
            if self.actual_trade_position:  # Se a posição estiver comprada
                quantity = self.adjust_to_step(self.last_stock_account_balance, self.step_size, as_string=True)
                order_sell = self.client_binance.create_order(
                    symbol=self.operation_code,
                    side=SIDE_SELL,
                    type=ORDER_TYPE_MARKET,
                    quantity=quantity
                )
                self.actual_trade_position = False
                createLogOrder(order_sell)
                print(f"\nOrdem de VENDA a mercado enviada com sucesso:")
                return order_sell
            else:
                logging.warning('Erro ao vender: Posição já vendida.')
                print('\nErro ao vender: Posição já vendida.')
                return False
        except Exception as e:
            logging.error(f"Erro ao executar ordem de venda a mercado: {e}")
            print(f"\nErro ao executar ordem de venda a mercado: {e}")
            return False

    def sellLimitedOrder(self, price=0):
        close_price = self.stock_data["close_price"].iloc[-1]
        volume = self.stock_data["volume"].iloc[-1]
        avg_volume = self.stock_data["volume"].rolling(window=20).mean().iloc[-1]
        rsi = Indicators.getRSI(series=self.stock_data["close_price"])
        if price == 0:
            if rsi > 70:
                limit_price = close_price + (0.002 * close_price)
            elif volume < avg_volume:
                limit_price = close_price - (0.002 * close_price)
            else:
                limit_price = close_price - (0.005 * close_price)
            if limit_price < (self.last_buy_price * (1 - self.acceptable_loss_percentage)):
                print(f'\nAjuste de venda aceitável ({self.acceptable_loss_percentage*100}%):')
                print(f' - De: {limit_price:.4f}')
                limit_price = self.getMinimumPriceToSell()
                print(f' - Para: {limit_price}')
        else:
            limit_price = price
        limit_price = self.adjust_to_step(limit_price, self.tick_size, as_string=True)
        quantity = self.adjust_to_step(self.last_stock_account_balance, self.step_size, as_string=True)
        print(f"\nEnviando ordem limitada de VENDA para {self.operation_code}:")
        print(f" - RSI: {rsi}")
        print(f" - Quantidade: {quantity}")
        print(f" - Close Price: {close_price}")
        print(f" - Preço Limite: {limit_price}")
        try:
            order_sell = self.client_binance.create_order(
                symbol=self.operation_code,
                side=SIDE_SELL,
                type=ORDER_TYPE_LIMIT,
                timeInForce="GTC",
                quantity=str(quantity),
                price=str(limit_price)
            )
            self.actual_trade_position = False
            print(f"\nOrdem VENDA limitada enviada com sucesso:")
            createLogOrder(order_sell)
            return order_sell
        except Exception as e:
            logging.error(f"Erro ao enviar ordem limitada de VENDA: {e}")
            print(f"\nErro ao enviar ordem limitada de VENDA: {e}")
            return False

    def getOpenOrders(self):
        open_orders = self.client_binance.get_open_orders(symbol=self.operation_code)
        return open_orders

    def cancelOrderById(self, order_id):
        self.client_binance.cancel_order(symbol=self.operation_code, orderId=order_id)

    def cancelAllOrders(self):
        if self.open_orders:
            for order in self.open_orders:
                try:
                    self.client_binance.cancel_order(symbol=self.operation_code, orderId=order['orderId'])
                    print(f"❌ Ordem {order['orderId']} cancelada.")
                except Exception as e:
                    print(f"Erro ao cancelar ordem {order['orderId']}: {e}")

    def hasOpenBuyOrder(self):
        self.partial_quantity_discount = 0.0
        try:
            open_orders = self.client_binance.get_open_orders(symbol=self.operation_code)
            buy_orders = [order for order in open_orders if order['side'] == 'BUY']
            if buy_orders:
                self.last_buy_price = 0.0
                print(f"\nOrdens de compra abertas para {self.operation_code}:")
                for order in buy_orders:
                    executed_qty = float(order['executedQty'])
                    price = float(order['price'])
                    print(f" - ID da Ordem: {order['orderId']}, Preço: {price}, Qnt.: {order['origQty']}, Qnt. Executada: {executed_qty}")
                    self.partial_quantity_discount += executed_qty
                    if executed_qty > 0 and price > self.last_buy_price:
                        self.last_buy_price = price
                print(f" - Quantidade parcial executada no total: {self.partial_quantity_discount}")
                print(f" - Maior preço parcialmente executado: {self.last_buy_price}")
                return True
            else:
                print(f" - Não há ordens de compra abertas para {self.operation_code}.")
                return False
        except Exception as e:
            print(f"Erro ao verificar ordens abertas para {self.operation_code}: {e}")
            return False

    def hasOpenSellOrder(self):
        self.partial_quantity_discount = 0.0
        try:
            open_orders = self.client_binance.get_open_orders(symbol=self.operation_code)
            sell_orders = [order for order in open_orders if order['side'] == 'SELL']
            if sell_orders:
                print(f"\nOrdens de venda abertas para {self.operation_code}:")
                for order in sell_orders:
                    executed_qty = float(order['executedQty'])
                    print(f" - ID da Ordem: {order['orderId']}, Preço: {order['price']}, Qnt.: {order['origQty']}, Qnt. Executada: {executed_qty}")
                    self.partial_quantity_discount += executed_qty
                print(f" - Quantidade parcial executada no total: {self.partial_quantity_discount}")
                return True
            else:
                print(f" - Não há ordens de venda abertas para {self.operation_code}.")
                return False
        except Exception as e:
            print(f"Erro ao verificar ordens abertas para {self.operation_code}: {e}")
            return False

    def getFinalDecisionStrategy(self):
        """
        Obtém a decisão final de todas as estratégias configuradas
        """
        from strategies.strategy_runner import run_all_strategies
        
        if self.stock_data is None or self.stock_data.empty:
            print("Erro: stock_data não está definido ou está vazio.")
            return None
            
        return run_all_strategies(self)

    def getMinimumPriceToSell(self):
        return (self.last_buy_price * (1 - self.acceptable_loss_percentage))

    def stopLossTrigger(self):
        if self.stock_data is None or self.stock_data.empty:
            print("Erro: stock_data não está definido.")
            return False
        close_price = self.stock_data["close_price"].iloc[-1]
        weighted_price = self.stock_data["close_price"].iloc[-2]
        stop_loss_price = self.last_buy_price * (1 - self.stop_loss_percentage)
        print(f'\n - Preço atual: {close_price}')
        print(f' - Preço mínimo para vender: {self.getMinimumPriceToSell()}')
        print(f' - Stop Loss em: {stop_loss_price:.4f} (-{self.stop_loss_percentage*100}%)\n')
        if close_price < stop_loss_price and weighted_price < stop_loss_price and self.actual_trade_position:
            print("🔴 Ativando STOP LOSS...")
            self.cancelAllOrders()
            time.sleep(2)
            self.sellMarketOrder()
            return True
        return False

    def create_order(self, _symbol, _side, _type, _quantity, _timeInForce=None, _limit_price=None, _stop_price=None):
        order_buy = TraderOrder.create_order(
            self.client_binance,
            _symbol=_symbol,
            _side=_side,
            _type=_type,
            _timeInForce=_timeInForce,
            _quantity=_quantity,
            _limit_price=_limit_price,
            _stop_price=_stop_price
        )
        return order_buy

    def execute(self):
        print('------------------------------------------------')
        print(f'🟢 Executado {datetime.now().strftime("(%H:%M:%S) %d-%m-%Y")}\n')
        self.updateAllData(verbose=True)
        # Nova parte: Aplicação da estratégia EMA MACD e impressão do resultado
        if self.stock_data is not None and not self.stock_data.empty:
            point_signal = getEMAMACDTradeStrategy(self.stock_data)
            print("\nResultados da estratégia EMA MACD:")
            print(point_signal)
        else:
            print("\nstock_data está vazio ou não definido.")
        print('\n-------')
        print('Detalhes:')
        print(f' - Posição atual: {"Comprado" if self.actual_trade_position else "Vendido"}')
        print(f' - Balanço atual: {self.last_stock_account_balance:.4f} ({self.stock_code})')
        # Estratégia de stop loss
        if self.stopLossTrigger():
            print("📉 STOP LOSS executado...")
            return
        # Obtém a decisão final (comprar, vender ou manter)
        self.last_trade_decision = self.getFinalDecisionStrategy()
        # Se houver ordens abertas da mesma direção, cancele-as
        if self.last_trade_decision == True:
            if self.hasOpenBuyOrder():
                self.cancelAllOrders()
                time.sleep(2)
        if self.last_trade_decision == False:
            if self.hasOpenSellOrder():
                self.cancelAllOrders()
                time.sleep(2)
        print('\n--------------')
        print(f'🔎 Decisão Final: {"Comprar" if self.last_trade_decision == True else "Vender" if self.last_trade_decision == False else "Inconclusiva"}')
        if self.actual_trade_position == False and self.last_trade_decision == True:
            print('🏁 Ação final: Comprar')
            print('--------------')
            print(f'\nCarteira em {self.stock_code} [ANTES]:')
            self.printStock()
            self.buyLimitedOrder()
            time.sleep(2)
            self.updateAllData(verbose=True)
            print(f'Carteira em {self.stock_code} [DEPOIS]:')
            self.printStock()
            self.time_to_sleep = self.delay_after_order
        elif self.actual_trade_position == True and self.last_trade_decision == False:
            print('🏁 Ação final: Vender')
            print('--------------')
            print(f'\nCarteira em {self.stock_code} [ANTES]:')
            self.printStock()
            self.sellLimitedOrder()
            time.sleep(2)
            self.updateAllData(verbose=True)
            print(f'\nCarteira em {self.stock_code} [DEPOIS]:')
            self.printStock()
            self.time_to_sleep = self.delay_after_order
        else:
            print(f'🏁 Ação final: Manter posição ({"Comprado" if self.actual_trade_position else "Vendido"})')
            print('--------------')
            self.time_to_sleep = self.time_to_trade
        print('------------------------------------------------')

# Fim da classe BinanceTraderBot
