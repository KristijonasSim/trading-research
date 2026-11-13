# Mahan's conservative trend strategy — pullback-in-uptrend entries
# Simplified, readable, backtest-friendly. Spot only.

from freqtrade.strategy import IStrategy, DecimalParameter, IntParameter
from pandas import DataFrame
import talib.abstract as ta


class MahanTrend(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "1h"
    can_short = False

    # Risk management
    minimal_roi = {"0": 0.12, "24": 0.06, "48": 0.03, "96": 0}
    stoploss = -0.10
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.05
    trailing_only_offset_is_reached = True

    # Exit on signal flip
    use_exit_signal = True
    exit_profit_only = False

    # Buy zone tuning
    rsi_buy_low = IntParameter(25, 45, default=35, space="entry")
    ema_buffer = DecimalParameter(0.995, 1.0, default=0.9975, space="entry")

    startup_candle_count = 200

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Core trend
        dataframe["ema50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)

        # Momentum
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        macd = ta.MACD(dataframe)
        dataframe["macd"] = macd["macd"]
        dataframe["macdsignal"] = macd["macdsignal"]

        # Volume baseline
        dataframe["volume_mean_20"] = dataframe["volume"].rolling(20).mean()

        # ATR for context (informational)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Fresh golden cross: ema50 crossing above ema200
        golden_cross = (
            (dataframe["ema50"] > dataframe["ema200"])
            & (dataframe["ema50"].shift(1) <= dataframe["ema200"].shift(1))
        )
        # Or strong breakout: price making 20-bar high with volume surge
        breakout = (
            (dataframe["close"] > dataframe["close"].rolling(20).max().shift(1))
            & (dataframe["volume"] > dataframe["volume_mean_20"] * 1.5)
            & (dataframe["rsi"] < 75)
        )
        # Shared filters
        base_ok = (
            (dataframe["rsi"] > 40)
            & (dataframe["macd"] > dataframe["macdsignal"])
            & (dataframe["volume"] > 0)
        )

        enter_mask = (golden_cross | breakout) & base_ok
        dataframe.loc[enter_mask, "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exit on death cross
        death_cross = (
            (dataframe["ema50"] < dataframe["ema200"])
            & (dataframe["ema50"].shift(1) >= dataframe["ema200"].shift(1))
        )
        dataframe.loc[death_cross, "exit_long"] = 1
        return dataframe
