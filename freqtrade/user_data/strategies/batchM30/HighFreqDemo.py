"""
HighFreqDemo - built to a trade-count target, on 1-minute candles, with leverage.

WHAT THIS IS FOR
You asked for 100+ trades in an hour, on futures, with leverage. This delivers
that. It is a stress rig for the machinery: order placement, position tracking,
exits, margin, and the dashboard all under real load.

WHAT IT IS NOT
It is not a strategy. Its entry rule is deliberately trivial and its exit is a
timer. Nothing here was validated, because there is nothing here to validate.

THE ARITHMETIC YOU SHOULD KNOW BEFORE WATCHING IT
Binance charges 0.045% taker to open and 0.045% to close a futures position.
That is 0.09% per round trip, on notional. At 3x leverage the notional is 3x the
stake, so the fee is effectively 0.27% of your own money per trade.

    100 trades/hour  x  0.09% notional  x  3x leverage
    = about 27% of account equity per hour, in fees alone

The position has to make that back before it makes you anything. Earlier in this
project I measured 68 public strategies; the ones trading 5-minute candles
(1,000-1,700 trades) lost 50-76%, and fees were the mechanism. This runs on
1-minute candles, which is worse.

Protections are switched OFF here on purpose - StoplossGuard would halt trading
within minutes at this rate, which would defeat the stated goal. That means there
is no circuit breaker. Paper mode only.
"""
from datetime import datetime

import talib.abstract as ta
from pandas import DataFrame
from freqtrade.strategy import IStrategy, DecimalParameter


class HighFreqDemo(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "1m"
    can_short = True

    # A timer, not a thesis. Take a small gain fast, and be out within 8
    # minutes regardless, so positions keep turning over.
    minimal_roi = {"0": 0.003, "1": 0.0015, "3": 0}
    stoploss = -0.015
    trailing_stop = False
    use_custom_stoploss = False

    process_only_new_candles = True
    startup_candle_count = 60

    order_types = {
        "entry": "market", "exit": "market",
        "stoploss": "market", "stoploss_on_exchange": False,
    }

    lev = DecimalParameter(1.0, 10.0, default=3.0, decimals=1,
                           space="buy", optimize=False, load=False)

    # No protections. See the module docstring - this is deliberate and it
    # means nothing will stop this rig if it starts bleeding.
    @property
    def protections(self):
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema9"] = ta.EMA(dataframe, timeperiod=9)
        dataframe["ema21"] = ta.EMA(dataframe, timeperiod=21)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        vol = dataframe["volume"] > 0
        # Trivially loose on purpose: short-term momentum in either direction.
        dataframe.loc[
            (dataframe["close"] > dataframe["ema9"])
            & (dataframe["ema9"] > dataframe["ema21"]) & vol,
            ["enter_long", "enter_tag"]] = (1, "hf_long")
        dataframe.loc[
            (dataframe["close"] < dataframe["ema9"])
            & (dataframe["ema9"] < dataframe["ema21"]) & vol,
            ["enter_short", "enter_tag"]] = (1, "hf_short")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exits are handled by minimal_roi and the stoploss. Nothing here.
        return dataframe

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float,
                 entry_tag: str, side: str, **kwargs) -> float:
        return min(float(self.lev.value), max_leverage)
