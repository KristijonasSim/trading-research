from freqtrade.strategy import IStrategy
from pandas import DataFrame
import pandas as pd
import talib.abstract as ta
from datetime import datetime


class FutureUltraMomentum(IStrategy):
    timeframe = '1m'
    max_open_trades = 1
    stake_amount = 100
    startup_candle_count = 100

    minimal_roi = {
        "0": 0.03,
        "60": 0.02,
        "180": 0.015,
        "360": 0.01
    }

    stoploss = -0.01
    trailing_stop = False

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
        'BTC/USDT:USDT': 30.0,
        'ETH/USDT:USDT': 30.0,
        'SOL/USDT:USDT': 25.0,
        'XRP/USDT:USDT': 25.0,
        'DOGE/USDT:USDT': 25.0
    }

    def informative_pairs(self) -> list:
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()

        # Core indicators
        df['rsi'] = ta.RSI(df['close'].values, timeperiod=14)
        df['rsi_6'] = ta.RSI(df['close'].values, timeperiod=6)
        df['volume_sma'] = ta.SMA(df['volume'].values, timeperiod=20)

        # Trend indicators
        df['ema_12'] = ta.EMA(df['close'].values, timeperiod=12)
        df['ema_26'] = ta.EMA(df['close'].values, timeperiod=26)
        df['ema_trend'] = (df['ema_12'] - df['ema_26']) / df['close']

        # Momentum indicators
        df['momentum'] = df['close'] / df['close'].shift(3) - 1
        df['momentum_6'] = df['close'] / df['close'].shift(6) - 1

        # Volatility
        df['atr'] = ta.ATR(df['high'].values, df['low'].values, df['close'].values, timeperiod=14)
        df['atr_percent'] = df['atr'] / df['close']

        # Volume indicators
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        df['volume_trend'] = df['volume'] / df['volume'].shift(3)

        # Price action
        df['high_5m'] = pd.Series(df['high']).rolling(5).max().values
        df['close_change'] = df['close'].pct_change(3)

        return df

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 current_profit: float, min_stops: float, max_stops: float,
                 current_time_rows: DataFrame, **kwargs) -> float:
        return self.leverage_config.get(pair, 25.0)

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        df['enter_long'] = 0

        if len(df) < self.startup_candle_count:
            return df

        # Optimized entry conditions balancing quality and frequency
        trend_up = df['ema_trend'] > 0.002  # Mild uptrend
        rsi_good = (df['rsi'] > 55) & (df['rsi'] < 75)  # RSI in favorable range
        rsi_not_overbought = df['rsi'] < 80  # Not overbought
        momentum_positive = df['momentum'] > 0.003  # Positive momentum
        volume_ok = df['volume_ratio'] > 1.3  # Decent volume
        price_stable = df['atr_percent'] < 0.04  # Reasonable volatility

        # Most conditions must be met (allow some flexibility)
        strong_setup = (
            trend_up &
            rsi_good &
            rsi_not_overbought &
            momentum_positive &
            volume_ok &
            price_stable
        )

        df.loc[strong_setup, 'enter_long'] = 1

        return df

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        df['exit'] = 0

        # Trend reversal exits
        trend_down = df['ema_trend'] < -0.005
        rsi_overbought = df['rsi'] > 80
        momentum_weak = df['momentum'] < -0.005

        df.loc[trend_down | rsi_overbought | momentum_weak, 'exit'] = 1

        return df

    def custom_exit(self, pair: str, current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs) -> bool:
        # Partial profit taking for better risk management
        if current_profit > 0.025:  # Take 50% profit at 2.5%
            return True
        if current_profit > 0.05:   # Take remaining at 5%
            return True
        if current_profit < -0.015: # Stop loss at -1.5%
            return True
        return False
