from freqtrade.strategy import IStrategy
from pandas import DataFrame
import numpy as np
import pandas as pd
import talib.abstract as ta


class FutureMLV2(IStrategy):
    timeframe = '5m'
    max_open_trades = 5
    stake_amount = 0.20
    startup_candle_count = 200

    minimal_roi = {
        "0": 0.025,
        "60": 0.018,
        "180": 0.01,
        "360": 0.005
    }

    stoploss = -0.025
    trailing_stop = True
    trailing_stop_positive = 0.012
    trailing_stop_positive_offset = 0.018
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

    def informative_pairs(self) -> list:
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()

        close_arr = df['close'].values

        df['rsi'] = ta.RSI(close_arr, timeperiod=14)
        df['rsi_6'] = ta.RSI(close_arr, timeperiod=6)

        df['ema_9'] = ta.EMA(close_arr, timeperiod=9)
        df['ema_21'] = ta.EMA(close_arr, timeperiod=21)
        df['ema_50'] = ta.EMA(close_arr, timeperiod=50)

        df['ema_trend'] = (df['ema_9'] - df['ema_21']) / close_arr
        df['ema_trend_strong'] = ((df['ema_9'] - df['ema_50']) / close_arr)

        df['momentum'] = close_arr / np.roll(close_arr, 12) - 1
        df['momentum_6'] = close_arr / np.roll(close_arr, 6) - 1

        df['volatility'] = pd.Series(close_arr).pct_change().rolling(12).std().values

        df['rsi_trend'] = df['rsi'] - np.roll(df['rsi'], 6)

        return df

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        df['enter_long'] = 0

        if len(df) < self.startup_candle_count:
            return df

        try:
            uptrend = (
                (df['ema_9'] > df['ema_21']) &
                (df['ema_21'] > df['ema_50'])
            )

            rsi_ok = (df['rsi'] > 40) & (df['rsi'] < 70)

            rsi_rising = df['rsi_trend'] > 0

            momentum_ok = df['momentum'] > -0.02

            strong_buy = (
                uptrend &
                rsi_ok &
                rsi_rising &
                momentum_ok
            )

            df.loc[strong_buy, 'enter_long'] = 1

        except Exception:
            pass

        return df

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        df['exit'] = 0

        if len(df) < self.startup_candle_count:
            return df

        try:
            downtrend = (
                (df['ema_9'] < df['ema_21']) |
                (df['ema_21'] < df['ema_50'])
            )

            overbought = df['rsi'] > 80

            rsi_falling = df['rsi_trend'] < -5

            sell = downtrend | overbought | rsi_falling

            df.loc[sell, 'exit'] = 1

        except Exception:
            pass

        return df
