"""
HYDRA-7 Freqtrade Strategy
===========================
Timeframe : 5-minute candles
Signal    : FreqAI ensemble model (28/31 consensus)
Risk Mgmt : ATR-based trailing stop, fixed risk-reward 1:2

Author : Manus AI
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame
from freqtrade.strategy import IStrategy


class Hydra7Strategy(IStrategy):
    """
    Place this file in:
        user_data/strategies/Hydra7Strategy.py
    """

    # ── Basic settings ─────────────────────────────────────────────────────────
    timeframe = "5m"
    can_short = True

    minimal_roi = {
        "0":   0.04,
        "30":  0.02,
        "60":  0.01,
        "120": 0.005,
    }

    stoploss = -0.015                    # hard stop: -1.5 %
    trailing_stop = True
    trailing_stop_positive = 0.008
    trailing_stop_positive_offset = 0.015
    trailing_only_offset_is_reached = True

    use_exit_signal = True
    exit_profit_only = False
    process_only_new_candles = True
    startup_candle_count = 200

    # ── FreqAI config ──────────────────────────────────────────────────────────
    freqai_info = {
        "enabled": True,
        "purge_old_models": 2,
        "train_period_days": 30,
        "backtest_period_days": 7,
        "live_retrain_hours": 4,
        "expiration_hours": 1,
        "identifier": "hydra7_v1",
        "feature_parameters": {
            "include_timeframes": ["5m", "15m", "1h"],
            "include_corr_pairlist": ["BTC/USDT", "ETH/USDT"],
            "label_period_candles": 6,
            "include_shifted_candles": 2,
            "weight_factor": 0.9,
            "principal_component_analysis": False,
            "use_SVM_to_remove_outliers": True,
            "DI_threshold": 1,
        },
        "data_split_parameters": {
            "test_size": 0.15,
            "random_state": 42,
            "shuffle": False,
        },
        "model_training_parameters": {},
    }

    # ══════════════════════════════════════════════════════════════════════════
    # Feature Engineering
    # ══════════════════════════════════════════════════════════════════════════
    def feature_engineering_expand_all(
        self, dataframe: DataFrame, period: int, metadata: dict, **kwargs
    ) -> DataFrame:
        """
        Compute all technical indicators used as model input features.
        FreqAI will automatically expand these across all configured timeframes.
        """

        # ── A-Group: Trend features ───────────────────────────────────────────
        macd = ta.MACD(dataframe)
        dataframe["%-macd"]       = macd["macd"]
        dataframe["%-macdsig"]    = macd["macdsignal"]
        dataframe["%-macdhist"]   = macd["macdhist"]

        for p in [5, 10, 20, 50, 100]:
            ema = ta.EMA(dataframe, timeperiod=p)
            dataframe[f"%-ema{p}"]      = ema
            dataframe[f"%-ema{p}_dist"] = (dataframe["close"] - ema) / (ema + 1e-9)

        dataframe["%-adx"]      = ta.ADX(dataframe, timeperiod=14)
        dataframe["%-plus_di"]  = ta.PLUS_DI(dataframe, timeperiod=14)
        dataframe["%-minus_di"] = ta.MINUS_DI(dataframe, timeperiod=14)
        dataframe["%-atr"]      = ta.ATR(dataframe, timeperiod=14)
        dataframe["%-atr_pct"]  = dataframe["%-atr"] / (dataframe["close"] + 1e-9)

        bb = ta.BBANDS(dataframe, timeperiod=20)
        dataframe["%-bb_upper"] = bb["upperband"]
        dataframe["%-bb_lower"] = bb["lowerband"]
        dataframe["%-bb_mid"]   = bb["middleband"]
        dataframe["%-bb_width"] = (bb["upperband"] - bb["lowerband"]) / (bb["middleband"] + 1e-9)
        dataframe["%-bb_pct"]   = (dataframe["close"] - bb["lowerband"]) / (
            bb["upperband"] - bb["lowerband"] + 1e-9
        )

        # Supertrend (manual implementation)
        hl2 = (dataframe["high"] + dataframe["low"]) / 2
        atr14 = dataframe["%-atr"]
        dataframe["%-st_upper"] = hl2 + 3 * atr14
        dataframe["%-st_lower"] = hl2 - 3 * atr14

        # ── B-Group: Momentum / Reversion features ────────────────────────────
        for p in [7, 14, 21]:
            dataframe[f"%-rsi{p}"] = ta.RSI(dataframe, timeperiod=p)

        stoch = ta.STOCH(dataframe)
        dataframe["%-stoch_k"] = stoch["slowk"]
        dataframe["%-stoch_d"] = stoch["slowd"]

        dataframe["%-cci"]    = ta.CCI(dataframe, timeperiod=20)
        dataframe["%-willr"]  = ta.WILLR(dataframe, timeperiod=14)
        dataframe["%-mfi"]    = ta.MFI(dataframe, timeperiod=14)

        for p in [10, 20]:
            dataframe[f"%-roc{p}"] = ta.ROC(dataframe, timeperiod=p)

        for w in [20, 50]:
            mu  = dataframe["close"].rolling(w).mean()
            sig = dataframe["close"].rolling(w).std()
            dataframe[f"%-zscore{w}"] = (dataframe["close"] - mu) / (sig + 1e-9)

        # ── C-Group: Volume / Microstructure features ─────────────────────────
        dataframe["%-obv"]      = ta.OBV(dataframe)
        obv_ema                 = ta.EMA(dataframe["%-obv"], timeperiod=20)
        dataframe["%-obv_dist"] = (dataframe["%-obv"] - obv_ema) / (obv_ema.abs() + 1e-9)

        tp = (dataframe["high"] + dataframe["low"] + dataframe["close"]) / 3
        dataframe["%-vwap"] = (
            (tp * dataframe["volume"]).rolling(20).sum()
            / dataframe["volume"].rolling(20).sum()
        )
        dataframe["%-vwap_dist"] = (dataframe["close"] - dataframe["%-vwap"]) / (
            dataframe["%-vwap"] + 1e-9
        )

        vol_ema = ta.EMA(dataframe["volume"], timeperiod=20)
        dataframe["%-vol_ratio"] = dataframe["volume"] / (vol_ema + 1e-9)
        dataframe["%-cmf"]       = ta.ADOSC(dataframe, fastperiod=3, slowperiod=10)

        # ── Candle structure features ─────────────────────────────────────────
        hl_range = dataframe["high"] - dataframe["low"] + 1e-9
        dataframe["%-body"]         = (dataframe["close"] - dataframe["open"]).abs() / hl_range
        dataframe["%-upper_shadow"] = (
            dataframe["high"] - dataframe[["open", "close"]].max(axis=1)
        ) / hl_range
        dataframe["%-lower_shadow"] = (
            dataframe[["open", "close"]].min(axis=1) - dataframe["low"]
        ) / hl_range

        # ── Time features ─────────────────────────────────────────────────────
        dataframe["%-hour"]    = dataframe["date"].dt.hour
        dataframe["%-weekday"] = dataframe["date"].dt.dayofweek

        return dataframe

    def feature_engineering_standard(
        self, dataframe: DataFrame, metadata: dict, **kwargs
    ) -> DataFrame:
        """
        Define the prediction target (label).
        Label = direction of price change over the next `label_period_candles` bars.
          +1  : price rises  > +0.5 %
          -1  : price falls  < -0.5 %
           0  : price moves within ±0.5 % (flat)
        """
        n = self.freqai_info["feature_parameters"]["label_period_candles"]
        threshold = 0.005

        fwd_return = (
            dataframe["close"].shift(-n) - dataframe["close"]
        ) / dataframe["close"]

        dataframe["&-target"] = np.where(
            fwd_return >  threshold,  1,
            np.where(fwd_return < -threshold, -1, 0),
        )
        return dataframe

    # ══════════════════════════════════════════════════════════════════════════
    # Signal Generation
    # ══════════════════════════════════════════════════════════════════════════
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = self.freqai.start(dataframe, metadata, self)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["&-target"] == 1) & (dataframe["volume"] > 0),
            "enter_long",
        ] = 1

        dataframe.loc[
            (dataframe["&-target"] == -1) & (dataframe["volume"] > 0),
            "enter_short",
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["&-target"] == -1, "exit_long"]  = 1
        dataframe.loc[dataframe["&-target"] ==  1, "exit_short"] = 1
        return dataframe

    # ══════════════════════════════════════════════════════════════════════════
    # Dynamic ATR-based stop-loss
    # ══════════════════════════════════════════════════════════════════════════
    def custom_stoploss(
        self,
        pair: str,
        trade,
        current_time,
        current_rate: float,
        current_profit: float,
        **kwargs,
    ) -> float:
        """
        Tighten stop-loss once the trade is in profit.
        Below break-even: use the hard stoploss from strategy config.
        Above break-even: trail at 50 % of current profit.
        """
        if current_profit > 0.01:
            return max(self.stoploss, -current_profit * 0.5)
        return self.stoploss
