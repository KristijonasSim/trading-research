# pragma: no cover
from typing import Dict, Tuple
from datetime import datetime
import numpy as np
import pandas as pd
from pandas import DataFrame

from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter, RealParameter
from freqtrade.persistence import Trade

import talib


class Pull_Back_Strategy(IStrategy):
    """
    多空皆可的 Pull back (1h + 4h)策略：
      Long 進場（下一根）需同時滿足：
        1) 4h RSI > threshold
        2) 1h ADX > threshold
        3) 4h ADX > threshold
        4) 1h 收盤 < BB 下軌
      Short 進場（下一根）需同時滿足：
        1) 4h RSI < threshold
        2) 1h ADX > threshold
        3) 4h ADX > threshold
        4) 1h 收盤 > BB 上軌

      出場：
        Long:1h 收盤 > BB 上軌
        Short:1h 收盤 < BB 下軌

      自訂停損:以「訊號K」的價格與 ATR 決定，並在開倉後固定（不追蹤）。
      倉位 sizing:根據 ATR 停損距離與單筆風險比例(risk_per_trade)動態計算。
    """

    # --- 基本設定 ---
    timeframe = "1h"
    informative_timeframe = "4h"
    can_short = True

    minimal_roi = {"0": 1.0}   # 不使用 ROI 強制出場（全靠 exit_signal / stoploss）
    stoploss = -0.99           # 全域保險底線，實際用 custom_stoploss
    use_custom_stoploss = True
    process_only_new_candles = True
    startup_candle_count = 200

    # --- 超參數（可 hyperopt）---
    bb_period = IntParameter(10, 60, default=20, space="buy", optimize=True)
    bb_stds   = RealParameter(1.0, 3.5, step=0.1, default=2.0, space="buy", optimize=True)

    htf_rsi_threshold = IntParameter(30, 70, default=45, space="buy", optimize=True)   # 4h RSI 閾值
    htf_adx_threshold = IntParameter(15, 40, default=25, space="buy", optimize=True)   # 4h ADX 閾值
    adx_threshold     = IntParameter(10, 40, default=20, space="buy", optimize=True)   # 1h ADX 閾值

    atr_mult = RealParameter(2.0, 6.0, default=4.5, step=0.1, space="sell", optimize=True)
    
    # risk_per_trade_hp = RealParameter(0.002, 0.02, default=0.01, step=0.005, space="sell", optimize=True)

    # 固定視窗
    adx_window = 14
    atr_window = 14

    # 風險參數（單筆最大風險佔用戶總資金比例）
    risk_per_trade: float = 0.01

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 用來存每筆 trade 的固定停損比例
        self._sl_cache = {}

    # --------- 工具函式（計算指標）---------
    @staticmethod
    def _add_bbands(df: DataFrame, period: int, stdevs: float, prefix: str = "") -> DataFrame:
        upper, middle, lower = talib.BBANDS(
            df["close"], timeperiod=period, nbdevup=stdevs, nbdevdn=stdevs, matype=0
        )
        df[f"{prefix}bb_up"]  = upper
        df[f"{prefix}bb_mid"] = middle
        df[f"{prefix}bb_low"] = lower
        return df

    @staticmethod
    def _add_adx(df: DataFrame, window: int, prefix: str = "") -> DataFrame:
        df[f"{prefix}adx"] = talib.ADX(df["high"], df["low"], df["close"], timeperiod=window)
        return df

    @staticmethod
    def _add_atr(df: DataFrame, window: int, prefix: str = "") -> DataFrame:
        df[f"{prefix}atr"] = talib.ATR(df["high"], df["low"], df["close"], timeperiod=window)
        return df

    @staticmethod
    def _add_rsi(df: DataFrame, window: int, colname: str = "rsi") -> DataFrame:
        df[colname] = talib.RSI(df["close"], timeperiod=window)
        return df

    # --------- 將 4h 指標合併到 1h ---------
    @staticmethod
    def _merge_4h_into_1h(df_1h: DataFrame, df_4h: DataFrame) -> DataFrame:
        """
        將 4h 的 rsi_4h / adx_4h 透過時間對齊 forward-fill 進 1h dataframe。
        支援 'date' 欄或 datetime index 兩種格式。
        """
        inf = df_4h.copy()
        if "date" not in inf.columns:
            inf["date"] = inf.index

        inf_small = inf[["date", "rsi_4h", "adx_4h"]].dropna(how="all")

        if "date" in df_1h.columns:
            one_sorted = df_1h.sort_values(by="date")
            inf_sorted = inf_small.sort_values(by="date")
            merged = pd.merge_asof(one_sorted, inf_sorted, on="date", direction="backward")
            merged = merged.ffill().sort_index()
            return merged
        else:
            out = df_1h.sort_index().copy()
            inf2 = inf_small.set_index("date").sort_index()
            out[["rsi_4h", "adx_4h"]] = inf2[["rsi_4h", "adx_4h"]].reindex(out.index, method="ffill")
            return out

    def informative_pairs(self):
        return [(pair, self.informative_timeframe) for pair in self.dp.current_whitelist()]

    def merge_informative(self, df: DataFrame, metadata: Dict) -> DataFrame:
        pair = metadata["pair"]
        inf = self.dp.get_pair_dataframe(pair=pair, timeframe=self.informative_timeframe)

        # 計算 4h 指標
        inf = self._add_rsi(inf, 14, colname="rsi_4h")
        inf = self._add_adx(inf, self.adx_window, prefix="")
        inf.rename(columns={"adx": "adx_4h"}, inplace=True)

        # 合併到 1h
        df = self._merge_4h_into_1h(df, inf)
        return df

    # --------- 指標計算 ---------
    def populate_indicators(self, df: DataFrame, metadata: Dict) -> DataFrame:
        df = self.merge_informative(df, metadata)

        df = self._add_bbands(df, period=int(self.bb_period.value), stdevs=float(self.bb_stds.value))
        df = self._add_adx(df, window=self.adx_window)
        df = self._add_atr(df, window=self.atr_window)

        df["volume_ok"] = df["volume"] > 0
        return df

    # --------- 進出場條件 ---------
    def _long_entry_condition(self, df: DataFrame) -> pd.Series:
        return (
            (df["rsi_4h"] > int(self.htf_rsi_threshold.value)) &
            (df["adx"]    > int(self.adx_threshold.value)) &
            (df["adx_4h"] > int(self.htf_adx_threshold.value)) &
            (df["close"]  < df["bb_low"]) &
            (df["volume_ok"])
        )

    def _short_entry_condition(self, df: DataFrame) -> pd.Series:
        return (
            (df["rsi_4h"] < int(self.htf_rsi_threshold.value)) &
            (df["adx"]    > int(self.adx_threshold.value)) &
            (df["adx_4h"] > int(self.htf_adx_threshold.value)) &
            (df["close"]  > df["bb_up"]) &
            (df["volume_ok"])
        )

    def populate_entry_trend(self, df: DataFrame, metadata: Dict) -> DataFrame:
        df.loc[self._long_entry_condition(df),  ["enter_long",  "enter_tag"]] = (1, "rsi4h_adx_bb_long")
        df.loc[self._short_entry_condition(df), ["enter_short", "enter_tag"]] = (1, "rsi4h_adx_bb_short")
        return df

    def populate_exit_trend(self, df: DataFrame, metadata: Dict) -> DataFrame:
        df.loc[(df["close"] > df["bb_up"]), "exit_long"] = 1
        df.loc[(df["close"] < df["bb_low"]), "exit_short"] = 1
        return df

    # ===============================
    # 倉位計算小工具（根據停損距離）
    # ===============================
    def position_size(self, balance: float, entry_price: float, stop_price: float, risk_per_trade: float = 0.01) -> float:
        """
        根據停損距離 & 風險承受度，自動計算倉位大小。
        回傳值：應投入的 USDT 數量
        """
        max_loss = balance * risk_per_trade            # 允許的最大虧損（USDT）
        risk_per_unit = abs(entry_price - stop_price)  # 每單位風險（USDT）
        if risk_per_unit <= 0:
            return 0.0
        position_units = max_loss / risk_per_unit
        stake_amount = position_units * entry_price
        return float(stake_amount)

    # ===============================
    # Freqtrade callback: 自訂倉位大小
    # ===============================
    def custom_stake_amount(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_stake: float,
        min_stake: float,
        max_stake: float,
        **kwargs,
    ) -> float:
        """
        動態計算倉位大小：
          - 以 ATR(1h) * atr_mult 當作停損距離
          - 單筆風險 = risk_per_trade(預設 1%)
        """
        try:
            balance = float(self.wallets.get_total_stake_balance())
        except Exception:
            # 回退：若無法讀取錢包（回測理論上可以），用 10000 模擬
            balance = 10000.0

        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if df is None or df.empty or "atr" not in df.columns:
            # 沒資料就使用系統建議
            stake = proposed_stake
        else:
            atr = float(df["atr"].iloc[-1])
            stop_price = current_rate - float(self.atr_mult.value) * atr
            # risk = float(self.risk_per_trade_hp.value)
            risk = self.risk_per_trade
            stake = self.position_size(
                balance=balance,
                entry_price=current_rate,
                stop_price=stop_price,
                risk_per_trade=risk,
            )

        # 夾在交易所允許範圍內
        if max_stake is not None:
            stake = min(stake, max_stake)
        if min_stake is not None:
            stake = max(stake, min_stake)
        return float(stake)

    # ===============================
    # 自訂停損（固定，不追蹤）
    # ===============================
    def custom_stoploss(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs,
    ) -> float:
        """
        以「訊號K」計算固定相對停損:
        Long: stop = 訊號收盤 - atr_mult * ATR(1h)
        Short: stop = 訊號最高 + atr_mult * ATR(1h)
        回傳 *相對損失比*（負值）。首次計算後鎖定於 _sl_cache, 之後不再更新。
        """

        # 若已計算，直接回傳
        if trade.id in self._sl_cache:
            return self._sl_cache[trade.id]

        # 取得 dataframe
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if df is None or df.empty or "atr" not in df.columns:
            return 1

        # 找到訊號K位置
        if "date" in df.columns:
            idx = df.index[df["date"] >= trade.open_date_utc]
        else:
            idx = df.index[df.index >= trade.open_date_utc]
        if len(idx) == 0:
            return 1

        entry_loc = idx[0]
        try:
            sig_pos = df.index.get_loc(entry_loc) - 1
            if sig_pos < 0:
                return 1
        except Exception:
            return 1

        row_sig = df.iloc[sig_pos]
        atr_mult = float(self.atr_mult.value)

        # 判斷方向
        direction = getattr(trade, "direction", None)
        if direction is None:
            direction = "short" if getattr(trade, "is_short", False) else "long"

        entry_price = float(trade.open_rate)
        if direction == "long":
            stop_price = float(row_sig["close"]) - atr_mult * float(row_sig["atr"])
            rel_sl = (stop_price - entry_price) / entry_price
        else:
            stop_price = float(row_sig["high"]) + atr_mult * float(row_sig["atr"])
            rel_sl = (entry_price - stop_price) / entry_price

        # 停損比例需為負值
        rel_sl = min(rel_sl, -0.001)

        # 鎖定在內部 cache，而不是 trade.user_data
        self._sl_cache[trade.id] = rel_sl

        return rel_sl


    # 槓桿（若使用合約）
    def leverage(self, *args, **kwargs) -> float:
        return 3.0

    # 繪圖設定 (Freqtrade plot-dataframe 用)
    plot_config = {
        "main_plot": {
            # K 線上畫的
            "bb_up": {"color": "red"},
            "bb_mid": {"color": "orange"},
            "bb_low": {"color": "green"},
        },
        "subplots": {
            # 額外開小圖
            "RSI (4h)": {
                "rsi_4h": {"color": "blue"},
            },
            "ADX (1h)": {
                "adx": {"color": "purple"},
            },
            "ADX (4h)": {
                "adx_4h": {"color": "pink"},
            },
            "ATR (1h)": {
                "atr": {"color": "black"},
            },
        }
    }


# --- Strategy idea ---
# https://www.youtube.com/watch?v=c9-SIpy3dEw