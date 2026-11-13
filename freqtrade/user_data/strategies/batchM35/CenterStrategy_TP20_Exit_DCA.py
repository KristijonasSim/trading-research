# pragma pylint: disable=missing-module-docstring, invalid-name, pointless-string-statement
from __future__ import annotations
import re
from datetime import datetime
from typing import Optional
import talib.abstract as ta
import pandas as pd
from freqtrade.exchange import timeframe_to_seconds
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from freqtrade.persistence import Trade


class CenterStrategy_TP20_Exit_DCA_Test(IStrategy):
    """
    CenterStrategy_TP20_Exit_DCA_Test
    """

    INTERFACE_VERSION = 3
    timeframe = "5m"
    can_short = False

    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    initial_capital = 0.0
    target_profit_ratio = 0.20
    entry_cutoff_ratio = 0.15

    stake_ratio = 0.15
    so_ratio = 0.07
    dca_cooldown_candles = 2

    minimal_roi = {
        "0": 100.0
    }

    trailing_stop = False

    stoploss = -0.30

    position_adjustment_enable = True
    max_entry_position_adjustment = 30

    max_capital_usage_pct = 0.95
    min_free_cash_quote = 250.0
    max_trade_exposure_quote = 5000.0

    buy_grid_step = DecimalParameter(0.006, 0.015, default=0.008, space='buy', optimize=True)
    sell_grid_step = DecimalParameter(0.010, 0.030, default=0.015, space='sell', optimize=True)

    max_so_count = IntParameter(5, 20, default=12, space='buy', optimize=True)
    so_quote_amount = DecimalParameter(50.0, 500.0, default=150.0, space='buy', optimize=True)

    base_order_quote = 150.0
    max_tp_levels = 5
    tp_reduce_fraction = 0.20

    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                            proposed_stake: float, min_stake: float, max_stake: float,
                            leverage: float, entry_tag: Optional[str], side: str,
                            **kwargs) -> float:

        try:
            total_capital = self.wallets.get_total_stake_amount()
            available_stake = self.wallets.get_available_stake_amount()
            budget = max(0.0, available_stake - self.min_free_cash_quote)
            dynamic_stake = total_capital * self.stake_ratio
            stake = min(dynamic_stake, budget, self.max_trade_exposure_quote, max_stake)
            if stake < min_stake:
                return 0.0
            return stake
        except:
            return proposed_stake

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        dataframe['adx'] = ta.ADX(dataframe)
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['atr_pct'] = dataframe['atr'] / dataframe['close']

        dataframe['ema200'] = ta.EMA(dataframe, timeperiod=200)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)

        dataframe['block_entry'] = (
            (dataframe['adx'] > 25) |
            (dataframe['atr_pct'] > 0.015)
        ).astype(int)

        dataframe['block_dca'] = (
            (dataframe['adx'] > 30) |
            (dataframe['atr_pct'] > 0.018)
        ).astype(int)

        return dataframe

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        dataframe['enter_long'] = 0

        dataframe.loc[
            (
                (dataframe['block_entry'] == 0) &
                (dataframe['close'] > dataframe['ema200']) &
                (dataframe['rsi'] < 55)
            ),
            'enter_long'] = 1

        dataframe.loc[
            (
                (dataframe['block_entry'] == 0) &
                (dataframe['close'] < dataframe['ema200']) &
                (dataframe['rsi'] < 35) &
                (dataframe['close'] > dataframe['ema200'] * 0.85)
            ),
            'enter_long'] = 1

        return dataframe

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                            time_in_force: str, current_time: datetime, entry_tag: Optional[str],
                            **kwargs) -> bool:
        try:
            total_realized_capital = self.wallets.get_total_stake_amount()

            if self.initial_capital == 0.0:
                self.initial_capital = total_realized_capital

            stop_entry_threshold = self.initial_capital * (1.0 + self.entry_cutoff_ratio)

            if total_realized_capital >= stop_entry_threshold:
                return False
        except:
            pass

        return True

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        return dataframe

    def _get_cd(self, trade: Trade) -> dict:
        cd = trade.get_custom_data("grid_state")
        if not isinstance(cd, dict):
            cd = {}
        return cd

    def _set_cd(self, trade: Trade, cd: dict) -> None:
        trade.set_custom_data("grid_state", cd)

    def adjust_trade_position(self, trade: Trade, current_time: datetime, current_rate: float,
                              current_profit: float, min_stake: float, max_stake: float, **kwargs) -> Optional[float]:

        try:
            tag = trade.enter_tag or ""
            amt_str = f"Amt:{trade.stake_amount:.1f}"

            if "Amt:" in tag:
                new_tag = re.sub(r"Amt:[\d\.]+", amt_str, tag)
            else:
                new_tag = f"{tag} {amt_str}".strip()

            if len(new_tag) > 255:
                new_tag = new_tag[:255]

            if tag != new_tag:
                trade.enter_tag = new_tag
        except Exception:
            pass

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

        sell_step = cd["sell_step"]
        target_sell_price = float(trade.open_rate) * (1.0 + sell_step)

        if cd["next_sell"] > target_sell_price:
            cd["next_sell"] = target_sell_price

        buy_step = cd["buy_step"]

        so_count = cd["so_count"]
        next_buy = cd["next_buy"]

        if current_rate <= next_buy and so_count < self.max_so_count.value:
            if trade.has_open_orders:
                cd["last_adj_time"] = current_candle_time
                self._set_cd(trade, cd)
                return None

            last_dca_time = cd.get("last_dca_time", 0)
            if last_dca_time:
                cooldown_seconds = timeframe_to_seconds(self.timeframe) * self.dca_cooldown_candles
                if current_candle_time < (last_dca_time + cooldown_seconds):
                    cd["last_adj_time"] = current_candle_time
                    self._set_cd(trade, cd)
                    return None

            if last_candle['block_dca'] == 1:
                return None

            try:
                total_capital = self.wallets.get_total_stake_amount()
                so_stake = total_capital * self.so_ratio
            except:
                so_stake = self.so_quote_amount.value

            try:
                available_stake = self.wallets.get_available_stake_amount()
                budget = max(0.0, available_stake - self.min_free_cash_quote)
            except Exception:
                budget = max_stake

            remaining_exposure = self.max_trade_exposure_quote - trade.stake_amount
            so_stake = min(so_stake, budget, remaining_exposure, max_stake)
            if so_stake < min_stake:
                cd["last_adj_time"] = current_candle_time
                self._set_cd(trade, cd)
                return None

            cd["so_count"] += 1
            cd["next_buy"] = current_rate * (1.0 - buy_step)
            cd["last_dca_time"] = current_candle_time

            cd["last_adj_time"] = current_candle_time
            self._set_cd(trade, cd)
            return so_stake

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

        try:
            current_value = trade.amount * current_rate
            cost_basis = trade.amount * trade.open_rate
            current_profit_abs = current_value - cost_basis

            total_realized_capital = self.wallets.get_total_stake_amount()

            if self.initial_capital == 0.0:
                self.initial_capital = total_realized_capital

            total_equity = total_realized_capital + current_profit_abs
            target_equity = self.initial_capital * (1.0 + self.target_profit_ratio)

            if total_equity >= target_equity:
                return "portfolio_tp_adaptive_stop"

        except Exception:
            pass

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
