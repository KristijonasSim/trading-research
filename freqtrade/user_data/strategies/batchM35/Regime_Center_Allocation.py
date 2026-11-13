# pragma pylint: disable=missing-module-docstring, invalid-name, pointless-string-statement
from __future__ import annotations
import re
from datetime import datetime
from typing import Optional
import numpy as np
import pandas as pd
import talib.abstract as ta
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter, merge_informative_pair
from freqtrade.persistence import Trade

class Regime_Center_Allocation(IStrategy):
    """
    Regime_Center_Allocation
    A composite strategy combining:
    1. RegimeV7 (Trend) - 60% Capital Allocation
    2. CenterStrategy (Grid) - 40% Capital Allocation

    Risk Control:
    - RegimeV7: Capital Guardian (80% Hard Stop)
    - CenterStrategy: Manual Kill Switch (Bear Mode) logic included
    """
    INTERFACE_VERSION = 3
    timeframe = '15m'
    can_short = False
    startup_candle_count = 200

    # --- 1. RegimeV7 Parameters ---
    trend_adx_min = IntParameter(20, 30, default=25, space='buy', optimize=True)
    crash_atr_mult = DecimalParameter(1.5, 3.0, default=2.0, space='buy', optimize=True)
    breakout_period = IntParameter(20, 100, default=50, space='buy', optimize=True)
    atr_stop_mult = DecimalParameter(2.0, 5.0, default=3.0, space='sell', optimize=True)

    # --- 2. CenterStrategy Parameters ---
    buy_grid_step = DecimalParameter(0.006, 0.015, default=0.008, space='buy', optimize=True)
    sell_grid_step = DecimalParameter(0.010, 0.030, default=0.015, space='sell', optimize=True)
    max_so_count = IntParameter(5, 20, default=12, space='buy', optimize=True)
    so_quote_amount = DecimalParameter(50.0, 500.0, default=150.0, space='buy', optimize=True)
    max_tp_levels = 5
    tp_reduce_fraction = 0.20

    # --- 3. Capital Allocation ---
    # RegimeV7 gets 60% of TOTAL capital
    # CenterStrategy gets 40% of TOTAL capital
    regime_alloc = 0.60
    center_alloc = 0.40

    # Capital Guardian for RegimeV7 (80% Hard Stop of its allocation)
    regime_min_capital_ratio = 0.80

    initial_capital = 0.0

    # --- Global Settings ---
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    stoploss = -0.30  # Wide stoploss, managed by strategies individually
    trailing_stop = False
    position_adjustment_enable = True
    max_entry_position_adjustment = 30

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        return [(pair, '4h') for pair in pairs]

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        # --- Common Indicators ---
        dataframe['adx'] = ta.ADX(dataframe)
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['atr_pct'] = dataframe['atr'] / dataframe['close']
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['ema200'] = ta.EMA(dataframe, timeperiod=200)

        # --- RegimeV7 Specific ---
        dataframe['donchian_high'] = dataframe['high'].rolling(self.breakout_period.value).max().shift(1)
        dataframe['atr_fast_ma'] = ta.SMA(dataframe['atr'], timeperiod=24)
        dataframe['crash_fast'] = (dataframe['atr'] > dataframe['atr_fast_ma'] * 2.0).astype(int)

        # --- CenterStrategy Specific ---
        dataframe['block_entry_grid'] = ((dataframe['adx'] > 25) | (dataframe['atr_pct'] > 0.015)).astype(int)
        dataframe['block_dca_grid'] = ((dataframe['adx'] > 30) | (dataframe['atr_pct'] > 0.018)).astype(int)

        # --- Informative 4h (Regime Engine) ---
        informative = self.dp.get_pair_dataframe(metadata['pair'], '4h')
        informative['ema_50'] = ta.EMA(informative, timeperiod=50)
        informative['ema_200'] = ta.EMA(informative, timeperiod=200)
        informative['adx'] = ta.ADX(informative, timeperiod=14)

        # Bear Mode (Price < EMA200 4h) - Used for Kill Switch
        informative['is_bear_4h'] = (informative['close'] < informative['ema_200']).astype(int)

        trend_start_val = self.trend_adx_min.value
        trend_end_val = trend_start_val - 3

        informative['trend_signal_raw'] = 0
        informative.loc[informative['adx'] > trend_start_val, 'trend_signal_raw'] = 1
        informative.loc[informative['adx'] < trend_end_val, 'trend_signal_raw'] = -1
        informative['trend_active_flag'] = informative['trend_signal_raw'].replace(0, np.nan).ffill().fillna(0)
        informative['is_trend_adx'] = (informative['trend_active_flag'] == 1).astype(int)

        informative['atr'] = ta.ATR(informative, timeperiod=14)
        informative['atr_ma'] = ta.SMA(informative['atr'], timeperiod=20)

        dataframe = merge_informative_pair(dataframe, informative, self.timeframe, '4h', ffill=True)

        crash_cond_4h = (
            (dataframe['atr_4h'] > dataframe['atr_ma_4h'] * self.crash_atr_mult.value) &
            (dataframe['close_4h'] < dataframe['ema_200_4h'] * 0.99)
        )
        dataframe['regime_crash'] = (crash_cond_4h | (dataframe['crash_fast'] == 1)).astype(int)

        dataframe['regime_trend'] = (
            (dataframe['ema_50_4h'] > dataframe['ema_200_4h']) &
            (dataframe['is_trend_adx_4h'] == 1) &
            (dataframe['regime_crash'] == 0)
        ).astype(int)

        return dataframe

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        dataframe['enter_long'] = 0
        dataframe['enter_tag'] = ''

        # --- 1. RegimeV7 Entry (Trend) ---
        trend_cond = (
            (dataframe['regime_trend'] == 1) &
            (dataframe['regime_crash'] == 0) &
            (dataframe['close'] > dataframe['donchian_high'])
        )
        dataframe.loc[trend_cond, 'enter_long'] = 1
        dataframe.loc[trend_cond, 'enter_tag'] = 'regime_v7'

        # --- 2. CenterStrategy Entry (Grid) ---
        # Logic: Bull Dip OR Bear Reversion
        grid_base_cond = (dataframe['block_entry_grid'] == 0)

        grid_entry_1 = (
            grid_base_cond &
            (dataframe['close'] > dataframe['ema200']) &
            (dataframe['rsi'] < 55)
        )
        grid_entry_2 = (
            grid_base_cond &
            (dataframe['close'] < dataframe['ema200']) &
            (dataframe['rsi'] < 35) &
            (dataframe['close'] > dataframe['ema200'] * 0.85)
        )

        # We will use 'enter_tag' to distinguish in custom_stake_amount
        # If NOT Trend Entry, check Grid Entry
        grid_mask = (dataframe['enter_long'] == 0) & (grid_entry_1 | grid_entry_2)
        dataframe.loc[grid_mask, 'enter_long'] = 1
        dataframe.loc[grid_mask, 'enter_tag'] = 'center_grid'

        return dataframe

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        dataframe['exit_long'] = 0
        return dataframe

    # --- Capital Allocation & Stake Sizing ---
    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                            proposed_stake: float, min_stake: float, max_stake: float,
                            leverage: float, entry_tag: Optional[str], side: str,
                            **kwargs) -> float:
        try:
            total_capital = self.wallets.get_total_stake_amount()
            if self.initial_capital == 0.0:
                self.initial_capital = total_capital
        except:
            return proposed_stake

        if entry_tag == 'regime_v7':
            # --- RegimeV7 Allocation: 60% of Total ---
            # And use 80% of THAT allocation (RegimeV7 internal logic)
            # So: Total * 0.60 * 0.80 = 48% of Total Capital

            # Capital Guardian Check for Regime Portion
            # If Total Equity < 80% Initial, RegimeV7 stops (Risk Control)
            if total_capital < (self.initial_capital * self.regime_min_capital_ratio):
                return 0.0

            alloc_amount = total_capital * self.regime_alloc
            stake_amount = alloc_amount * 0.80  # 80% of its allocation
            return min(max(stake_amount, min_stake), max_stake)

        elif entry_tag == 'center_grid':
            # --- CenterStrategy Allocation: 40% of Total ---
            # Center uses 15% of its allocation for initial entry
            # So: Total * 0.40 * 0.15 = 6% of Total Capital
            alloc_amount = total_capital * self.center_alloc
            stake_amount = alloc_amount * 0.15  # 15% of its allocation
            return min(max(stake_amount, min_stake), max_stake)

        return proposed_stake

    # --- Grid Logic Helpers ---
    def _get_cd(self, trade: Trade) -> dict:
        cd = trade.get_custom_data("grid_state")
        if not isinstance(cd, dict):
            cd = {}
        return cd

    def _set_cd(self, trade: Trade, cd: dict) -> None:
        trade.set_custom_data("grid_state", cd)

    def adjust_trade_position(self, trade: Trade, current_time: datetime,
                              current_rate: float, current_profit: float,
                              min_stake: float, max_stake: float,
                              **kwargs) -> Optional[float]:
        # Only adjust for CenterStrategy trades
        if trade.enter_tag != 'center_grid':
            return None

        if self.dp:
            dataframe, _ = self.dp.get_analyzed_dataframe(trade.pair, self.timeframe)
            if dataframe is None or len(dataframe) < 1:
                return None
            last_candle = dataframe.iloc[-1]
        else:
            return None

        cd = self._get_cd(trade)
        last_adj_time = cd.get("last_adj_time", 0)
        current_candle_time = int(last_candle['date'].timestamp())

        if last_adj_time == current_candle_time:
            return None

        # Initialize Grid
        if "base_price" not in cd:
            cd["base_price"] = float(trade.open_rate)
            cd["so_count"] = 0
            cd["tp_count"] = 0
            buy_step = self.buy_grid_step.value
            sell_step = max(self.sell_grid_step.value, buy_step + 0.006)
            cd["buy_step"] = buy_step
            cd["sell_step"] = sell_step
            cd["next_buy"] = cd["base_price"] * (1.0 - buy_step)
            cd["next_sell"] = cd["base_price"] * (1.0 + sell_step)
            cd["last_adj_time"] = current_candle_time
            self._set_cd(trade, cd)
            return None

        # Logic from CenterStrategy...
        sell_step = cd["sell_step"]
        target_sell_price = float(trade.open_rate) * (1.0 + sell_step)
        if cd["next_sell"] > target_sell_price:
            cd["next_sell"] = target_sell_price

        buy_step = cd["buy_step"]

        # DCA
        so_count = cd["so_count"]
        next_buy = cd["next_buy"]

        if current_rate <= next_buy and so_count < self.max_so_count.value:
            if last_candle['block_dca_grid'] == 1:
                return None

            # DCA Stake: 7% of Allocation (40% of Total)
            # Total * 0.40 * 0.07 = 2.8% of Total Capital
            try:
                total_capital = self.wallets.get_total_stake_amount()
                alloc_amount = total_capital * self.center_alloc
                so_stake = alloc_amount * 0.07
            except:
                so_stake = self.so_quote_amount.value

            cd["so_count"] += 1
            cd["next_buy"] = next_buy * (1.0 - buy_step)
            cd["last_adj_time"] = current_candle_time
            self._set_cd(trade, cd)
            return so_stake

        # TP
        tp_count = cd["tp_count"]
        next_sell = cd["next_sell"]

        if current_rate >= next_sell and tp_count < self.max_tp_levels:
            current_value = trade.amount * current_rate
            reduce_amt = current_value * self.tp_reduce_fraction
            if reduce_amt < min_stake:
                return None

            cd["tp_count"] += 1
            cd["next_sell"] = next_sell * (1.0 + sell_step)

            new_buy = current_rate * (1.0 - buy_step)
            if new_buy > cd["next_buy"]:
                cd["next_buy"] = new_buy

            cd["last_adj_time"] = current_candle_time
            self._set_cd(trade, cd)
            return -reduce_amt

        return None

    def custom_exit(self, pair: str, trade: Trade, current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs):
        tag = trade.enter_tag

        # --- RegimeV7 Exit Logic ---
        if tag == 'regime_v7':
            # Capital Guardian (Total Equity Check)
            try:
                current_book_value = self.wallets.get_total_stake_amount()
                floating_profit = trade.calc_profit(current_rate)
                real_time_equity = current_book_value + floating_profit

                if self.initial_capital > 0 and real_time_equity < (self.initial_capital * self.regime_min_capital_ratio):
                    return "capital_guardian_stop_80pct"
            except:
                pass

            # Regime Crash Exit
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            try:
                last_candle = dataframe.loc[dataframe['date'] < current_time].iloc[-1]
                if last_candle['regime_crash'] == 1:
                    return "regime_crash_exit"
            except:
                pass

            return None

        # --- CenterStrategy Exit Logic ---
        if tag == 'center_grid':
            cd = self._get_cd(trade)
            tp_count = cd.get("tp_count", 0)

            if tp_count >= self.max_tp_levels and current_profit > 0.005:
                return "grid_finished"

            if self.dp:
                dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
                last_candle = dataframe.iloc[-1]
                if (
                    cd.get("so_count", 0) > 2 and
                    current_rate > last_candle['ema200'] and
                    current_profit > 0.01
                ):
                    return "grid_mean_reversion_done"

            duration_hrs = (current_time - trade.open_date_utc).total_seconds() / 3600
            if duration_hrs > 48 and current_profit > 0.002:
                return "zombie_cleanup"

        return None

    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float, **kwargs) -> float:
        tag = trade.enter_tag

        if tag == 'regime_v7':
            # ATR Trailing Stop
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            try:
                candidate = dataframe.loc[dataframe['date'] < current_time].iloc[-1]
                current_atr = candidate['atr']
                stop_dist = current_atr * self.atr_stop_mult.value
                return -(stop_dist / current_rate)
            except:
                return -0.15  # Fallback

        if tag == 'center_grid':
            # CenterStrategy default stoploss
            return -0.30

        return -0.30
