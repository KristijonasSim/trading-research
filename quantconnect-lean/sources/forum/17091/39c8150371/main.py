# region imports
from AlgorithmImports import *
import numpy as np
import pandas as pd
from datetime import timedelta
# endregion


START_DATE = (2007, 5, 1)               # starting date
END_DATE = (2024, 4, 30)                # ending date
CASH = 100_000                          # starting cash
RESOLUTION = Resolution.MINUTE          # data resolution
LEVERAGE = 4                            # maximum leverage
DEBUG = True                            # enable/disable debug messages in logs
PERIOD = 14                             # strategy period
TIMEFRAME = timedelta(minutes=30)       # strategy timeframe
IGNORE_MARGIN_CALLS = False              # double buying power to ignore those pesky margin calls
EXECUTE_MID_PRICE = False                # do not use proper bid/ask price, but average price instead


class MidPriceFillModel(FillModel):
    def MarketFill(self, asset, order) -> OrderEvent:
        # Get the current QuoteBar for the target security
        # Calculate the mid price
        mid_price = (asset.bid_price + asset.ask_price) / 2.
        # Create an order event with the fill price set to the mid price
        fill = OrderEvent(order_id=order.Id, symbol=order.Symbol, utc_time=order.Time, status=OrderStatus.FILLED,
                          direction=order.direction,
                          fill_price=mid_price, fill_quantity=order.quantity, order_fee=OrderFee.ZERO)
        return fill


class BeatTheMarketSPY(QCAlgorithm):
    def initialize(self) -> None:
        self.set_cash(CASH)
        self.set_start_date(*START_DATE)
        self.set_end_date(*END_DATE)
        self.set_brokerage_model(BrokerageName.INTERACTIVE_BROKERS_BROKERAGE, AccountType.MARGIN)
        self.upper_sched = None
        self.lower_sched = None
        self.daily_vol = None
        self.open_price = None
        self.spy = self.add_equity("SPY", RESOLUTION,
                                   data_normalization_mode=DataNormalizationMode.TOTAL_RETURN).symbol
        self.securities[self.spy].set_margin_model(PatternDayTradingMarginModel())
        # !!! not for actual use, but if we want to follow the paper, they don't check for margin with full leverage...
        if IGNORE_MARGIN_CALLS:
            self.securities[self.spy].set_buying_power_model(BuyingPowerModel(8))
        if EXECUTE_MID_PRICE:
            self.securities[self.spy].set_fill_model(MidPriceFillModel())
        self.last_close = self.identity(self.spy, resolution=Resolution.DAILY, selector=Field.CLOSE)
        self.windows = []
        self.vwap_ind = self.vwap(self.spy)
        self.consolidator = self.consolidate(self.spy, TIMEFRAME, self.on_bar)
        self.schedule.on(
            self.date_rules.every_day(self.spy),
            self.time_rules.before_market_close(self.spy, 1),
            self.flat_positions
        )
        self.schedule.on(
            self.date_rules.every_day(self.spy),
            self.time_rules.before_market_close(self.spy, -1),
            self.cleanup
        )

        # plot SPY for reference, why can't they do it automatically?
        self.spy_mult = None
        self.set_benchmark(self.spy)
        self.schedule.on(
            self.date_rules.every_day(self.spy),
            self.time_rules.before_market_close(self.spy, -1),
            self.plot_price
        )

    def on_data(self, slice: Slice) -> None:
        if self.open_price is None and self.spy in slice.bars:
            self.open_price = slice.bars[self.spy].open
            self.session_setup()

    def session_setup(self) -> None:
        if self.open_price is None or not self.last_close.is_ready:
            return

        # GAP adjustment using yesterday’s close
        prev_close = self.last_close.current.value
        gap_open = max(self.open_price, prev_close)
        gap_low = min(self.open_price, prev_close)

        # request history for last 16 days plus current day minute
        hist = self.history(self.spy, 390 * 16 + 1, Resolution.MINUTE, fill_forward=False).loc[self.spy]
        trading_days = sorted({ts.date() for ts in hist.index})
        rels = []

        # just skip short days
        last_14_full_days = [d for d in trading_days if
                             hist[hist.index.date == d].resample("30T").agg("last").dropna().shape[0] >= 13]
        if len(last_14_full_days) < 14:
            self._debug("Not enough full days!")
            return

        last_14_full_days = last_14_full_days[-14:]
        for day in last_14_full_days[-14:]:
            day_bars = hist[hist.index.date == day]
            day_bars.index -= timedelta(minutes=1)  # switch to bar start times
            bars30 = (
                day_bars
                .resample("30T")
                .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
                .dropna()
            )
            day_open = bars30["open"].iloc[0]
            slot_moves = (bars30["close"].iloc[1:13] - day_open).abs() / day_open
            rels.append(slot_moves.reset_index(drop=True))

        # calculate sigma vector
        rail_matrix = pd.concat(rels, axis=1)
        sigma_vec = rail_matrix.mean(axis=1)
        if sigma_vec.isnull().any():
            self._debug(f"SessionSetup: sigma_vec contains NaNs")
            return

        # calculate daily moves
        self.upper_sched = [gap_open * (1 + s) for s in sigma_vec]
        self.lower_sched = [gap_low * (1 - s) for s in sigma_vec]

        # calculate daily volatility for position sizing
        df_daily = self.history(self.spy, 15, Resolution.DAILY)
        last_14_intraday = (df_daily["close"] / df_daily["open"]).dropna()
        if last_14_intraday.shape[0] < 14:
            self._debug(f"SessionSetup: only {last_14_intraday.shape[0]} intraday returns")
            return

        self.daily_vol = last_14_intraday.std()
        if self.daily_vol == 0 or np.isnan(self.daily_vol):
            self._debug(f"SessionSetup: daily_vol invalid ({self.daily_vol})")
            return

    def on_bar(self, bar: TradeBar) -> None:
        if self.upper_sched is None:
            return

        t = bar.end_time
        idx = (t.hour - 10) * 2 + (1 if t.minute >= 30 else 0)

        # Only trade slots 0…11 (10:00→10:30 through 15:30→16:00).
        if idx < 0 or idx > 11:
            return

        price = bar.close
        upper = self.upper_sched[idx]
        lower = self.lower_sched[idx]
        vwap_now = self.vwap_ind.current.value if self.vwap_ind.is_ready else price
        holding = self.portfolio[self.spy]

        # Log every time on_bar fires, so we know which slots are being delivered:
        # self._debug(
        #     f"[{self.time:%Y-%m-%d %H:%M}] on_bar: idx={idx}, price={price:.2f}, upper={upper:.2f}, lower={lower:.2f}, vwap={vwap_now:.2f}")

        # --- close position on stop ------------------------------------
        if holding.invested:
            if holding.is_long:
                stop = max(vwap_now, upper)
                if price < stop:
                    self.liquidate(self.spy, tag=f"LONG stop: price {price:.2f} < stop {stop:.2f}")
            else:
                stop = min(vwap_now, lower)
                if price > stop:
                    self.liquidate(self.spy, tag=f"SHORT stop: (price {price:.2f} > stop {stop:.2f})")

        # --- entry logic -----------------------------------
        if not holding.invested:
            if price > upper:
                self.enter_long()
            elif price < lower:
                self.enter_short()

    def position_size_weight(self) -> float:
        """Vol-targeted weight (risk 2% per day, capped at 4×)."""
        if self.daily_vol is None or self.daily_vol == 0:
            return LEVERAGE
        return min(0.02 / self.daily_vol, LEVERAGE)

    def enter_long(self) -> None:
        qty = self.calculate_order_quantity(self.spy, self.position_size_weight())
        tag = f"dvol={self.daily_vol:.6f}"
        self.market_order(self.spy, qty, tag=tag)

    def enter_short(self) -> None:
        qty = self.calculate_order_quantity(self.spy, -self.position_size_weight())
        tag = f"dvol={self.daily_vol:.6f}"
        self.market_order(self.spy, qty, tag=tag)

    def flat_positions(self) -> None:
        if self.portfolio[self.spy].invested:
            self.liquidate(self.spy, tag="EOD")

    def cleanup(self):
        self.upper_sched = None
        self.lower_sched = None
        self.daily_vol = None
        self.open_price = None

    def plot_price(self):
        if self.spy_mult is None:
            self.spy_mult = CASH / self.securities[self.spy].close
        self.plot("Strategy Equity", "SPY", self.securities[self.spy].close * self.spy_mult)

    def _debug(self, message):
        if DEBUG:
            self.log(message)
