from freqtrade.strategy import IStrategy
from pandas import DataFrame
from typing import List
import talib.abstract as ta


class FutureMeanRevV1(IStrategy):
    """
    Futures Mean Reversion Strategy V1

    Strategy logic:
    - Uses Bollinger Bands and RSI for mean reversion trading
    - Buy when price touches lower Bollinger Band and RSI < 35
    - Sell when price touches upper Bollinger Band or RSI > 75
    """

    # Base configuration from BaseFuturesStrategy
    minimal_roi = {
        "0": 0.05
    }
    stoploss = -0.03
    trailing_stop = False
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02
    trailing_only_offset_is_reached = False
    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }
    timeframe = '5m'
    stake_amount = 0.01
    startup_candle_count = 300
    unfilledtimeout = {
        'entry': 10,
        'exit': 10,
        'exit_timeout_count': 0,
        'unit': 'seconds'
    }

    # Strategy-specific parameters
    bb_period = 20
    bb_std = 2.0
    rsi_period = 14
    rsi_oversold = 35
    rsi_overbought = 75

    def informative_pairs(self) -> List[tuple]:
        """
        Define informative pairs.
        """
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Calculate indicators for the strategy.
        """
        bb = ta.BBANDS(dataframe, timeperiod=self.bb_period, nbdevup=self.bb_std, nbdevdn=self.bb_std)
        dataframe['bb_lower'] = bb['lowerband']
        dataframe['bb_middle'] = bb['middleband']
        dataframe['bb_upper'] = bb['upperband']

        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=self.rsi_period)

        dataframe['bb_position'] = (dataframe['close'] - dataframe['bb_lower']) / (dataframe['bb_upper'] - dataframe['bb_lower'])

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Entry signal logic.
        """
        dataframe.loc[
            (dataframe['bb_position'] < 0.05) &
            (dataframe['rsi'] < self.rsi_oversold) &
            (dataframe['volume'] > 0),
            'enter_long'
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Exit signal logic.
        """
        dataframe.loc[
            (
                (dataframe['bb_position'] > 0.95) |
                (dataframe['rsi'] > self.rsi_overbought)
            ) &
            (dataframe['volume'] > 0),
            'exit'
        ] = 1

        return dataframe
