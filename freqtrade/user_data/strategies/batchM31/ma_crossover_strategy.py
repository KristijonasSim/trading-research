import talib
from freqtrade.strategy import IStrategy, merge_informative_pair
from pandas import DataFrame
import numpy as np


class MACrossoverStrategy(IStrategy):
    """
    Simple Moving Average Crossover Strategy
    
    Entry: When fast MA crosses above slow MA (bullish signal)
    Exit: When fast MA crosses below slow MA (bearish signal)
    """

    INTERFACE_VERSION = 3
    
    # Buy hyperspace parameters
    buy_ma_fast = 9
    buy_ma_slow = 21
    
    # Sell hyperspace parameters
    sell_ma_fast = 9
    sell_ma_slow = 21
    
    # Stoploss
    stoploss = -0.10
    
    # Trailing stop
    trailing_stop = False
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02
    trailing_only_offset_is_reached = True
    
    # Optimal timeframe
    timeframe = '5m'
    
    # Can short
    can_short = False

    def informative_pairs(self):
        """
        Define additional candle (OHLCV) pairs to be requested.
        """
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Add technical indicators to the dataframe.
        
        Args:
            dataframe: OHLCV data
            metadata: Additional metadata (symbol, etc.)
            
        Returns:
            DataFrame with indicators
        """
        # Calculate moving averages
        dataframe['ma_fast'] = talib.SMA(dataframe['close'], timeperiod=self.buy_ma_fast)
        dataframe['ma_slow'] = talib.SMA(dataframe['close'], timeperiod=self.buy_ma_slow)
        
        # Calculate RSI for additional filtering (optional)
        dataframe['rsi'] = talib.RSI(dataframe['close'], timeperiod=14)
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate BUY signal for the given dataframe.
        """
        dataframe.loc[
            (
                # Bullish crossover: fast MA crosses above slow MA
                (dataframe['ma_fast'] > dataframe['ma_slow']) &
                (dataframe['ma_fast'].shift(1) <= dataframe['ma_slow'].shift(1)) &
                # Optional: RSI filter to avoid overbought conditions
                (dataframe['rsi'] < 70) &
                # Volume filter (optional)
                (dataframe['volume'] > 0)
            ),
            'enter_long'] = 1
            
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate SELL signal for the given dataframe.
        """
        dataframe.loc[
            (
                # Bearish crossover: fast MA crosses below slow MA
                (dataframe['ma_fast'] < dataframe['ma_slow']) &
                (dataframe['ma_fast'].shift(1) >= dataframe['ma_slow'].shift(1)) &
                (dataframe['volume'] > 0)
            ),
            'exit_long'] = 1

        return dataframe
