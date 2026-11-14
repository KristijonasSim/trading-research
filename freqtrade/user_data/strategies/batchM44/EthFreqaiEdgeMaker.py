from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from pandas import DataFrame, Series

from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy


ETH_RETURN_1M = "&-eth_return_1m"
ETH_RETURN_3M = "&-eth_return_3m"
ETH_RETURN_5M = "&-eth_return_5m"
RESIDUAL_1M = "&-eth_btc_residual_1m"
RESIDUAL_3M = "&-eth_btc_residual_3m"
RESIDUAL_5M = "&-eth_btc_residual_5m"
ADVERSE_PROXY_1M = "&-adverse_proxy_1m"


class EthFreqaiEdgeMaker(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "1m"
    can_short = True
    process_only_new_candles = True
    startup_candle_count = 1500

    minimal_roi = {"0": 100.0}
    stoploss = -0.15
    trailing_stop = False
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    order_types = {
        "entry": "limit",
        "exit": "limit",
        "emergency_exit": "market",
        "force_entry": "market",
        "force_exit": "market",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }
    order_time_in_force = {"entry": "PO", "exit": "GTC"}

    beta_window = 1440
    realized_vol_window = 60
    max_realized_vol = 0.006
    target_realized_vol = 0.002

    maker_fee = 0.00040
    slippage_cost = 0.00003
    half_spread_capture = 0.00005
    adverse_cost_weight = 0.35
    inventory_risk_weight = 0.20
    eth_prediction_weight = 0.40
    residual_prediction_weight = 0.60

    leverage_value = 1.0
    external_features_enabled = False
    external_features_path = Path(
        "user_data/data/external/features/derivatives_features_1m.feather"
    )

    @staticmethod
    def _log_return(series: Series) -> Series:
        return np.log(series).diff()

    @staticmethod
    def _forward_log_return(series: Series, periods: int) -> Series:
        log_price = np.log(series)
        return log_price.shift(-periods) - log_price

    @staticmethod
    def _rolling_beta(asset_return: Series, market_return: Series, window: int) -> Series:
        return asset_return.rolling(window).cov(market_return) / market_return.rolling(window).var()

    @staticmethod
    def _btc_pair_for(pair: str) -> str:
        if pair.endswith(":USDT"):
            return "BTC/USDT:USDT"
        return "BTC/USDT"

    @staticmethod
    def _weighted_prediction(dataframe: DataFrame, prefix: str) -> Series:
        return (
            dataframe[f"{prefix}_1m"] * 0.20
            + dataframe[f"{prefix}_3m"] * 0.30
            + dataframe[f"{prefix}_5m"] * 0.50
        )

    def _merge_btc_close(self, dataframe: DataFrame, pair: str) -> DataFrame:
        btc_pair = self._btc_pair_for(pair)
        btc = self.dp.get_pair_dataframe(pair=btc_pair, timeframe=self.timeframe)
        if btc.empty:
            raise ValueError(f"missing BTC data: {btc_pair} {self.timeframe}")

        dataframe["date"] = pd.to_datetime(dataframe["date"], utc=True).astype("datetime64[ns, UTC]")
        btc_close = btc[["date", "close"]].rename(columns={"close": "btc_close"})
        btc_close["date"] = pd.to_datetime(btc_close["date"], utc=True).astype("datetime64[ns, UTC]")
        return pd.merge_asof(
            dataframe.sort_values("date"),
            btc_close.sort_values("date"),
            on="date",
            direction="backward",
        )

    def _merge_external_features(self, dataframe: DataFrame) -> DataFrame:
        if not self.external_features_enabled:
            return dataframe
        if not self.external_features_path.exists():
            return dataframe

        external = pd.read_feather(self.external_features_path)
        if "date" not in external.columns:
            raise ValueError(f"{self.external_features_path} missing date column")

        dataframe["date"] = pd.to_datetime(dataframe["date"], utc=True).astype("datetime64[ns, UTC]")
        external["date"] = pd.to_datetime(external["date"], utc=True).astype("datetime64[ns, UTC]")
        feature_columns = [column for column in external.columns if column != "date"]
        external = external.rename(
            columns={column: f"%-external_{column}" for column in feature_columns}
        )
        return pd.merge_asof(
            dataframe.sort_values("date"),
            external.sort_values("date"),
            on="date",
            direction="backward",
        )

    def _add_edge_columns(self, dataframe: DataFrame) -> DataFrame:
        eth_prediction = self._weighted_prediction(dataframe, "&-eth_return")
        residual_prediction = self._weighted_prediction(dataframe, "&-eth_btc_residual")
        dataframe["predicted_return"] = (
            eth_prediction * self.eth_prediction_weight
            + residual_prediction * self.residual_prediction_weight
        )

        adverse_cost = dataframe[ADVERSE_PROXY_1M].clip(lower=0) * self.adverse_cost_weight
        inventory_penalty = dataframe["realized_vol"] * self.inventory_risk_weight
        base_cost = self.maker_fee + self.slippage_cost + inventory_penalty + adverse_cost

        dataframe["filled_edge_long"] = (
            dataframe["predicted_return"] + self.half_spread_capture - base_cost
        )
        dataframe["filled_edge_short"] = (
            -dataframe["predicted_return"] + self.half_spread_capture - base_cost
        )
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["realized_vol"] = (
            self._log_return(dataframe["close"]).rolling(self.realized_vol_window).std()
        )
        dataframe = self.freqai.start(dataframe, metadata, self)
        return self._add_edge_columns(dataframe)

    def feature_engineering_expand_all(
        self,
        dataframe: DataFrame,
        period: int,
        metadata: dict,
        **kwargs,
    ) -> DataFrame:
        log_return = self._log_return(dataframe["close"])
        volume_mean = dataframe["volume"].rolling(period).mean()
        high_max = dataframe["high"].rolling(period).max()
        low_min = dataframe["low"].rolling(period).min()
        range_width = (high_max - low_min).replace(0, np.nan)

        dataframe["%-return_sum-period"] = log_return.rolling(period).sum()
        dataframe["%-realized_vol-period"] = log_return.rolling(period).std()
        dataframe["%-range_pct-period"] = (dataframe["high"] - dataframe["low"]) / dataframe["close"]
        dataframe["%-body_pct-period"] = (dataframe["close"] - dataframe["open"]) / dataframe["open"]
        dataframe["%-volume_pressure-period"] = dataframe["volume"] / volume_mean - 1.0
        dataframe["%-close_position-period"] = (dataframe["close"] - low_min) / range_width
        return dataframe

    def feature_engineering_expand_basic(
        self,
        dataframe: DataFrame,
        metadata: dict,
        **kwargs,
    ) -> DataFrame:
        log_return = self._log_return(dataframe["close"])
        dataframe["%-return_1m"] = log_return
        dataframe["%-range_1m"] = (dataframe["high"] - dataframe["low"]) / dataframe["close"]
        dataframe["%-body_1m"] = (dataframe["close"] - dataframe["open"]) / dataframe["open"]
        return dataframe

    def feature_engineering_standard(
        self,
        dataframe: DataFrame,
        metadata: dict,
        **kwargs,
    ) -> DataFrame:
        dataframe = self._merge_btc_close(dataframe, metadata["pair"])
        eth_return = self._log_return(dataframe["close"])
        btc_return = self._log_return(dataframe["btc_close"])
        beta = self._rolling_beta(eth_return, btc_return, self.beta_window)

        dataframe["%-btc_return_1m"] = btc_return
        dataframe["%-btc_return_3m"] = np.log(dataframe["btc_close"]).diff(3)
        dataframe["%-btc_return_5m"] = np.log(dataframe["btc_close"]).diff(5)
        dataframe["%-btc_realized_vol_60m"] = btc_return.rolling(60).std()
        dataframe["%-eth_btc_residual_now"] = eth_return - beta * btc_return
        dataframe["%-hour"] = dataframe["date"].dt.hour
        dataframe["%-day_of_week"] = dataframe["date"].dt.dayofweek
        dataframe = self._merge_external_features(dataframe)
        dataframe = dataframe.drop(columns=["btc_close"])
        return dataframe

    def set_freqai_targets(
        self,
        dataframe: DataFrame,
        metadata: dict,
        **kwargs,
    ) -> DataFrame:
        dataframe = self._merge_btc_close(dataframe, metadata["pair"])
        eth_return = self._log_return(dataframe["close"])
        btc_return = self._log_return(dataframe["btc_close"])
        beta = self._rolling_beta(eth_return, btc_return, self.beta_window)

        targets = {}
        for periods in (1, 3, 5):
            eth_future = self._forward_log_return(dataframe["close"], periods)
            btc_future = self._forward_log_return(dataframe["btc_close"], periods)
            targets[f"&-eth_return_{periods}m"] = eth_future
            targets[f"&-eth_btc_residual_{periods}m"] = eth_future - beta * btc_future

        targets[ADVERSE_PROXY_1M] = self._forward_log_return(dataframe["close"], 1).abs()
        target_frame = pd.DataFrame(targets, index=dataframe.index)
        return pd.concat([dataframe.drop(columns=["btc_close"]), target_frame], axis=1)

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        tradable = (
            (dataframe["do_predict"] == 1)
            & (dataframe["volume"] > 0)
            & (dataframe["realized_vol"] <= self.max_realized_vol)
        )
        enter_long = (
            tradable
            & (dataframe["filled_edge_long"] > 0)
            & (dataframe["filled_edge_long"] > dataframe["filled_edge_short"])
        )
        enter_short = (
            tradable
            & (dataframe["filled_edge_short"] > 0)
            & (dataframe["filled_edge_short"] > dataframe["filled_edge_long"])
        )

        dataframe.loc[enter_long, ["enter_long", "enter_tag"]] = (1, "edge_maker_long")
        dataframe.loc[enter_short, ["enter_short", "enter_tag"]] = (1, "edge_maker_short")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        predict_ok = dataframe["do_predict"] == 1
        exit_long = predict_ok & (dataframe["filled_edge_long"] <= 0)
        exit_short = predict_ok & (dataframe["filled_edge_short"] <= 0)

        dataframe.loc[exit_long, ["exit_long", "exit_tag"]] = (1, "edge_gone_long")
        dataframe.loc[exit_short, ["exit_short", "exit_tag"]] = (1, "edge_gone_short")
        return dataframe

    def custom_entry_price(
        self,
        pair: str,
        trade: Trade | None,
        current_time: datetime,
        proposed_rate: float,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> float:
        if self.config["runmode"].value in ("live", "dry_run"):
            orderbook = self.dp.orderbook(pair, 1)
            if side == "long":
                return orderbook["bids"][0][0]
            return orderbook["asks"][0][0]
        return proposed_rate

    def custom_exit_price(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        proposed_rate: float,
        current_profit: float,
        exit_tag: str | None,
        **kwargs,
    ) -> float:
        if self.config["runmode"].value in ("live", "dry_run"):
            orderbook = self.dp.orderbook(pair, 1)
            if trade.is_short:
                return orderbook["bids"][0][0]
            return orderbook["asks"][0][0]
        return proposed_rate

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
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        last_candle = dataframe.iloc[-1].squeeze()
        if last_candle["realized_vol"] <= 0:
            return 0.0

        vol_scale = min(1.0, self.target_realized_vol / last_candle["realized_vol"])
        return min(proposed_stake * vol_scale, max_stake)

    def leverage(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_leverage: float,
        max_leverage: float,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> float:
        return min(self.leverage_value, max_leverage)


class EthSpotFreqaiEdgeMaker(EthFreqaiEdgeMaker):
    can_short = False
    maker_fee = 0.00100

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        if "enter_short" in dataframe.columns:
            short_entry = dataframe["enter_short"].eq(1)
            dataframe.loc[short_entry, "enter_tag"] = None
            dataframe.loc[:, "enter_short"] = 0
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_exit_trend(dataframe, metadata)
        if "exit_short" in dataframe.columns:
            dataframe.loc[:, "exit_short"] = 0
            dataframe.loc[dataframe["exit_long"].eq(1), "exit_tag"] = "edge_gone_long"
        return dataframe


class EthFreqaiEdgeMakerLev15(EthFreqaiEdgeMaker):
    leverage_value = 15.0


class EthFreqaiEdgeMakerLev18(EthFreqaiEdgeMaker):
    leverage_value = 18.0


class EthFreqaiEdgeMakerLev18Stop12(EthFreqaiEdgeMakerLev18):
    stoploss = -0.12


class EthFreqaiEdgeMakerLev18Stop12RankScalp(EthFreqaiEdgeMakerLev18Stop12):
    rank_scalp_window = 10080
    rank_scalp_quantile = 0.995
    rank_scalp_stake_fraction = 0.10
    rank_scalp_hold_minutes = 1.0

    @staticmethod
    def _is_rank_scalp(entry_tag: str | None) -> bool:
        return entry_tag in (
            "rank_scalp_long",
            "rank_scalp_short",
        )

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        score_abs = dataframe[ETH_RETURN_1M].abs()
        range_width = (dataframe["high"] - dataframe["low"]).replace(0, np.nan)
        dataframe["rank_scalp_threshold"] = (
            score_abs.rolling(self.rank_scalp_window, min_periods=1440)
            .quantile(self.rank_scalp_quantile)
            .shift(1)
        )
        dataframe["rank_scalp_close_position"] = (
            dataframe["close"] - dataframe["low"]
        ) / range_width
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        no_main_entry = dataframe["enter_long"].ne(1) & dataframe["enter_short"].ne(1)
        score = dataframe[ETH_RETURN_1M]
        scalp = (
            no_main_entry
            & dataframe["do_predict"].eq(1)
            & dataframe["volume"].gt(0)
            & dataframe["rank_scalp_threshold"].notna()
            & score.abs().gt(dataframe["rank_scalp_threshold"])
        )

        long_scalp = scalp & score.gt(0)
        short_scalp = (
            scalp
            & score.lt(0)
            & dataframe["rank_scalp_close_position"].gt(0.5)
        )

        dataframe.loc[long_scalp, ["enter_long", "enter_tag"]] = (
            1,
            "rank_scalp_long",
        )
        dataframe.loc[short_scalp, ["enter_short", "enter_tag"]] = (
            1,
            "rank_scalp_short",
        )
        return dataframe

    def custom_exit(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs,
    ) -> str | bool | None:
        if self._is_rank_scalp(trade.enter_tag):
            hold_minutes = (current_time - trade.open_date_utc).total_seconds() / 60.0
            if hold_minutes >= self.rank_scalp_hold_minutes:
                return "rank_scalp_time"
            return None

        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe.empty:
            return None

        row = dataframe[dataframe["date"] <= current_time].tail(1)
        if row.empty:
            return None

        candle = row.iloc[0]
        if trade.is_short and candle["filled_edge_short"] <= 0:
            return "edge_gone_short"
        if not trade.is_short and candle["filled_edge_long"] <= 0:
            return "edge_gone_long"
        return None

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, "exit_long"] = 0
        dataframe.loc[:, "exit_short"] = 0
        return dataframe

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
        if self._is_rank_scalp(entry_tag):
            return min(proposed_stake * self.rank_scalp_stake_fraction, max_stake)
        return super().custom_stake_amount(
            pair,
            current_time,
            current_rate,
            proposed_stake,
            min_stake,
            max_stake,
            leverage,
            entry_tag,
            side,
            **kwargs,
        )

    def leverage(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_leverage: float,
        max_leverage: float,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> float:
        if self._is_rank_scalp(entry_tag):
            return 1.0
        return super().leverage(
            pair,
            current_time,
            current_rate,
            proposed_leverage,
            max_leverage,
            entry_tag,
            side,
            **kwargs,
        )


class EthFreqaiEdgeMakerLev18Stop14RankScalp(EthFreqaiEdgeMakerLev18Stop12RankScalp):
    stoploss = -0.14


class EthFreqaiEdgeMakerLev18Stop14VolumeImpulseScalp(
    EthFreqaiEdgeMakerLev18Stop14RankScalp
):
    scalp_volume_z_window = 1440

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        volume_mean = dataframe["volume"].rolling(self.scalp_volume_z_window).mean()
        volume_std = dataframe["volume"].rolling(self.scalp_volume_z_window).std()
        dataframe["rank_scalp_volume_z"] = (
            dataframe["volume"] - volume_mean
        ) / volume_std.replace(0, np.nan)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        low_volume_scalp = (
            dataframe["enter_tag"].isin(["rank_scalp_long", "rank_scalp_short"])
            & dataframe["rank_scalp_volume_z"].le(1.0)
        )
        dataframe.loc[low_volume_scalp, ["enter_long", "enter_short", "enter_tag"]] = (
            0,
            0,
            None,
        )
        return dataframe


class EthFreqaiEdgeMakerLev18Stop14VolumeImpulseContextStakeScalp(
    EthFreqaiEdgeMakerLev18Stop14VolumeImpulseScalp
):
    scalp_context_window = 1440
    scalp_context_min_periods = 240
    scalp_probe_scale = 0.25
    eth_aggtrade_path = Path(
        "user_data/data/external/features/eth_aggtrade_features_1m.feather"
    )
    btc_aggtrade_path = Path(
        "user_data/data/external/features/btc_aggtrade_features_1m.feather"
    )
    book_depth_path = Path(
        "user_data/data/external/features/book_depth_features_1m.feather"
    )

    @staticmethod
    def _rolling_zscore(series: Series, window: int, min_periods: int) -> Series:
        mean = series.rolling(window, min_periods=min_periods).mean()
        std = series.rolling(window, min_periods=min_periods).std()
        return (series - mean) / std.replace(0, np.nan)

    @staticmethod
    def _depth_slope_pressure(dataframe: DataFrame, prefix: str) -> Series:
        bid = dataframe[f"{prefix}_book_bid_notional_slope_5_1"]
        ask = dataframe[f"{prefix}_book_ask_notional_slope_5_1"]
        return (bid - ask) / (bid + ask).replace(0, np.nan)

    def _build_scalp_context_features(self) -> DataFrame:
        eth = pd.read_feather(
            self.eth_aggtrade_path,
            columns=["date", "eth_agg_net_quote_volume"],
        )
        btc = pd.read_feather(
            self.btc_aggtrade_path,
            columns=["date", "btc_agg_net_quote_volume"],
        )
        book = pd.read_feather(
            self.book_depth_path,
            columns=[
                "date",
                "eth_book_bid_notional_slope_5_1",
                "eth_book_ask_notional_slope_5_1",
                "btc_book_bid_notional_slope_5_1",
                "btc_book_ask_notional_slope_5_1",
            ],
        )
        for frame in (eth, btc, book):
            frame["date"] = pd.to_datetime(frame["date"], utc=True).astype(
                "datetime64[ns, UTC]"
            )

        context = eth[["date", "eth_agg_net_quote_volume"]].merge(
            btc[["date", "btc_agg_net_quote_volume"]],
            on="date",
        )
        context = context.merge(
            book[
                [
                    "date",
                    "eth_book_bid_notional_slope_5_1",
                    "eth_book_ask_notional_slope_5_1",
                    "btc_book_bid_notional_slope_5_1",
                    "btc_book_ask_notional_slope_5_1",
                ]
            ],
            on="date",
        )

        eth_flow_z = self._rolling_zscore(
            context["eth_agg_net_quote_volume"],
            self.scalp_context_window,
            self.scalp_context_min_periods,
        )
        btc_flow_z = self._rolling_zscore(
            context["btc_agg_net_quote_volume"],
            self.scalp_context_window,
            self.scalp_context_min_periods,
        )
        context["scalp_rel_flow_z"] = eth_flow_z - btc_flow_z
        context["scalp_rel_depth_pressure"] = self._depth_slope_pressure(
            context, "eth"
        ) - self._depth_slope_pressure(context, "btc")
        return context[["date", "scalp_rel_flow_z", "scalp_rel_depth_pressure"]]

    def _get_scalp_context_features(self) -> DataFrame:
        context = getattr(self, "_scalp_context_features", None)
        if context is None:
            context = self._build_scalp_context_features()
            self._scalp_context_features = context
        return context

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        context = self._get_scalp_context_features()
        dataframe["date"] = pd.to_datetime(dataframe["date"], utc=True).astype(
            "datetime64[ns, UTC]"
        )
        return pd.merge_asof(
            dataframe.sort_values("date"),
            context.sort_values("date"),
            on="date",
            direction="backward",
        )

    def _scalp_context_scale(
        self,
        pair: str,
        current_time: datetime,
        side: str,
    ) -> float:
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        row = dataframe[dataframe["date"] <= current_time].tail(1)
        if row.empty:
            return self.scalp_probe_scale

        candle = row.iloc[0]
        direction = 1.0 if side == "long" else -1.0
        supports = (
            direction * candle["scalp_rel_flow_z"] > 0
            and direction * candle["scalp_rel_depth_pressure"] > 0
        )
        if supports:
            return 1.0
        return self.scalp_probe_scale

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
        stake = super().custom_stake_amount(
            pair,
            current_time,
            current_rate,
            proposed_stake,
            min_stake,
            max_stake,
            leverage,
            entry_tag,
            side,
            **kwargs,
        )
        if self._is_rank_scalp(entry_tag):
            return stake * self._scalp_context_scale(pair, current_time, side)
        return stake


class EthFreqaiEdgeMakerLev18Stop14ContextStakeBoostScalp(
    EthFreqaiEdgeMakerLev18Stop14VolumeImpulseContextStakeScalp
):
    rank_scalp_stake_fraction = 1.0
    scalp_probe_scale = 0.025


class EthFreqaiEdgeMakerLev18Stop14ContextStakeStrongFlowLev8Scalp(
    EthFreqaiEdgeMakerLev18Stop14ContextStakeBoostScalp
):
    scalp_supported_leverage = 8.0
    scalp_full_flow_z = 1.0

    def leverage(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_leverage: float,
        max_leverage: float,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> float:
        if not self._is_rank_scalp(entry_tag):
            return super().leverage(
                pair,
                current_time,
                current_rate,
                proposed_leverage,
                max_leverage,
                entry_tag,
                side,
                **kwargs,
            )

        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        row = dataframe[dataframe["date"] <= current_time].tail(1)
        if row.empty:
            return 1.0

        candle = row.iloc[0]
        direction = 1.0 if side == "long" else -1.0
        strong_support = (
            direction * candle["scalp_rel_flow_z"] > self.scalp_full_flow_z
            and direction * candle["scalp_rel_depth_pressure"] > 0
        )
        if strong_support:
            return min(self.scalp_supported_leverage, max_leverage)
        return 1.0


class EthFreqaiEdgeMakerLev18Stop14ContextStakeStrongFlowResidualLev8Scalp(
    EthFreqaiEdgeMakerLev18Stop14ContextStakeStrongFlowLev8Scalp
):
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        residual_abs = dataframe[RESIDUAL_1M].abs()
        dataframe["rank_residual_scalp_threshold"] = (
            residual_abs.rolling(self.rank_scalp_window, min_periods=1440)
            .quantile(self.rank_scalp_quantile)
            .shift(1)
        )
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        no_entry = dataframe["enter_long"].ne(1) & dataframe["enter_short"].ne(1)
        residual_score = dataframe[RESIDUAL_1M]
        residual_scalp = (
            no_entry
            & dataframe["do_predict"].eq(1)
            & dataframe["volume"].gt(0)
            & dataframe["rank_scalp_volume_z"].gt(1.0)
            & dataframe["rank_residual_scalp_threshold"].notna()
            & residual_score.abs().gt(dataframe["rank_residual_scalp_threshold"])
        )

        long_scalp = residual_scalp & residual_score.gt(0)
        short_scalp = (
            residual_scalp
            & residual_score.lt(0)
            & dataframe["rank_scalp_close_position"].gt(0.5)
        )

        dataframe.loc[long_scalp, ["enter_long", "enter_tag"]] = (
            1,
            "rank_scalp_long",
        )
        dataframe.loc[short_scalp, ["enter_short", "enter_tag"]] = (
            1,
            "rank_scalp_short",
        )
        return dataframe


class EthFreqaiEdgeMakerLev14Stop14ContextStakeStrongFlowResidualVolTargetLev8Scalp(
    EthFreqaiEdgeMakerLev18Stop14ContextStakeStrongFlowResidualLev8Scalp
):
    leverage_value = 14.0

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
        stake = super().custom_stake_amount(
            pair,
            current_time,
            current_rate,
            proposed_stake,
            min_stake,
            max_stake,
            leverage,
            entry_tag,
            side,
            **kwargs,
        )
        if not self._is_rank_scalp(entry_tag):
            return stake

        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        row = dataframe[dataframe["date"] <= current_time].tail(1)
        if row.empty:
            return stake

        realized_vol = row.iloc[0]["realized_vol"]
        if realized_vol <= 0:
            return 0.0
        return stake * min(1.0, self.target_realized_vol / realized_vol)


class EthFreqaiEdgeMakerLev14Stop14ContextStakeStrongOnlyResidualVolTargetLev8Scalp(
    EthFreqaiEdgeMakerLev14Stop14ContextStakeStrongFlowResidualVolTargetLev8Scalp
):
    def _scalp_context_scale(
        self,
        pair: str,
        current_time: datetime,
        side: str,
    ) -> float:
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        row = dataframe[dataframe["date"] <= current_time].tail(1)
        if row.empty:
            return self.scalp_probe_scale

        candle = row.iloc[0]
        direction = 1.0 if side == "long" else -1.0
        strong_support = (
            direction * candle["scalp_rel_flow_z"] > self.scalp_full_flow_z
            and direction * candle["scalp_rel_depth_pressure"] > 0
        )
        if strong_support:
            return 1.0
        return self.scalp_probe_scale


class EthEdgeRev3m129(
    EthFreqaiEdgeMakerLev14Stop14ContextStakeStrongOnlyResidualVolTargetLev8Scalp
):
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["edge_recent_return_3m"] = np.log(dataframe["close"]).diff(3).shift(1)
        return dataframe

    def leverage(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_leverage: float,
        max_leverage: float,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> float:
        if self._is_rank_scalp(entry_tag):
            return super().leverage(
                pair,
                current_time,
                current_rate,
                proposed_leverage,
                max_leverage,
                entry_tag,
                side,
                **kwargs,
            )

        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        row = dataframe[dataframe["date"] <= current_time].tail(1)
        if row.empty:
            return super().leverage(
                pair,
                current_time,
                current_rate,
                proposed_leverage,
                max_leverage,
                entry_tag,
                side,
                **kwargs,
            )

        direction = 1.0 if side == "long" else -1.0
        if direction * row.iloc[0]["edge_recent_return_3m"] > 0:
            return 1.0
        return super().leverage(
            pair,
            current_time,
            current_rate,
            proposed_leverage,
            max_leverage,
            entry_tag,
            side,
            **kwargs,
        )


class EthEdgeRev3mEthWeighted135(EthEdgeRev3m129):
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["rank_eth_weighted_score"] = self._weighted_prediction(
            dataframe, "&-eth_return"
        )
        dataframe["rank_eth_weighted_threshold"] = (
            dataframe["rank_eth_weighted_score"]
            .abs()
            .rolling(self.rank_scalp_window, min_periods=1440)
            .quantile(self.rank_scalp_quantile)
            .shift(1)
        )
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        no_entry = dataframe["enter_long"].ne(1) & dataframe["enter_short"].ne(1)
        score = dataframe["rank_eth_weighted_score"]
        scalp = (
            no_entry
            & dataframe["do_predict"].eq(1)
            & dataframe["volume"].gt(0)
            & dataframe["rank_scalp_volume_z"].gt(1.0)
            & dataframe["rank_eth_weighted_threshold"].notna()
            & score.abs().gt(dataframe["rank_eth_weighted_threshold"])
        )

        long_scalp = scalp & score.gt(0)
        short_scalp = (
            scalp
            & score.lt(0)
            & dataframe["rank_scalp_close_position"].gt(0.5)
        )

        dataframe.loc[long_scalp, ["enter_long", "enter_tag"]] = (
            1,
            "rank_scalp_long",
        )
        dataframe.loc[short_scalp, ["enter_short", "enter_tag"]] = (
            1,
            "rank_scalp_short",
        )
        return dataframe


class EthEdgeRev3mEthWeightedDailyStrongScout153(EthEdgeRev3mEthWeighted135):
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        rank_entry = dataframe["enter_tag"].isin(
            ["rank_scalp_long", "rank_scalp_short"]
        )
        direction = dataframe["enter_long"].where(
            dataframe["enter_long"].eq(1),
            -dataframe["enter_short"],
        )
        strong_rank = (
            rank_entry
            & (direction * dataframe["scalp_rel_flow_z"]).gt(self.scalp_full_flow_z)
            & (direction * dataframe["scalp_rel_depth_pressure"]).gt(0)
        )
        day = dataframe["date"].dt.normalize()
        strong_seen = (
            strong_rank.groupby(day)
            .transform(lambda signals: signals.shift(1).cummax())
            .fillna(False)
            .astype(bool)
        )
        rank_seen = (
            rank_entry.groupby(day)
            .transform(lambda signals: signals.shift(1).cummax())
            .fillna(False)
            .astype(bool)
        )
        weak_after_scout = rank_entry & ~strong_rank & ~strong_seen & rank_seen
        dataframe.loc[weak_after_scout, ["enter_long", "enter_short", "enter_tag"]] = (
            0,
            0,
            None,
        )
        return dataframe


class EthEdgeRev3mBodyLong154(EthEdgeRev3mEthWeightedDailyStrongScout153):
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        range_width = (dataframe["high"] - dataframe["low"]).replace(0, np.nan)
        body_density = (dataframe["close"] - dataframe["open"]).abs() / range_width
        dataframe["rank_scalp_body_density"] = body_density.shift(1)
        dataframe["rank_scalp_body_density_median"] = (
            body_density.rolling(self.rank_scalp_window, min_periods=1440)
            .median()
            .shift(1)
        )
        return dataframe

    def leverage(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_leverage: float,
        max_leverage: float,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> float:
        leverage = super().leverage(
            pair,
            current_time,
            current_rate,
            proposed_leverage,
            max_leverage,
            entry_tag,
            side,
            **kwargs,
        )
        if entry_tag != "rank_scalp_long":
            return leverage

        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        row = dataframe[dataframe["date"] <= current_time].tail(1)
        if row.empty:
            return leverage
        candle = row.iloc[0]
        if candle["rank_scalp_body_density"] < candle["rank_scalp_body_density_median"]:
            return 1.0
        return leverage


class EthEdgeRev3mStrongRankBodyLongBlock163(EthEdgeRev3mBodyLong154):
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        rank_entry = dataframe["enter_tag"].isin(
            ["rank_scalp_long", "rank_scalp_short"]
        )
        direction = dataframe["enter_long"].where(
            dataframe["enter_long"].eq(1),
            -dataframe["enter_short"],
        )
        strong_rank = (
            rank_entry
            & (direction * dataframe["scalp_rel_flow_z"]).gt(self.scalp_full_flow_z)
            & (direction * dataframe["scalp_rel_depth_pressure"]).gt(0)
        )
        weak_rank = rank_entry & ~strong_rank
        dataframe.loc[weak_rank, ["enter_long", "enter_short", "enter_tag"]] = (
            0,
            0,
            None,
        )
        weak_body_long = (
            dataframe["enter_tag"].eq("rank_scalp_long")
            & dataframe["rank_scalp_body_density"].lt(
                dataframe["rank_scalp_body_density_median"]
            )
        )
        dataframe.loc[weak_body_long, ["enter_long", "enter_short", "enter_tag"]] = (
            0,
            0,
            None,
        )
        return dataframe


class EthEdgeHfSmartPosition164(EthEdgeRev3mBodyLong154):
    """
    Current high-frequency mainline:
    core edge entries + strong-flow scalp + low-risk probe entries.

    163 keeps only strong rank entries and misses the required frequency.
    164 keeps the 154 position stack under an explicit production-candidate name.
    """


class EthEdgeHfSmartPosition167(EthEdgeHfSmartPosition164):
    """
    0.04% fee mainline candidate.

    Low body-density long probes were only de-levered in 164.  At the higher
    fee they have negative expectancy, so 167 blocks them instead.
    """

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        weak_body_long = (
            dataframe["enter_tag"].eq("rank_scalp_long")
            & dataframe["rank_scalp_body_density"].lt(
                dataframe["rank_scalp_body_density_median"]
            )
        )
        dataframe.loc[weak_body_long, ["enter_long", "enter_short", "enter_tag"]] = (
            0,
            0,
            None,
        )
        return dataframe


class EthEdgeHfSmartPosition170(EthEdgeHfSmartPosition167):
    """
    Current 0.04% fee mainline candidate.

    Uses the existing 18x main-edge risk tier, requires a same-day strong rank
    scalp before weak probes, and blocks two broad low-quality UTC sessions.
    """

    leverage_value = 18.0
    blocked_entry_hours = (6, 13)

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_entry_trend(dataframe, metadata)
        rank_entry = dataframe["enter_tag"].isin(
            ["rank_scalp_long", "rank_scalp_short"]
        )
        direction = dataframe["enter_long"].where(
            dataframe["enter_long"].eq(1),
            -dataframe["enter_short"],
        )
        strong_rank = (
            rank_entry
            & (direction * dataframe["scalp_rel_flow_z"]).gt(self.scalp_full_flow_z)
            & (direction * dataframe["scalp_rel_depth_pressure"]).gt(0)
        )
        day = dataframe["date"].dt.normalize()
        strong_seen = (
            strong_rank.groupby(day)
            .transform(lambda signals: signals.shift(1).cummax())
            .fillna(False)
            .astype(bool)
        )
        weak_before_strong = rank_entry & ~strong_rank & ~strong_seen
        dataframe.loc[
            weak_before_strong,
            ["enter_long", "enter_short", "enter_tag"],
        ] = (0, 0, None)
        blocked_hour = dataframe["date"].dt.hour.isin(self.blocked_entry_hours)
        dataframe.loc[blocked_hour, ["enter_long", "enter_short", "enter_tag"]] = (
            0,
            0,
            None,
        )
        return dataframe


class EthEdgeHfSmartPosition171(EthEdgeHfSmartPosition170):
    """
    Coarse session-filter test for the 170 mainline.

    Main-edge and rank-scap risk stay inherited. Weak handoff sessions are
    filtered more tightly to improve day-level loss structure.
    """

    blocked_entry_hours = (6, 12, 13, 19)


class EthEdgeHfSmartPosition173(EthEdgeHfSmartPosition171):
    """
    Current 0.04% fee mainline candidate.

    Long strong-rank scalp uses a conservative 14x tier. Short strong-rank
    scalp has the cleaner 2026 sample edge, so that side moves to the
    main-edge 18x tier. UTC 15 rank scalp entries are downgraded to the 1x
    probe tier to avoid the US cash-open whipsaw window.
    """

    scalp_supported_leverage = 14.0
    short_scalp_supported_leverage = 18.0
    rank_scalp_probe_hours = (15,)

    def leverage(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_leverage: float,
        max_leverage: float,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> float:
        leverage = super().leverage(
            pair,
            current_time,
            current_rate,
            proposed_leverage,
            max_leverage,
            entry_tag,
            side,
            **kwargs,
        )
        if entry_tag == "rank_scalp_short" and leverage == self.scalp_supported_leverage:
            leverage = min(self.short_scalp_supported_leverage, max_leverage)
        if (
            entry_tag in ["rank_scalp_long", "rank_scalp_short"]
            and leverage > 1.0
            and current_time.hour in self.rank_scalp_probe_hours
        ):
            return 1.0
        return leverage


class EthEdgeHfSmartPosition174(EthEdgeHfSmartPosition173):
    """
    TD Sequential multi-timeframe execution-risk test.

    The TD setup is computed from OHLCV only, following the supplied Pine logic:
    close < close[4] increments buy setup, close > close[4] increments sell
    setup, and counts wrap after 13.  Strong rank scalp entries are downgraded
    to 1x when the same-side TD late setup is crowded across multiple
    timeframes without an opposite late setup.
    """

    td_timeframes_minutes = (1, 5, 15, 60, 240)
    td_crowded_late_count = 2

    @staticmethod
    def _td_setup_counts(close: Series) -> tuple[Series, Series]:
        values = close.to_numpy(dtype=float)
        buy = np.zeros(len(values), dtype=np.int16)
        sell = np.zeros(len(values), dtype=np.int16)
        for index in range(4, len(values)):
            current = values[index]
            anchor = values[index - 4]
            if not np.isfinite(current) or not np.isfinite(anchor):
                continue
            if current < anchor:
                buy[index] = 1 if buy[index - 1] == 13 else buy[index - 1] + 1
            elif current > anchor:
                sell[index] = 1 if sell[index - 1] == 13 else sell[index - 1] + 1
        return (
            pd.Series(buy, index=close.index),
            pd.Series(sell, index=close.index),
        )

    @classmethod
    def _td_timeframe_features(cls, dataframe: DataFrame, minutes: int) -> DataFrame:
        source = dataframe[["date", "close"]].copy()
        source["date"] = pd.to_datetime(source["date"], utc=True).astype(
            "datetime64[ns, UTC]"
        )
        if minutes == 1:
            frame = source.set_index("date")
        else:
            frame = source.set_index("date").resample(
                f"{minutes}min",
                label="right",
                closed="right",
            ).last()
        frame = frame.dropna()
        buy, sell = cls._td_setup_counts(frame["close"])
        prefix = f"td_{minutes}m"
        features = pd.DataFrame(
            {
                "date": frame.index,
                f"{prefix}_buy_late": buy.ge(7).astype(float),
                f"{prefix}_sell_late": sell.ge(7).astype(float),
            }
        )
        features.index = pd.RangeIndex(len(features))
        return features

    def _add_td_execution_columns(self, dataframe: DataFrame) -> DataFrame:
        dataframe["date"] = pd.to_datetime(dataframe["date"], utc=True).astype(
            "datetime64[ns, UTC]"
        )
        for minutes in self.td_timeframes_minutes:
            features = self._td_timeframe_features(dataframe, minutes)
            dataframe = pd.merge_asof(
                dataframe.sort_values("date"),
                features.sort_values("date"),
                on="date",
                direction="backward",
            )
        dataframe["td_buy_late_sum"] = sum(
            dataframe[f"td_{minutes}m_buy_late"]
            for minutes in self.td_timeframes_minutes
        )
        dataframe["td_sell_late_sum"] = sum(
            dataframe[f"td_{minutes}m_sell_late"]
            for minutes in self.td_timeframes_minutes
        )
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        return self._add_td_execution_columns(dataframe)

    def _td_crowded_late(self, pair: str, current_time: datetime, side: str) -> bool:
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        row = dataframe[dataframe["date"] <= current_time].tail(1)
        if row.empty:
            return False
        candle = row.iloc[0]
        if side == "short":
            support = candle["td_sell_late_sum"]
            oppose = candle["td_buy_late_sum"]
        else:
            support = candle["td_buy_late_sum"]
            oppose = candle["td_sell_late_sum"]
        return support >= self.td_crowded_late_count and oppose == 0

    def leverage(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_leverage: float,
        max_leverage: float,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> float:
        leverage = super().leverage(
            pair,
            current_time,
            current_rate,
            proposed_leverage,
            max_leverage,
            entry_tag,
            side,
            **kwargs,
        )
        if (
            entry_tag in ["rank_scalp_long", "rank_scalp_short"]
            and leverage > 1.0
            and self._td_crowded_late(pair, current_time, side)
        ):
            return 1.0
        return leverage
