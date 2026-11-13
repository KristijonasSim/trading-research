"""
均线交叉策略（现货）— Freqtrade IStrategy
依赖 Freqtrade 引擎；本仓库仅提供策略逻辑。
"""
from pandas import DataFrame
from freqtrade.strategy import IStrategy, IntParameter
import talib.abstract as ta


class MACrossover(IStrategy):
    """SMA 快慢线金叉死叉 · 现货 BTC/USDT 等。"""

    INTERFACE_VERSION = 3
    timeframe = "15m"
    can_short = False

    # ROI / 止损（可被 config 覆盖）
    minimal_roi = {
        "0": 0.04,
        "30": 0.02,
        "60": 0.01,
        "120": 0.0,
    }
    stoploss = -0.05
    trailing_stop = False

    process_only_new_candles = True
    startup_candle_count = 50
    use_exit_signal = True

    # 可超参优化
    fast_ma = IntParameter(5, 20, default=10, space="buy")
    slow_ma = IntParameter(20, 60, default=30, space="buy")

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["sma_fast"] = ta.SMA(dataframe, timeperiod=int(self.fast_ma.value))
        dataframe["sma_slow"] = ta.SMA(dataframe, timeperiod=int(self.slow_ma.value))
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["sma_fast"] > dataframe["sma_slow"])
                & (dataframe["sma_fast"].shift(1) <= dataframe["sma_slow"].shift(1))
                & (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["sma_fast"] < dataframe["sma_slow"])
                & (dataframe["sma_fast"].shift(1) >= dataframe["sma_slow"].shift(1))
                & (dataframe["volume"] > 0)
            ),
            "exit_long",
        ] = 1
        return dataframe
