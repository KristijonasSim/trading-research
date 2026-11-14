from pandas import DataFrame
import talib.abstract as ta

from freqtrade.strategy import IStrategy
from freqtrade.vendor.qtpylib import indicators as qtpylib


class PersonalBaselineStrategy(IStrategy):
    """A deliberately simple pipeline-smoke strategy, not a qualified edge."""

    INTERFACE_VERSION = 3
    timeframe = "15m"
    can_short = False
    process_only_new_candles = True
    startup_candle_count = 60

    minimal_roi = {"0": 0.03, "720": 0.01}
    stoploss = -0.08
    trailing_stop = False
    use_exit_signal = True

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=50)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            qtpylib.crossed_above(dataframe["ema_fast"], dataframe["ema_slow"])
            & (dataframe["volume"] > 0),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            qtpylib.crossed_below(dataframe["ema_fast"], dataframe["ema_slow"])
            & (dataframe["volume"] > 0),
            "exit_long",
        ] = 1
        return dataframe

