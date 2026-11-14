"""Installation example only; no profitability claim. Long/short at 1x."""
from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta
from technical import qtpylib

class StarterFutures(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "15m"
    can_short = True
    startup_candle_count = 200
    process_only_new_candles = True
    minimal_roi = {"0": 0.04}
    stoploss = -0.02
    use_exit_signal = True
    order_types = {"entry": "market", "exit": "market", "stoploss": "market", "stoploss_on_exchange": False}

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[qtpylib.crossed_above(dataframe["ema_fast"], dataframe["ema_slow"]) & (dataframe["rsi"] > 50) & (dataframe["volume"] > 0), ["enter_long", "enter_tag"]] = (1, "ema_long")
        dataframe.loc[qtpylib.crossed_below(dataframe["ema_fast"], dataframe["ema_slow"]) & (dataframe["rsi"] < 50) & (dataframe["volume"] > 0), ["enter_short", "enter_tag"]] = (1, "ema_short")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[qtpylib.crossed_below(dataframe["ema_fast"], dataframe["ema_slow"]) & (dataframe["volume"] > 0), "exit_long"] = 1
        dataframe.loc[qtpylib.crossed_above(dataframe["ema_fast"], dataframe["ema_slow"]) & (dataframe["volume"] > 0), "exit_short"] = 1
        return dataframe

    def leverage(self, pair, current_time, current_rate, proposed_leverage, max_leverage, entry_tag, side, **kwargs):
        return 1.0

    plot_config = {"main_plot": {"ema_fast": {}, "ema_slow": {}}, "subplots": {"RSI": {"rsi": {}}}}
