# filename: TSMOM_ADX_VOL_Strategy.py
from freqtrade.strategy import IStrategy, IntParameter
from pandas import DataFrame
import talib.abstract as ta
import numpy as np

class TSMOM_ADX_VOL_Strategy(IStrategy):
    """
    簡單的 Time-Series Momentum:
      進場（下一根）：
        Long:  ADX > adx_threshold 且 MOM(mom_len) > 0 且 量能 > 均量(20)
        Short: ADX > adx_threshold 且 MOM(mom_len) < 0 且 量能 > 均量(20)

      出場（下一根）：
        Long:  MOM <= 0 或 ADX < adx_threshold
        Short: MOM >= 0 或 ADX < adx_threshold
    """

    INTERFACE_VERSION = 3
    timeframe = "1h"
    can_short = True
    process_only_new_candles = True
    startup_candle_count = 200

    # 讓 threshold / mom_len 可 hyperopt
    adx_threshold = IntParameter(10, 35, default=20, space="buy", optimize=True, load=True)
    mom_len       = IntParameter(5, 60, default=20, space="buy", optimize=True, load=True)
    vol_ma_len    = IntParameter(5, 60, default=20, space="buy", optimize=True, load=True)

    # 不靠 ROI，交給條件和停損（保險底線）
    minimal_roi = {"0": 1.0}
    stoploss = -0.10
    use_exit_signal = True
    trailing_stop = False

    def populate_indicators(self, df: DataFrame, metadata: dict) -> DataFrame:
        # ADX
        df["adx"] = ta.ADX(df)

        # Momentum（價格動能；>0 表示近 mom_len 根價格正動能）
        df["mom"] = ta.MOM(df["close"], timeperiod=int(self.mom_len.value))

        # 量能均線（20 根）
        win = int(self.vol_ma_len.value) 
        df["vol_ma"] = df["volume"].rolling(window=win, min_periods=win).mean()

        # 量能是否大於均量
        df["vol_ok"] = df["volume"] > df["vol_ma"]

        # 清理可能的 NaN
        df.fillna(method="ffill", inplace=True)
        df.fillna(0, inplace=True)
        return df

    def populate_entry_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        adx_thr = int(self.adx_threshold.value)

        long_cond = (
            (df["adx"] > adx_thr) &
            (df["mom"] > 0) &
            (df["vol_ok"])
        )

        short_cond = (
            (df["adx"] > adx_thr) &
            (df["mom"] < 0) &
            (df["vol_ok"])
        )

        df.loc[long_cond,  ["enter_long",  "enter_tag"]]  = (1, "tsmom_adx_vol_long")
        df.loc[short_cond, ["enter_short", "enter_tag"]] = (1, "tsmom_adx_vol_short")
        return df

    def populate_exit_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        adx_thr = int(self.adx_threshold.value)

        # 動能轉弱或趨勢衰退就離場
        df.loc[((df["mom"] <= 0) | (df["adx"] < adx_thr)), "exit_long"] = 1
        df.loc[((df["mom"] >= 0) | (df["adx"] < adx_thr)), "exit_short"] = 1
        return df

    # 繪圖（可選）
    plot_config = {
        "main_plot": {},
        "subplots": {
            "ADX": {"adx": {"color": "purple"}},
            "Momentum": {"mom": {"color": "blue"}},
            "Volume": {"volume": {"color": "grey"}, "vol_ma": {"color": "orange"}},
        },
    }


# ref: https://www.youtube.com/watch?v=alkOUlpSYYI