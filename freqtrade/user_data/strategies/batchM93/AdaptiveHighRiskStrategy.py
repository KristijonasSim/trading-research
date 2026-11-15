from freqtrade.strategy import IStrategy
from pandas import DataFrame
import pandas as pd
import talib.abstract as ta
import numpy as np
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
import joblib
import os


class AdaptiveHighRiskStrategy(IStrategy):
    """
    Adaptive High Risk Strategy for High Returns

    Features:
    - Market regime detection (trending vs ranging)
    - Dynamic leverage adjustment (20x-50x)
    - Multiple entry/exit strategies
    - Risk management with high drawdown tolerance
    """

    timeframe = '1m'
    max_open_trades = 3
    stake_amount = 100
    startup_candle_count = 200

    minimal_roi = {
        "0": 0.01,
        "30": 0.008,
        "60": 0.005,
        "120": 0.003
    }

    stoploss = -0.015
    trailing_stop = True
    trailing_stop_positive = 0.03
    trailing_stop_positive_offset = 0.04
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
        'ETH/USDT:USDT': 4.0,
        'SOL/USDT:USDT': 3.0,
        'XRP/USDT:USDT': 2.0,
        'DOGE/USDT:USDT': 2.0
    }

    def informative_pairs(self) -> list:
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()

        # Core indicators for winter market
        df['ema_9'] = ta.EMA(df['close'].values, timeperiod=9)
        df['ema_21'] = ta.EMA(df['close'].values, timeperiod=21)
        df['ema_50'] = ta.EMA(df['close'].values, timeperiod=50)
        df['rsi'] = ta.RSI(df['close'].values, timeperiod=14)
        df['volume_sma'] = ta.SMA(df['volume'].values, timeperiod=20)
        df['volume_ratio'] = df['volume'] / df['volume_sma']

        # Momentum indicators
        df['momentum'] = df['close'] / df['close'].shift(3) - 1

        # Market regime detection (simplified)
        df['returns'] = df['close'].pct_change()
        df['volatility'] = df['returns'].rolling(20).std()
        df['trend_strength'] = abs(df['ema_9'] - df['ema_21']) / df['close']

        # Very lenient regime detection for current market
        # Allow trading in any regime with basic trend
        df['regime'] = np.where(df['trend_strength'] > 0.005, 2,  # Very low threshold for trending
                               np.where(df['volatility'] > df['volatility'].rolling(50).mean() * 1.1, 1, 0))  # Volatile, Ranging

        # MACD for timing
        macd, macdsignal, macdhist = ta.MACD(df['close'].values)
        df['macd'] = macd
        df['macd_signal'] = macdsignal
        df['macd_hist'] = macdhist

        # Bollinger Bands
        df['bb_upper'], df['bb_middle'], df['bb_lower'] = ta.BBANDS(df['close'].values)
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])

        return df

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 current_profit: float = 0.0, min_stops: float = 0.0,
                 max_stops: float = 0.0, current_time_rows: DataFrame = None,
                 **kwargs) -> float:
        base_leverage = self.leverage_config.get(pair, 25.0)

        # Adjust based on current profit (only available after position is open)
        if current_profit > 0.05:
            base_leverage *= 1.1  # Increase leverage when winning
        elif current_profit < -0.05:
            base_leverage *= 0.9  # Decrease when losing

        return min(base_leverage, 50.0)  # Cap at 50x

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        df['enter_long'] = 0

        if len(df) < self.startup_candle_count:
            return df

        # Different strategies for different market regimes
        regime = df['regime']

        # Strategy 1: Trending market (conservative winter entries)
        trending_condition = (
            (regime == 2) &  # Only trending regime for winter
            (df['ema_9'] > df['ema_21']) &  # Clear uptrend
            (df['ema_21'] > df['ema_50']) &  # Strong uptrend confirmation
            (df['rsi'] > 50) & (df['rsi'] < 75) &  # RSI in optimal range
            (df['macd'] > df['macd_signal']) &  # MACD bullish
            (df['volume_ratio'] > 1.5) &  # Good volume confirmation
            (df['trend_strength'] > 0.01) &  # Decent trend strength
            (df['momentum'] > 0.005)  # Positive momentum
        )

        # Strategy 2: High volatility market (mean reversion entries)
        volatile_condition = (
            (regime == 1) &  # High volatility regime
            (df['bb_position'] < 0.2) &  # Price near lower BB
            (df['rsi'] < 35) &  # Oversold
            (df['volume_ratio'] > 2.0) &  # High volume
            (df['volatility'] > df['volatility'].shift(1))  # Increasing volatility
        )

        # Strategy 3: Ranging market (breakout entries)
        ranging_condition = (
            (regime == 0) &  # Ranging regime
            (df['close'] > df['bb_upper'].shift(1)) &  # Break upper BB
            (df['rsi'] > 70) &  # RSI confirming
            (df['volume_ratio'] > 1.8) &  # Volume spike
            (df['macd_hist'] > 0)  # MACD positive
        )

        # Only use trending condition for quality control
        # Comment out volatile and ranging for now to focus on trending
        # volatile_condition = ...
        # ranging_condition = ...

        entry_signal = trending_condition

        df.loc[entry_signal, 'enter_long'] = 1

        return df

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        df['exit'] = 0

        # Dynamic exit conditions based on regime
        regime = df['regime']

        # Exit conditions vary by market type
        trending_exit = (
            (regime == 2) & (
                (df['ema_9'] < df['ema_21']) |  # Trend reversal
                (df['rsi'] > 90) |  # Overbought
                (df['macd'] < df['macd_signal'])  # MACD bearish
            )
        )

        volatile_exit = (
            (regime == 1) & (
                (df['bb_position'] > 0.8) |  # Near upper BB
                (df['rsi'] > 75) |  # RSI overbought
                (df['macd'] < df['macd_signal'])  # MACD bearish
            )
        )

        ranging_exit = (
            (regime == 0) & (
                (df['close'] < df['bb_middle']) |  # Return to middle
                (df['rsi'] > 80) |  # Overbought
                (df['macd_hist'] < df['macd_hist'].shift(1))  # MACD weakening
            )
        )

        exit_signal = trending_exit | volatile_exit | ranging_exit
        df.loc[exit_signal, 'exit'] = 1

        return df

    def custom_exit(self, pair: str, current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs) -> bool:
        # Winter market profit taking - let profits run longer
        if current_profit > 0.12:  # Take profit at 12% (higher threshold)
            return True
        if current_profit > 0.25:  # Take all profit at 25% (let big wins run)
            return True
        if current_profit < -0.025:  # Stop loss at -2.5% (tighter in winter)
            return True
        return False
