"""
AdaptiveRegime - reads the market, decides what kind of market it is, then
applies the approach that suits it.

The design is not a guess. Across the literature and the 68 strategies in the
official Freqtrade reference repo, the same finding keeps recurring: momentum
methods work in TRENDING markets, mean-reversion methods work in RANGING
markets, and each is actively harmful in the other. Most public strategies pick
one and hope. This one measures which regime it is in first.

Regime measure: Kaufman Efficiency Ratio.

    ER = |close[t] - close[t-n]| / sum(|close[i] - close[i-1]|)

Net distance travelled divided by total distance travelled. ER near 1.0 means
price went somewhere in a straight line (a trend). ER near 0 means it thrashed
about and ended where it started (chop). One number, one parameter, and far
harder to curve-fit than a stack of indicators.

    ER >= er_trend  -> TRENDING: Donchian breakout, ride it, channel exit
    ER <= er_range  -> RANGING : fade Bollinger extremes with RSI confirmation
    in between      -> FLAT    : no edge either way, so hold nothing

RSI(14) and Bollinger(20, 2) are fixed at conventional values rather than
optimised. Tuning them is precisely how the reference strategies fool
themselves, and every extra knob is another way to fit noise.
"""
from datetime import datetime
import numpy as np
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter


class AdaptiveRegime(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "1d"
    can_short = True

    minimal_roi = {"0": 100}
    stoploss = -0.35
    trailing_stop = False
    use_custom_stoploss = True

    process_only_new_candles = True
    startup_candle_count = 220

    order_types = {
        "entry": "market", "exit": "market",
        "stoploss": "market", "stoploss_on_exchange": False,
    }

    # --- regime detection ---
    er_period = IntParameter(8, 30, default=14, space="buy", optimize=True)
    er_trend = DecimalParameter(0.25, 0.60, default=0.35, decimals=2,
                                space="buy", optimize=True)
    er_range = DecimalParameter(0.05, 0.25, default=0.15, decimals=2,
                                space="buy", optimize=True)

    # --- trending arm ---
    entry_lookback = IntParameter(15, 60, default=20, space="buy", optimize=True)
    exit_lookback = IntParameter(5, 30, default=10, space="sell", optimize=True)
    atr_stop_mult = DecimalParameter(1.5, 10.0, default=8.0, decimals=1,
                                     space="sell", optimize=True)

    # --- ranging arm: fixed at convention, NOT optimised, on purpose ---
    RSI_LEN, RSI_LOW, RSI_HIGH = 14, 35, 65
    BB_LEN, BB_STD = 20, 1.5

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

    @staticmethod
    def efficiency_ratio(close: pd.Series, n: int) -> pd.Series:
        direction = (close - close.shift(n)).abs()
        volatility = close.diff().abs().rolling(n).sum()
        return (direction / volatility.replace(0, np.nan)).fillna(0.0)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        for v in self.er_period.range:
            dataframe[f"er_{v}"] = self.efficiency_ratio(dataframe["close"], v)

        for v in set(list(self.entry_lookback.range) + list(self.exit_lookback.range)):
            dataframe[f"dc_high_{v}"] = dataframe["high"].rolling(v).max().shift(1)
            dataframe[f"dc_low_{v}"] = dataframe["low"].rolling(v).min().shift(1)

        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=self.RSI_LEN)

        mid = dataframe["close"].rolling(self.BB_LEN).mean()
        sd = dataframe["close"].rolling(self.BB_LEN).std()
        dataframe["bb_mid"] = mid
        dataframe["bb_up"] = mid + self.BB_STD * sd
        dataframe["bb_low"] = mid - self.BB_STD * sd
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        er = dataframe[f"er_{self.er_period.value}"]
        trending = er >= self.er_trend.value
        ranging = er <= self.er_range.value

        n = self.entry_lookback.value
        up, dn = dataframe[f"dc_high_{n}"], dataframe[f"dc_low_{n}"]
        vol = dataframe["volume"] > 0

        # TRENDING: go with the break
        dataframe.loc[
            trending & (dataframe["close"] > up)
            & (dataframe["close"] > dataframe["ema200"]) & vol,
            ["enter_long", "enter_tag"]] = (1, "trend_long")
        dataframe.loc[
            trending & (dataframe["close"] < dn)
            & (dataframe["close"] < dataframe["ema200"]) & vol,
            ["enter_short", "enter_tag"]] = (1, "trend_short")

        # RANGING: fade the extreme.
        # Note the band is 1.5 sigma, not 2.0. A 2-sigma breach is itself a
        # high-volatility event, which pushes ER *up* - so "low ER AND 2-sigma
        # breach" is very nearly a contradiction and almost never fires.
        dataframe.loc[
            ranging & (dataframe["close"] < dataframe["bb_low"])
            & (dataframe["rsi"] < self.RSI_LOW) & vol,
            ["enter_long", "enter_tag"]] = (1, "range_long")
        dataframe.loc[
            ranging & (dataframe["close"] > dataframe["bb_up"])
            & (dataframe["rsi"] > self.RSI_HIGH) & vol,
            ["enter_short", "enter_tag"]] = (1, "range_short")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exits are regime-aware and therefore live in custom_exit(), which can
        # see which arm opened the trade. Doing it here would be wrong: a trend
        # long enters ABOVE the middle band by definition, so a shared
        # "exit at the mean" rule closes it on the very next candle.
        return dataframe

    def custom_exit(self, pair: str, trade, current_time: datetime,
                    current_rate: float, current_profit: float, **kwargs):
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if df is None or len(df) == 0:
            return None
        last = df.iloc[-1]
        tag = (trade.enter_tag or "")
        m = self.exit_lookback.value

        if tag.startswith("trend"):
            # Ride it until the opposite channel breaks.
            if not trade.is_short and last["close"] < last[f"dc_low_{m}"]:
                return "trend_channel_exit"
            if trade.is_short and last["close"] > last[f"dc_high_{m}"]:
                return "trend_channel_exit"
        elif tag.startswith("range"):
            # The trade thesis was "price is stretched"; it ends at the mean.
            if not trade.is_short and last["close"] >= last["bb_mid"]:
                return "range_mean_exit"
            if trade.is_short and last["close"] <= last["bb_mid"]:
                return "range_mean_exit"
            # Regime changed under us - the fade thesis no longer applies.
            if last[f"er_{self.er_period.value}"] >= self.er_trend.value:
                return "range_regime_flip"
        return None

    def custom_stoploss(self, pair: str, trade, current_time: datetime,
                        current_rate: float, current_profit: float,
                        after_fill: bool, **kwargs) -> float:
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if df is None or len(df) == 0:
            return self.stoploss
        atr = df["atr"].iat[-1]
        if not np.isfinite(atr) or current_rate <= 0:
            return self.stoploss
        return max(-abs((atr * float(self.atr_stop_mult.value)) / current_rate),
                   self.stoploss)

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float,
                 entry_tag: str, side: str, **kwargs) -> float:
        return min(float(self.lev.value), max_leverage)
