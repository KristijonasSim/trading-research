# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from typing import Optional, List, Tuple

import numpy as np
from pandas import DataFrame

import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib

from freqtrade.strategy.interface import IStrategy
from freqtrade.strategy import merge_informative_pair


class BTCRegimeAligned_Aggressive_v2(IStrategy):
    """
    BTC Regime Aligned v2 (agressiva, mas mais "viva"):

    Melhorias vs v1:
    - Regime BTC menos estrito (reduz bloqueio total em "semi-lateral")
    - Entradas um pouco mais permissivas (mais trades para medir comportamento)
    - Remove exit automático por flip do BTC dentro do populate_exit_trend
      (isso gerava churn e muitos losses no backtest)
    - BTC flip vira custom_exit condicional: corta rápido só quando o trade está fraco
    - Time-stop leve para trades "presos" sem ir a lugar nenhum
    """

    INTERFACE_VERSION = 3
    can_short = True

    # -------------------------
    # Timeframes
    # -------------------------
    timeframe = "15m"
    informative_timeframe = "1h"
    BTC_PAIR = "BTC/USDT:USDT"

    startup_candle_count = 240

    # -------------------------
    # Risco / Saídas
    # -------------------------
    stoploss = -0.06

    minimal_roi = {
        "0": 0.08,
        "60": 0.05,
        "180": 0.03,
        "360": 0.015,
    }

    trailing_stop = True
    trailing_stop_positive = 0.012
    trailing_stop_positive_offset = 0.020
    trailing_only_offset_is_reached = True

    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = True

    # -------------------------
    # Proteções
    # -------------------------
    @property
    def protections(self):
        return [
            {"method": "CooldownPeriod", "stop_duration_candles": 2},
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 48,
                "trade_limit": 2,
                "stop_duration_candles": 12,
                "only_per_pair": False,
            },
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 96,
                "stop_duration_candles": 24,
                "max_allowed_drawdown": 0.18,
            },
        ]

    # -------------------------
    # Leverage dinâmica (1–3x)
    # -------------------------
    def leverage(
        self,
        pair: str,
        entry_tag: str,
        current_time: datetime,
        proposed_leverage: float,
        max_leverage: float,
        side: str,
        **kwargs
    ) -> float:
        try:
            df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            atrp = float(df["atrp"].iloc[-1])
            dyn = float(np.clip(0.9 / max(atrp, 0.001), 1.0, 3.0))
            return min(3.0, max(1.0, dyn))
        except Exception:
            return 2.0

    # -------------------------
    # Informativos (obrigatório no LIVE)
    # -------------------------
    def informative_pairs(self) -> List[Tuple[str, str]]:
        return [
            (self.BTC_PAIR, self.informative_timeframe),
        ]

    # -------------------------
    # Indicadores
    # -------------------------
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # ALT indicators
        dataframe["ema20"] = ta.EMA(dataframe["close"], timeperiod=20)
        dataframe["ema50"] = ta.EMA(dataframe["close"], timeperiod=50)
        dataframe["ema200"] = ta.EMA(dataframe["close"], timeperiod=200)

        dataframe["rsi"] = ta.RSI(dataframe["close"], timeperiod=14)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)

        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["atrp"] = (dataframe["atr"] / dataframe["close"]).replace([np.inf, -np.inf], np.nan)

        bb = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe["bb_lower"] = bb["lower"]
        dataframe["bb_mid"] = bb["mid"]
        dataframe["bb_upper"] = bb["upper"]
        dataframe["bb_width"] = (dataframe["bb_upper"] - dataframe["bb_lower"]) / dataframe["bb_mid"]

        dataframe["vol_mean"] = dataframe["volume"].rolling(24).mean()

        # BTC informative
        if self.dp:
            try:
                btc = self.dp.get_pair_dataframe(pair=self.BTC_PAIR, timeframe=self.informative_timeframe)

                btc["btc_ema50"] = ta.EMA(btc["close"], timeperiod=50)
                btc["btc_ema200"] = ta.EMA(btc["close"], timeperiod=200)
                btc["btc_adx"] = ta.ADX(btc, timeperiod=14)
                btc["btc_close"] = btc["close"]

                btc["btc_ret_3h"] = btc["close"].pct_change(3)
                btc["btc_ret_6h"] = btc["close"].pct_change(6)
                btc["btc_ret_12h"] = btc["close"].pct_change(12)

                dataframe = merge_informative_pair(
                    dataframe,
                    btc,
                    self.timeframe,
                    self.informative_timeframe,
                    ffill=True
                )
            except Exception:
                pass

        # Safety for missing cols
        btc_cols = [
            "btc_ema50_1h",
            "btc_ema200_1h",
            "btc_adx_1h",
            "btc_close_1h",
            "btc_ret_6h_1h",
            "btc_ret_12h_1h",
        ]
        for c in btc_cols:
            if c not in dataframe.columns:
                dataframe[c] = np.nan

        # -------------------------
        # BTC Regime v2 (menos estrito)
        # -------------------------
        # Tendência: ADX um pouco menor pra liberar mais trades
        adx_trend = dataframe["btc_adx_1h"] > 18

        # Momentum: usa 12h (mais estável) + 6h (mais responsivo)
        bull_momo = (dataframe["btc_ret_12h_1h"] > 0.006) | (dataframe["btc_ret_6h_1h"] > 0.004)
        bear_momo = (dataframe["btc_ret_12h_1h"] < -0.006) | (dataframe["btc_ret_6h_1h"] < -0.004)

        dataframe["btc_bull"] = (
            (dataframe["btc_ema50_1h"] > dataframe["btc_ema200_1h"]) &
            (dataframe["btc_close_1h"] > dataframe["btc_ema50_1h"]) &
            adx_trend &
            bull_momo
        )

        dataframe["btc_bear"] = (
            (dataframe["btc_ema50_1h"] < dataframe["btc_ema200_1h"]) &
            (dataframe["btc_close_1h"] < dataframe["btc_ema50_1h"]) &
            adx_trend &
            bear_momo
        )

        # Sideways v2: mais tolerante (não bloqueia tanto)
        # Só considera sideways forte se ADX bem baixo E variação fraca.
        dataframe["btc_sideways"] = (
            (dataframe["btc_adx_1h"] < 16) &
            (dataframe["btc_ret_6h_1h"].abs() < 0.0025)
        )

        dataframe["allow_long"] = dataframe["btc_bull"] & (~dataframe["btc_sideways"])
        dataframe["allow_short"] = dataframe["btc_bear"] & (~dataframe["btc_sideways"])

        return dataframe

    # -------------------------
    # Entradas
    # -------------------------
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0
        dataframe["enter_tag"] = None

        # ALT quality (v2 um pouco mais permissiva)
        alt_ok = (
            (dataframe["volume"] > 0) &
            (dataframe["vol_mean"] > 0) &
            (dataframe["volume"] > dataframe["vol_mean"] * 1.10) &   # 1.2x -> 1.1x
            (dataframe["atrp"] > 0.0018) &
            (dataframe["atrp"] < 0.050) &                             # tolera um pouco mais
            (dataframe["bb_width"] > 0.008)
        )

        # Trend filters suaves (evita entrar contra a maré da alt)
        alt_up = dataframe["ema50"] > dataframe["ema200"]
        alt_down = dataframe["ema50"] < dataframe["ema200"]

        # LONG: BTC bull + retomada EMA20 + alt acima da EMA50 (tendência)
        long_cond = (
            (dataframe["allow_long"] == True) &
            alt_ok &
            alt_up &
            (dataframe["rsi"] > 38) & (dataframe["rsi"] < 65) &
            qtpylib.crossed_above(dataframe["close"], dataframe["ema20"]) &
            (dataframe["close"] < dataframe["bb_upper"] * 1.015)
        )

        # SHORT: BTC bear + perda EMA20 + alt abaixo da EMA50
        short_cond = (
            (dataframe["allow_short"] == True) &
            alt_ok &
            alt_down &
            (dataframe["rsi"] > 35) & (dataframe["rsi"] < 72) &
            qtpylib.crossed_below(dataframe["close"], dataframe["ema20"]) &
            (dataframe["close"] > dataframe["bb_lower"] * 0.985)
        )

        dataframe.loc[long_cond, ["enter_long", "enter_tag"]] = (1, "btc_bull_pullback_resume_v2")
        dataframe.loc[short_cond, ["enter_short", "enter_tag"]] = (1, "btc_bear_pullback_break_v2")

        return dataframe

    # -------------------------
    # Saídas (sinais) - v2: SEM BTC flip automático aqui
    # -------------------------
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        dataframe["exit_tag"] = None

        # Saída técnica simples: EMA20
        exit_long = qtpylib.crossed_below(dataframe["close"], dataframe["ema20"])
        exit_short = qtpylib.crossed_above(dataframe["close"], dataframe["ema20"])

        dataframe.loc[exit_long, ["exit_long", "exit_tag"]] = (1, "ema20_exit")
        dataframe.loc[exit_short, ["exit_short", "exit_tag"]] = (1, "ema20_exit")

        return dataframe

    # -------------------------
    # Custom exit v2: BTC flip CONDICIONAL + time-stop
    # -------------------------
    def custom_exit(
        self,
        pair: str,
        trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs
    ) -> Optional[str]:

        try:
            df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            last = df.iloc[-1]

            allow_long = bool(last.get("allow_long", False))
            allow_short = bool(last.get("allow_short", False))
            btc_sideways = bool(last.get("btc_sideways", False))

            # --- 1) BTC flip: só corta rápido se trade estiver fraco ---
            # Se já está bem positivo, deixa trailing / ROI trabalharem.
            weak_profit_threshold = 0.005   # 0.5%
            if trade.is_long and (not allow_long):
                if current_profit < weak_profit_threshold:
                    return "btc_flip_weak_long_exit"

            if trade.is_short and (not allow_short):
                if current_profit < weak_profit_threshold:
                    return "btc_flip_weak_short_exit"

            # --- 2) Se BTC entrou em sideways forte e trade não andou, corta ruído ---
            if btc_sideways and current_profit < 0.002:  # < 0.2%
                # evita ficar preso em chop
                return "btc_sideways_low_edge_exit"

            # --- 3) Time-stop leve: trade preso e negativo por muito tempo ---
            # (evita sangrar em range)
            if trade.open_date_utc:
                held = current_time.replace(tzinfo=None) - trade.open_date_utc.replace(tzinfo=None)
                if held > timedelta(hours=3) and current_profit < -0.01:
                    return "time_stop_stuck_trade"

        except Exception:
            return None

        return None

