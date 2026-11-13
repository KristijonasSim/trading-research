# --- Do not remove these libs ---
from datetime import datetime
from typing import TYPE_CHECKING, Dict, Optional, Tuple

import numpy as np
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import (
    BooleanParameter,
    CategoricalParameter,
    DecimalParameter,
    IntParameter,
    IStrategy,
)


if TYPE_CHECKING:
    from freqtrade.persistence import Trade

# --------------------------------


class FractalStrategyV7(IStrategy):
    """
    Robust fractal-corridor breakout strategy (futures-ready, can_short=True)

    Upgrades included:
    - ATR-normalized breakout threshold (blended with fixed % threshold)
    - Corridor-width sanity modifier (soft, not a hard filter)
    - ATR-based adaptive initial stoploss via custom_stoploss (optionally corridor-aware)
    - Per-side micro cooldown after exit (0-2 candles) using confirm_trade_exit
    - Indicator computation optimized (no fragmented insert loops; aligned Series indices)
    - Uses candle matching by current_time (no dataframe.iloc[-1] assumptions)
    """

    INTERFACE_VERSION = 3
    can_short: bool = True

    # If you switch between 1h and 15m, this still works.
    timeframe = "1h"
    process_only_new_candles = True

    # Need enough candles for ATR max period + fractal shifts.
    startup_candle_count = 120

    # Keep ROI "never take profit by ROI" behavior (rely on trailing/custom logic).
    minimal_roi = {"0": 100}

    # We'll use custom_stoploss as the primary protective layer.
    # Set a very wide base stoploss so it won't fight the adaptive stop in practice.
    stoploss = -0.99
    trailing_stop = False

    # ---------- Hyperopt parameters ----------
    # Fractals
    long_fractal_window = CategoricalParameter([3, 5], default=5, space="buy", optimize=True)
    short_fractal_window = CategoricalParameter([3, 5], default=5, space="sell", optimize=True)

    # Breakout thresholds: blend fixed % and ATR-normalized (% of price)
    long_breakout_threshold = DecimalParameter(
        0.0005, 0.05, default=0.01, decimals=4, space="buy", optimize=True
    )
    short_breakout_threshold = DecimalParameter(
        0.0005, 0.05, default=0.01, decimals=4, space="sell", optimize=True
    )

    long_breakout_atr_k = DecimalParameter(
        0.05, 2.50, default=0.50, decimals=2, space="buy", optimize=True
    )
    short_breakout_atr_k = DecimalParameter(
        0.05, 2.50, default=0.50, decimals=2, space="sell", optimize=True
    )

    # Corridor width "soft sanity": modulate effective threshold when corridor is narrow
    corridor_min = DecimalParameter(
        0.001, 0.05, default=0.010, decimals=4, space="buy", optimize=True
    )
    corridor_k = DecimalParameter(0.0, 5.0, default=1.0, decimals=2, space="buy", optimize=True)

    # ATR periods (keep broad enough for 15m/1h)
    entry_atr_period = IntParameter(7, 60, default=14, space="buy", optimize=True)
    trailing_atr_period = IntParameter(7, 60, default=14, space="sell", optimize=True)

    trailing_atr_k = DecimalParameter(
        1.0, 5.0, default=2.0, decimals=2, space="sell", optimize=True
    )

    # Adaptive initial stoploss
    init_sl_atr_k = DecimalParameter(0.5, 6.0, default=2.0, decimals=2, space="sell", optimize=True)

    use_corridor_stop = BooleanParameter(default=True, space="sell", optimize=True)
    corridor_sl_buffer = DecimalParameter(
        0.0, 0.02, default=0.002, decimals=4, space="sell", optimize=True
    )

    # Per-side cooldown after exit (0-2 candles)
    cooldown_candles_long = IntParameter(0, 2, default=1, space="buy", optimize=True)
    cooldown_candles_short = IntParameter(0, 2, default=1, space="sell", optimize=True)

    # ---------- Internal constants ----------
    _ATR_MIN = 7
    _ATR_MAX = 60

    # Store last exit candle time per pair+side for micro cooldown
    _last_exit_time: Dict[Tuple[str, str], datetime] = {}

    # -------------------- Helpers --------------------
    @staticmethod
    def _calculate_fractals(
        dataframe: DataFrame, window_size: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Returns arrays (tops, bottoms) with NaNs except where fractal found.
        For window_size=5: fractal at shift(2); for 3: fractal at shift(1)
        """
        if window_size == 5:
            top = (
                (dataframe["high"].shift(2) > dataframe["high"].shift(3))
                & (dataframe["high"].shift(2) > dataframe["high"].shift(4))
                & (dataframe["high"].shift(2) > dataframe["high"].shift(1))
                & (dataframe["high"].shift(2) > dataframe["high"])
            )
            bottom = (
                (dataframe["low"].shift(2) < dataframe["low"].shift(3))
                & (dataframe["low"].shift(2) < dataframe["low"].shift(4))
                & (dataframe["low"].shift(2) < dataframe["low"].shift(1))
                & (dataframe["low"].shift(2) < dataframe["low"])
            )
            tops = np.where(top, dataframe["high"].shift(2), np.nan)
            bottoms = np.where(bottom, dataframe["low"].shift(2), np.nan)
            return tops, bottoms

        if window_size == 3:
            top = (dataframe["high"].shift(1) > dataframe["high"].shift(2)) & (
                dataframe["high"].shift(1) > dataframe["high"]
            )
            bottom = (dataframe["low"].shift(1) < dataframe["low"].shift(2)) & (
                dataframe["low"].shift(1) < dataframe["low"]
            )
            tops = np.where(top, dataframe["high"].shift(1), np.nan)
            bottoms = np.where(bottom, dataframe["low"].shift(1), np.nan)
            return tops, bottoms

        return np.full(len(dataframe), np.nan), np.full(len(dataframe), np.nan)

    @staticmethod
    def _side_key(trade: "Trade") -> str:
        return "short" if trade.is_short else "long"

    def _get_row_for_time(
        self, dataframe: DataFrame, current_time: datetime
    ) -> Optional[pd.Series]:
        """
        Return the candle row matching current_time (or the last candle before it).
        Avoids using dataframe.iloc[-1] blindly.
        """
        if dataframe is None or dataframe.empty:
            return None
        if "date" not in dataframe.columns:
            return dataframe.iloc[-1]

        df = dataframe[dataframe["date"] <= current_time]
        if df.empty:
            return dataframe.iloc[-1]
        return df.iloc[-1]

    def _cooldown_ok(self, pair: str, side: str, current_time: datetime) -> bool:
        """
        Check if we are still within cooldown window after last exit for this pair+side.
        """
        if side == "long":
            cd = int(self.cooldown_candles_long.value)
        else:
            cd = int(self.cooldown_candles_short.value)

        if cd <= 0:
            return True

        last_exit = self._last_exit_time.get((pair, side))
        if not last_exit:
            return True

        # Cooldown measured in candles, approximate with minutes from timeframe.
        # Works for typical timeframe strings ("15m", "1h", etc.).
        tf = self.timeframe.lower().strip()
        if tf.endswith("m"):
            minutes = int(tf[:-1])
        elif tf.endswith("h"):
            minutes = int(tf[:-1]) * 60
        elif tf.endswith("d"):
            minutes = int(tf[:-1]) * 1440
        else:
            # Fallback: assume 60m
            minutes = 60

        cooldown_until = last_exit + pd.Timedelta(minutes=minutes * cd)
        return current_time > cooldown_until

    # -------------------- Indicators --------------------
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Fractals (compute once for both window sizes, align indices, ffill)
        fractal_cols = {}
        for w in (3, 5):
            tops, bottoms = self._calculate_fractals(dataframe, w)
            fractal_cols[f"fractal_top_{w}"] = pd.Series(tops, index=dataframe.index).ffill()
            fractal_cols[f"fractal_bottom_{w}"] = pd.Series(bottoms, index=dataframe.index).ffill()

        fractal_df = pd.DataFrame(fractal_cols, index=dataframe.index)

        # ATR columns for a fixed range to keep hyperopt/backtest consistency.
        # Build dict then concat once (avoid fragmented frame inserts).
        atr_cols = {
            f"atr_{p}": ta.ATR(dataframe, timeperiod=p)
            for p in range(self._ATR_MIN, self._ATR_MAX + 1)
        }
        atr_df = pd.DataFrame(atr_cols, index=dataframe.index)

        dataframe = pd.concat([dataframe, fractal_df, atr_df], axis=1)
        return dataframe

    # -------------------- Entries --------------------
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair = metadata.get("pair", "")

        # Base levels
        ft_long = dataframe[f"fractal_top_{self.long_fractal_window.value}"]
        fb_short = dataframe[f"fractal_bottom_{self.short_fractal_window.value}"]

        # Corridor width (use matching windows for each side where possible)
        fb_long = dataframe[f"fractal_bottom_{self.long_fractal_window.value}"]
        ft_short = dataframe[f"fractal_top_{self.short_fractal_window.value}"]

        corridor_w_long = (ft_long - fb_long) / dataframe["close"]
        corridor_w_short = (ft_short - fb_short) / dataframe["close"]

        # ATR% for volatility-normalization
        atr_e = dataframe[f"atr_{self.entry_atr_period.value}"]
        atr_pct = (atr_e / dataframe["close"]).fillna(0.0)

        # Effective threshold = max(fixed_pct, atr_k * atr_pct) then modulate by corridor narrowness
        fixed_long = float(self.long_breakout_threshold.value)
        fixed_short = float(self.short_breakout_threshold.value)

        eff_long = np.maximum(fixed_long, float(self.long_breakout_atr_k.value) * atr_pct)
        eff_short = np.maximum(fixed_short, float(self.short_breakout_atr_k.value) * atr_pct)

        # Soft corridor modifier: if corridor is narrow (< corridor_min), increase threshold slightly.
        cmin = float(self.corridor_min.value)
        ck = float(self.corridor_k.value)

        # Avoid div-by-zero and keep modifier stable
        cmin_safe = max(cmin, 1e-9)

        narrow_long = (cmin_safe - corridor_w_long).clip(lower=0.0) / cmin_safe
        narrow_short = (cmin_safe - corridor_w_short).clip(lower=0.0) / cmin_safe

        mod_long = 1.0 + ck * narrow_long
        mod_short = 1.0 + ck * narrow_short

        eff_long = eff_long * mod_long
        eff_short = eff_short * mod_short

        # Signal conditions
        long_cond = dataframe["close"] > ft_long * (1.0 + eff_long)
        short_cond = dataframe["close"] < fb_short * (1.0 - eff_short)

        # Micro cooldown per side (vectorized is hard; apply as a final mask using date)
        # We'll compute a boolean mask using the last exit time (single timestamp), if any.
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0

        if "date" in dataframe.columns:
            # Long cooldown mask
            if (
                self._last_exit_time.get((pair, "long"))
                and int(self.cooldown_candles_long.value) > 0
            ):
                last_exit = self._last_exit_time[(pair, "long")]
                # approximate as timedelta based on timeframe
                tf = self.timeframe.lower().strip()
                if tf.endswith("m"):
                    minutes = int(tf[:-1])
                elif tf.endswith("h"):
                    minutes = int(tf[:-1]) * 60
                elif tf.endswith("d"):
                    minutes = int(tf[:-1]) * 1440
                else:
                    minutes = 60
                cooldown_until = last_exit + pd.Timedelta(
                    minutes=minutes * int(self.cooldown_candles_long.value)
                )
                cd_long_mask = dataframe["date"] > cooldown_until
            else:
                cd_long_mask = pd.Series(True, index=dataframe.index)

            # Short cooldown mask
            if (
                self._last_exit_time.get((pair, "short"))
                and int(self.cooldown_candles_short.value) > 0
            ):
                last_exit = self._last_exit_time[(pair, "short")]
                tf = self.timeframe.lower().strip()
                if tf.endswith("m"):
                    minutes = int(tf[:-1])
                elif tf.endswith("h"):
                    minutes = int(tf[:-1]) * 60
                elif tf.endswith("d"):
                    minutes = int(tf[:-1]) * 1440
                else:
                    minutes = 60
                cooldown_until = last_exit + pd.Timedelta(
                    minutes=minutes * int(self.cooldown_candles_short.value)
                )
                cd_short_mask = dataframe["date"] > cooldown_until
            else:
                cd_short_mask = pd.Series(True, index=dataframe.index)
        else:
            cd_long_mask = pd.Series(True, index=dataframe.index)
            cd_short_mask = pd.Series(True, index=dataframe.index)

        dataframe.loc[long_cond & cd_long_mask, "enter_long"] = 1
        dataframe.loc[short_cond & cd_short_mask, "enter_short"] = 1
        return dataframe

    # We rely on custom_exit for trailing; no static exit signal.
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe

    # -------------------- Adaptive Stoploss --------------------
    def custom_stoploss(
        self,
        pair: str,
        trade: "Trade",
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs,
    ) -> float:
        """
        Adaptive initial stoploss based on ATR (optionally corridor-aware).
        Returns a stoploss value relative to current_rate (negative float).
        """
        try:
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        except Exception:
            return self.stoploss

        row = self._get_row_for_time(dataframe, current_time)
        if row is None:
            return self.stoploss

        atr = row.get(f"atr_{self.entry_atr_period.value}", np.nan)
        if atr is None or not np.isfinite(atr) or atr <= 0:
            return self.stoploss

        entry_price = float(trade.open_rate)
        k = float(self.init_sl_atr_k.value)

        # ATR-based stop price
        if not trade.is_short:
            atr_stop_price = entry_price - (k * float(atr))
        else:
            atr_stop_price = entry_price + (k * float(atr))

        stop_price = atr_stop_price

        # Optional corridor-based stop (choose tighter one)
        if bool(self.use_corridor_stop.value):
            buf = float(self.corridor_sl_buffer.value)

            if not trade.is_short:
                # For longs, corridor stop under fractal bottom (entry-window fractal)
                fb = row.get(f"fractal_bottom_{self.long_fractal_window.value}", np.nan)
                if fb is not None and np.isfinite(fb) and fb > 0:
                    corridor_stop = float(fb) * (1.0 - buf)
                    # tighter for long = higher stop price
                    stop_price = max(stop_price, corridor_stop)
            else:
                # For shorts, corridor stop above fractal top
                ft = row.get(f"fractal_top_{self.short_fractal_window.value}", np.nan)
                if ft is not None and np.isfinite(ft) and ft > 0:
                    corridor_stop = float(ft) * (1.0 + buf)
                    # tighter for short = lower stop price (closer to current)
                    stop_price = min(stop_price, corridor_stop)

        # Convert stop_price to stoploss-relative-to-current_rate (must be negative)
        if not trade.is_short:
            # stop below current_rate => negative
            sl = (stop_price / float(current_rate)) - 1.0
        else:
            # short stop above current_rate => negative loss distance
            sl = (float(current_rate) / stop_price) - 1.0 if stop_price > 0 else self.stoploss

        # Clamp to valid range
        sl = float(np.clip(sl, -0.99, -0.0001))
        return sl

    # -------------------- Trailing Exit (kept) --------------------
    def custom_exit(
        self,
        pair: str,
        trade: "Trade",
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs,
    ):
        """
        ATR trailing exit based on max_rate/min_rate, using candle matching for current_time.
        """
        try:
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        except Exception:
            return None

        row = self._get_row_for_time(dataframe, current_time)
        if row is None:
            return None

        atr = row.get(f"atr_{self.trailing_atr_period.value}", np.nan)
        if atr is None or not np.isfinite(atr) or atr <= 0:
            return None

        k = float(self.trailing_atr_k.value)

        if not trade.is_short:
            trail_price = float(trade.max_rate) - (float(atr) * k)
            if float(current_rate) < trail_price:
                return "atr_trailing_exit"
        else:
            trail_price = float(trade.min_rate) + (float(atr) * k)
            if float(current_rate) > trail_price:
                return "atr_trailing_exit"

        return None

    # -------------------- Record exits for per-side cooldown --------------------
    def confirm_trade_exit(
        self,
        pair: str,
        trade: "Trade",
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        exit_reason: str,
        current_time: datetime,
        **kwargs,
    ) -> bool:
        """
        Called when a trade exit is confirmed. We record exit time for micro cooldown per side.
        """
        side = self._side_key(trade)
        self._last_exit_time[(pair, side)] = current_time
        return True
