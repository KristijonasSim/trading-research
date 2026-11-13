# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
from pandas import DataFrame

import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib

from freqtrade.strategy.interface import IStrategy
from freqtrade.strategy import merge_informative_pair


class BTCRegimeAligned_Aggressive_v1(IStrategy):
    """
    Estratégia por camadas:
    (1) Regime do BTC define se pode LONG/SHORT e bloqueia lateral
    (2) Filtros de qualidade na ALT: volume e volatilidade (ATR%)
    (3) Gatilho na ALT: pullback + retomada (long) / pullback + perda (short)
    (4) Saídas: trailing + flip de regime do BTC (corta rápido)
    """

    INTERFACE_VERSION = 3
    can_short = True

    # -------------------------
    # Timeframes
    # -------------------------
    timeframe = "15m"
    informative_timeframe = "1h"

    # Ajuste se necessário
    BTC_PAIR = "BTC/USDT:USDT"

    startup_candle_count = 240

    # -------------------------
    # Risco / Saídas
    # -------------------------
    stoploss = -0.06  # agressivo, mas ainda controlado

    minimal_roi = {
        "0": 0.08,     # alvo inicial alto para permitir capturar pumps
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
    # Proteções (boas p/ futuros)
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

            # Quanto mais volátil (atrp alto), menor a alavancagem
            dyn = float(np.clip(0.9 / max(atrp, 0.001), 1.0, 3.0))
            return min(3.0, max(1.0, dyn))
        except Exception:
            return 2.0

    def informative_pairs(self):
        """
        Declara explicitamente os pares informativos
        Necessário para LIVE / DRY-RUN
        """
        return [
            (self.BTC_PAIR, self.informative_timeframe),
        ]


    # -------------------------
    # Indicadores
    # -------------------------
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # === Indicadores na ALT ===
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

        # === Informativo BTC (regime) ===
        if self.dp:
            try:
                btc = self.dp.get_pair_dataframe(pair=self.BTC_PAIR, timeframe=self.informative_timeframe)

                btc["btc_ema50"] = ta.EMA(btc["close"], timeperiod=50)
                btc["btc_ema200"] = ta.EMA(btc["close"], timeperiod=200)
                btc["btc_adx"] = ta.ADX(btc, timeperiod=14)
                btc["btc_close"] = btc["close"]

                # Retornos (agressivo)
                btc["btc_ret_3h"] = btc["close"].pct_change(3)   # 3 candles de 1h
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
                # Se falhar, segue sem regime (vai bloquear entradas lá embaixo)
                pass

        # === Regime flags (BTC) ===
        # Agressivo: ADX > 20 já permite tendência (mais trades)
        btc_cols = ["btc_ema50_1h", "btc_ema200_1h", "btc_adx_1h", "btc_close_1h", "btc_ret_6h_1h"]
        for c in btc_cols:
            if c not in dataframe.columns:
                dataframe[c] = np.nan

        dataframe["btc_bull"] = (
            (dataframe["btc_ema50_1h"] > dataframe["btc_ema200_1h"]) &
            (dataframe["btc_adx_1h"] > 20) &
            (dataframe["btc_close_1h"] > dataframe["btc_ema50_1h"]) &
            (dataframe["btc_ret_6h_1h"] > 0.008)   # +0.8% em 6h
        )

        dataframe["btc_bear"] = (
            (dataframe["btc_ema50_1h"] < dataframe["btc_ema200_1h"]) &
            (dataframe["btc_adx_1h"] > 20) &
            (dataframe["btc_close_1h"] < dataframe["btc_ema50_1h"]) &
            (dataframe["btc_ret_6h_1h"] < -0.008)  # -0.8% em 6h
        )

        # Lateral / incerto = bloqueia
        dataframe["btc_sideways"] = (
            (dataframe["btc_adx_1h"] < 18) |
            (dataframe["btc_ret_6h_1h"].abs() < 0.003)  # <0.3% em 6h
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

        # Filtros gerais na ALT (qualidade / evita lixo)
        alt_ok = (
            (dataframe["volume"] > 0) &
            (dataframe["vol_mean"] > 0) &
            (dataframe["volume"] > dataframe["vol_mean"] * 1.2) &   # agressivo: só 1.2x
            (dataframe["atrp"] > 0.002) &                           # volatilidade mínima
            (dataframe["atrp"] < 0.040) &                           # evita moedas absurdas
            (dataframe["bb_width"] > 0.01)                          # precisa “respirar”
        )

        # LONG: BTC bull + pullback (RSI moderado) + retomada acima da EMA20
        long_cond = (
            (dataframe["allow_long"] == True) &
            alt_ok &
            (dataframe["rsi"] > 40) & (dataframe["rsi"] < 60) &
            (dataframe["close"] > dataframe["ema50"]) &
            qtpylib.crossed_above(dataframe["close"], dataframe["ema20"]) &
            (dataframe["close"] < dataframe["bb_upper"] * 1.01)      # evita entrar esticado no topo
        )

        # SHORT: BTC bear + pullback (RSI moderado) + perda abaixo da EMA20
        short_cond = (
            (dataframe["allow_short"] == True) &
            alt_ok &
            (dataframe["rsi"] > 45) & (dataframe["rsi"] < 68) &
            (dataframe["close"] < dataframe["ema50"]) &
            qtpylib.crossed_below(dataframe["close"], dataframe["ema20"]) &
            (dataframe["close"] > dataframe["bb_lower"] * 0.99)      # evita vender no fundo esticado
        )

        dataframe.loc[long_cond, ["enter_long", "enter_tag"]] = (1, "btc_bull_pullback_resume")
        dataframe.loc[short_cond, ["enter_short", "enter_tag"]] = (1, "btc_bear_pullback_break")

        return dataframe

    # -------------------------
    # Saídas (sinais)
    # -------------------------
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        dataframe["exit_tag"] = None

        # Saída técnica simples + trailing já faz o resto
        exit_long = (
            qtpylib.crossed_below(dataframe["close"], dataframe["ema20"]) |
            (dataframe["allow_long"] == False)  # se BTC parar de permitir long, sai
        )

        exit_short = (
            qtpylib.crossed_above(dataframe["close"], dataframe["ema20"]) |
            (dataframe["allow_short"] == False)  # se BTC parar de permitir short, sai
        )

        dataframe.loc[exit_long, ["exit_long", "exit_tag"]] = (1, "ema20_or_btc_flip")
        dataframe.loc[exit_short, ["exit_short", "exit_tag"]] = (1, "ema20_or_btc_flip")

        return dataframe

    # -------------------------
    # “Corte” rápido por flip do BTC (melhora futuros)
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

            # Se estou em LONG e BTC não permite mais long -> sai rápido
            if trade.is_long and not bool(last.get("allow_long", False)):
                return "btc_regime_flip_fast_exit"

            # Se estou em SHORT e BTC não permite mais short -> sai rápido
            if trade.is_short and not bool(last.get("allow_short", False)):
                return "btc_regime_flip_fast_exit"

        except Exception:
            return None

        return None

