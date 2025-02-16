import threading
import time
from modules.BinanceRobot import BinanceTraderBot
from binance.client import Client
from Models.AssetStartModel import AssetStartModel
import logging
import os
from datetime import datetime

# Define o logger
logging.basicConfig(
    filename='src/logs/trading_bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def validate_environment():
    """Valida as variáveis de ambiente necessárias"""
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_SECRET_KEY")

    if not api_key or not api_secret:
        raise ValueError("⚠️ As chaves da API da Binance não foram configuradas. Configure as variáveis de ambiente BINANCE_API_KEY e BINANCE_SECRET_KEY.")
    return api_key, api_secret

# ------------------------------------------------------------------
# 🟢 CONFIGURAÇÕES - PODEM ALTERAR - INICIO 🟢


# Ajustes Técnicos
VOLATILITY_FACTOR           = 0.5       # Interfere na antecipação e nos lances de compra de venda limitados
ACCEPTABLE_LOSS_PERCENTAGE  = 0         # (Usar em base 100%) O quando o bot aceita perder de % (se for negativo, o bot só aceita lucro)
STOP_LOSS_PERCENTAGE        = 3         # (Usar em base 100%) % Máxima de loss que ele aceita para vender à mercado independente
FALLBACK_ACTIVATED          = True      # Define se a estratégia de Fallback será usada (ela pode entrar comprada em mercados subindo)


# Ajustes de Tempo
CANDLE_PERIOD = Client.KLINE_INTERVAL_1HOUR # Périodo do candle análisado
TEMPO_ENTRE_TRADES          = 5 * 60    # Tempo que o bot espera para verificar o mercado (em segundos)
DELAY_ENTRE_ORDENS          = 15 * 60   # Tempo que o bot espera depois de realizar uma ordem de compra ou venda (ajuda a diminuir trades de borda)


# Ajustes de Execução
THREAD_LOCK = True # True = Executa 1 moeda por vez | False = Executa todas simultânemaente


# Configurações da API Binance
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_SECRET_KEY")

if not API_KEY or not API_SECRET:
    raise ValueError("As chaves da API da Binance não foram configuradas. Configure as variáveis de ambiente BINANCE_API_KEY e BINANCE_SECRET_KEY.")

# Moedas negociadas
COIN_01 = AssetStartModel(  stockCode = "BTC",
                            operationCode = "BTCUSDT",
                            tradedQuantity = 0.01000,
                            candlePeriod = CANDLE_PERIOD, volatilityFactor = VOLATILITY_FACTOR, stopLossPercentage = STOP_LOSS_PERCENTAGE, tempoEntreTrades = TEMPO_ENTRE_TRADES, delayEntreOrdens = DELAY_ENTRE_ORDENS, acceptableLossPercentage = ACCEPTABLE_LOSS_PERCENTAGE, fallBackActivated= FALLBACK_ACTIVATED)

COIN_02 = AssetStartModel(  stockCode = "ETH",
                            operationCode = "ETHUSDC",
                            tradedQuantity = 0.056,
                            candlePeriod = CANDLE_PERIOD, volatilityFactor = VOLATILITY_FACTOR, stopLossPercentage = STOP_LOSS_PERCENTAGE, tempoEntreTrades = TEMPO_ENTRE_TRADES, delayEntreOrdens = DELAY_ENTRE_ORDENS, acceptableLossPercentage = ACCEPTABLE_LOSS_PERCENTAGE, fallBackActivated= FALLBACK_ACTIVATED)

COIN_03 = AssetStartModel(  stockCode = "BNB",
                            operationCode = "BNBUSDT",
                            tradedQuantity = 0.036,
                            candlePeriod = CANDLE_PERIOD, volatilityFactor = VOLATILITY_FACTOR, stopLossPercentage = STOP_LOSS_PERCENTAGE, tempoEntreTrades = TEMPO_ENTRE_TRADES, delayEntreOrdens = DELAY_ENTRE_ORDENS, acceptableLossPercentage = ACCEPTABLE_LOSS_PERCENTAGE, fallBackActivated= FALLBACK_ACTIVATED)

# Array que DEVE CONTER as moedas que serão negociadas
assetsTraders = [COIN_01, COIN_02,COIN_03] 

# assetsTraders = [XRP_USDT, SOL_BRL] # Exemplo com mais de uma moeda




# 🔴 CONFIGURAÇÕES - PODEM ALTERAR - FIM 🔴
# ---------------------------------------------------------------------------------------------
# LOOP PRINCIPAL

thread_lock = threading.Lock()

def trader_loop(assetStart: AssetStartModel):
    try:
        MaTrader = BinanceTraderBot(
            stock_code=assetStart.stockCode,
            operation_code=assetStart.operationCode,
            traded_quantity=assetStart.tradedQuantity,
            traded_percentage=assetStart.tradedPercentage,
            candle_period=assetStart.candlePeriod,
            volatility_factor=assetStart.volatilityFactor,
            time_to_trade=assetStart.tempoEntreTrades,
            delay_after_order=assetStart.delayEntreOrdens,
            acceptable_loss_percentage=assetStart.acceptableLossPercentage,
            stop_loss_percentage=assetStart.stopLossPercentage,
            fallback_activated=assetStart.fallBackActivated
        )
        
        totalExecucao = 1
        
        while True:
            try:
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if THREAD_LOCK:
                    with thread_lock:
                        print(f"\n[{current_time}][{MaTrader.operation_code}][{totalExecucao}] Iniciando execução")
                        MaTrader.execute()
                        print(f"✅ [{MaTrader.operation_code}][{totalExecucao}] Próxima execução em {MaTrader.time_to_sleep/60:.2f} minutos")
                        print("-" * 50)
                else:
                    print(f"\n[{current_time}][{MaTrader.operation_code}][{totalExecucao}] Iniciando execução")
                    MaTrader.execute()
                    print(f"✅ [{MaTrader.operation_code}][{totalExecucao}] Próxima execução em {MaTrader.time_to_sleep/60:.2f} minutos")
                    print("-" * 50)
                
                totalExecucao += 1
                time.sleep(MaTrader.time_to_sleep)
                
            except Exception as e:
                logging.error(f"Erro na execução {totalExecucao} do {MaTrader.operation_code}: {str(e)}")
                print(f"⚠️ Erro na execução: {str(e)}")
                time.sleep(60)  # Espera 1 minuto antes de tentar novamente
                
    except Exception as e:
        logging.error(f"Erro fatal no trader_loop para {assetStart.operationCode}: {str(e)}")
        print(f"❌ Erro fatal no trader_loop: {str(e)}")

def main():
    try:
        # Valida ambiente
        api_key, api_secret = validate_environment()
        
        # Verifica se há ativos configurados
        if not assetsTraders:
            raise ValueError("❌ Nenhum ativo configurado para negociação")
            
        print("\n🤖 Iniciando RoboTrader Binance")
        print(f"📈 Ativos configurados: {', '.join(asset.operationCode for asset in assetsTraders)}")
        
        # Criando e iniciando uma thread para cada objeto
        threads = []
        for asset in assetsTraders:
            thread = threading.Thread(target=trader_loop, args=(asset,))
            thread.daemon = True
            thread.start()
            threads.append(thread)
            print(f"✅ Thread iniciada para {asset.operationCode}")
        
        print("\n🟢 Bot em execução. Pressione Ctrl+C para encerrar.")
        
        # Mantém o programa rodando
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n🔴 Programa encerrado pelo usuário.")
    except Exception as e:
        logging.error(f"Erro fatal na execução principal: {str(e)}")
        print(f"\n❌ Erro fatal: {str(e)}")

if __name__ == "__main__":
    main()


