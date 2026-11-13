import talib.abstract as ta
from datetime import datetime, timezone
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from pandas import DataFrame
from functools import reduce
import numpy as np
import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logger = logging.getLogger(__name__)


class ADA_MeanReversion(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "5m"
    startup_candle_count = 100
    process_only_new_candles = False
    can_short = False
    position_adjustment_enable = False

    minimal_roi = {
        "0": 0.005,
        "10": 0.003,
        "20": 0.001,
        "30": 0.0,
        "60": -0.01,
    }

    stoploss = -0.04
    use_custom_stoploss = True

    trailing_stop = False

    max_open_trades = 2

    buy_params = {
        "bb_deviation": 1.5,
        "rsi_oversold": 35,
        "rsi_overbought": 65,
        "adx_max": 25,
        "stake_base_pct": 0.15,
    }

    bb_deviation = DecimalParameter(1.0, 2.0, default=1.5, space="buy")
    rsi_oversold = IntParameter(25, 45, default=35, space="buy")
    rsi_overbought = IntParameter(55, 75, default=65, space="buy")
    adx_max = IntParameter(18, 30, default=25, space="buy")
    stake_base_pct = DecimalParameter(0.05, 0.25, default=0.15, space="buy")

    def informative_pairs(self):
        return []

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self._consecutive_losses = 0
        self._current_trading_day = None
        self._day_initial_balance = 0.0
        self._circuit_active = False
        self._circuit_reason = ""
        self._trade_count = 0
        self._start_time = datetime.now(timezone.utc)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi_14"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["rsi_7"] = ta.RSI(dataframe, timeperiod=7)

        for period in [7, 14, 21]:
            dataframe[f"ema_{period}"] = ta.EMA(dataframe, timeperiod=period)

        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)

        bb = ta.BBANDS(dataframe, timeperiod=20, nbdevup=self.bb_deviation.value, nbdevdn=self.bb_deviation.value)
        dataframe["bb_upper"] = bb["upperband"]
        dataframe["bb_middle"] = bb["middleband"]
        dataframe["bb_lower"] = bb["lowerband"]
        dataframe["bb_width"] = (dataframe["bb_upper"] - dataframe["bb_lower"]) / (dataframe["bb_middle"] + 1e-10)

        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["atr_pct"] = dataframe["atr"] / (dataframe["close"] + 1e-10)

        dataframe["volume_ema"] = ta.EMA(dataframe["volume"], timeperiod=10)
        dataframe["volume_ratio"] = dataframe["volume"] / (dataframe["volume_ema"] + 1e-10)

        dataframe["close_std"] = dataframe["close"].rolling(20).std()
        dataframe["close_mean"] = dataframe["close"].rolling(20).mean()
        dataframe["deviation_from_mean"] = (dataframe["close"] - dataframe["close_mean"]) / (dataframe["close_std"] + 1e-10)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["enter_long"] = 0
        dataframe["enter_tag"] = ""

        mean_reversion_long = [
            dataframe["deviation_from_mean"] < -self.bb_deviation.value,
            dataframe["close"] < dataframe["bb_lower"],
            dataframe["rsi_14"] < self.rsi_oversold.value,
            dataframe["adx"] < self.adx_max.value,
            dataframe["volume_ratio"] > 0.5,
            dataframe["volume"] > 0,
        ]
        sig_long = reduce(lambda x, y: x & y, mean_reversion_long)

        df = dataframe
        df.loc[sig_long, ["enter_long", "enter_tag"]] = (1, "mean_reversion_long")

        return df

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_tag"] = ""

        mean_reversion_exit = [
            dataframe["deviation_from_mean"] > -0.3,
            dataframe["close"] > dataframe["bb_middle"],
            dataframe["rsi_14"] > self.rsi_overbought.value,
        ]
        sig_exit = reduce(lambda x, y: x & y, mean_reversion_exit)

        df = dataframe
        df.loc[sig_exit, ["exit_long", "exit_tag"]] = (1, "mean_reversion_exit")

        return df

    def custom_stoploss(self, pair: str, trade, current_time: datetime,
                        current_rate: float, current_profit: float,
                        after_fill: bool, **kwargs) -> float:
        if after_fill:
            return -0.99
        elapsed = (current_time - trade.open_date_utc).total_seconds() / 60
        if elapsed < 5:
            return -0.99
        if elapsed > 30:
            return -0.01
        profit_asset = current_profit / trade.leverage
        if profit_asset > 0.002:
            return -0.001
        return -0.002

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: str | None,
                 side: str, **kwargs) -> float:
        return 3.0

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                            proposed_stake: float, min_stake: float, max_stake: float,
                            entry_tag: str | None, side: str, **kwargs) -> float:
        wallet = self.wallets.get_total_stake_amount()
        base_pct = float(self.stake_base_pct.value)

        if self._consecutive_losses >= 3:
            base_pct = base_pct * 0.25
        elif self._consecutive_losses >= 1:
            base_pct = base_pct * 0.50

        return max(min_stake, min(wallet * base_pct, max_stake))

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                            time_in_force: str, current_time: datetime, entry_tag: str | None,
                            side: str, **kwargs) -> bool:
        today = current_time.date()
        if self._current_trading_day != today:
            self._current_trading_day = today
            self._consecutive_losses = 0
            self._day_initial_balance = self.wallets.get_total_stake_amount()
            self._circuit_active = False
            self._circuit_reason = ""

        if self._consecutive_losses >= 4:
            logger.info(f'Loss breaker: {self._consecutive_losses} consecutive, rejecting {pair}')
            return False

        if self._day_initial_balance > 0:
            current_balance = self.wallets.get_total_stake_amount()
            day_loss_pct = (current_balance - self._day_initial_balance) / self._day_initial_balance * 100
            if day_loss_pct < -3.0:
                if not self._circuit_active:
                    self._circuit_active = True
                    self._circuit_reason = "daily_nav_limit"
                    logger.info(f'Daily NAV limit -{day_loss_pct:.1f}% hit, entries halted')
                return False

        return True

    def confirm_trade_exit(self, pair: str, trade, order_type: str, amount: float,
                           rate: float, time_in_force: str, exit_reason: str,
                           current_time: datetime, **kwargs) -> bool:
        profit_pct = trade.calc_profit_ratio(rate=rate) * 100
        today = current_time.date()
        if self._current_trading_day != today:
            self._current_trading_day = today
            self._consecutive_losses = 0
            self._day_initial_balance = self.wallets.get_total_stake_amount()
        if profit_pct < 0:
            self._consecutive_losses += 1
        else:
            self._consecutive_losses = 0
        return True