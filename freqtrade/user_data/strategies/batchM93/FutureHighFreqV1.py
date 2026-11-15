from freqtrade.strategy import IStrategy
from pandas import DataFrame
from datetime import datetime
from typing import List
import talib.abstract as ta


class FutureHighFreqV1(IStrategy):
    """
    Simple Trend Following Strategy

    Buy when:
    - EMA 9 > EMA 21 (confirmed trend)
    - Price above EMA 50 (major trend)
    - RSI not overbought

    Sell when:
    - EMA 9 < EMA 21 (trend reversal)
    - Or RSI overbought
    """

    timeframe = '5m'
    max_open_trades = 10
    stake_amount = 0.10
    startup_candle_count = 300

    # Higher profit targets for strong trends
    minimal_roi = {
        "0": 0.03,   # 3% quick
        "60": 0.02,  # 2% in 1h
        "180": 0.01, # 1% in 3h
        "360": 0.005 # 0.5% in 6h
    }

    stoploss = -0.015
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.015
    trailing_only_offset_is_reached = True

    order_types = {
        'entry': 'market',
        'exit': 'market',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    unfilledtimeout = {
        'entry': 10,
        'exit': 10,
        'unit': 'seconds'
    }

    # ===== Parameters =====
    fast_ema = 9
    slow_ema = 21
    ema50_period = 50
    rsi_period = 14
    rsi_buy = 60
    rsi_sell = 75

    cooldown_period = 5

    def informative_pairs(self) -> List[tuple]:
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['fast_ema'] = ta.EMA(dataframe, timeperiod=self.fast_ema)
        dataframe['slow_ema'] = ta.EMA(dataframe, timeperiod=self.slow_ema)
        dataframe['ema50'] = ta.EMA(dataframe, timeperiod=self.ema50_period)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=self.rsi_period)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Strong trend: Fast > Slow > EMA50
        strong_trend = (
            (dataframe['fast_ema'] > dataframe['slow_ema']) &
            (dataframe['slow_ema'] > dataframe['ema50'])
        )

        # RSI not overbought
        rsi_ok = dataframe['rsi'] < self.rsi_buy

        conditions = strong_trend & rsi_ok & (dataframe['volume'] > 0)
        dataframe.loc[conditions, 'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Trend reversal
        trend_reversal = dataframe['fast_ema'] < dataframe['slow_ema']

        # Or RSI overbought
        overbought = dataframe['rsi'] > self.rsi_sell

        conditions = (trend_reversal | overbought) & (dataframe['volume'] > 0)
        dataframe.loc[conditions, 'exit'] = 1
        return dataframe
