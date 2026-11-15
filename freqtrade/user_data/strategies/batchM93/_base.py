from freqtrade.strategy import IStrategy
from pandas import DataFrame
from typing import Dict, List


class BaseFuturesStrategy(IStrategy):
    """
    Base class for futures trading strategies.
    Provides common functionality for all futures strategies.
    """

    # Define minimal ROI
    minimal_roi = {
        "0": 0.05
    }

    # Define stoploss
    stoploss = -0.03

    # Use trailing stop
    trailing_stop = False
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02
    trailing_only_offset_is_reached = False

    # Order types
    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    # Timeframe for the strategy
    timeframe = '5m'

    # Stake amount in USDT
    stake_amount = 0.01

    # Number of startup candles
    startup_candle_count = 300

    # Unfilled timeout
    unfilledtimeout = {
        'entry': 10,
        'exit': 10,
        'exit_timeout_count': 0,
        'unit': 'seconds'
    }

    def informative_pairs(self) -> List[tuple]:
        """
        Define additional informative pairs.
        """
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        This method is invoked for each candle and should implement the indicators creation logic.
        """
        # Base implementation - to be overridden by specific strategies
        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        This method is invoked for each candle and should implement the buy signal logic.
        """
        # Base implementation - to be overridden by specific strategies
        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        This method is invoked for each candle and should implement the sell signal logic.
        """
        # Base implementation - to be overridden by specific strategies
        return dataframe