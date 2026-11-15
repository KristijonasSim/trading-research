# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
# --- Do not remove these libs ---
import numpy as np  # noqa
import pandas as pd  # noqa
from pandas import DataFrame

from freqtrade.strategy import (BooleanParameter, CategoricalParameter, DecimalParameter,
                                IStrategy, IntParameter)

# --------------------------------
# Add your lib to import here
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib


# This class is a sample. Feel free to customize it.
class MeanReversionATR(IStrategy):
    """


    You must keep:
    - the lib in the section "Do not remove these libs"
    - the methods: populate_indicators, populate_entry_trend, populate_exit_trend
    You should keep:
    - timeframe, minimal_roi, stoploss, trailing_*
    """
    # Strategy interface version - allow new iterations of the strategy interface.
    # Check the documentation or the Sample strategy to get the latest version.
    INTERFACE_VERSION = 3

    # Can this strategy go short?
    can_short: bool = False

    # Minimal ROI designed for the strategy.
    # This attribute will be overridden if the config file contains "minimal_roi".
    minimal_roi = {
        "60": 0.01,
        "30": 0.02,
        "0": 0.04
    }

    # Optimal stoploss designed for the strategy.
    # This attribute will be overridden if the config file contains "stoploss".
    stoploss = -0.10

    # Trailing stoploss
    trailing_stop = False
    # trailing_only_offset_is_reached = False
    # trailing_stop_positive = 0.01
    # trailing_stop_positive_offset = 0.0  # Disabled / not configured

    # Optimal timeframe for the strategy.
    timeframe = '1h'

    # Run "populate_indicators()" only for new candle.
    process_only_new_candles = True

    # These values can be overridden in the config.
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    ema_long_window = IntParameter(low=150, high=250, default=200, space='buy', optimize=True, load=True)
    ema_short_window = IntParameter(low=15, high=25, default=20, space='buy', optimize=True, load=True)

    atr_period = IntParameter(low=5, high=10, default=5, space='buy', optimize=True, load=True)
    atr_band = DecimalParameter(low=0.5, high=1.5, default=1, space='buy', optimize=True, load=True)

    atr_stretch = DecimalParameter(low=0.5, high=1.5, default=1, space='buy', optimize=True, load=True)
    # sell_band = CategoricalParameter(['Top', 'Middle', 'Bottom'],
    #                                  default='Middle',
    #                                  space='buy',
    #                                  optimize=True,
    #                                  load=True)

    # sell_src = CategoricalParameter(['open', 'high', 'low', 'close'],
    #                                 default='high',
    #                                 space='buy',
    #                                 optimize=True,
    #                                 load=True)

    # Number of candles the strategy requires before producing valid signals
    startup_candle_count: int = 250

    # Optional order type mapping.
    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    # Optional order time in force.
    order_time_in_force = {
        'entry': 'gtc',
        'exit': 'gtc'
    }

    plot_config = {
        'main_plot': {
            'ema_long': {'color': 'orange'},
            'atr_top': {'color': 'green'},
            'atr_bottom': {'color': 'red'},
        },
        'subplots': {

        }
    }

    def informative_pairs(self):
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['ema_short'] = ta.EMA(dataframe, timeperiod=self.ema_short_window.value)
        dataframe['ema_long'] = ta.EMA(dataframe, timeperiod=self.ema_long_window.value)
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=self.atr_period.value)
        dataframe['atr_top'] = dataframe['ema_short'] + (dataframe['atr'] * self.atr_band.value)
        dataframe['atr_bottom'] = dataframe['ema_short'] - (dataframe['atr'] * self.atr_band.value)
        dataframe['setup_condition'] = (dataframe['close'] < dataframe['atr_bottom']) & (
                dataframe['low'] > dataframe['ema_long'])

        dataframe['buy_limit_price'] = None
        dataframe['buy_limit_price'] = dataframe['buy_limit_price'].where(dataframe['setup_condition'],
                                                                          (dataframe['low'] - (dataframe[
                                                                                                   'atr'] * self.atr_stretch.value))
                                                                          )

        dataframe['previous_buy_limit_price'] = dataframe['buy_limit_price'].shift(1)
        dataframe['previous_buy_limit_price'] = dataframe['previous_buy_limit_price'].fillna(-1)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe['low'] <= dataframe['previous_buy_limit_price'])
            ),
            'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                    (dataframe['high'] > dataframe['ema_short']) | (dataframe['close'] < dataframe['ema_long'])
            ),
            'exit_long'] = 1

        return dataframe
