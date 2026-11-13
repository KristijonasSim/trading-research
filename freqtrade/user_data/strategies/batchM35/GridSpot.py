"""
现货网格 / DCA 风格策略 — Freqtrade IStrategy + 仓位加仓
在价格区间内逢低加仓，受 max_open_trades / max_entry_position_adjustment 约束。
"""
from datetime import datetime
from typing import Optional

from pandas import DataFrame
from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy, DecimalParameter, IntParameter
import talib.abstract as ta


class GridSpot(IStrategy):
    """实用现货网格：均线下方分批买入，上方退出。"""

    INTERFACE_VERSION = 3
    timeframe = "5m"
    can_short = False

    minimal_roi = {
        "0": 0.03,
        "60": 0.015,
        "180": 0.005,
        "360": 0.0,
    }
    stoploss = -0.08
    trailing_stop = False

    process_only_new_candles = True
    startup_candle_count = 40
    use_exit_signal = True

    # 启用仓位调整（DCA / 网格加仓）
    position_adjustment_enable = True
    max_entry_position_adjustment = 4  # 首单外最多再加 4 次

    grid_step = DecimalParameter(0.005, 0.03, default=0.012, decimals=3, space="buy")
    rsi_buy = IntParameter(20, 45, default=35, space="buy")
    rsi_sell = IntParameter(55, 80, default=65, space="sell")

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["sma"] = ta.SMA(dataframe, timeperiod=40)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 价格低于均线且 RSI 偏低时开首单
        dataframe.loc[
            (
                (dataframe["close"] < dataframe["sma"])
                & (dataframe["rsi"] < int(self.rsi_buy.value))
                & (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                (dataframe["close"] > dataframe["sma"])
                & (dataframe["rsi"] > int(self.rsi_sell.value))
                & (dataframe["volume"] > 0)
            ),
            "exit_long",
        ] = 1
        return dataframe

    def adjust_trade_position(
        self,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        min_stake: Optional[float],
        max_stake: float,
        current_entry_rate: float,
        current_exit_rate: float,
        current_entry_profit: float,
        current_exit_profit: float,
        **kwargs,
    ) -> Optional[float]:
        """价格相对均价再跌 grid_step 时加仓一档。"""
        filled = trade.nr_of_successful_entries
        if filled > self.max_entry_position_adjustment:
            return None
        # 已浮亏达到下一档网格步长才加仓
        threshold = -float(self.grid_step.value) * filled
        if current_profit > threshold:
            return None
        try:
            stake = trade.stake_amount
        except Exception:
            stake = max_stake * 0.2
        # 每次加仓约首单同等金额，受 max_stake 限制
        amount = min(stake, max_stake)
        if min_stake is not None and amount < min_stake:
            return None
        return amount
