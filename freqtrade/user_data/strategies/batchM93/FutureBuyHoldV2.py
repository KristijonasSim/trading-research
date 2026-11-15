from freqtrade.strategy import IStrategy
from pandas import DataFrame
import pandas as pd
from datetime import datetime


class FutureBuyHoldV2(IStrategy):
    timeframe = '1m'
    max_open_trades = 3
    stake_amount = 100
    startup_candle_count = 100

    minimal_roi = {
        "0": 0.025,
        "60": 0.018,
        "180": 0.012,
        "360": 0.008,
        "720": 0.005
    }

    stoploss = -0.05
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.028
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

        close = df['close'].values

        df['ema_20'] = pd.Series(close).ewm(span=20, adjust=False).mean().values
        df['ema_50'] = pd.Series(close).ewm(span=50, adjust=False).mean().values

        df['atr'] = self._calculate_atr(df, 14)

        return df

    def _calculate_atr(self, df: DataFrame, period: int) -> list:
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values

        tr = []
        for i in range(len(close)):
            if i == 0:
                tr.append(high[i] - low[i])
            else:
                hl = high[i] - low[i]
                hc = abs(high[i] - close[i-1])
                lc = abs(low[i] - close[i-1])
                tr.append(max(hl, hc, lc))

        atr = pd.Series(tr).rolling(period).mean().values
        return atr

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 current_profit: float, min_stops: float, max_stops: float,
                 current_time_rows: DataFrame, **kwargs) -> float:
        leverage = self.leverage_config.get(pair, 3.0)

        if current_profit < -0.03:
            leverage = leverage * 0.5
        elif current_profit < -0.02:
            leverage = leverage * 0.75

        return min(leverage, 5.0)

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

    def custom_stoploss(self, pair: str, current_time: datetime, current_rate: float,
                        current_profit: float, min_stops: float, max_stops: float,
                        current_time_rows: DataFrame, **kwargs) -> float:
        if current_profit > 0.02:
            return 0
        if current_profit > 0.01:
            return -0.02
        return -0.05
