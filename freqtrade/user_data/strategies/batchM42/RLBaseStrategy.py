from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from freqtrade.freqai.data_kitchen import FreqaiDataKitchen
from freqtrade.freqai.prediction_writer import write_predictions_to_ohlcv
from freqtrade.strategy import IStrategy, merge_informative_pair

from freqai.rl.action_space import ActionSpace
from freqai.rl.reward import RewardCalculator
from freqai.rl.state_builder import StateBuilder
from utils.logging import get_logger


class RLBaseStrategy(IStrategy):
    """Базовая RL стратегия для Freqtrade с FreqAI."""

    minimal_roi = {"0": 10}
    stoploss = -0.99
    timeframe = "1m"
    informative_timeframe = "1h"
    startup_candle_count = 200
    process_only_new_candles = True
    can_short: bool = False
    use_custom_stoploss = False
    use_sell_signal = True
    use_custom_sell = False

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self.logger = get_logger(self.__class__.__name__)
        rl_cfg = config.get("freqai", {}).get("rl_config", {})
        self.long_only = rl_cfg.get("long_only", True)
        self.state_builder = StateBuilder(rl_cfg)
        self.action_space = ActionSpace(rl_cfg)
        self.reward_calc = RewardCalculator(rl_cfg)
        self.last_action_ts: Optional[datetime] = None

    def informative_pairs(self):
        return [(pair, self.informative_timeframe) for pair in self.dp.current_whitelist()]

    def merge_informative(self, df: pd.DataFrame, metadata: Dict[str, Any]) -> pd.DataFrame:
        inf_tf = self.informative_timeframe
        informative = self.dp.get_pair_dataframe(pair=metadata["pair"], timeframe=inf_tf)
        informative_cols = [c for c in informative.columns if c not in ["pair"]]
        informative = informative[informative_cols]
        merged = merge_informative_pair(df, informative, timeframe=inf_tf, ffill=True)
        return merged

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: Dict[str, Any]):
        df = self.merge_informative(dataframe.copy(), metadata)
        df = self.state_builder.add_state(df)

        # Запишем прогнозы агента в OHLVC для FreqAI
        dk = FreqaiDataKitchen(self, df, metadata)
        predictions = dk.get_data()
        df = write_predictions_to_ohlcv(df, predictions)
        return df

    def _position_features(self, row: pd.Series) -> Dict[str, float]:
        equity = row.get("equity", np.nan)
        balance = row.get("balance", np.nan)
        position_size = row.get("position_size", 0.0)
        entry_price = row.get("entry_price", np.nan)
        close = row.get("close", np.nan)
        assert not np.isnan(close), "Цена должна быть доступна"  # только для относительных расчётов

        free_cash = max(balance, 0.0) if not np.isnan(balance) else 0.0
        equity_est = equity if not np.isnan(equity) else free_cash + position_size * close
        position_value = position_size * close

        in_position = 1.0 if position_size > 0 else 0.0
        position_size_ratio = position_value / equity_est if equity_est > 0 else 0.0
        free_cash_ratio = free_cash / equity_est if equity_est > 0 else 0.0

        unrealized_pnl_pct = 0.0
        if position_size > 0 and not np.isnan(entry_price) and entry_price > 0:
            unrealized_pnl_pct = (close - entry_price) / entry_price

        trade_age = row.get("trade_duration", 0.0)
        trade_age_norm = trade_age / 1_000 if trade_age else 0.0

        entry_distance = 0.0
        if position_size > 0 and not np.isnan(entry_price) and entry_price > 0:
            entry_distance = (close / entry_price) - 1.0

        features = {
            "in_position": in_position,
            "position_size_ratio": position_size_ratio,
            "free_cash_ratio": free_cash_ratio,
            "unrealized_pnl_pct": unrealized_pnl_pct,
            "trade_age_norm": trade_age_norm,
            "entry_distance": entry_distance,
        }
        assert not any(np.isnan(v) for v in features.values()), "Позиционные признаки должны быть заданы"
        return features

    def _prepare_action(self, row: pd.Series) -> float:
        action = row.get("rl_action", 0.0)
        position_feats = self._position_features(row)
        action = self.action_space.apply_constraints(action, position_feats, self.last_action_ts)
        self.last_action_ts = row.name if isinstance(row.name, datetime) else datetime.utcnow()
        return action

    def _apply_action(self, action: float, row: pd.Series) -> Dict[str, float]:
        position_value = row.get("position_size", 0.0) * row["close"]
        balance = row.get("balance", 0.0)
        target = self.action_space.translate_action(action, balance, position_value)
        return target

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: Dict[str, Any]):
        df = dataframe.copy()
        df["enter_long"] = 0
        df["exit_long"] = 0

        for idx, row in df.iterrows():
            action = self._prepare_action(row)
            target = self._apply_action(action, row)

            if self.long_only and target.get("delta_buy", 0) > 0:
                df.at[idx, "enter_long"] = 1
            if target.get("delta_sell", 0) > 0:
                df.at[idx, "exit_long"] = 1

        return df

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: Dict[str, Any]):
        return dataframe


class RLLongOnlyStrategy(RLBaseStrategy):
    """Long-only обёртка с готовой конфигурацией."""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self.long_only = True
        self.can_short = False
