# ---------------------------------------------------------------------------
# ⚠️  검증 실패한 연구용 전략 — 실거래 금지
#
#   EXP-002: Profit Factor 0.71 / MDD ~98%
#   EXP-004: Profit Factor 0.41 / MDD 99.91% / 계좌 77일 만에 소진
#
#   3x 레버리지 USDT-M 선물 + stoploss=-0.99 (실질 손절은 custom_stoploss).
#   이 코드를 그대로 실행하면 계좌를 잃는다. 실패 사례 기록 목적으로만 공개한다.
#
# Licensed under GPL-3.0 (see LICENSE). freqtrade(GPL-3.0) 기반 파생 저작물.
# ---------------------------------------------------------------------------
import logging
from datetime import datetime, timezone
from functools import reduce
from typing import Optional

import numpy as np
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame
from technical import qtpylib

from freqtrade.persistence import Trade
from freqtrade.strategy import (
    IStrategy,
    IntParameter,
    DecimalParameter,
)

logger = logging.getLogger(__name__)


class AggressiveFreqAI(IStrategy):
    """
    공격적 FreqAI 추세 추종 전략 (v2) — Binance USDT-M Futures.

    가설: "60분 후 로그수익률이 예측 가능하다"
    -> 모든 청산 로직의 시간 척도를 60분 타깃에 정렬.
    -> ROI 사실상 비활성, 트레일링 +6% 활성, ATR×2.5 동적 손절,
       AI flip 청산은 30분 최소 보유 후에만.
    """

    INTERFACE_VERSION = 3

    timeframe = "5m"
    can_short = True
    process_only_new_candles = True
    use_exit_signal = True
    use_custom_stoploss = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = True

    # 4h × indicator_periods_candles[max=30] = 5m 1440개 + 안전 마진
    startup_candle_count = 2400

    # static stoploss는 사실상 비활성. 진짜 손절은 custom_stoploss가 결정.
    stoploss = -0.99

    trailing_stop = False
    trailing_stop_positive = 0.03
    trailing_stop_positive_offset = 0.06
    trailing_only_offset_is_reached = True

    # ROI 사실상 비활성 — 청산은 트레일링/AI flip/custom_stoploss가 담당.
    minimal_roi = {"0": 100}

    threshold_long  = DecimalParameter(0.001, 0.010, default=0.0035, decimals=4, space="buy")
    threshold_short = DecimalParameter(-0.010, -0.001, default=-0.0035, decimals=4, space="sell")
    di_max          = DecimalParameter(0.6, 1.0, default=0.9, decimals=2, space="buy")
    leverage_value  = IntParameter(1, 5, default=3, space="buy")

    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }

    # =========================================================
    # FreqAI: 피처 엔지니어링
    # =========================================================
    def feature_engineering_expand_all(
        self, dataframe: DataFrame, period: int, metadata: dict, **kwargs
    ) -> DataFrame:
        dataframe[f"%-rsi-period_{period}"]       = ta.RSI(dataframe, timeperiod=period)
        dataframe[f"%-mfi-period_{period}"]       = ta.MFI(dataframe, timeperiod=period)
        dataframe[f"%-adx-period_{period}"]       = ta.ADX(dataframe, timeperiod=period)
        dataframe[f"%-cci-period_{period}"]       = ta.CCI(dataframe, timeperiod=period)
        dataframe[f"%-roc-period_{period}"]       = ta.ROC(dataframe, timeperiod=period)

        atr = ta.ATR(dataframe, timeperiod=period)
        dataframe[f"%-atr-period_{period}"] = atr / dataframe["close"]

        ema = ta.EMA(dataframe, timeperiod=period)
        dataframe[f"%-ema-ratio-period_{period}"] = (dataframe["close"] - ema) / ema

        bb = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=period, stds=2.2)
        dataframe[f"%-bb-pct-period_{period}"] = (
            (dataframe["close"] - bb["lower"]) / (bb["upper"] - bb["lower"])
        )

        vol_mean = dataframe["volume"].rolling(period).mean()
        vol_std  = dataframe["volume"].rolling(period).std()
        dataframe[f"%-volume-z-period_{period}"] = (
            (dataframe["volume"] - vol_mean) / (vol_std + 1e-9)
        )
        return dataframe

    def feature_engineering_expand_basic(
        self, dataframe: DataFrame, metadata: dict, **kwargs
    ) -> DataFrame:
        dataframe["%-pct-change"]  = dataframe["close"].pct_change()
        dataframe["%-log-return"]  = np.log(dataframe["close"] / dataframe["close"].shift(1))
        dataframe["%-hl-range"]    = (dataframe["high"] - dataframe["low"]) / dataframe["close"]
        dataframe["%-co-range"]    = (dataframe["close"] - dataframe["open"]) / dataframe["open"]
        dataframe["%-volume-pct"]  = dataframe["volume"].pct_change()

        macd = ta.MACD(dataframe, fastperiod=12, slowperiod=26, signalperiod=9)
        dataframe["%-macd-hist"] = macd["macdhist"]
        return dataframe

    def feature_engineering_standard(
        self, dataframe: DataFrame, metadata: dict, **kwargs
    ) -> DataFrame:
        dataframe["%-day_of_week"] = (dataframe["date"].dt.dayofweek + 1) / 7
        dataframe["%-hour_of_day"] = (dataframe["date"].dt.hour + 1) / 25
        return dataframe

    def set_freqai_targets(
        self, dataframe: DataFrame, metadata: dict, **kwargs
    ) -> DataFrame:
        """
        타깃: label_period_candles 캔들 후 로그수익률.

        룩어헤드 방지 assert:
          buffer_train_data_candles >= label_period_candles + include_shifted_candles + 5
        hyperopt에서 label_period_candles 만질 때 buffer도 같이 늘려야 함.
        """
        fp = self.freqai_info["feature_parameters"]
        label_period = fp["label_period_candles"]
        shifted      = fp.get("include_shifted_candles", 0)
        buffer       = fp.get("buffer_train_data_candles", 0)
        assert buffer >= label_period + shifted + 5, (
            f"Lookahead risk: buffer_train_data_candles ({buffer}) must be "
            f">= label_period_candles ({label_period}) + include_shifted_candles "
            f"({shifted}) + 5. Increase buffer_train_data_candles in config."
        )

        dataframe["&-target"] = np.log(
            dataframe["close"].shift(-label_period) / dataframe["close"]
        )
        return dataframe

    # =========================================================
    # 표준 indicators / entry / exit
    # =========================================================
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = self.freqai.start(dataframe, metadata, self)

        dataframe["volume_ma20"] = dataframe["volume"].rolling(20).mean()
        dataframe["atr14"]       = ta.ATR(dataframe, timeperiod=14)
        dataframe["ema50"]       = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema200"]      = ta.EMA(dataframe, timeperiod=200)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        long_conds = [
            dataframe["do_predict"] == 1,
            dataframe["&-target"] > self.threshold_long.value,
            dataframe["volume"] > dataframe["volume_ma20"],
        ]
        dataframe.loc[
            reduce(lambda a, b: a & b, long_conds),
            ["enter_long", "enter_tag"],
        ] = (1, "ai_long")

        short_conds = [
            dataframe["do_predict"] == 1,
            dataframe["&-target"] < self.threshold_short.value,
            dataframe["volume"] > dataframe["volume_ma20"],
        ]
        dataframe.loc[
            reduce(lambda a, b: a & b, short_conds),
            ["enter_short", "enter_tag"],
        ] = (1, "ai_short")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["do_predict"] == 1) & (dataframe["&-target"] < 0),
            ["exit_long", "exit_tag"],
        ] = (1, "ai_flip")

        dataframe.loc[
            (dataframe["do_predict"] == 1) & (dataframe["&-target"] > 0),
            ["exit_short", "exit_tag"],
        ] = (1, "ai_flip")
        return dataframe

    # =========================================================
    # 시간 척도 가드 — 30분 최소 보유
    # =========================================================
    def custom_exit(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs,
    ) -> Optional[str]:
        """
        AI flip 신호가 진입 30분 내에 뒤집히면 무시.
        custom_stoploss는 별개 경로로 작동하므로 손절은 그대로 발동됨.
        """
        held = (current_time - trade.open_date_utc).total_seconds()
        if held < 1800:
            return None
        return None

    # =========================================================
    # 동적 손절 / 레버리지
    # =========================================================
    def custom_stoploss(
        self, pair: str, trade: Trade, current_time: datetime,
        current_rate: float, current_profit: float, **kwargs
    ) -> float:
        """ATR×2.5 동적 손절. clip(2.5%, 10%). stoploss=-0.99로 풀려있어 진짜 적용됨."""
        df, _ = self.dp.get_analyzed_dataframe(pair=pair, timeframe=self.timeframe)
        if df is None or len(df) == 0:
            return -0.05
        atr   = df["atr14"].iat[-1]
        price = df["close"].iat[-1]
        if not np.isfinite(atr) or atr <= 0 or price <= 0:
            return -0.05
        return -float(np.clip(2.5 * atr / price, 0.025, 0.10))

    def leverage(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_leverage: float,
        max_leverage: float,
        side: str,
        **kwargs,
    ) -> float:
        return float(min(self.leverage_value.value, max_leverage))
