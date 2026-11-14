"""Small-capital Binance spot strategy using FreqAI as a probability filter.

This strategy is deliberately dry-run first.  FreqAI estimates the expected
return after a conservative cost buffer.  Deterministic rules retain final
control over entries, exits, position size, and account-level loss limits.
"""

from __future__ import annotations

import json
import logging
import math
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy, informative
from technical import qtpylib


logger = logging.getLogger(__name__)


class SmallCapitalFreqAI(IStrategy):
    """Frequently evaluated spot strategy with safe dynamic pair rotation."""

    INTERFACE_VERSION = 3
    can_short = False
    timeframe = "3m"
    # FreqAI trains/predicts once per completed 3-minute candle.  The bot loop,
    # order supervision, stops, API, and dashboard still run every 5 seconds.
    process_only_new_candles = True
    startup_candle_count = 200

    # Freqtrade ROI calculations include exchange fees.
    minimal_roi = {
        "0": 0.0060,
        "20": 0.0045,
        "45": 0.0030,
        "90": 0.0015,
        "150": -1.0,
    }
    stoploss = -0.0075
    use_custom_stoploss = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    order_types = {
        "entry": "market",
        "exit": "market",
        "emergency_exit": "market",
        "force_entry": "market",
        "force_exit": "market",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }
    order_time_in_force = {"entry": "GTC", "exit": "GTC"}

    # The training target already subtracts the complete estimated round-trip
    # cost.  Requiring another +0.25% here previously double-counted costs and
    # made every one of 1,520 valid overnight predictions fail the AI gate.
    estimated_round_trip_cost = 0.0022
    ai_min_net_return = 0.0
    trend_entry_min_gross_return = 0.0003
    momentum_entry_min_gross_return = -0.0005
    breakout_entry_min_gross_return = -0.0010
    ai_reversal_min_gross_return = -0.0015
    ai_exit_min_hold_minutes = 12
    loss_adaptation_window_hours = 3
    loss_adaptation_trade_count = 2
    reduced_stake_usdt = 8.00
    max_trades_per_day = 36
    max_daily_loss_usdt = 1.50
    max_total_loss_usdt = 5.00
    normal_stake_usdt = 12.00
    active_stake_usdt = 10.50
    active_pairs = {"INJ/USDT", "TIA/USDT"}
    min_quote_volume_24h = 2_000_000.0
    min_range_7d = 0.035
    max_range_7d = 0.25
    max_realized_volatility_7d = 0.12
    max_hourly_shock_7d = 0.03
    max_entry_spread = 0.0008
    max_signal_price_deviation = 0.0035

    plot_config = {
        "main_plot": {
            "ema_9": {"color": "#4FC3F7"},
            "ema_21": {"color": "#FFB74D"},
            "ema_50": {"color": "#AB47BC"},
        },
        "subplots": {
            "AI扣费后预测": {"&-net_return": {"color": "#66BB6A"}},
            "信号分数": {"signal_score": {"color": "#42A5F5"}},
            "RSI": {"rsi": {"color": "#EF5350"}},
        },
    }

    @property
    def protections(self) -> list[dict[str, Any]]:
        return [
            {"method": "CooldownPeriod", "stop_duration": 3},
            {
                "method": "StoplossGuard",
                "lookback_period": 60,
                "trade_limit": 2,
                "stop_duration": 12,
                "required_profit": 0.0,
                "only_per_pair": True,
            },
            {
                "method": "MaxDrawdown",
                "calculation_mode": "equity",
                "lookback_period": 1440,
                "trade_limit": 6,
                "stop_duration": 60,
                "max_allowed_drawdown": 0.03,
            },
            {
                "method": "LowProfitPairs",
                "lookback_period": 180,
                "trade_limit": 2,
                "stop_duration": 30,
                "required_profit": 0.0,
                "only_per_pair": True,
            },
        ]

    def version(self) -> str:
        return "2.7.1-market-fill-paper"

    # ---------------------------- FreqAI features ----------------------------
    def feature_engineering_expand_all(
        self, dataframe: DataFrame, period: int, metadata: dict, **kwargs
    ) -> DataFrame:
        dataframe["%-rsi-period"] = ta.RSI(dataframe, timeperiod=period)
        dataframe["%-adx-period"] = ta.ADX(dataframe, timeperiod=period)
        dataframe["%-roc-period"] = ta.ROC(dataframe, timeperiod=period)
        dataframe["%-atr-pct-period"] = ta.ATR(dataframe, timeperiod=period) / dataframe["close"]
        volume_mean = dataframe["volume"].rolling(period).mean()
        dataframe["%-relative-volume-period"] = dataframe["volume"] / volume_mean.replace(0, np.nan)
        return dataframe

    def feature_engineering_expand_basic(
        self, dataframe: DataFrame, metadata: dict, **kwargs
    ) -> DataFrame:
        dataframe["%-pct-change"] = dataframe["close"].pct_change()
        dataframe["%-candle-range"] = (dataframe["high"] - dataframe["low"]) / dataframe["close"]
        dataframe["%-volume-change"] = dataframe["volume"].pct_change().replace([np.inf, -np.inf], np.nan)
        return dataframe

    def feature_engineering_standard(
        self, dataframe: DataFrame, metadata: dict, **kwargs
    ) -> DataFrame:
        hour = dataframe["date"].dt.hour
        weekday = dataframe["date"].dt.dayofweek
        dataframe["%-hour-sin"] = np.sin(2 * np.pi * hour / 24)
        dataframe["%-hour-cos"] = np.cos(2 * np.pi * hour / 24)
        dataframe["%-weekday-sin"] = np.sin(2 * np.pi * weekday / 7)
        dataframe["%-weekday-cos"] = np.cos(2 * np.pi * weekday / 7)
        return dataframe

    def set_freqai_targets(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        horizon = int(self.freqai_info["feature_parameters"]["label_period_candles"])
        future_mean = dataframe["close"].shift(-horizon).rolling(horizon).mean()
        # Net target: predicted gross movement minus 0.20% round-trip fees and
        # 0.02% slippage reserve.  The entry gate compares this value with zero,
        # so costs are counted exactly once.
        dataframe["&-net_return"] = (
            future_mean / dataframe["close"] - 1.0 - self.estimated_round_trip_cost
        )
        return dataframe

    # ---------------------- deterministic market context ---------------------
    @informative("15m")
    def populate_indicators_pair_15m(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema_20"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema_50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["return_1"] = dataframe["close"].pct_change()
        dataframe["range_4"] = (
            dataframe["high"].rolling(4).max()
            / dataframe["low"].rolling(4).min().replace(0, np.nan)
            - 1.0
        )
        return dataframe

    @informative("1h")
    def populate_indicators_pair_1h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        log_return = np.log(dataframe["close"] / dataframe["close"].shift(1))
        dataframe["quote_volume_24h"] = (
            (dataframe["volume"] * dataframe["close"]).rolling(24).sum()
        )
        dataframe["range_7d"] = (
            dataframe["high"].rolling(168).max()
            / dataframe["low"].rolling(168).min().replace(0, np.nan)
            - 1.0
        )
        dataframe["realized_volatility_7d"] = log_return.rolling(168).std() * np.sqrt(168)
        dataframe["hourly_shock_7d"] = log_return.abs().rolling(168).max()
        return dataframe

    @informative("5m", "BTC/{stake}", fmt="btc_{column}_{timeframe}")
    def populate_indicators_btc_5m(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["return_2"] = dataframe["close"].pct_change(2)
        dataframe["ema_9"] = ta.EMA(dataframe, timeperiod=9)
        dataframe["ema_21"] = ta.EMA(dataframe, timeperiod=21)
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = self.freqai.start(dataframe, metadata, self)

        dataframe["ema_9"] = ta.EMA(dataframe, timeperiod=9)
        dataframe["ema_21"] = ta.EMA(dataframe, timeperiod=21)
        dataframe["ema_50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)
        dataframe["atr_pct"] = ta.ATR(dataframe, timeperiod=14) / dataframe["close"]
        dataframe["relative_volume"] = dataframe["volume"] / dataframe["volume"].rolling(20).mean()
        dataframe["return_1"] = dataframe["close"].pct_change()
        dataframe["return_5"] = dataframe["close"].pct_change(5)
        dataframe["recent_shock"] = dataframe["return_1"].abs().rolling(20).max()
        dataframe["range_20"] = (
            dataframe["high"].rolling(20).max()
            / dataframe["low"].rolling(20).min().replace(0, np.nan)
            - 1.0
        )

        bands = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2.0)
        dataframe["bb_lower"] = bands["lower"]
        dataframe["bb_mid"] = bands["mid"]
        dataframe["bb_upper"] = bands["upper"]
        dataframe["recent_high"] = dataframe["high"].rolling(12).max().shift(1)

        dataframe["trend_15m_ok"] = (
            (dataframe["ema_20_15m"] > dataframe["ema_50_15m"])
            & (dataframe["close_15m"] > dataframe["ema_50_15m"] * 0.994)
            & (dataframe["adx_15m"] > 9)
        )
        dataframe["btc_market_ok"] = (
            (dataframe["btc_return_2_5m"] > -0.009)
            & (dataframe["btc_ema_9_5m"] > dataframe["btc_ema_21_5m"] * 0.990)
        )
        # Seek enough movement to cover costs, but reject pump/dump behaviour.
        # A pair stays blocked for roughly one hour after an abnormal 3-minute
        # candle, instead of immediately chasing the spike.
        dataframe["volatility_ok"] = dataframe["atr_pct"].between(0.00065, 0.006)
        dataframe["stability_ok"] = (
            (dataframe["return_1"].abs() < 0.012)
            & dataframe["return_5"].between(-0.025, 0.030)
            & (dataframe["recent_shock"] < 0.018)
            & (dataframe["range_20"] < 0.055)
            & (dataframe["return_1_15m"].abs() < 0.025)
            & (dataframe["range_4_15m"] < 0.075)
            & (dataframe["relative_volume"] < 6.0)
        )
        dataframe["market_eligible"] = (
            (dataframe["quote_volume_24h_1h"] >= self.min_quote_volume_24h)
            & dataframe["range_7d_1h"].between(self.min_range_7d, self.max_range_7d)
            & (dataframe["realized_volatility_7d_1h"] <= self.max_realized_volatility_7d)
            & (dataframe["hourly_shock_7d_1h"] < self.max_hourly_shock_7d)
        )
        dataframe["volume_ok"] = dataframe["relative_volume"] > 0.55
        dataframe["rsi_ok"] = dataframe["rsi"].between(30, 76)
        dataframe["ai_ok"] = (
            (dataframe["do_predict"] == 1)
            & (dataframe["&-net_return"] > self.ai_min_net_return)
        )
        dataframe["ai_gross_return"] = (
            dataframe["&-net_return"] + self.estimated_round_trip_cost
        )
        # A single 3-minute prediction is noisy. Require two materially
        # negative predictions before the AI-reversal exit may trigger.
        dataframe["ai_reversal_confirmed"] = (
            (dataframe["do_predict"] == 1)
            & (dataframe["ai_gross_return"] < self.ai_reversal_min_gross_return)
            & (dataframe["ai_gross_return"].shift(1) < self.ai_reversal_min_gross_return)
        )

        crossed_ema9 = (
            (dataframe["close"] > dataframe["ema_9"])
            & (dataframe["close"].shift(1) <= dataframe["ema_9"].shift(1) * 1.003)
        )
        dataframe["pattern_pullback"] = (
            (dataframe["ema_9"] > dataframe["ema_21"])
            & (dataframe["ema_21"] > dataframe["ema_50"])
            & crossed_ema9
            & dataframe["rsi"].between(38, 69)
            & (dataframe["relative_volume"] > 0.75)
        )
        dataframe["pattern_breakout"] = (
            (dataframe["close"] > dataframe["high"].rolling(8).max().shift(1))
            & (dataframe["relative_volume"] > 1.05)
            & dataframe["rsi"].between(46, 76)
        )
        dataframe["pattern_rebound"] = (
            (dataframe["adx"] < 28)
            & (dataframe["close"] > dataframe["bb_lower"])
            & (dataframe["close"].shift(1) <= dataframe["bb_lower"].shift(1) * 1.010)
            & crossed_ema9
            & dataframe["rsi"].between(31, 52)
            & (dataframe["relative_volume"] > 0.70)
            & (dataframe["ema_20_15m"] > dataframe["ema_50_15m"] * 0.998)
            & (dataframe["close_15m"] > dataframe["ema_50_15m"] * 0.990)
        )
        dataframe["pattern_momentum"] = (
            (dataframe["ema_9"] > dataframe["ema_21"])
            & (dataframe["ema_21"] > dataframe["ema_50"] * 0.998)
            & (dataframe["close"] > dataframe["ema_9"])
            & (dataframe["close"] <= dataframe["ema_9"] * 1.004)
            & dataframe["adx"].between(12, 48)
            & dataframe["rsi"].between(45, 65)
            & (dataframe["relative_volume"] > 0.75)
        )
        dataframe["pattern_ok"] = (
            dataframe["pattern_pullback"]
            | dataframe["pattern_breakout"]
            | dataframe["pattern_rebound"]
            | dataframe["pattern_momentum"]
        )

        dataframe["signal_score"] = (
            (dataframe["do_predict"] == 1).astype(int) * 10
            + dataframe["ai_ok"].astype(int) * 20
            + dataframe["trend_15m_ok"].astype(int) * 15
            + dataframe["btc_market_ok"].astype(int) * 15
            + dataframe["volatility_ok"].astype(int) * 10
            + dataframe["volume_ok"].astype(int) * 10
            + dataframe["rsi_ok"].astype(int) * 10
            + dataframe["stability_ok"].astype(int) * 10
            + dataframe["market_eligible"].astype(int) * 10
            + dataframe["pattern_ok"].astype(int) * 10
        )

        dataframe["decision"] = "等待：尚未形成合格买入组合"
        dataframe.loc[dataframe["do_predict"] != 1, "decision"] = "等待：AI模型训练中或样本异常"
        dataframe.loc[
            (dataframe["do_predict"] == 1)
            & (dataframe["ai_gross_return"] <= self.breakout_entry_min_gross_return),
            "decision",
        ] = "等待：AI方向明显偏弱"
        dataframe.loc[
            (dataframe["do_predict"] == 1)
            & (dataframe["ai_gross_return"] > self.breakout_entry_min_gross_return)
            & ~dataframe["pattern_ok"]
            & ~dataframe["trend_15m_ok"],
            "decision",
        ] = "观察：AI方向可用，等待趋势或突破"
        dataframe.loc[~dataframe["btc_market_ok"], "decision"] = "等待：BTC短线偏弱，暂缓买入其他币"
        dataframe.loc[~dataframe["volatility_ok"], "decision"] = "等待：当前波动过低或过高"
        dataframe.loc[
            (dataframe["do_predict"] == 1)
            & (dataframe["ai_gross_return"] > self.breakout_entry_min_gross_return)
            & ~dataframe["pattern_ok"],
            "decision",
        ] = "观察：方向合格，等待价格形态确认"
        dataframe.loc[~dataframe["stability_ok"], "decision"] = "等待：检测到急涨急跌，进入冷静观察"
        dataframe.loc[~dataframe["market_eligible"], "decision"] = (
            "动态排除：成交额或7日稳定性不合格"
        )
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        common = (
            (dataframe["do_predict"] == 1)
            & dataframe["market_eligible"]
            & dataframe["btc_market_ok"]
            & dataframe["volatility_ok"]
            & dataframe["stability_ok"]
            & dataframe["volume_ok"]
            & dataframe["rsi_ok"]
            & (dataframe["signal_score"] >= 75)
            & (dataframe["volume"] > 0)
        )

        # Active paper-trading routes use the predicted gross direction. Fees
        # remain in P&L and model diagnostics, but no longer veto every entry.
        pullback_entry = (
            common
            & (dataframe["ai_gross_return"] > self.trend_entry_min_gross_return)
            & dataframe["trend_15m_ok"]
            & (dataframe["rsi"] < 72)
        )
        momentum_entry = (
            common
            & (dataframe["ai_gross_return"] > self.momentum_entry_min_gross_return)
            & dataframe["trend_15m_ok"]
            & (dataframe["pattern_momentum"] | dataframe["pattern_pullback"])
        )
        breakout_entry = (
            common
            & (dataframe["ai_gross_return"] > self.breakout_entry_min_gross_return)
            & dataframe["pattern_breakout"]
            & (dataframe["relative_volume"] > 1.15)
        )
        # Range-bottom entries were the only consistently losing family in
        # walk-forward tests.  Keep the pattern visible for diagnostics, but
        # never turn it into an order until a later version re-validates it.
        rebound_entry = dataframe["pattern_rebound"] & False

        dataframe.loc[pullback_entry, ["enter_long", "enter_tag", "decision"]] = (
            1,
            "ai_positive_trend",
            "买入信号：AI通过＋趋势延续/回踩确认",
        )
        dataframe.loc[momentum_entry, ["enter_long", "enter_tag", "decision"]] = (
            1,
            "ai_trend_momentum",
            "买入信号：方向通过＋趋势动量/回踩确认",
        )
        dataframe.loc[breakout_entry, ["enter_long", "enter_tag", "decision"]] = (
            1,
            "ai_volume_breakout",
            "买入信号：AI通过＋放量突破确认",
        )
        dataframe.loc[rebound_entry, ["enter_long", "enter_tag", "decision"]] = (
            1,
            "ai_range_rebound",
            "买入信号：AI通过＋震荡反弹确认",
        )
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        exit_condition = (
            dataframe["ai_reversal_confirmed"]
            & (dataframe["ema_9"] < dataframe["ema_21"])
            & (dataframe["rsi"] < 47)
            & (dataframe["volume"] > 0)
        )
        dataframe.loc[exit_condition, ["exit_long", "exit_tag"]] = (1, "ai_trend_reversal")
        return dataframe

    # ------------------------------ live guards ------------------------------
    def custom_stake_amount(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_stake: float,
        min_stake: float | None,
        max_stake: float,
        leverage: float,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> float:
        wanted = self.active_stake_usdt if pair in self.active_pairs else self.normal_stake_usdt
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if not dataframe.empty:
            last = dataframe.iloc[-1]
            if not bool(last.get("market_eligible", False)):
                logger.info("跳过 %s：动态市场资格未通过", pair)
                return 0.0
            if not bool(last.get("stability_ok", False)):
                logger.info("跳过 %s：实时急涨急跌保护未通过", pair)
                return 0.0
            if float(last.get("atr_pct", 0.0)) > 0.003:
                wanted = min(wanted, self.active_stake_usdt)
        cutoff = current_time.astimezone(timezone.utc) - timedelta(
            hours=self.loss_adaptation_window_hours
        )
        recent_closed = Trade.get_trades_proxy(is_open=False, close_date=cutoff)
        recent_losses = [
            trade for trade in recent_closed if float(trade.close_profit_abs or 0.0) < 0
        ]
        if len(recent_losses) >= self.loss_adaptation_trade_count:
            wanted = min(wanted, self.reduced_stake_usdt)
            logger.info(
                "最近%d小时有%d笔亏损：继续交易但单笔降至%.2f USDT",
                self.loss_adaptation_window_hours,
                len(recent_losses),
                wanted,
            )
        if min_stake is not None and wanted < min_stake:
            logger.warning("跳过 %s：交易所最小下单额 %.4f 高于计划金额 %.4f", pair, min_stake, wanted)
            return 0.0
        return max(0.0, min(wanted, max_stake))

    def confirm_trade_entry(
        self,
        pair: str,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        current_time: datetime,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> bool:
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe.empty:
            return False
        last = dataframe.iloc[-1]
        if float(last.get("signal_score", 0)) < 75 or int(last.get("do_predict", 0)) != 1:
            return False
        if not bool(last.get("stability_ok", False)):
            return False
        if not bool(last.get("market_eligible", False)):
            return False
        if rate > float(last["close"]) * (1 + self.max_signal_price_deviation):
            logger.info("拒绝 %s：成交价偏离信号价超过0.35%%", pair)
            return False
        try:
            orderbook = self.dp.orderbook(pair, 1)
            best_bid = float(orderbook["bids"][0][0])
            best_ask = float(orderbook["asks"][0][0])
            spread = 1.0 - best_bid / best_ask
        except Exception as exc:
            logger.warning("拒绝 %s：无法读取实时买卖价差：%s", pair, exc)
            return False
        if spread > self.max_entry_spread:
            logger.info("拒绝 %s：实时买卖价差 %.4f%% 超过上限", pair, spread * 100)
            return False

        day_start = current_time.astimezone(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        today_trades = Trade.get_trades_proxy(is_open=False, close_date=day_start)
        daily_profit = sum(float(t.close_profit_abs or 0.0) for t in today_trades)
        if len(today_trades) >= self.max_trades_per_day:
            logger.warning("拒绝新交易：今日已达到%d笔上限", self.max_trades_per_day)
            return False
        if daily_profit <= -self.max_daily_loss_usdt:
            logger.warning("拒绝新交易：今日亏损 %.4f USDT 已触发保护", daily_profit)
            return False
        if float(Trade.get_total_closed_profit() or 0.0) <= -self.max_total_loss_usdt:
            logger.warning("拒绝新交易：总亏损已达到 %.2f USDT", self.max_total_loss_usdt)
            return False

        return True

    def custom_stoploss(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        after_fill: bool,
        **kwargs,
    ) -> float | None:
        if current_profit > 0.007:
            return 0.0020
        if current_profit > 0.004:
            return 0.0025
        if current_profit > 0.0025 and current_time - trade.open_date_utc > timedelta(minutes=45):
            return 0.0030
        return None

    def custom_exit(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs,
    ) -> str | None:
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe.empty:
            return None
        last = dataframe.iloc[-1]
        held = current_time - trade.open_date_utc
        if not bool(last.get("stability_ok", True)) and current_profit > -0.004:
            return "sudden_move_risk"
        if held > timedelta(minutes=90) and current_profit < 0.0015:
            return "time_limit_90m"
        if current_profit > 0.0035 and float(last.get("ema_9", 0)) < float(last.get("ema_21", 0)):
            return "protect_small_profit"
        if (
            held >= timedelta(minutes=self.ai_exit_min_hold_minutes)
            and
            int(last.get("do_predict", 0)) == 1
            and bool(last.get("ai_reversal_confirmed", False))
            and current_profit > -0.003
        ):
            return "ai_risk_reversal"
        if not bool(last.get("btc_market_ok", True)) and current_profit > -0.004:
            return "btc_market_risk"
        return None

    def bot_loop_start(self, current_time: datetime, **kwargs) -> None:
        """Write a compact, Chinese-readable status snapshot every bot loop."""
        if self.config["runmode"].value not in ("live", "dry_run"):
            return
        self._loop_count = getattr(self, "_loop_count", 0) + 1
        signals: list[dict[str, Any]] = []
        for pair in self.dp.current_whitelist():
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            if dataframe.empty:
                continue
            row = dataframe.iloc[-1]
            signals.append(
                {
                    "pair": pair,
                    "candle_time": self._json_value(row.get("date")),
                    "price": self._number(row.get("close")),
                    "score": self._number(row.get("signal_score")),
                    "ai_net_return_pct": self._number(row.get("&-net_return"), scale=100),
                    "ai_gross_return_pct": self._number(row.get("ai_gross_return"), scale=100),
                    "do_predict": int(self._number(row.get("do_predict"))),
                    "rsi": self._number(row.get("rsi")),
                    "atr_pct": self._number(row.get("atr_pct"), scale=100),
                    "range_1h_pct": self._number(row.get("range_20"), scale=100),
                    "stable": bool(row.get("stability_ok", False)),
                    "market_eligible": bool(row.get("market_eligible", False)),
                    "quote_volume_24h_usdt": self._number(row.get("quote_volume_24h_1h")),
                    "range_7d_pct": self._number(row.get("range_7d_1h"), scale=100),
                    "realized_volatility_7d_pct": self._number(
                        row.get("realized_volatility_7d_1h"), scale=100
                    ),
                    "relative_volume": self._number(row.get("relative_volume")),
                    "decision": str(row.get("decision", "等待：数据准备中")),
                    "entry_tag": str(row.get("enter_tag", "") or ""),
                }
            )
        configured_pairs = list(self.config.get("exchange", {}).get("pair_whitelist", []))
        eligibility = {item["pair"]: item.get("market_eligible", False) for item in signals}
        active_pairs = [pair for pair in configured_pairs if eligibility.get(pair, False)]
        payload = {
            "updated_at": current_time.astimezone(timezone.utc).isoformat(),
            "loop_count": self._loop_count,
            "loop_interval_seconds": int(self.config.get("internals", {}).get("process_throttle_secs", 5)),
            "pair_selection": {
                "mode": "安全动态轮换",
                "universe_count": len(configured_pairs),
                "active_count": len(active_pairs),
                "active_pairs": active_pairs,
                "filtered_pairs": sorted(set(configured_pairs) - set(active_pairs)),
                "refresh_minutes": 60,
            },
            "signals": sorted(signals, key=lambda item: item.get("score", 0), reverse=True),
        }
        user_dir = Path(self.config["user_data_dir"])
        runtime_dir = user_dir / "runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        target = runtime_dir / "strategy_status.json"
        temporary = runtime_dir / "strategy_status.tmp"
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        for attempt in range(3):
            try:
                os.replace(temporary, target)
                break
            except PermissionError:
                if attempt < 2:
                    time.sleep(0.05)
                else:
                    # A Windows dashboard reader can briefly hold the existing
                    # file.  Missing one 5-second refresh is safer than turning
                    # a harmless display race into a strategy error.
                    logger.debug("中文状态文件正被读取，本轮面板刷新已跳过")
                    temporary.unlink(missing_ok=True)

    @staticmethod
    def _number(value: Any, scale: float = 1.0) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 0.0
        if not math.isfinite(number):
            return 0.0
        return round(number * scale, 6)

    @staticmethod
    def _json_value(value: Any) -> str:
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return str(value)
