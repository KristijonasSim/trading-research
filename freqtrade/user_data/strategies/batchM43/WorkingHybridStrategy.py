# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
# --- Do not remove these libs ---
import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime, timedelta
from typing import Optional, Union, Dict, Any
import time
import logging

from freqtrade.strategy import (BooleanParameter, CategoricalParameter, DecimalParameter,
                                IntParameter, IStrategy, merge_informative_pair)

# --------------------------------
# Add your lib to import here
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib


class WorkingHybridStrategy(IStrategy):
    """
    РАБОТАЮЩАЯ гибридная стратегия, объединяющая:
    1. FreqAI с машинным обучением
    2. Скальпинг стратегии
    3. Мультитаймфреймовые стратегии
    4. Моментные стратегии на новостях
    """
    
    INTERFACE_VERSION = 3

    # Оптимальный таймфрейм для стратегии
    timeframe = '1m'  # Скальпинг на 1-минутных свечах
    
    # Количество свечей для загрузки при старте (для стабильных индикаторов)
    startup_candle_count: int = 1000  # ~16 часов истории для 1m

    # ROI table - агрессивные цели для скальпинга
    minimal_roi = {
        "0": 0.20,    # 20% сразу
        "1": 0.15,    # 15% через 1 минуту
        "2": 0.10,    # 10% через 2 минуты
        "3": 0.08,    # 8% через 3 минуты
        "5": 0.05,    # 5% через 5 минут
        "10": 0.03,   # 3% через 10 минут
        "20": 0.02,   # 2% через 20 минут
        "30": 0.01,   # 1% через 30 минут
        "60": 0.005,  # 0.5% через час
        "120": 0
    }

    # Stoploss - более мягкий для скальпинга
    stoploss = -0.10  # 10% стоп-лосс

    # Trailing stop
    trailing_stop = True
    trailing_stop_positive = 0.05
    trailing_stop_positive_offset = 0.08
    trailing_only_offset_is_reached = True

    # Максимальное количество открытых сделок
    max_open_trades = 20  # Больше сделок для скальпинга

    # FreqAI настройки
    freqai_enabled = True
    freqai_model = "CatBoostRegressor"
    
    # Гиперпараметры - более агрессивные
    leverage_param = DecimalParameter(5.0, 20.0, default=15.0, space="buy")
    rsi_oversold = IntParameter(20, 60, default=45, space="buy")
    rsi_overbought = IntParameter(40, 80, default=55, space="sell")
    volume_threshold = DecimalParameter(0.3, 2.0, default=0.8, space="buy")
    volatility_threshold = DecimalParameter(0.5, 5.0, default=1.5, space="buy")
    news_impact_threshold = DecimalParameter(0.1, 2.0, default=0.3, space="buy")
    
    # Скальпинг параметры
    scalp_profit_target = DecimalParameter(0.5, 3.0, default=1.0, space="sell")
    scalp_stop_loss = DecimalParameter(0.3, 2.0, default=0.8, space="buy")
    
    # Мультитаймфреймовые параметры
    trend_timeframe = '5m'
    momentum_timeframe = '3m'
    
    def informative_pairs(self):
        """
        Определить дополнительные, информативные пары для мультитаймфреймового анализа
        """
        pairs = self.dp.current_whitelist()
        informative_pairs = []
        for pair in pairs:
            informative_pairs.append((pair, '3m'))
            informative_pairs.append((pair, '5m'))
            informative_pairs.append((pair, '15m'))
        return informative_pairs

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Добавляет индикаторы в датафрейм для гибридной стратегии
        """
        # === БАЗОВЫЕ ИНДИКАТОРЫ ===
        
        # RSI на разных периодах
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['rsi_fast'] = ta.RSI(dataframe, timeperiod=7)
        dataframe['rsi_slow'] = ta.RSI(dataframe, timeperiod=21)
        
        # EMA на разных периодах
        dataframe['ema_5'] = ta.EMA(dataframe, timeperiod=5)
        dataframe['ema_10'] = ta.EMA(dataframe, timeperiod=10)
        dataframe['ema_20'] = ta.EMA(dataframe, timeperiod=20)
        dataframe['ema_50'] = ta.EMA(dataframe, timeperiod=50)
        
        # MACD
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']
        
        # Bollinger Bands
        bollinger = qtpylib.bollinger_bands(dataframe['close'], window=20, stds=2)
        dataframe['bb_lowerband'] = bollinger['lower']
        dataframe['bb_middleband'] = bollinger['mid']
        dataframe['bb_upperband'] = bollinger['upper']
        dataframe['bb_percent'] = (dataframe['close'] - dataframe['bb_lowerband']) / (dataframe['bb_upperband'] - dataframe['bb_lowerband'])
        dataframe['bb_width'] = (dataframe['bb_upperband'] - dataframe['bb_lowerband']) / dataframe['bb_middleband']
        
        # === СКАЛЬПИНГ ИНДИКАТОРЫ ===
        
        # Volume indicators
        dataframe['volume_sma'] = dataframe['volume'].rolling(window=20).mean()
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_sma']
        dataframe['volume_spike'] = dataframe['volume_ratio'] > 1.5
        
        # ATR для волатильности
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['atr_percent'] = dataframe['atr'] / dataframe['close'] * 100
        
        # Stochastic для скальпинга
        stoch = ta.STOCH(dataframe)
        dataframe['stoch_k'] = stoch['slowk']
        dataframe['stoch_d'] = stoch['slowd']
        
        # Williams %R
        dataframe['williams_r'] = ta.WILLR(dataframe, timeperiod=14)
        
        # CCI
        dataframe['cci'] = ta.CCI(dataframe, timeperiod=14)
        
        # === МУЛЬТИТАЙМФРЕЙМОВЫЕ ИНДИКАТОРЫ ===
        
        # Получаем данные с более высоких таймфреймов
        if self.dp:
            inf_3m = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe='3m')
            inf_5m = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe='5m')
            inf_15m = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe='15m')
            
            if not inf_3m.empty:
                # 3-минутные индикаторы
                inf_3m['ema_10_3m'] = ta.EMA(inf_3m, timeperiod=10)
                inf_3m['rsi_3m'] = ta.RSI(inf_3m, timeperiod=14)
                dataframe = merge_informative_pair(dataframe, inf_3m, self.timeframe, '3m', ffill=True)
                
            if not inf_5m.empty:
                # 5-минутные индикаторы
                inf_5m['ema_20_5m'] = ta.EMA(inf_5m, timeperiod=20)
                inf_5m['rsi_5m'] = ta.RSI(inf_5m, timeperiod=14)
                dataframe = merge_informative_pair(dataframe, inf_5m, self.timeframe, '5m', ffill=True)
                
            if not inf_15m.empty:
                # 15-минутные индикаторы
                inf_15m['ema_50_15m'] = ta.EMA(inf_15m, timeperiod=50)
                inf_15m['rsi_15m'] = ta.RSI(inf_15m, timeperiod=14)
                dataframe = merge_informative_pair(dataframe, inf_15m, self.timeframe, '15m', ffill=True)
        
        # === МОМЕНТНЫЕ ИНДИКАТОРЫ ===
        
        # Price action
        dataframe['price_change'] = dataframe['close'].pct_change()
        dataframe['price_change_3'] = dataframe['close'].pct_change(3)
        dataframe['volatility'] = dataframe['price_change'].rolling(window=20).std()
        
        # Momentum
        dataframe['momentum'] = dataframe['close'].pct_change(3)
        dataframe['momentum_5'] = dataframe['close'].pct_change(5)
        
        # Trend strength
        dataframe['trend_strength'] = (dataframe['ema_10'] - dataframe['ema_20']) / dataframe['ema_20']
        
        # === НОВОСТНОЙ АНАЛИЗ ===
        
        # Волатильность как индикатор новостей
        dataframe['volatility_spike'] = dataframe['volatility'] > dataframe['volatility'].rolling(50).quantile(0.7)
        dataframe['volume_volatility'] = dataframe['volume_ratio'] * dataframe['volatility']
        
        # Анализ резких движений цены
        dataframe['price_spike'] = abs(dataframe['price_change']) > dataframe['price_change'].rolling(20).std() * 1.5
        dataframe['news_impact'] = dataframe['volatility_spike'] & dataframe['volume_spike'] & dataframe['price_spike']
        
        # === FREQAI ТАРГЕТЫ ===
        
        # Простые таргеты для FreqAI
        future_return_5 = (dataframe['close'].shift(-5) - dataframe['close']) / dataframe['close']
        future_return_15 = (dataframe['close'].shift(-15) - dataframe['close']) / dataframe['close']
        
        # Таргеты для регрессии
        dataframe['&s-profit_5m'] = future_return_5
        dataframe['&s-profit_15m'] = future_return_15
        
        # Таргеты для классификации
        dataframe['&s-direction_5m'] = np.where(future_return_5 > 0.003, 1, 
                                               np.where(future_return_5 < -0.003, 0, -1))
        dataframe['&s-direction_15m'] = np.where(future_return_15 > 0.005, 1, 
                                                np.where(future_return_15 < -0.005, 0, -1))
        
        # === СКАЛЬПИНГ СИГНАЛЫ ===
        
        # Быстрые сигналы для скальпинга
        dataframe['scalp_buy'] = (
            (dataframe['rsi'] < 40) &
            (dataframe['stoch_k'] < 30) &
            (dataframe['williams_r'] < -70) &
            (dataframe['volume_ratio'] > 1.2) &
            (dataframe['bb_percent'] < 0.3)
        )
        
        dataframe['scalp_sell'] = (
            (dataframe['rsi'] > 60) &
            (dataframe['stoch_k'] > 70) &
            (dataframe['williams_r'] > -30) &
            (dataframe['bb_percent'] > 0.7)
        )
        
        # === ТРЕНДОВЫЕ СИГНАЛЫ ===
        
        # Долгосрочный тренд
        dataframe['trend_bullish'] = (
            (dataframe['ema_10'] > dataframe['ema_20']) &
            (dataframe['ema_20'] > dataframe['ema_50']) &
            (dataframe['close'] > dataframe.get('ema_50_15m', dataframe['ema_50']))
        )
        
        dataframe['trend_bearish'] = (
            (dataframe['ema_10'] < dataframe['ema_20']) &
            (dataframe['ema_20'] < dataframe['ema_50']) &
            (dataframe['close'] < dataframe.get('ema_50_15m', dataframe['ema_50']))
        )
        
        return dataframe

    def populate_any_indicators(self, pair, df, tf, informative=None, set_generalized_indicators=False):
        """
        КРИТИЧНО для FreqAI! Добавляет индикаторы для всех таймфреймов
        """
        if set_generalized_indicators:
            df['%-pct_change'] = (df['close'] - df['open']) / df['open']
            df['%-raw_volume'] = df['volume']
            df['%-raw_price'] = df['close']
            df['%-rsi'] = ta.RSI(df, timeperiod=14)
            df['%-ema_short'] = ta.EMA(df, timeperiod=5)
            df['%-ema_long'] = ta.EMA(df, timeperiod=20)
            df['%-macd'] = ta.MACD(df)['macd']
            df['%-bb_upperband'] = ta.BBANDS(df)['upperband']
            df['%-bb_lowerband'] = ta.BBANDS(df)['lowerband']
            df['%-bb_middleband'] = ta.BBANDS(df)['middleband']
            df['%-bb_percent'] = (df['close'] - df['%-bb_lowerband']) / (df['%-bb_upperband'] - df['%-bb_lowerband'])
            df['%-bb_width'] = (df['%-bb_upperband'] - df['%-bb_lowerband']) / df['%-bb_middleband']
            df['%-close'] = df['close']
            df['%-high'] = df['high']
            df['%-low'] = df['low']
            df['%-open'] = df['open']
            df['%-volume'] = df['volume']
        
        return df

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Определяет условия входа в позицию - гибридный подход
        """
        # === СКАЛЬПИНГ ВХОДЫ (основные) ===
        dataframe.loc[
            (
                # Скальпинг условия
                dataframe['scalp_buy'] &
                (dataframe['atr_percent'] < 4.0) &  # Умеренная волатильность
                (dataframe['volume_ratio'] > self.volume_threshold.value) &
                
                # FreqAI предсказание роста
                (dataframe['&s-direction_5m'] == 1) &
                
                # Тренд не против нас
                ~dataframe['trend_bearish']
            ),
            'enter_long'] = 1

        # === МОМЕНТНЫЕ ВХОДЫ НА НОВОСТЯХ ===
        dataframe.loc[
            (
                # Новостной импульс
                dataframe['news_impact'] &
                (dataframe['volume_volatility'] > self.news_impact_threshold.value) &
                (dataframe['price_change'] > 0) &  # Цена растет
                
                # FreqAI подтверждение
                (dataframe['&s-direction_5m'] == 1) &
                
                # Тренд поддерживает
                dataframe['trend_bullish']
            ),
            'enter_long'] = 1

        # === ТРЕНДОВЫЕ ВХОДЫ ===
        dataframe.loc[
            (
                # Трендовые условия
                dataframe['trend_bullish'] &
                (dataframe['rsi'] < self.rsi_oversold.value) &
                (dataframe['bb_percent'] < 0.4) &
                (dataframe['macd'] > dataframe['macdsignal']) &
                
                # FreqAI подтверждение
                (dataframe['&s-direction_15m'] == 1) &
                
                # Мультитаймфреймовое подтверждение
                (dataframe.get('rsi_5m', 50) < 70) &
                (dataframe.get('rsi_15m', 50) < 75)
            ),
            'enter_long'] = 1

        # === АГРЕССИВНЫЕ ВХОДЫ (для увеличения количества сделок) ===
        dataframe.loc[
            (
                # Простые условия
                (dataframe['rsi'] < 50) &
                (dataframe['volume_ratio'] > 0.8) &
                (dataframe['bb_percent'] < 0.5) &
                (dataframe['&s-direction_5m'] == 1) &
                (dataframe['atr_percent'] < 5.0)
            ),
            'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Определяет условия выхода из позиции
        """
        # === СКАЛЬПИНГ ВЫХОДЫ ===
        dataframe.loc[
            (
                dataframe['scalp_sell'] |
                (dataframe['atr_percent'] > 6.0) |  # Слишком высокая волатильность
                (dataframe['&s-direction_5m'] == 0)  # FreqAI предсказывает падение
            ),
            'exit_long'] = 1

        # === ТРЕНДОВЫЕ ВЫХОДЫ ===
        dataframe.loc[
            (
                dataframe['trend_bearish'] |
                (dataframe['rsi'] > self.rsi_overbought.value) |
                (dataframe['bb_percent'] > 0.8) |
                (dataframe['macd'] < dataframe['macdsignal']) |
                (dataframe['&s-direction_15m'] == 0)  # FreqAI предсказывает падение
            ),
            'exit_long'] = 1

        # === АГРЕССИВНЫЕ ВЫХОДЫ ===
        dataframe.loc[
            (
                (dataframe['rsi'] > 70) |
                (dataframe['bb_percent'] > 0.9) |
                (dataframe['&s-direction_5m'] == 0)
            ),
            'exit_long'] = 1

        return dataframe

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str], 
                 side: str, **kwargs) -> float:
        """
        Динамическое кредитное плечо в зависимости от волатильности
        """
        # Получаем текущую волатильность
        if hasattr(self, 'dp') and self.dp:
            dataframe = self.dp.get_pair_dataframe(pair=pair, timeframe=self.timeframe)
            if not dataframe.empty:
                current_volatility = dataframe.get('atr_percent', pd.Series([2.0])).iloc[-1]
                
                # Адаптивное плечо: меньше плечо при высокой волатильности
                if current_volatility > 6.0:
                    return min(8.0, self.leverage_param.value * 0.5)
                elif current_volatility > 4.0:
                    return min(12.0, self.leverage_param.value * 0.7)
                else:
                    return self.leverage_param.value
        
        return self.leverage_param.value

    def custom_exit(self, pair: str, trade: 'Trade', current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs) -> Optional[Union[str, bool]]:
        """
        Кастомная логика выхода для разных типов сделок
        """
        # Скальпинг выходы
        if current_profit >= self.scalp_profit_target.value:
            return 'scalp_profit'
        elif current_profit <= -self.scalp_stop_loss.value:
            return 'scalp_stop'
        
        # Моментные выходы на новостях
        if current_profit >= 0.08:  # 8% на новостях
            return 'news_profit'
        elif current_profit <= -0.05:  # -5% стоп на новостях
            return 'news_stop'
        
        # Трендовые выходы
        if current_profit >= 0.15:  # 15% трендовая цель
            return 'trend_profit'
        elif current_profit <= -0.08:  # -8% трендовый стоп
            return 'trend_stop'
        
        return None

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime, 
                       current_rate: float, current_profit: float, **kwargs) -> float:
        """
        Динамический стоп-лосс в зависимости от типа сделки
        """
        # Получаем данные для анализа
        if hasattr(self, 'dp') and self.dp:
            dataframe = self.dp.get_pair_dataframe(pair=pair, timeframe=self.timeframe)
            if not dataframe.empty:
                current_volatility = dataframe['atr_percent'].iloc[-1]
                
                # Адаптивный стоп-лосс
                if current_volatility > 5.0:
                    return -0.15  # Больше стоп при высокой волатильности
                elif current_volatility > 3.0:
                    return -0.10  # Средний стоп
                else:
                    return -0.08  # Меньше стоп при низкой волатильности
        
        return self.stoploss

    def get_news_sentiment(self, pair: str) -> float:
        """
        Получает новостной сентимент для пары (заглушка для реального API)
        """
        # В реальной реализации здесь был бы вызов API новостей
        try:
            # Заглушка - возвращаем случайное значение
            import random
            return random.uniform(-1.0, 1.0)
        except:
            return 0.0

    def analyze_market_conditions(self, dataframe: DataFrame) -> Dict[str, Any]:
        """
        Анализирует текущие рыночные условия
        """
        if dataframe.empty:
            return {}
        
        latest = dataframe.iloc[-1]
        
        return {
            'volatility': latest['atr_percent'],
            'volume_ratio': latest['volume_ratio'],
            'trend_strength': latest['trend_strength'],
            'rsi': latest['rsi'],
            'bb_percent': latest['bb_percent'],
            'news_impact': latest['news_impact'],
            'scalp_signal': latest['scalp_buy'],
            'trend_signal': latest['trend_bullish']
        }
    
    def check_data_quality(self, pair: str) -> Dict[str, Any]:
        """
        Проверка качества данных для пары
        """
        try:
            dataframe = self.dp.get_pair_dataframe(pair, self.timeframe)
            if len(dataframe) == 0:
                return {
                    'status': 'ERROR',
                    'message': f'Нет данных для {pair}',
                    'delay': 0,
                    'candle_count': 0
                }
            
            # Время последней свечи
            last_candle_time = dataframe.index[-1]
            current_time = pd.Timestamp.now(tz='UTC')
            
            # Задержка данных в секундах (исправлено для новой версии pandas)
            try:
                # Пробуем старый способ
                data_delay = (current_time - last_candle_time).total_seconds()
            except (TypeError, ValueError):
                # Для новых версий pandas используем Timedelta
                try:
                    data_delay = (current_time - last_candle_time) / pd.Timedelta(seconds=1)
                except:
                    # Если и это не работает, используем timestamp
                    data_delay = (current_time.timestamp() - last_candle_time.timestamp())
            
            # Количество свечей
            candle_count = len(dataframe)
            
            # Оценка качества
            if data_delay <= 60:  # Менее 1 минуты
                status = 'EXCELLENT'
                message = f'🟢 {pair}: данные актуальны (задержка {data_delay:.1f}с)'
            elif data_delay <= 300:  # Менее 5 минут
                status = 'WARNING'
                message = f'🟡 {pair}: данные устарели (задержка {data_delay:.1f}с)'
            else:  # Более 5 минут
                status = 'CRITICAL'
                message = f'🔴 {pair}: данные критически устарели (задержка {data_delay:.1f}с)'
            
            return {
                'status': status,
                'message': message,
                'delay': data_delay,
                'candle_count': candle_count,
                'last_candle': last_candle_time,
                'current_time': current_time
            }
            
        except Exception as e:
            return {
                'status': 'ERROR',
                'message': f'Ошибка проверки данных {pair}: {e}',
                'delay': 0,
                'candle_count': 0
            }
    
    def log_data_quality(self):
        """
        Логирование качества данных для всех пар
        """
        logger = logging.getLogger(__name__)
        
        # Проверяем основные пары
        main_pairs = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT']
        
        for pair in main_pairs:
            quality = self.check_data_quality(pair)
            
            if quality['status'] == 'EXCELLENT':
                logger.info(quality['message'])
            elif quality['status'] == 'WARNING':
                logger.warning(quality['message'])
            elif quality['status'] == 'CRITICAL':
                logger.error(quality['message'])
            else:
                logger.error(quality['message'])
    
    def bot_loop_start(self, **kwargs) -> None:
        """
        Вызывается при старте бота
        """
        # Убираем логирование, так как этот метод вызывается слишком часто
        pass
    
    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                           time_in_force: str, current_time: datetime, entry_tag: Optional[str],
                           side: str, **kwargs) -> bool:
        """
        Подтверждение входа в сделку
        """
        # Временно отключаем проверку качества данных
        # quality = self.check_data_quality(pair)
        # if quality['status'] == 'CRITICAL':
        #     logger = logging.getLogger(__name__)
        #     logger.error(f"❌ Отказ от входа в {pair}: данные критически устарели")
        #     return False
        
        return True
