# -*- coding: utf-8 -*-
import threading
import time
import random
import logging
from typing import Dict, Optional

import numpy as np
import pandas as pd
from pandas import DataFrame

import talib.abstract as ta
from freqtrade.strategy import IStrategy, IntParameter

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# === Fonctions crossover manuelles ===
def crossover(series1: pd.Series, series2: pd.Series) -> pd.Series:
    """Retourne True si series1 croise à la hausse series2."""
    if isinstance(series2, (int, float)):
        series2 = pd.Series(series2, index=series1.index)
    return (series1.shift(1) < series2.shift(1)) & (series1 > series2)

def crossunder(series1: pd.Series, series2: pd.Series) -> pd.Series:
    """Retourne True si series1 croise à la baisse series2."""
    if isinstance(series2, (int, float)):
        series2 = pd.Series(series2, index=series1.index)
    return (series1.shift(1) > series2.shift(1)) & (series1 < series2)


class AI_ModulaireV1(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "5m"
    informative_timeframe = "1h"
    can_short: bool = False

    minimal_roi = {"60": 0.0015, "30": 0.003, "0": 0.005}
    stoploss = -0.10
    trailing_stop = False
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = True
    ignore_roi_if_entry_signal = False
    startup_candle_count: int = 60

    # === PARAMÈTRES MODIFIABLES PAR L’IA ===
    buy_rsi = IntParameter(8, 50, default=30, space="buy")
    sell_rsi = IntParameter(50, 95, default=70, space="sell")

    # === ÉTAT INTERNE ===
    _optimizer_thread_started = False
    _optimizer_lock = threading.Lock()
    _optimizer_state = {
        "best_score": -1e9,
        "best_params": None,
        "last_applied_at": 0
    }

    OPTIMIZER_SLEEP = 5
    OPTIMIZER_WINDOW = 1000
    OPTIMIZER_BATCH = 20
    OPTIMIZER_IMPROVEMENT_THRESH = 0.01
    OPTIMIZER_COOLDOWN = 30
    OPTIMIZER_MIN_TRADES = 3

    def plot_config(self):
        return {
            "main_plot": {"tema": {}, "sar": {"color": "white"}},
            "subplots": {
                "MACD": {"macd": {"color": "blue"}, "macdsignal": {"color": "orange"}},
                "RSI": {"rsi": {"color": "red"}}
            }
        }

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        informative_pairs = [(pair, self.informative_timeframe) for pair in pairs]
        return informative_pairs

    def _typical_price(self, df: DataFrame) -> pd.Series:
        return (df['high'] + df['low'] + df['close']) / 3

    def _start_optimizer_thread(self):
        with self._optimizer_lock:
            if self._optimizer_thread_started:
                return
            self._optimizer_thread_started = True

        t = threading.Thread(target=self._optimizer_loop, daemon=True, name="AI_Modulaire_Optimizer")
        t.start()
        logger.info("AI_Modulaire optimizer thread started.")

    def _get_history_df(self, pair: Optional[str] = None) -> DataFrame:
        try:
            if getattr(self, "dp", None) and pair:
                df = self.dp.get_pair_dataframe(pair, timeframe=self.timeframe)
                return df.copy().sort_index()
        except Exception:
            logger.debug("Could not fetch history via dp.get_pair_dataframe.")
        return pd.DataFrame()

    def _ensure_indicators(self, df: DataFrame) -> DataFrame:
        df = df.copy()
        if "rsi" not in df.columns:
            df["rsi"] = ta.RSI(df)
        if "tema" not in df.columns:
            df["tema"] = ta.TEMA(df, timeperiod=9)
        if "bb_middleband" not in df.columns:
            tp = self._typical_price(df)
            upper, middle, lower = ta.BBANDS(tp, timeperiod=20, nbdevup=2.0, nbdevdn=2.0, matype=0)
            df["bb_upperband"] = upper
            df["bb_middleband"] = middle
            df["bb_lowerband"] = lower
        if "volume" not in df.columns:
            df["volume"] = 1.0

        # === Indicateur force du signal ===
        high_price_line = df["high"].max()
        low_price_line = df["low"].min()
        df["high_price_line"] = high_price_line
        df["low_price_line"] = low_price_line

        range_total = (high_price_line - low_price_line) or 1
        df["signal_strength"] = 1 - ((df["close"] - low_price_line) / range_total)

        return df

    def _evaluate_candidate_on_df(self, df: DataFrame, params: Dict) -> Dict:
        df = df.copy().reset_index(drop=False)
        df = self._ensure_indicators(df)

        buy_rsi_val = int(params["buy_rsi"])
        sell_rsi_val = int(params["sell_rsi"])

        enters = (
            crossover(df["rsi"], buy_rsi_val) &
            (df["tema"] <= df["bb_middleband"]) &
            (df["tema"] > df["tema"].shift(1)) &
            (df["volume"] > 0)
        )
        exits = (
            crossover(df["rsi"], sell_rsi_val) &
            (df["tema"] > df["bb_middleband"]) &
            (df["tema"] < df["tema"].shift(1)) &
            (df["volume"] > 0)
        )

        enters_idx = np.where(enters.values)[0]
        exits_idx = np.where(exits.values)[0]

        trades = []
        for i in enters_idx:
            possible_exits = exits_idx[exits_idx > i]
            if len(possible_exits) == 0:
                continue
            j = possible_exits[0]
            entry_price = df.loc[i, "close"]
            exit_price = df.loc[j, "close"]
            ret = (exit_price - entry_price) / entry_price
            trades.append(ret)

        trades = np.array(trades) if trades else np.array([])
        profit = float(trades.sum()) if trades.size > 0 else 0.0
        num_trades = int(trades.size)
        score = profit * (np.sqrt(num_trades) if num_trades > 0 else 0.5)

        return {"score": float(score), "profit": float(profit), "trades": num_trades, "params": params}

    def _apply_new_params(self, params: Dict):
        with self._optimizer_lock:
            try:
                self.buy_rsi.value = int(params["buy_rsi"])
                self.sell_rsi.value = int(params["sell_rsi"])
                logger.info("Applied params: buy_rsi=%s sell_rsi=%s", self.buy_rsi.value, self.sell_rsi.value)
            except Exception as e:
                logger.exception("Error applying params: %s", str(e))

    def _optimizer_loop(self):
        random.seed()
        while True:
            try:
                hist_df = None
                pair = None
                if getattr(self, "dp", None):
                    pairs = self.dp.get_pair_list() if hasattr(self.dp, "get_pair_list") else []
                    if pairs:
                        pair = pairs[0]
                        hist_df = self._get_history_df(pair)

                if hist_df is None or hist_df.empty:
                    hist_df = getattr(self, "_last_history_backup", pd.DataFrame())

                if hist_df.empty or len(hist_df) < max(self.startup_candle_count, 200):
                    time.sleep(self.OPTIMIZER_SLEEP)
                    continue

                df_window = hist_df.tail(self.OPTIMIZER_WINDOW).copy()
                df_window = self._ensure_indicators(df_window)

                current_params = {"buy_rsi": int(self.buy_rsi.value), "sell_rsi": int(self.sell_rsi.value)}
                baseline = self._evaluate_candidate_on_df(df_window, current_params)
                baseline_score = baseline["score"]

                if self._optimizer_state["best_score"] < 0:
                    self._optimizer_state["best_score"] = baseline_score
                    self._optimizer_state["best_params"] = current_params

                candidates = []
                for _ in range(self.OPTIMIZER_BATCH):
                    if random.random() < 0.6 and self._optimizer_state["best_params"]:
                        base = self._optimizer_state["best_params"]
                        cand = {
                            "buy_rsi": int(np.clip(int(random.gauss(base["buy_rsi"], 5)), 8, 50)),
                            "sell_rsi": int(np.clip(int(random.gauss(base["sell_rsi"], 6)), 50, 95)),
                        }
                    else:
                        cand = {
                            "buy_rsi": random.randint(8, 50),
                            "sell_rsi": random.randint(50, 95),
                        }

                    if cand["buy_rsi"] >= cand["sell_rsi"]:
                        cand["buy_rsi"] = max(8, cand["sell_rsi"] - 5)

                    candidates.append(cand)

                best_local = {"score": -1e9, "params": None, "metrics": None}
                for cand in candidates:
                    res = self._evaluate_candidate_on_df(df_window, cand)
                    if res["trades"] < self.OPTIMIZER_MIN_TRADES:
                        continue
                    if res["score"] > best_local["score"]:
                        best_local = {"score": res["score"], "params": cand, "metrics": res}

                if best_local["params"] is not None:
                    rel_improve = (best_local["score"] - self._optimizer_state["best_score"]) / (
                        abs(self._optimizer_state["best_score"]) + 1e-9)
                    now = time.time()
                    cooldown_ok = (now - self._optimizer_state["last_applied_at"]) >= self.OPTIMIZER_COOLDOWN

                    if rel_improve > self.OPTIMIZER_IMPROVEMENT_THRESH and cooldown_ok:
                        self._apply_new_params(best_local["params"])
                        self._optimizer_state.update({
                            "best_score": best_local["score"],
                            "best_params": best_local["params"],
                            "last_applied_at": now,
                        })

            except Exception as e:
                logger.exception("Optimizer loop error: %s", str(e))
            time.sleep(self.OPTIMIZER_SLEEP)

    # === STRATÉGIE ===
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        if not self._optimizer_thread_started:
            self._last_history_backup = dataframe.copy()
            self._start_optimizer_thread()

        dataframe["rsi"] = ta.RSI(dataframe)
        tp = self._typical_price(dataframe)
        upper, middle, lower = ta.BBANDS(tp, timeperiod=20, nbdevup=2.0, nbdevdn=2.0, matype=0)
        dataframe["bb_lowerband"] = lower
        dataframe["bb_middleband"] = middle
        dataframe["bb_upperband"] = upper
        dataframe["tema"] = ta.TEMA(dataframe, timeperiod=9)
        dataframe["sar"] = ta.SAR(dataframe)

        # === High/Low + Force du signal ===
        high_price_line = dataframe["high"].max()
        low_price_line = dataframe["low"].min()
        dataframe["high_price_line"] = high_price_line
        dataframe["low_price_line"] = low_price_line

        amplitude = (high_price_line - low_price_line) or 1
        dataframe["signal_strength"] = 1 - ((dataframe["close"] - low_price_line) / amplitude)

        # === Timeframe 1h ===
        if getattr(self, "dp", None):
            inf_tf = self.dp.get_pair_dataframe(metadata["pair"], timeframe=self.informative_timeframe)
            inf_tf["rsi_htf"] = ta.RSI(inf_tf)
            inf_tf["tema_htf"] = ta.TEMA(inf_tf, timeperiod=9)
            dataframe = dataframe.merge(
                inf_tf[["rsi_htf", "tema_htf"]], left_index=True, right_index=True, how="left"
            ).fillna(method="ffill")

        self._last_history_backup = dataframe.copy()
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        buy_rsi_series = pd.Series(int(self.buy_rsi.value), index=dataframe.index)

        dataframe.loc[
            (
                crossover(dataframe["rsi"], buy_rsi_series) &
                (dataframe["tema"] <= dataframe["bb_middleband"]) &
                (dataframe["tema"] > dataframe["tema"].shift(1)) &
                (dataframe["rsi_htf"] > 50) &
                (dataframe["volume"] > 0) &
                (dataframe["signal_strength"] > 0.5)
            ),
            "enter_long"
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe
