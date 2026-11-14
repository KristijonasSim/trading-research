
import numpy as np
import pandas as pd
from pandas import DataFrame
from freqtrade.strategy import IStrategy
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib

class HeikinAshiStrategy(IStrategy):
    """
    Heikin Ashi Strategy for Futures (Long/Short)
    
    Indicators:
    - Heikin Ashi Candles (calculated manually)
    - EMA 50 (Trend Direction)
    - ADX 14 (Trend Strength)
    
    Entry Logic:
    - Long: HA Green Candle + Close > EMA 50 + ADX > 25
    - Short: HA Red Candle + Close < EMA 50 + ADX > 25
    
    Exit Logic:
    - Trend Reversal (HA color flip) or Stoploss/ROI
    """

    INTERFACE_VERSION = 3

    # Minimal ROI
    minimal_roi = {
        "60": 0.01,
        "30": 0.03,
        "0": 0.04
    }

    # Stoploss
    stoploss = -0.10

    # Trailing Stop
    trailing_stop = False

    # Timeframe
    timeframe = '5m'

    # Can this strategy go short?
    can_short = True

    # Startup Candle Count (need enough for EMA/ADX/HA)
    startup_candle_count: int = 50

    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    order_time_in_force = {
        'entry': 'gtc',
        'exit': 'gtc'
    }

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 1. Heikin Ashi Calculation
        # HA_Close = (Open + High + Low + Close) / 4
        dataframe['ha_close'] = (dataframe['open'] + dataframe['high'] + dataframe['low'] + dataframe['close']) / 4

        # HA_Open = (Previous HA_Open + Previous HA_Close) / 2
        # Note: This is recursive, so we use shift() + manual iteration or pandas-ta if available. 
        # For speed in vectorized backtesting, we can approximate or iterate.
        # Freqtrade recommends qtpylib.heikinashi or manual implementation.
        
        # Using qtpylib if available is best, but let's do a robust manual version for clarity using standard methods
        heikinashi = qtpylib.heikinashi(dataframe)
        dataframe['ha_open'] = heikinashi['open']
        dataframe['ha_close'] = heikinashi['close']
        dataframe['ha_high'] = heikinashi['high']
        dataframe['ha_low'] = heikinashi['low']

        # 2. Trend Indicators (EMA)
        dataframe['ema_50'] = ta.EMA(dataframe, timeperiod=50)

        # 3. Strength Indicator (ADX)
        dataframe['adx'] = ta.ADX(dataframe)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Entry signals
        """
        # LONG Entry
        dataframe.loc[
            (
                (dataframe['volume'] > 0) &
                (dataframe['ha_close'] > dataframe['ha_open']) &  # Green HA Candle
                (dataframe['close'] > dataframe['ema_50']) &      # Price above moving average
                (dataframe['adx'] > 25)                           # Strong trend
            ),
            'enter_long'] = 1

        # SHORT Entry
        dataframe.loc[
            (
                (dataframe['volume'] > 0) &
                (dataframe['ha_close'] < dataframe['ha_open']) &  # Red HA Candle
                (dataframe['close'] < dataframe['ema_50']) &      # Price below moving average
                (dataframe['adx'] > 25)                           # Strong trend
            ),
            'enter_short'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Exit signals (optional, if using ROI/Stoploss primarily)
        """
        # Exit LONG if significant reversal (Red HA Candle)
        dataframe.loc[
            (
                (dataframe['ha_close'] < dataframe['ha_open'])    # Red HA Candle
            ),
            'exit_long'] = 1

        # Exit SHORT if significant reversal (Green HA Candle)
        dataframe.loc[
            (
                (dataframe['ha_close'] > dataframe['ha_open'])    # Green HA Candle
            ),
            'exit_short'] = 1

        return dataframe
