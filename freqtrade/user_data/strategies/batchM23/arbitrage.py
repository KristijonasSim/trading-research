from typing import Dict

import numpy as np
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy.interface import IStrategy


class Arbitrage(IStrategy):
    """
    一个简单的“统计套利 / 相对强弱”策略示例。

    核心思想（同一交易所内的“软套利”而不是高频搬砖）：
    - 参考 BTC/USDT 作为“市场指数”；
    - 对每个交易对，计算它自己的收益率和 BTC 的收益率之差（相对收益）；
    - 当某个币在一段时间内明显“跑输 BTC”时（相对收益偏低、z 值为负），我们认为它有一定的均值回归机会 → 考虑买入；
    - 当相对收益回到均值附近甚至变正（z 值>0），或者 RSI 偏高时 → 离场。

    特点：
    - 使用 5m 时间周期，信号不会特别频繁，但也足够“动起来”。
    - 只依赖 OHLCV + talib 指标，不依赖订单簿，也尽量降低对 websocket 的依赖。
    - 只做多（现货），不做空。
    """

    # 使用 5 分钟周期做“慢速”统计套利
    timeframe: str = "5m"

    # 只做多
    can_short: bool = False

    # 止损 3%
    stoploss: float = -0.03

    # 当浮盈达到 1% 时可以离场
    minimal_roi: Dict[str, float] = {
        "0": 0.01
    }

    # 只在新 K 线来临时计算一次信号
    process_only_new_candles: bool = True

    # 启动时至少需要这么多根 K 线来计算滚动均值 / 波动
    startup_candle_count: int = 150

    use_custom_stoploss: bool = False

    btc_reference_pair: str = "BTC/USDT"

    def informative_pairs(self):
        """
        本策略通过 DataProvider 手动获取 BTC/USDT 的数据，
        不使用 freqtrade 的 informative_pairs 机制，避免过于复杂。
        """
        return []

    def _get_btc_dataframe(self, metadata: dict) -> DataFrame:
        """
        从 DataProvider 中获取 BTC/USDT 的 DataFrame。
        回测 / 回放时 dp 一定存在；实盘中也通常存在。
        如果拿不到，就返回一个空 DataFrame，后续逻辑会做防护。
        """
        if not self.dp:
            return DataFrame()

        try:
            btc_df = self.dp.get_pair_dataframe(self.btc_reference_pair, self.timeframe).copy()
        except Exception:
            return DataFrame()

        return btc_df

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        计算本策略需要的技术指标：
        - 本币种的收益率、成交量均线、RSI
        - BTC/USDT 的收益率
        - 本币种相对 BTC 的超额收益（spread）及其 z 值
        """
        if dataframe.empty:
            return dataframe

        # --- 本币种自身指标 ---
        # 收益率（简单百分比变化）
        dataframe["ret"] = dataframe["close"].pct_change()

        # 成交量均线
        dataframe["volume_ma"] = dataframe["volume"].rolling(30).mean()

        # RSI
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        # --- BTC 参考收益 ---
        btc_df = self._get_btc_dataframe(metadata)

        if not btc_df.empty:
            btc_df = btc_df[["date", "close"]].copy()
            btc_df["btc_ret"] = btc_df["close"].pct_change()

            # 只保留需要的列
            btc_df = btc_df[["date", "btc_ret"]]

            # 按 date 合并到当前交易对的 dataframe 上
            dataframe = dataframe.merge(btc_df, on="date", how="left")
        else:
            # 如果拿不到 BTC 数据，就用 0 填充（意味着没有相对强弱信息）
            dataframe["btc_ret"] = 0.0

        # 相对收益：本币种收益 - BTC 收益
        dataframe["spread"] = dataframe["ret"] - dataframe["btc_ret"]

        # 计算 spread 的滚动均值和标准差
        window = 50
        dataframe["spread_mean"] = dataframe["spread"].rolling(window).mean()
        dataframe["spread_std"] = dataframe["spread"].rolling(window).std()

        # z-score：当前相对收益距离均值多少个标准差
        dataframe["spread_z"] = (dataframe["spread"] - dataframe["spread_mean"]) / dataframe["spread_std"]

        # 处理缺失值，避免 NaN 干扰后续条件判断
        dataframe.replace([np.inf, -np.inf], np.nan, inplace=True)
        dataframe.fillna(method="ffill", inplace=True)
        dataframe.fillna(method="bfill", inplace=True)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        进场逻辑（相对强弱“套利”逻辑）：

        1. spread_z < -1.0 ：本币种在最近一段时间明显“跑输” BTC（低估 / 超跌）；
        2. RSI < 45 ：本币种处于相对偏冷 / 未过热状态；
        3. 成交量 > 均量：当前 K 线成交量高于 30 根均量，避免在极度冷清时随便出手。
        """
        if dataframe.empty:
            return dataframe

        dataframe["enter_long"] = 0

        conditions = []

        # 1. 明显跑输 BTC
        conditions.append(dataframe["spread_z"] < -1.0)

        # 2. RSI 不过高
        conditions.append(dataframe["rsi"] < 45)

        # 3. 放量
        conditions.append(dataframe["volume"] > dataframe["volume_ma"])

        # 4. 基本防守：volume > 0
        conditions.append(dataframe["volume"] > 0)

        if conditions:
            dataframe.loc[
                np.logical_and.reduce(conditions),
                "enter_long",
            ] = 1

        # 不做空
        if "enter_short" in dataframe.columns:
            dataframe["enter_short"] = 0

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        离场逻辑：

        1. spread_z > 0 ：相对收益已经从低估回到均值附近甚至略微高估；
        2. 或 RSI > 60 ：本币种有一定程度的短线过热；
        """
        if dataframe.empty:
            return dataframe

        dataframe["exit_long"] = 0

        conditions = []

        # 1. 相对收益已经修复
        conditions.append(dataframe["spread_z"] > 0.0)

        # 2. RSI 较高
        conditions.append(dataframe["rsi"] > 60)

        if conditions:
            dataframe.loc[
                np.logical_or.reduce(conditions),
                "exit_long",
            ] = 1

        # 不做空
        if "exit_short" in dataframe.columns:
            dataframe["exit_short"] = 0

        return dataframe
