from freqtrade.strategy import IStrategy
from pandas import DataFrame
import pandas as pd
from datetime import datetime


class FutureLeveragedHold(IStrategy):
    timeframe = '1h'
    max_open_trades = 3
    stake_amount = 0.30
    startup_candle_count = 20

    minimal_roi = {
        "0": 0.03,
        "24": 0.02,
        "48": 0.015,
        "72": 0.01,
        "168": 0.005
    }

    stoploss = -0.05
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.025
    trailing_only_offset_is_reached = True

    order_types = {
        'entry': 'market',
        'exit': 'market',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    unfilledtimeout = {
        'entry': 30,
        'exit': 30,
        'unit': 'seconds'
    }

    leverage_config = {
        'BTC/USDT:USDT': 5.0,
        'ETH/USDT:USDT': 5.0,
        'SOL/USDT:USDT': 5.0,
        'XRP/USDT:USDT': 3.0,
        'DOGE/USDT:USDT': 3.0,
        'LTC/USDT:USDT': 3.0,
        'LINK/USDT:USDT': 3.0,
        'UNI/USDT:USDT': 3.0,
        'ARB/USDT:USDT': 3.0,
        'OP/USDT:USDT': 3.0
    }

    def informative_pairs(self) -> list:
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 current_profit: float, min_stops: float, max_stops: float,
                 current_time_rows: DataFrame, **kwargs) -> float:
        leverage = self.leverage_config.get(pair, 3.0)
        return min(leverage, 5.0)

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        df['enter_long'] = 0

        if len(df) < self.startup_candle_count:
            return df

        df['ema_9'] = pd.Series(df['close']).ewm(span=9, adjust=False).mean()
        df['ema_21'] = pd.Series(df['close']).ewm(span=21, adjust=False).mean()

        df['trend_up'] = df['ema_9'] > df['ema_21']

        df.loc[df['trend_up'], 'enter_long'] = 1

        return df

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        df['exit'] = 0

        df['ema_9'] = pd.Series(df['close']).ewm(span=9, adjust=False).mean()
        df['ema_21'] = pd.Series(df['close']).ewm(span=21, adjust=False).mean()

        df['trend_down'] = df['ema_9'] < df['ema_21']

        df.loc[df['trend_down'], 'exit'] = 1

        return df
