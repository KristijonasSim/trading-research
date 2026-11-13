"""
TrendFutures - the Donchian trend follower, long AND short, on perpetuals.

Why futures are worth testing rather than just leverage-chasing: the spot version
in this project could only go long, and the walk-forward showed it underperformed
badly in rising markets while OUTPERFORMING in falling ones. If that defensive
skew is real, being able to short should capture the down-legs instead of merely
sitting them out. That is a testable claim, and this strategy exists to test it.

LEVERAGE IS NOT AN EDGE. It multiplies whatever expectancy the strategy already
has. Applied to a negative expectancy it multiplies the losses and adds
liquidation, which converts a recoverable drawdown into a permanent one. The
default here is 1.0 -- shorting enabled, no leverage. Raise it deliberately or
not at all.
"""
from datetime import datetime
import numpy as np
import talib.abstract as ta
from pandas import DataFrame
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter


class TrendFutures(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "1d"
    can_short = True                 # the whole point of this variant

    minimal_roi = {"0": 100}         # let winners run; the channel decides the exit
    stoploss = -0.35
    trailing_stop = False
    use_custom_stoploss = True

    process_only_new_candles = True
    startup_candle_count = 220

    order_types = {
        "entry": "market", "exit": "market",
        "stoploss": "market", "stoploss_on_exchange": False,
    }

    # --- knobs, kept few ---
    entry_lookback = IntParameter(15, 60, default=20, space="buy", optimize=True)
    exit_lookback = IntParameter(5, 30, default=10, space="sell", optimize=True)
    atr_stop_mult = DecimalParameter(1.5, 10.0, default=3.0, decimals=1,
                                     space="sell", optimize=True)
    # Deliberately NOT optimised: an optimiser always picks maximum leverage,
    # because backtests cannot be liquidated the way a real account can.
    lev = DecimalParameter(1.0, 5.0, default=1.0, decimals=1,
                           space="buy", optimize=False, load=True)

    @property
    def protections(self):
        return [
            {"method": "CooldownPeriod", "stop_duration_candles": 2},
            {"method": "MaxDrawdown", "lookback_period_candles": 60, "trade_limit": 8,
             "stop_duration_candles": 10, "max_allowed_drawdown": 0.20},
            {"method": "StoplossGuard", "lookback_period_candles": 30, "trade_limit": 3,
             "stop_duration_candles": 10, "only_per_pair": False},
            {"method": "LowProfitPairs", "lookback_period_candles": 90, "trade_limit": 4,
             "stop_duration_candles": 20, "required_profit": -0.05},
        ]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Channels for BOTH directions, shifted so the current bar cannot see itself.
        for v in set(list(self.entry_lookback.range) + list(self.exit_lookback.range)):
            dataframe[f"dc_high_{v}"] = dataframe["high"].rolling(v).max().shift(1)
            dataframe[f"dc_low_{v}"] = dataframe["low"].rolling(v).min().shift(1)
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        n = self.entry_lookback.value
        up, dn = dataframe[f"dc_high_{n}"], dataframe[f"dc_low_{n}"]

        dataframe.loc[
            (dataframe["close"] > up)
            & (dataframe["close"] > dataframe["ema200"])
            & (dataframe["volume"] > 0),
            ["enter_long", "enter_tag"],
        ] = (1, "break_up")

        dataframe.loc[
            (dataframe["close"] < dn)
            & (dataframe["close"] < dataframe["ema200"])
            & (dataframe["volume"] > 0),
            ["enter_short", "enter_tag"],
        ] = (1, "break_down")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        m = self.exit_lookback.value
        dataframe.loc[
            (dataframe["close"] < dataframe[f"dc_low_{m}"]) & (dataframe["volume"] > 0),
            ["exit_long", "exit_tag"],
        ] = (1, "channel_exit_long")
        dataframe.loc[
            (dataframe["close"] > dataframe[f"dc_high_{m}"]) & (dataframe["volume"] > 0),
            ["exit_short", "exit_tag"],
        ] = (1, "channel_exit_short")
        return dataframe

    def custom_stoploss(self, pair: str, trade, current_time: datetime,
                        current_rate: float, current_profit: float,
                        after_fill: bool, **kwargs) -> float:
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if df is None or len(df) == 0:
            return self.stoploss
        atr = df["atr"].iat[-1]
        if not np.isfinite(atr) or current_rate <= 0:
            return self.stoploss
        dist = (atr * float(self.atr_stop_mult.value)) / current_rate
        return max(-abs(dist), self.stoploss)

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float,
                 entry_tag: str, side: str, **kwargs) -> float:
        return min(float(self.lev.value), max_leverage)
