from freqtrade.strategy import IStrategy, DecimalParameter, IntParameter
from pandas import DataFrame
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib


class EMA_RSI_Strategy(IStrategy):
    """
    EMA crossover + RSI filter strategy for low-capital Binance spot trading.
    Timeframe: 5m | Pairs: XRP/USDT, DOGE/USDT, ADA/USDT, TRX/USDT
    """

    INTERFACE_VERSION = 3
    timeframe = "5m"
    can_short = False

    # ROI table
    minimal_roi = {
        "0": 0.05,
        "30": 0.025,
        "60": 0.01
    }

    # Stop-loss
    stoploss = -0.03
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.015
    trailing_only_offset_is_reached = True

    # Startup candles needed
    startup_candle_count: int = 50

    # Hyperopt parameters
    buy_ema_fast = IntParameter(8, 20, default=12, space="buy")
    buy_ema_slow = IntParameter(21, 50, default=26, space="buy")
    buy_rsi_low = IntParameter(25, 45, default=35, space="buy")
    buy_rsi_high = IntParameter(50, 70, default=60, space="buy")
    sell_rsi = IntParameter(60, 80, default=70, space="sell")

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # EMA
        for val in self.buy_ema_fast.range:
            dataframe[f"ema_fast_{val}"] = ta.EMA(dataframe, timeperiod=val)
        for val in self.buy_ema_slow.range:
            dataframe[f"ema_slow_{val}"] = ta.EMA(dataframe, timeperiod=val)

        # RSI
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        # Volume SMA for confirmation
        dataframe["volume_sma"] = ta.SMA(dataframe["volume"], timeperiod=20)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        fast = self.buy_ema_fast.value
        slow = self.buy_ema_slow.value

        dataframe.loc[
            (
                # EMA crossover: fast crosses above slow
                qtpylib.crossed_above(
                    dataframe[f"ema_fast_{fast}"],
                    dataframe[f"ema_slow_{slow}"]
                ) &
                # RSI in buy zone (not overbought, not too low = trend confirmed)
                (dataframe["rsi"] > self.buy_rsi_low.value) &
                (dataframe["rsi"] < self.buy_rsi_high.value) &
                # Volume above average (real move)
                (dataframe["volume"] > dataframe["volume_sma"] * 0.8) &
                (dataframe["volume"] > 0)
            ),
            "enter_long"
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        fast = self.buy_ema_fast.value
        slow = self.buy_ema_slow.value

        dataframe.loc[
            (
                # EMA crossover: fast crosses below slow
                qtpylib.crossed_below(
                    dataframe[f"ema_fast_{fast}"],
                    dataframe[f"ema_slow_{slow}"]
                ) |
                # RSI overbought
                (dataframe["rsi"] > self.sell_rsi.value)
            ),
            "exit_long"
        ] = 1

        return dataframe
