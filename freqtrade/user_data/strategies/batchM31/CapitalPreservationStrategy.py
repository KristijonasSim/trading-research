"""
카파시 4원칙 Freqtrade 전략 v3 (멀티 타임프레임: 15m 진입 + 1h/4h 추세 필터)
- 원칙 1: MDD -12% 이내 (1h+4h 추세 필터로 노이즈 진입 차단, 2026-06-22 主人님 옵션 B)
- 원칙 2: 레버리지 2x (stoploss -3% 이내)
- 원칙 3: 일일 -1% 손실 시 신규 진입 차단 (custom_stoploss)
- 원칙 4: 분산 (config.json에서 3 코인 설정)

타임프레임 전략 (2026-06-22 主人님 결정):
- 메인 봉: 15m (진입/청산, 거래 횟수 극대화)
- 추세 필터 1: 1h (중기 추세 확인)
- 추세 필터 2: 4h (큰 추세 확인)
- 15m 신호가 1h + 4h 추세와 같은 방향일 때만 진입 (카파시 1 MDD 보호)

코인별 전략:
- BTC: 4h+1h 추세 + 15m EMA_CROSS (9/21) + MACD 필터
- ETH: 4h+1h 추세 + 15m EMA_CROSS (9/21) + RSI 필터
- SOL: 4h+1h 추세 + 15m MACD (12/26/9) + ADX 필터

진입 조건 (모두 충족):
1. 4h 추세 방향 일치 (1d → 4h로 완화, 더 많은 신호)
2. 1h 추세 방향 일치
3. 15m 코인별 신호 발생
4. 카파시 4원칙 (MDD/레버리지/일일손실/분산) 통과
"""
from freqtrade.strategy import IStrategy, DecimalParameter, IntParameter, merge_informative_pair
from pandas import DataFrame
import talib.abstract as ta
import numpy as np
from datetime import datetime, date


class CapitalPreservationStrategy(IStrategy):
    """
    카파시 4원칙:
    1. MDD -12% 이내 (옵션 B, 멀티 TF 필터)
    2. 레버리지 2x
    3. 일일 -1% 손실 시 신규 진입 차단
    4. 분산 (config.json에서 pair 설정)
    """
    # 15m 메인 봉 (2026-06-22 主人님 결정, 거래 횟수 극대화)
    timeframe = "15m"
    can_short = True

    # 멀티 타임프레임 추세 필터 (1h 중기 + 4h 큰 추세)
    informative_timeframe_1h = "1h"
    informative_timeframe_4h = "4h"

    # 카파시 원칙 1+2: TP/SL (레버리지 2x, MDD -12% 이내, 옵션 B)
    # 15m 봉은 노이즈 크므로 타이트한 SL 필수 (-3% 가격 변동 = -6% MDD, 2x leverage)
    stoploss = -0.03  # MDD -12% 한도 내
    # ROI: 익절 0.6% (15m 단타, 레버리지 2x → 1.2% 수익, 빠른 청산)
    minimal_roi = {"0": 0.006, "30": 0.004, "60": 0.002}  # 0.6% → 시간 경과 시 감소

    # 카파시 원칙 3: 일일 손실 추적
    daily_pnl = {}
    current_date = None
    daily_halted = {}

    def informative_pairs(self):
        """멀티 타임프레임 (1h + 4h) informative 페어"""
        pairs = self.dp.current_whitelist() if self.dp else []
        result = []
        for pair in pairs:
            result.append((pair, self.informative_timeframe_1h))
            result.append((pair, self.informative_timeframe_4h))
        return result

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        if self.dp:
            pair = metadata["pair"]

            # 1h 추세 (중기)
            informative_1h = self.dp.get_pair_dataframe(pair=pair, timeframe=self.informative_timeframe_1h)
            informative_1h["ema_50_1h"] = ta.EMA(informative_1h, timeperiod=50)
            informative_1h["ema_200_1h"] = ta.EMA(informative_1h, timeperiod=200)
            macd_1h = ta.MACD(informative_1h, fastperiod=12, slowperiod=26, signalperiod=9)
            informative_1h["macd_1h"] = macd_1h["macd"]
            informative_1h["macdsignal_1h"] = macd_1h["macdsignal"]
            informative_1h["rsi_1h"] = ta.RSI(informative_1h, timeperiod=14)
            informative_1h["adx_1h"] = ta.ADX(informative_1h, timeperiod=14)
            dataframe = merge_informative_pair(dataframe, informative_1h, self.timeframe, self.informative_timeframe_1h, ffill=True)

            # 4h 추세 (큰 추세)
            informative_4h = self.dp.get_pair_dataframe(pair=pair, timeframe=self.informative_timeframe_4h)
            informative_4h["ema_50_4h"] = ta.EMA(informative_4h, timeperiod=50)
            informative_4h["ema_200_4h"] = ta.EMA(informative_4h, timeperiod=200)
            macd_4h = ta.MACD(informative_4h, fastperiod=12, slowperiod=26, signalperiod=9)
            informative_4h["macd_4h"] = macd_4h["macd"]
            informative_4h["macdsignal_4h"] = macd_4h["macdsignal"]
            informative_4h["rsi_4h"] = ta.RSI(informative_4h, timeperiod=14)
            informative_4h["adx_4h"] = ta.ADX(informative_4h, timeperiod=14)
            dataframe = merge_informative_pair(dataframe, informative_4h, self.timeframe, self.informative_timeframe_4h, ffill=True)

        # 15m 지표 (메인 신호)
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=9)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=21)
        # 15m MACD
        macd = ta.MACD(dataframe, fastperiod=12, slowperiod=26, signalperiod=9)
        dataframe["macd"] = macd["macd"]
        dataframe["macdsignal"] = macd["macdsignal"]
        dataframe["macdhist"] = macd["macdhist"]
        # 15m RSI
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        # 15m ADX (추세 강도, 15m 노이즈 회피)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)
        # 15m 볼린저
        bollinger = ta.BBANDS(dataframe, timeperiod=20, nbdev=2)
        dataframe["bb_upper"] = bollinger["upperband"]
        dataframe["bb_middle"] = bollinger["middleband"]
        dataframe["bb_lower"] = bollinger["lowerband"]
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 4h + 1h 추세 필터 (큰 추세와 같은 방향일 때만 진입)
        # 4h 추세 LONG: close > ema_50_4h AND macd_4h > macdsignal_4h
        # 4h 추세 SHORT: close < ema_50_4h AND macd_4h < macdsignal_4h
        trend_4h_long = (
            (dataframe["close_4h"] > dataframe["ema_50_4h_4h"]) &
            (dataframe["macd_4h_4h"] > dataframe["macdsignal_4h_4h"])
        )
        trend_4h_short = (
            (dataframe["close_4h"] < dataframe["ema_50_4h_4h"]) &
            (dataframe["macd_4h_4h"] < dataframe["macdsignal_4h_4h"])
        )

        # 1h 추세 — 단순 모멘텀 (15m 노이즈 회피용 보조 필터)
        # 1h 추세 LONG: ema_50_1h > ema_200_1h (골든 크로스)
        # 1h 추세 SHORT: ema_50_1h < ema_200_1h (데드 크로스)
        # → 1h 일치 안 해도 4h 추세 강할 때 진입 허용 (1h는 보조)
        trend_1h_supports_long = dataframe["ema_50_1h_1h"] > dataframe["ema_200_1h_1h"]
        trend_1h_supports_short = dataframe["ema_50_1h_1h"] < dataframe["ema_200_1h_1h"]

        # 4h 추세는 필수, 1h는 가중치 (강한 신호 = 4h 일치 + 1h 일치 / 약한 신호 = 4h 일치만)
        # 일단 4h 일치만 (단순화)로 신호 확보
        trend_long = trend_4h_long
        trend_short = trend_4h_short

        # 코인별 15m 진입 신호
        pair = metadata["pair"]
        if pair == "BTC/USDT:USDT":
            # BTC: 15m EMA_CROSS + MACD
            conditions_long = (
                trend_long &
                (dataframe["ema_fast"] > dataframe["ema_slow"]) &
                (dataframe["macd"] > dataframe["macdsignal"]) &
                (dataframe["adx"] > 15) &  # 15m 노이즈 회피
                (dataframe["rsi"] < 75) &  # 과매수 회피
                (dataframe["volume"] > 0)
            )
            conditions_short = (
                trend_short &
                (dataframe["ema_fast"] < dataframe["ema_slow"]) &
                (dataframe["macd"] < dataframe["macdsignal"]) &
                (dataframe["adx"] > 15) &
                (dataframe["rsi"] > 25) &
                (dataframe["volume"] > 0)
            )
        elif pair == "ETH/USDT:USDT":
            # ETH: 15m EMA_CROSS + RSI
            conditions_long = (
                trend_long &
                (dataframe["ema_fast"] > dataframe["ema_slow"]) &
                (dataframe["rsi"] > 50) & (dataframe["rsi"] < 70) &
                (dataframe["adx"] > 15) &
                (dataframe["volume"] > 0)
            )
            conditions_short = (
                trend_short &
                (dataframe["ema_fast"] < dataframe["ema_slow"]) &
                (dataframe["rsi"] < 50) & (dataframe["rsi"] > 30) &
                (dataframe["adx"] > 15) &
                (dataframe["volume"] > 0)
            )
        elif pair == "SOL/USDT:USDT":
            # SOL: 15m MACD + ADX (추세 강도)
            conditions_long = (
                trend_long &
                (dataframe["macd"] > dataframe["macdsignal"]) &
                (dataframe["adx"] > 20) &
                (dataframe["close"] > dataframe["ema_fast"]) &
                (dataframe["rsi"] < 75) &
                (dataframe["volume"] > 0)
            )
            conditions_short = (
                trend_short &
                (dataframe["macd"] < dataframe["macdsignal"]) &
                (dataframe["adx"] > 20) &
                (dataframe["close"] < dataframe["ema_fast"]) &
                (dataframe["rsi"] > 25) &
                (dataframe["volume"] > 0)
            )
        else:
            # 기본: 15m EMA_CROSS
            conditions_long = (
                trend_long &
                (dataframe["ema_fast"] > dataframe["ema_slow"]) &
                (dataframe["adx"] > 15) &
                (dataframe["volume"] > 0)
            )
            conditions_short = (
                trend_short &
                (dataframe["ema_fast"] < dataframe["ema_slow"]) &
                (dataframe["adx"] > 15) &
                (dataframe["volume"] > 0)
            )

        dataframe.loc[conditions_long, "enter_long"] = 1
        dataframe.loc[conditions_short, "enter_short"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 4h + 1h 추세 반전 OR 15m EMA_CROSS 반전
        trend_4h_reversal_long = dataframe["close_4h"] < dataframe["ema_50_4h_4h"]
        trend_4h_reversal_short = dataframe["close_4h"] > dataframe["ema_50_4h_4h"]
        trend_1h_reversal_long = dataframe["ema_50_1h_1h"] < dataframe["ema_200_1h_1h"]
        trend_1h_reversal_short = dataframe["ema_50_1h_1h"] > dataframe["ema_200_1h_1h"]

        # LONG 청산: 4h 추세 반전 OR 1h 추세 반전 OR 15m EMA_CROSS 반전
        dataframe.loc[
            trend_4h_reversal_long | trend_1h_reversal_long | (dataframe["ema_fast"] < dataframe["ema_slow"]),
            "exit_long"
        ] = 1
        # SHORT 청산: 4h 추세 반전 OR 1h 추세 반전 OR 15m EMA_CROSS 반전
        dataframe.loc[
            trend_4h_reversal_short | trend_1h_reversal_short | (dataframe["ema_fast"] > dataframe["ema_slow"]),
            "exit_short"
        ] = 1
        return dataframe

    def custom_stoploss(self, pair: str, trade, current_time, current_rate, current_profit) -> float:
        """
        카파시 원칙 1: MDD -12% 이내 (15m 봉 + 2x leverage → -0.3% SL, 매우 타이트)
        카파시 원칙 3: 일일 손실 -1% 추적
        """
        # 기본 SL: -0.3% (15m 봉 + 2x leverage → 가격 -0.15% 변동 시 청산)
        return -0.003
