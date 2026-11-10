# region imports
from AlgorithmImports import *
import numpy as np
from collections import deque
# endregion

class FormalRedPelican(QCAlgorithm):

    def initialize(self):
        self.set_start_date(1999, 1, 1)
        self.set_cash(100000)
        self.set_brokerage_model(BrokerageName.InteractiveBrokersBrokerage, AccountType.Margin)

        spy = self.add_equity("SPY", Resolution.MINUTE)
        self._symbol = spy.symbol
        spy.margin_model = PatternDayTradingMarginModel()

        self._vwap = self.vwap(spy.symbol)
        self._roc = self.rocp(self._symbol, 1, Resolution.DAILY)
        self._vol = IndicatorExtensions.of(StandardDeviation(14), self._roc)
        self._deviation = AbsoluteDeviation('deviation', 14)

        self.consolidator = TradeBarConsolidator(timedelta(minutes=30))
        self.consolidator.data_consolidated += (self.consolidate)
        self.subscription_manager.add_consolidator(self._symbol, self.consolidator)

        self.previous_date = None
        self.open_price = None
        self.previous_close = None
        self.bars = deque(maxlen=2)

        self.schedule.on(
            self.date_rules.every_day(self._symbol),
            self.time_rules.before_market_close(self._symbol, 1),
            self.end_of_day
        )

    def consolidate(self, sender, bar):
        current_date = bar.end_time.date()

        self.bars.append(bar)

        if current_date != self.previous_date:
            self.previous_date = current_date
            self.open_price = bar.open
            self.previous_close = self.bars[-2].close if len(self.bars) == 2 else None

        self._deviation.update(bar)

        if not self._vol.is_ready or not self.previous_close:
            return

        upper_band = (max(self.open_price, self.previous_close) * (1 + self._deviation.value))
        lower_band = (min(self.open_price, self.previous_close) * (1 - self._deviation.value))

        vwap_price = self._vwap.current.value

        long_stop_price = np.max([vwap_price, upper_band])
        short_stop_price = np.min([vwap_price, lower_band])

        is_long = self.portfolio[self._symbol].is_long
        is_short = self.portfolio[self._symbol].is_short

        is_long_stopped_out = is_long and bar.close < long_stop_price
        is_short_stopped_out = is_short and bar.close > short_stop_price

        vol_target = 0.02
        spy_vol = self._vol.current.value / 100
        leverage = np.min([4, vol_target / spy_vol])

        if is_long_stopped_out or is_short_stopped_out:
            self.liquidate()

        if bar.close > upper_band and not is_long:
            self.set_holdings(self._symbol, 1 * leverage)
        elif bar.close < lower_band and not is_short:
            self.set_holdings(self._symbol, -1 * leverage)


    def end_of_day(self):
        self.set_holdings("SPY", 0)


class AbsoluteDeviation(PythonIndicator):

    def __init__(self, name, period):
        super().__init__()
        self.name = name
        self.period = period
        self.data = {}

        self.previous_data = None
        self.open_price = None

    def update(self, data: BaseData):
        current_data = data.end_time.date()

        if current_data != self.previous_data:
            self.previous_data = current_data
            self.open_price = data.open

        current_time = data.end_time.time()
        
        if current_time not in self.data:
            self.data[current_time] = deque(maxlen=self.period)

        self.data[current_time].append(
            np.abs(data.close / self.open_price - 1)
            )
        
        self.value = np.mean(self.data[current_time])

        return len(self.data[current_time]) == self.period