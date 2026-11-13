# -*- coding: utf-8 -*-

# trigger workflow


from __future__ import annotations

from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta


class HybridDipVolatilityOptimized_PRO(IStrategy):
    """
    Estratégia de REVERSÃO em 1h (Long / Short) – VERSÃO PRODUÇÃO AJUSTADA

    AJUSTES:
    - Confirmação mínima de reversão (evita entradas no impulso)
    - SHORT apenas em pares "safe" (menos squeeze)
    - Mantém trailing, stoploss e proteções
    """

    INTERFACE_VERSION = 3
    timeframe = "1h"
    startup_candle_count = 80
    can_short = True

    # --------------------------------------------------
    # GESTÃO DE RISCO
    # --------------------------------------------------
    stoploss = -0.10

    minimal_roi = {
        "0": 0.233,
        "370": 0.075,
        "517": 0.029,
        "794": 0
    }

    trailing_stop = True
    trailing_stop_positive = 0.014
    trailing_stop_positive_offset = 0.058
    trailing_only_offset_is_reached = True

    # ==================================================
    # PROTEÇÕES
    # ==================================================
    @property
    def protections(self):
        return [
            {"method": "CooldownPeriod", "stop_duration_candles": 3},
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 36,
                "trade_limit": 3,
                "stop_duration_candles": 8,
            },
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 72,
                "stop_duration_candles": 12,
                "max_allowed_drawdown": 0.12,
            },
        ]

    # --------------------------------------------------
    # PARÂMETROS FIXOS (HYPEROPT VENCEDOR)
    # --------------------------------------------------
    adx_min = 35
    atrp_min = 1.16
    bbw_min = 0.104
    change_24h_threshold = 9.4
    consecutive_candles = 5
    rsi_threshold_long = 34
    rsi_threshold_short = 60
    vol_mult = 1.06

    # SHORT SAFE FILTERS
    min_short_price = 0.05          # evita micro-cap
    min_short_volume_mult = 1.3     # volume mais forte
    max_short_atrp = 3.0            # evita squeeze extremo

    # --------------------------------------------------
    # EXIT
    # --------------------------------------------------
    atr_tp_mult = 0.96
    rsi_exit_long = 60
    rsi_exit_short = 38

    # --------------------------------------------------
    # LEVERAGE
    # --------------------------------------------------
    leverage_value = 3

    def leverage(
        self,
        pair: str,
        current_time,
        current_rate: float,
        proposed_leverage: float,
        max_leverage: float,
        side: str,
        **kwargs
    ) -> float:
        return float(min(self.leverage_value, max_leverage))

    # ----------------- INDICADORES -----------------
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)

        dataframe["volume_mean"] = dataframe["volume"].rolling(window=20).mean()

        dataframe["change_24h"] = (
            (dataframe["close"] / dataframe["close"].shift(24)) - 1.0
        ) * 100.0

        dataframe["atr_percent"] = (
            dataframe["atr"] / dataframe["close"]
        ) * 100.0

        bb = ta.BBANDS(dataframe, timeperiod=20)
        dataframe["bb_upper"] = bb["upperband"]
        dataframe["bb_middle"] = bb["middleband"]
        dataframe["bb_lower"] = bb["lowerband"]

        dataframe["bb_width"] = (
            dataframe["bb_upper"] - dataframe["bb_lower"]
        ) / dataframe["bb_middle"]

        return dataframe

    # ----------------- ENTRADAS -----------------
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        c = self.consecutive_candles

        # ---------------- LONG ----------------
        dip = dataframe["close"] < dataframe["close"].shift(1)
        for i in range(2, c + 1):
            dip &= dataframe["close"].shift(i - 1) < dataframe["close"].shift(i)

        long_confirm = (
            (dataframe["rsi"].shift(1) < self.rsi_threshold_long) &
            (dataframe["rsi"] > dataframe["rsi"].shift(1)) &
            (dataframe["close"] > dataframe["open"])
        )

        # ---------------- SHORT ----------------
        pump = dataframe["close"] > dataframe["close"].shift(1)
        for i in range(2, c + 1):
            pump &= dataframe["close"].shift(i - 1) > dataframe["close"].shift(i)

        short_confirm = (
            (dataframe["rsi"].shift(1) > self.rsi_threshold_short) &
            (dataframe["rsi"] < dataframe["rsi"].shift(1)) &
            (dataframe["close"] < dataframe["open"])
        )

        vol_ok = dataframe["volume"] > (dataframe["volume_mean"] * self.vol_mult)
        trend_ok = dataframe["adx"] > self.adx_min
        vola_ok = (
            (dataframe["atr_percent"] >= self.atrp_min) &
            (dataframe["bb_width"] >= self.bbw_min)
        )

        # LONG
        dataframe.loc[
            dip &
            long_confirm &
            vol_ok &
            trend_ok &
            vola_ok &
            (dataframe["change_24h"] <= -self.change_24h_threshold),
            "enter_long"
        ] = 1

        # SHORT (SAFE)
        dataframe.loc[
            pump &
            short_confirm &
            vol_ok &
            trend_ok &
            vola_ok &
            (dataframe["change_24h"] >= self.change_24h_threshold) &
            (dataframe["close"] >= self.min_short_price) &
            (dataframe["volume"] > dataframe["volume_mean"] * self.min_short_volume_mult) &
            (dataframe["atr_percent"] <= self.max_short_atrp),
            "enter_short"
        ] = 1

        return dataframe

    # ----------------- SAÍDAS -----------------
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        atr_tp = dataframe["atr"] * self.atr_tp_mult

        dataframe.loc[
            (dataframe["rsi"] > self.rsi_exit_long) |
            (dataframe["close"] > (dataframe["close"].shift(1) + atr_tp)),
            "exit_long"
        ] = 1

        dataframe.loc[
            (dataframe["rsi"] < self.rsi_exit_short) |
            (dataframe["close"] < (dataframe["close"].shift(1) - atr_tp)),
            "exit_short"
        ] = 1

        return dataframe

