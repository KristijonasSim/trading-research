"""
合约趋势策略 — EMA/MA 多空，带杠杆上限
trading_mode=futures 时生效；can_short=True；leverage 默认 3，硬顶 10。
"""
from datetime import datetime
from typing import Optional

from pandas import DataFrame
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
import talib.abstract as ta


class FuturesTrendLeverage(IStrategy):
    """EMA 快慢线趋势跟随 · 合约多空。"""

    INTERFACE_VERSION = 3
    timeframe = "15m"
    can_short = True

    minimal_roi = {
        "0": 0.05,
        "40": 0.025,
        "90": 0.01,
        "180": 0.0,
    }
    stoploss = -0.06
    trailing_stop = True
    trailing_stop_positive = 0.015
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True

    process_only_new_candles = True
    startup_candle_count = 60
    use_exit_signal = True

    # 杠杆：策略默认 3x，硬限制 10x（可在 config 用 leverage_default 配合）
    leverage_default = 3.0
    leverage_hard_max = 10.0

    fast_ema = IntParameter(5, 20, default=12, space="buy")
    slow_ema = IntParameter(20, 80, default=26, space="buy")
    atr_mult = DecimalParameter(1.0, 3.0, default=1.5, decimals=1, space="sell")

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=int(self.fast_ema.value))
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=int(self.slow_ema.value))
        dataframe["sma_trend"] = ta.SMA(dataframe, timeperiod=50)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 多头：快线上穿慢线且价格在趋势均线上方
        dataframe.loc[
            (
                (dataframe["ema_fast"] > dataframe["ema_slow"])
                & (dataframe["ema_fast"].shift(1) <= dataframe["ema_slow"].shift(1))
                & (dataframe["close"] > dataframe["sma_trend"])
                & (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        # 空头：快线下穿慢线且价格在趋势均线下方
        dataframe.loc[
            (
                (dataframe["ema_fast"] < dataframe["ema_slow"])
                & (dataframe["ema_fast"].shift(1) >= dataframe["ema_slow"].shift(1))
                & (dataframe["close"] < dataframe["sma_trend"])
                & (dataframe["volume"] > 0)
            ),
            "enter_short",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["ema_fast"] < dataframe["ema_slow"])
                & (dataframe["volume"] > 0)
            ),
            "exit_long",
        ] = 1
        dataframe.loc[
            (
                (dataframe["ema_fast"] > dataframe["ema_slow"])
                & (dataframe["volume"] > 0)
            ),
            "exit_short",
        ] = 1
        return dataframe

    def leverage(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_leverage: float,
        max_leverage: float,
        entry_tag: Optional[str],
        side: str,
        **kwargs,
    ) -> float:
        """默认 3x，不超过交易所 max 与硬顶 10。"""
        target = float(self.leverage_default)
        hard = float(self.leverage_hard_max)
        return min(target, hard, float(max_leverage))
