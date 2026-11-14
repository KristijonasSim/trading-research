from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta
from freqtrade.vendor.qtpylib import indicators as qtpylib


class MultiCoin_AI_Strategy_20260530_052915_v001(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "5m"
    can_short = False

    minimal_roi = {
        "0": 0.02,
        "25": 0.015,
        "50": 0.01,
        "100": 0.005,
    }

    stoploss = -0.035

    trailing_stop = True
    trailing_stop_positive = 0.008
    trailing_stop_positive_offset = 0.014
    trailing_only_offset_is_reached = True

    use_exit_signal = False
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    process_only_new_candles = True
    startup_candle_count = 220

    @property
    def protections(self):
        return [
            {
                "method": "CooldownPeriod",
                "stop_duration_candles": 3,
            },
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 48,
                "trade_limit": 10,
                "stop_duration_candles": 6,
                "max_allowed_drawdown": 0.02,
            },
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 24,
                "trade_limit": 2,
                "stop_duration_candles": 8,
                "only_per_pair": True,
            },
        ]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema_12"] = ta.EMA(dataframe, timeperiod=12)
        dataframe["ema_20"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema_26"] = ta.EMA(dataframe, timeperiod=26)
        dataframe["ema_50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema_100"] = ta.EMA(dataframe, timeperiod=100)
        dataframe["ema_200"] = ta.EMA(dataframe, timeperiod=200)
        dataframe["rsi_14"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)

        macd = ta.MACD(dataframe, fastperiod=12, slowperiod=26, signalperiod=9)
        dataframe["macd"] = macd["macd"]
        dataframe["macd_signal"] = macd["macdsignal"]
        dataframe["macd_histogram"] = macd["macdhist"]

        dataframe["volume_mean_20"] = dataframe["volume"].rolling(window=20, min_periods=20).mean()

        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe["bb_upper"] = bollinger["upper"]
        dataframe["bb_lower"] = bollinger["lower"]
        dataframe["bb_width"] = (dataframe["bb_upper"] - dataframe["bb_lower"]) / dataframe["bb_lower"]
        dataframe["bb_width_mean_20"] = dataframe["bb_width"].rolling(window=20, min_periods=20).mean()

        dataframe["macd_hist_rising"] = (
            (dataframe["macd_histogram"] > dataframe["macd_histogram"].shift(1)) &
            (dataframe["macd_histogram"].shift(1) > dataframe["macd_histogram"].shift(2))
        )

        dataframe["bb_pctb"] = (dataframe["close"] - dataframe["bb_lower"]) / (dataframe["bb_upper"] - dataframe["bb_lower"])

        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["atr_sma"] = dataframe["atr"].rolling(window=20).mean()
        dataframe["atr_ratio"] = dataframe["atr"] / dataframe["atr_sma"]

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["enter_long"] = 0
        dataframe["enter_tag"] = ""

        pair = metadata.get("pair", "")

        atr_filter = (dataframe["atr_ratio"] < 1.3)

        macd_momentum = (
            (dataframe["ema_50"] > dataframe["ema_200"]) &
            (dataframe["ema_12"] > dataframe["ema_26"]) &
            (qtpylib.crossed_above(dataframe["macd_histogram"], 0)) &
            (dataframe["rsi_14"] > 40) &
            (dataframe["rsi_14"] < 72) &
            (dataframe["adx"] > 18) &
            (dataframe["close"] > dataframe["ema_50"]) &
            (dataframe["volume"] > dataframe["volume_mean_20"] * 1.0) &
            (dataframe["volume"] > 0) &
            atr_filter
        )

        if pair == "BTC/USDT":
            long_condition = None
        elif pair == "ETH/USDT":
            long_condition = (
                macd_momentum &
                (dataframe["close"] > dataframe["ema_200"]) &
                (dataframe["close"] > dataframe["ema_100"]) &
                (dataframe["close"] > dataframe["ema_20"]) &
                (dataframe["ema_20"] > dataframe["ema_50"]) &
                (dataframe["ema_50"] > dataframe["ema_200"]) &
                (dataframe["rsi_14"] > 45) &
                (dataframe["adx"] > 25) &
                (dataframe["macd_histogram"] > 0)
            )
        elif pair == "XRP/USDT":
            long_condition = None
        elif pair == "DOGE/USDT":
            long_condition = (
                macd_momentum &
                (dataframe["adx"] > 26) &
                (dataframe["rsi_14"] < 58) &
                (dataframe["close"] > dataframe["ema_200"]) &
                (dataframe["macd_hist_rising"])
            )
        elif pair == "SOL/USDT":
            long_condition = (
                (dataframe["ema_50"] > dataframe["ema_200"]) &
                (dataframe["ema_12"] > dataframe["ema_26"]) &
                (qtpylib.crossed_above(dataframe["macd_histogram"], 0)) &
                (dataframe["rsi_14"] > 38) &
                (dataframe["rsi_14"] < 74) &
                (dataframe["adx"] > 17) &
                (dataframe["close"] > dataframe["ema_50"]) &
                (dataframe["volume"] > dataframe["volume_mean_20"] * 0.9) &
                (dataframe["volume"] > 0) &
                atr_filter
            )
        else:
            long_condition = macd_momentum

        if long_condition is not None:
            dataframe.loc[long_condition, ["enter_long", "enter_tag"]] = (
                1,
                "macd_cross_momentum",
            )

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0
        return dataframe
