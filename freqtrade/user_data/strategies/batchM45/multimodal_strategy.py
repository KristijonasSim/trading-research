from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
import talib.abstract as ta
import numpy as np
import redis
import json
import os

class MultiModalStrategy(IStrategy):
    # ========== Общие настройки ==========
    minimal_roi = {"0": 0.01}
    stoploss = -0.10
    timeframe = '5m'
    startup_candle_count = 100
    can_short = True  # Включаем поддержку short
    process_only_new_candles = True
    use_exit_signal = True
    ignore_roi_if_entry_signal = True

    # ========== Подключение FreqAI ==========
    use_custom_stoploss = True  # для вызова custom_stoploss()
    use_custom_exit = True      # для RL-выхода
    custom_trade_info = {}      # хранение мета-инфо по трейду

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        # Redis: для общения с RL-агентом и LLM-фильтром
        self.redis = redis.Redis(host='localhost', port=6379, db=0)
        
        # Конфигурируемые пороги
        self.freqai_threshold = float(os.getenv("FREQAI_THRESHOLD", "0.005"))
        self.sentiment_threshold = float(os.getenv("SENTIMENT_THRESHOLD", "0.1"))
        self.volatility_multiplier = float(os.getenv("VOLATILITY_MULTIPLIER", "1.2"))

    # ========== Технические индикаторы ==========
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=12)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=26)
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['volume_mean'] = dataframe['volume'].rolling(20).mean()
        dataframe['vol_spike'] = dataframe['volume'] > 1.5 * dataframe['volume_mean']

        # FreqAI sanity check
        if not hasattr(self, "freqai"):
            self.logger.warning("FreqAI не инициализирован")
            return dataframe

        # Запуск FreqAI
        self.freqai.start(dataframe, metadata)

        return dataframe

    # ========== Сигналы на вход ==========
    def populate_entry_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        # Учет волатильности для фильтрации сигналов
        df['atr_mean'] = df['atr'].rolling(30).mean()
        df['low_volatility'] = df['atr'] < df['atr_mean'] * self.volatility_multiplier
        
        df['enter_long'] = (
            (df['rsi'] < 35) &
            (df['ema_fast'] > df['ema_slow']) &
            (df['freqai_prediction'] > self.freqai_threshold) &
            (df['low_volatility']) &
            (self._is_sentiment_positive())
        )

        df['enter_short'] = (
            (df['rsi'] > 65) &
            (df['ema_fast'] < df['ema_slow']) &
            (df['freqai_prediction'] < -self.freqai_threshold) &
            (df['low_volatility']) &
            (self._is_sentiment_negative())
        )

        return df

    # ========== Сигналы на выход ==========
    def populate_exit_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        df['exit_long'] = df['rsi'] > 70
        df['exit_short'] = df['rsi'] < 30
        return df

    # ========== Кастомный SL от RL-агента ==========
    def custom_stoploss(self, pair: str, trade, current_time, current_rate, current_profit, **kwargs):
        redis_key = f"sl_override:{trade.open_date_utc.timestamp()}"
        sl_value = self.redis.get(redis_key)
        if sl_value:
            sl_float = float(sl_value)
            return sl_float  # формат: -0.02, -0.03 и т.п.
        return 1  # fallback: оставить SL как есть

    # ========== Выход по RL/внешнему сигналу ==========
    def custom_exit(self, pair: str, trade, current_time, current_rate, current_profit, **kwargs):
        try:
            action_json = self.redis.get(f"exit_action:{trade.open_date_utc.timestamp()}")
            if action_json:
                action = json.loads(action_json)
                if action.get("close", False):
                    return "exit_by_rl"
        except Exception as e:
            self.logger.error(f"RL exit error: {e}")
        return None

    # ========== Вспомогательные функции ==========
    def _is_sentiment_positive(self) -> bool:
        try:
            val = float(self.redis.get("sentiment_score") or 0)
            return val > self.sentiment_threshold
        except Exception as e:
            self.logger.warning(f"Redis sentiment недоступен: {e}")
            return True  # если Redis упал — не мешать

    def _is_sentiment_negative(self) -> bool:
        try:
            val = float(self.redis.get("sentiment_score") or 0)
            return val < -self.sentiment_threshold
        except Exception as e:
            self.logger.warning(f"Redis sentiment недоступен: {e}")
            return True 