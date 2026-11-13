# =============================================================================
# ClassicGridTrading.py
# Classic grid trading strategy (long only / no FreqAI)
#
# Goal:
#   - Provide behavior closer to a traditional grid than a trade-average-based model
#   - Track each lot bought at each grid level independently
#   - Make sell decisions per lot instead of relying on the full trade average PnL guard
#
# Notes:
#   - Freqtrade reports profit using the whole trade average entry price,
#     so partial_exit can still look negative in reports
#   - The strategy logic itself is intentionally closer to a classic grid:
#     sell the matching lot when price reaches the next higher grid
# =============================================================================

import logging
import math
from datetime import datetime
from typing import Dict, List, Optional, Union

from pandas import DataFrame

from freqtrade.persistence import Order, Trade
from freqtrade.strategy import IStrategy

logger = logging.getLogger(__name__)


class ClassicGridTradingStrategy(IStrategy):
    """Classic grid strategy that tracks and exits lots individually."""

    timeframe = "15m"
    startup_candle_count: int = 1

    # Grid range
    grid_upper: float = 80000.0
    grid_lower: float = 60000.0
    stop_lower: float = 5000.0
    grid_count: int = 25

    # Leverage
    grid_leverage: float = 3.0

    # Plot helpers
    liquidation_maintenance_margin_ratio: float = 0.005

    # Position settings
    position_adjustment_enable = True
    max_entry_position_adjustment = -1

    # Exit handling is controlled by custom logic
    minimal_roi = {"0": 100.0}
    stoploss = -0.99
    trailing_stop = False

    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # Sell only when the selected lot itself is net profitable after fees.
    per_lot_min_profit_ratio: float = 0.0

    enable_logging: bool = True

    plot_config = {
        "main_plot": {
            "grid_upper_plot": {"color": "#c62828", "type": "line"},
            "grid_lower_plot": {"color": "#1565c0", "type": "line"},
            "stop_lower_plot": {"color": "#6d4c41", "type": "line"},
            "estimated_liquidation_plot": {"color": "#8e24aa", "type": "line"},
            **{
                f"grid_line_{level}": {"color": "#90a4ae", "type": "line"}
                for level in range(grid_count + 1)
            },
        },
        "subplots": {},
    }

    # In-memory state keyed by trade. This cache is rebuilt from order history
    # after reloads so the strategy can resume lot-level tracking safely.
    _grid_state: Dict[str, dict] = {}

    @property
    def grid_step(self) -> float:
        return (self.grid_upper - self.grid_lower) / self.grid_count

    @property
    def estimated_liquidation_ratio(self) -> float:
        if self.grid_leverage <= 1.0:
            return 0.0
        return max(0.0, 1.0 - (1.0 / self.grid_leverage) + self.liquidation_maintenance_margin_ratio)

    def grid_line_price(self, level: int) -> float:
        return self.grid_lower + level * self.grid_step

    def price_to_level(self, price: float) -> int:
        """Map a price to a grid level using floor semantics for sell decisions."""
        if price <= self.grid_lower:
            return 0
        if price >= self.grid_upper:
            return self.grid_count
        return int((price - self.grid_lower) / self.grid_step)

    def _entry_level(self, price: float) -> int:
        """Map a buy fill to the crossed grid line using ceil semantics.

        In a classic grid, a buy triggered by breaking below 76,000 belongs to
        the 76,000 grid line, and the sell is triggered one level above it.
        """
        if price <= self.grid_lower:
            return 0
        if price >= self.grid_upper:
            return self.grid_count
        return min(self.grid_count, math.ceil((price - self.grid_lower) / self.grid_step - 1e-9))

    @staticmethod
    def _trade_key(trade: Trade) -> str:
        return f"{trade.pair}_{trade.open_date_utc.timestamp()}"

    def _order_sort_key(self, order: Order) -> tuple:
        """Sort orders chronologically using filled time first, then creation time."""
        filled_at = getattr(order, "order_filled_utc", None)
        created_at = getattr(order, "order_date_utc", None)
        timestamp = filled_at or created_at or datetime.min
        return (timestamp, getattr(order, "order_id", ""))

    def _order_stake_amount(self, order: Order, fallback: float) -> float:
        """Read the most accurate filled stake value available on an order."""
        return float(
            getattr(order, "stake_amount_filled", None)
            or getattr(order, "stake_amount", None)
            or fallback
        )

    def _has_open_lot_at_level(self, info: dict, level: int) -> bool:
        """Check whether this trade already holds a lot assigned to the level."""
        return any(lot["level"] == level for lot in info["open_lots"])

    def _select_sell_lot(self, info: dict, current_level: int) -> Optional[dict]:
        """Return the highest lot bought below the current level."""
        eligible_lots = [lot for lot in info["open_lots"] if lot["level"] < current_level]
        if eligible_lots:
            return max(eligible_lots, key=lambda lot: lot["level"])
        return None

    def _lot_net_profit_ratio(self, trade: Trade, entry_price: float, exit_price: float) -> float:
        """Estimate the net profit ratio of a single lot after open and close fees."""
        if entry_price <= 0 or exit_price <= 0:
            return 0.0

        fee_open = max(0.0, float(getattr(trade, "fee_open", 0.0) or 0.0))
        fee_close = max(0.0, float(getattr(trade, "fee_close", fee_open) or fee_open))

        entry_cost = entry_price * (1.0 + fee_open)
        exit_value = exit_price * (1.0 - fee_close)
        if entry_cost <= 0:
            return 0.0

        return (exit_value / entry_cost) - 1.0

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Expose grid levels and helper lines for charting."""
        dataframe["grid_upper_plot"] = self.grid_upper
        dataframe["grid_lower_plot"] = self.grid_lower
        dataframe["stop_lower_plot"] = self.stop_lower
        for level in range(self.grid_count + 1):
            dataframe[f"grid_line_{level}"] = self.grid_line_price(level)
        dataframe["estimated_liquidation_plot"] = dataframe["close"] * self.estimated_liquidation_ratio
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Allow the initial entry while price stays inside the configured grid band."""
        dataframe.loc[
            (dataframe["close"] >= self.grid_lower)
            & (dataframe["close"] <= self.grid_upper)
            & (dataframe["volume"] > 0),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Regular exit signals are disabled; custom logic decides exits."""
        dataframe["exit_long"] = 0
        return dataframe

    def custom_stake_amount(
        self,
        current_time: datetime,
        current_rate: float,
        max_stake: float,
        min_stake: Optional[float] = None,
        entry_tag: Optional[str] = None,
        side: str = "long",
        **kwargs,
    ) -> float:
        """Split available stake evenly across the configured grid levels."""
        stake = max_stake / self.grid_count
        if min_stake is not None and stake < min_stake:
            stake = min_stake
        return stake

    def _init_grid_state(self, trade: Trade) -> dict:
        """Seed tracking state for a fresh trade when no order history is available."""
        level = self._entry_level(trade.open_rate)
        per_grid_stake = float(getattr(trade, "stake_amount", 0.0) or 0.0)
        bought_amount = float(getattr(trade, "amount", 0.0) or 0.0)
        info = {
            "per_grid_stake": per_grid_stake,
            "open_lots": [{"level": level, "stake": per_grid_stake, "price": trade.open_rate, "amount": bought_amount}],
            "last_buy_level": level,
            "last_sell_level": level,
        }
        if self.enable_logging:
            logger.info(
                f"ClassicGrid INIT | {trade.pair} | rate={trade.open_rate:.4f} "
                f"level={level} step={self.grid_step:.2f} stake_per_grid={per_grid_stake:.2f}"
            )
        return info

    def _build_grid_state_from_orders(self, trade: Trade) -> dict:
        """Reconstruct lot-level state from the trade's filled order history."""
        entry_side = getattr(trade, "entry_side", "buy")
        exit_side = getattr(trade, "exit_side", "sell")

        filled_orders = sorted(
            [
                order
                for order in getattr(trade, "orders", [])
                if getattr(order, "ft_order_side", None) in {entry_side, exit_side}
                and getattr(order, "safe_filled", 0.0) > 0
            ],
            key=self._order_sort_key,
        )

        if not filled_orders:
            return self._init_grid_state(trade)

        entry_orders = [order for order in filled_orders if getattr(order, "ft_order_side", None) == entry_side]
        first_entry = entry_orders[0] if entry_orders else None
        per_grid_stake = self._order_stake_amount(first_entry, trade.stake_amount) if first_entry else float(trade.stake_amount)
        seed_level = self._entry_level(trade.open_rate)

        info = {
            "per_grid_stake": per_grid_stake,
            "open_lots": [],
            "last_buy_level": seed_level,
            "last_sell_level": seed_level,
        }

        for order in filled_orders:
            order_price = getattr(order, "safe_price", None) or getattr(order, "price", None) or trade.open_rate
            order_level = self.price_to_level(order_price)
            order_side = getattr(order, "ft_order_side", None)
            order_stake = self._order_stake_amount(order, per_grid_stake)

            if order_side == entry_side:
                # Each filled entry becomes its own tracked lot at the crossed grid line.
                order_filled_amount = float(getattr(order, "safe_filled", 0.0) or 0.0)
                entry_level = self._entry_level(order_price)
                info["open_lots"].append({"level": entry_level, "stake": order_stake, "price": order_price, "amount": order_filled_amount})
                info["last_buy_level"] = entry_level
                info["last_sell_level"] = entry_level
                continue

            if order_side == exit_side and info["open_lots"]:
                # Replayed exits are matched against the highest eligible lower-grid lot first.
                remaining_exit_amount = float(getattr(order, "safe_filled", 0.0) or 0.0)
                while remaining_exit_amount > 1e-8 and info["open_lots"]:
                    sell_lot = self._select_sell_lot(info, order_level)
                    if sell_lot is None:
                        break
                    info["open_lots"].remove(sell_lot)
                    remaining_exit_amount -= float(sell_lot.get("amount", 0.0))

                info["last_sell_level"] = order_level
                info["last_buy_level"] = order_level

        if trade.amount > 0 and not info["open_lots"]:
            # Fall back to a single synthetic lot if the trade is still open but
            # the order replay no longer leaves any tracked lots.
            fallback_level = self._entry_level(trade.open_rate)
            fallback_stake = min(per_grid_stake, float(getattr(trade, "stake_amount", per_grid_stake) or per_grid_stake))
            fallback_amount = float(getattr(trade, "amount", 0.0) or 0.0)
            info["open_lots"].append({"level": fallback_level, "stake": fallback_stake, "price": trade.open_rate, "amount": fallback_amount})
            info["last_buy_level"] = fallback_level
            info["last_sell_level"] = fallback_level

        return info

    def _get_grid_state(self, trade: Trade) -> dict:
        key = self._trade_key(trade)
        if key not in self._grid_state:
            # On reload or restart, rebuild the cache entirely from order history.
            restored = self._build_grid_state_from_orders(trade)
            self._grid_state[key] = restored
            if self.enable_logging:
                lots_detail = ", ".join(
                    f"L{lot['level']}@{lot['price']:.1f}x{lot['amount']:.8f}"
                    for lot in restored["open_lots"]
                )
                logger.info(
                    f"ClassicGrid RESTORE | {trade.pair} | holding={len(restored['open_lots'])} lots "
                    f"last_buy={restored['last_buy_level']} last_sell={restored['last_sell_level']} "
                    f"lots=[{lots_detail}]"
                )
        return self._grid_state[key]

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
        """Drive grid re-entries and partial exits for an already open trade."""
        if trade.has_open_orders:
            return None

        info = self._get_grid_state(trade)
        current_level = self.price_to_level(current_rate)
        entry_level = self._entry_level(current_rate)

        # Do not adjust outside the active band. Full exits are handled separately.
        if current_rate >= self.grid_upper or current_rate <= self.grid_lower:
            return None

        # Buy one unit when price drops into a lower unused grid level.
        if not self._has_open_lot_at_level(info, entry_level) and entry_level < info["last_buy_level"]:
            buy_stake = min(info["per_grid_stake"], max_stake)
            if buy_stake <= 0:
                return None
            if min_stake is not None and buy_stake < min_stake:
                if self.enable_logging:
                    logger.warning(
                        f"ClassicGrid BUY skipped (stake {buy_stake:.2f} < min {min_stake:.2f}): "
                        f"{trade.pair} level={entry_level}"
                    )
                return None

            if self.enable_logging:
                logger.info(
                    f"ClassicGrid BUY signal | {trade.pair} | level={entry_level} "
                    f"price={current_rate:.4f} stake={buy_stake:.2f} holding={len(info['open_lots'])} lots"
                )
            return buy_stake

        # Sell the highest lower-grid lot once price climbs above that lot's level.
        sell_lot = self._select_sell_lot(info, current_level) if info["open_lots"] else None
        if sell_lot is not None:

            lot_entry_price = float(sell_lot["price"])
            lot_profit_ratio = self._lot_net_profit_ratio(trade, lot_entry_price, current_rate)
            if lot_profit_ratio < self.per_lot_min_profit_ratio:
                if self.enable_logging:
                    logger.info(
                        f"ClassicGrid SELL skipped | {trade.pair} | lot_level={sell_lot['level']} current_level={current_level} "
                        f"entry_price={lot_entry_price:.4f} sell_price={current_rate:.4f} "
                        f"lot_profit={lot_profit_ratio:.4%} < min_profit={self.per_lot_min_profit_ratio:.4%}"
                    )
                return None

            current_stake = max(0.0, float(getattr(trade, "stake_amount", 0.0) or 0.0))
            if current_stake <= 0:
                return None

            # Freqtrade internally converts stake back into an amount with:
            #   amount = abs(stake) * trade.amount / trade.stake_amount
            # Nudge the computed stake upward by 1 ULP so float rounding does not
            # shrink the converted amount below the tracked lot amount.
            lot_amount = float(sell_lot.get("amount", 0.0))
            if lot_amount <= 0:
                lot_amount = float(sell_lot["stake"]) / lot_entry_price if lot_entry_price > 0 else 0.0
            trade_amount = max(1e-15, float(getattr(trade, "amount", 0.0) or 0.0))
            sell_stake = lot_amount * (current_stake / trade_amount)
            sell_stake = math.nextafter(sell_stake, sell_stake * 2.0)
            sell_stake = min(sell_stake, current_stake)
            remaining_stake = max(0.0, current_stake - sell_stake)

            if min_stake is not None and 0 < remaining_stake < min_stake:
                if self.enable_logging:
                    logger.info(
                        f"ClassicGrid SELL finalizing | {trade.pair} | lot_level={sell_lot['level']} current_level={current_level} "
                        f"price={current_rate:.4f} remaining={remaining_stake:.4f} < min_stake={min_stake:.4f} "
                        f"-> closing full remaining stake={current_stake:.4f}"
                    )
                return -current_stake, "grid_final_exit"

            if self.enable_logging:
                logger.info(
                    f"ClassicGrid SELL signal | {trade.pair} | lot_level={sell_lot['level']} current_level={current_level} "
                    f"entry_price={lot_entry_price:.4f} sell_price={current_rate:.4f} "
                    f"lot_amount={lot_amount:.8f} lot_profit={lot_profit_ratio:.4%} stake=-{sell_stake:.2f}"
                )
            return -sell_stake

        return None

    def order_filled(
        self,
        pair: str,
        trade: Trade,
        order: Order,
        current_time: datetime,
        **kwargs,
    ) -> None:
        if getattr(order, "safe_filled", 0.0) <= 0:
            return

        if getattr(order, "ft_order_side", None) not in {
            getattr(trade, "entry_side", "buy"),
            getattr(trade, "exit_side", "sell"),
        }:
            return

        # Invalidate the cache so the next state read comes from order history.
        key = self._trade_key(trade)
        self._grid_state.pop(key, None)

        # Rebuild immediately so logging reflects the post-fill state.
        restored = self._get_grid_state(trade)

        if self.enable_logging:
            logger.info(
                f"ClassicGrid FILL sync | {pair} | side={getattr(order, 'ft_order_side', '?')} "
                f"price={getattr(order, 'safe_price', 0.0):.4f} filled={getattr(order, 'safe_filled', 0.0):.8f} "
                f"holding={len(restored['open_lots'])} lots"
            )

    def custom_exit(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs,
    ) -> Optional[Union[str, bool]]:
        """Close the remaining trade if price breaks above the grid or below the stop."""
        if current_rate >= self.grid_upper:
            key = self._trade_key(trade)
            if key in self._grid_state:
                del self._grid_state[key]
            if self.enable_logging:
                logger.info(
                    f"ClassicGrid EXIT (upper) | {pair} | rate={current_rate:.4f} >= upper={self.grid_upper:.2f} "
                    f"profit={current_profit:.2%}"
                )
            return "grid_upper_breakout"

        if current_rate <= self.stop_lower:
            key = self._trade_key(trade)
            if key in self._grid_state:
                del self._grid_state[key]
            if self.enable_logging:
                logger.info(
                    f"ClassicGrid EXIT (lower) | {pair} | rate={current_rate:.4f} <= stop_lower={self.stop_lower:.2f} "
                    f"profit={current_profit:.2%}"
                )
            return "grid_lower_break"

        return None

    def confirm_trade_exit(
        self,
        pair: str,
        trade: Trade,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        exit_reason: str,
        current_time: datetime,
        **kwargs,
    ) -> bool:
        """Keep state for partial exits and clear it on full-trade exits."""
        if exit_reason == "partial_exit":
            return True

        key = self._trade_key(trade)
        if key in self._grid_state:
            del self._grid_state[key]
            if self.enable_logging:
                logger.info(f"ClassicGrid state cleaned up | {pair} | reason={exit_reason}")
        return True

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
        return min(self.grid_leverage, max_leverage)