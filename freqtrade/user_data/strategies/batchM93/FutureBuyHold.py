from freqtrade.strategy import IStrategy
from pandas import DataFrame
import pandas as pd
from datetime import datetime


class FutureBuyHold(IStrategy):
    timeframe = '1m'
    max_open_trades = 3
    stake_amount = 0.30
    startup_candle_count = 100

    minimal_roi = {
        "0": 0.03,
        "60": 0.02,
        "180": 0.015,
        "360": 0.01,
        "720": 0.005
    }

    stoploss = -0.08
    trailing_stop = True
    trailing_stop_positive = 0.025
    trailing_stop_positive_offset = 0.035
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
        'DOGE/USDT:USDT': 3.0
    }

    def informative_pairs(self) -> list:
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        df['ema_20'] = pd.Series(df['close']).ewm(span=20, adjust=False).mean()
        df['ema_50'] = pd.Series(df['close']).ewm(span=50, adjust=False).mean()
        return df

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 current_profit: float, min_stops: float, max_stops: float,
                 current_time_rows: DataFrame, **kwargs) -> float:
        return self.leverage_config.get(pair, 3.0)

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        df['enter_long'] = 0

        if len(df) < self.startup_candle_count:
            return df

        uptrend = df['close'] > df['ema_50']
        df.loc[uptrend, 'enter_long'] = 1

        return df

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        df['exit'] = 0

        strong_down = df['close'] < df['ema_20']
        df.loc[strong_down, 'exit'] = 1

        return df
