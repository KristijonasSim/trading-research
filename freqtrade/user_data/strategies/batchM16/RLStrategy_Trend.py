import logging
from typing import Dict, Optional
import numpy as np
from pandas import DataFrame
from datetime import datetime
from freqtrade.strategy import IStrategy, IntParameter
from freqtrade.persistence import Trade
import talib.abstract as ta

logger = logging.getLogger(__name__)


class RLStrategy_Trend_Past(IStrategy):

    startup_candle_count: int = 200

    timeframe = '2h'
    process_only_new_candles = True
    use_exit_signal = False
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    position_adjustment_enable = False
    can_short = True

    stoploss = -0.15

    minimal_roi = {
        "0": 0.10,
        "480": 0.05,
        "960": 0.02,
        "1920": 0.01
    }

    buy_adx = IntParameter(15, 25, default=20, space="buy", optimize=True)
    sell_adx = IntParameter(20, 35, default=28, space="sell", optimize=True)

    def leverage(
        self, pair: str, current_time, current_rate: float, proposed_leverage: float, max_leverage: float,
        side: str, **kwargs
    ) -> float:
        return 1

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = self.freqai.start(dataframe, metadata, self)

        dataframe.fillna(0, inplace=True)

        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['rsi'] = dataframe['rsi'].fillna(50)

        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['adx'] = dataframe['adx'].fillna(25)

        dataframe['plus_di'] = ta.PLUS_DI(dataframe, timeperiod=14)
        dataframe['minus_di'] = ta.MINUS_DI(dataframe, timeperiod=14)
        dataframe['plus_di'] = dataframe['plus_di'].fillna(25)
        dataframe['minus_di'] = dataframe['minus_di'].fillna(25)

        dataframe['sma_20'] = ta.SMA(dataframe['close'], timeperiod=20)
        dataframe['sma_20'] = dataframe['sma_20'].fillna(dataframe['close'])

        dataframe['sma_50'] = ta.SMA(dataframe['close'], timeperiod=50)
        dataframe['sma_50'] = dataframe['sma_50'].fillna(dataframe['close'])

        dataframe['ema_20'] = ta.EMA(dataframe['close'], timeperiod=20)
        dataframe['ema_20'] = dataframe['ema_20'].fillna(dataframe['close'])

        dataframe['volume_sma'] = ta.SMA(dataframe['volume'], timeperiod=20)
        dataframe['volume_sma'] = dataframe['volume_sma'].fillna(dataframe['volume'])

        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd'].fillna(0)
        dataframe['macdsignal'] = macd['macdsignal'].fillna(0)
        dataframe['macdhist'] = macd['macdhist'].fillna(0)

        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['atr'] = dataframe['atr'].fillna(dataframe['close'] * 0.02)

        bollinger = ta.BBANDS(dataframe, timeperiod=20, nbdevup=2.0, nbdevdn=2.0, matype=0)
        dataframe['bb_lower'] = bollinger['lowerband'].fillna(dataframe['close'])
        dataframe['bb_middle'] = bollinger['middleband'].fillna(dataframe['close'])
        dataframe['bb_upper'] = bollinger['upperband'].fillna(dataframe['close'])

        dataframe['bb_width'] = (dataframe['bb_upper'] - dataframe['bb_lower']) / dataframe['bb_middle']
        dataframe['bb_width'] = dataframe['bb_width'].fillna(0.05)

        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_sma']
        dataframe['volume_ratio'] = dataframe['volume_ratio'].fillna(1)

        dataframe.fillna(0, inplace=True)

        return dataframe

    def feature_engineering_standard(self, dataframe: DataFrame, **kwargs) -> DataFrame:
        dataframe[f"%-raw_close"] = dataframe["close"]
        dataframe[f"%-raw_open"] = dataframe["open"]
        dataframe[f"%-raw_high"] = dataframe["high"]
        dataframe[f"%-raw_low"] = dataframe["low"]
        dataframe[f"%-raw_volume"] = dataframe["volume"]

        dataframe['%-rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['%-rsi'] = dataframe['%-rsi'].fillna(50)

        dataframe['%-adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['%-adx'] = dataframe['%-adx'].fillna(25)

        dataframe['%-plus_di'] = ta.PLUS_DI(dataframe, timeperiod=14)
        dataframe['%-minus_di'] = ta.MINUS_DI(dataframe, timeperiod=14)
        dataframe['%-plus_di'] = dataframe['%-plus_di'].fillna(25)
        dataframe['%-minus_di'] = dataframe['%-minus_di'].fillna(25)

        macd = ta.MACD(dataframe)
        dataframe['%-macd'] = macd['macd'].fillna(0)
        dataframe['%-macdsignal'] = macd['macdsignal'].fillna(0)
        dataframe['%-macdhist'] = macd['macdhist'].fillna(0)

        dataframe['%-sma_20'] = ta.SMA(dataframe['close'], timeperiod=20)
        dataframe['%-sma_20'] = dataframe['%-sma_20'].fillna(dataframe['close'])

        dataframe['%-sma_50'] = ta.SMA(dataframe['close'], timeperiod=50)
        dataframe['%-sma_50'] = dataframe['%-sma_50'].fillna(dataframe['close'])

        dataframe['%-ema_20'] = ta.EMA(dataframe['close'], timeperiod=20)
        dataframe['%-ema_20'] = dataframe['%-ema_20'].fillna(dataframe['close'])

        dataframe['%-volume_sma'] = ta.SMA(dataframe['volume'], timeperiod=20)
        dataframe['%-volume_sma'] = dataframe['%-volume_sma'].fillna(dataframe['volume'])
        dataframe['%-volume_ratio'] = dataframe['volume'] / dataframe['%-volume_sma']
        dataframe['%-volume_ratio'] = dataframe['%-volume_ratio'].fillna(1)

        dataframe['%-atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['%-atr'] = dataframe['%-atr'].fillna(dataframe['close'] * 0.02)

        bollinger = ta.BBANDS(dataframe, timeperiod=20, nbdevup=2.0, nbdevdn=2.0, matype=0)
        dataframe['%-bb_lower'] = bollinger['lowerband'].fillna(dataframe['close'])
        dataframe['%-bb_middle'] = bollinger['middleband'].fillna(dataframe['close'])
        dataframe['%-bb_upper'] = bollinger['upperband'].fillna(dataframe['close'])
        dataframe['%-bb_width'] = (dataframe['%-bb_upper'] - dataframe['%-bb_lower']) / dataframe['%-bb_middle']
        dataframe['%-bb_width'] = dataframe['%-bb_width'].fillna(0.05)

        dataframe['%-close_sma20_ratio'] = dataframe['close'] / dataframe['%-sma_20']
        dataframe['%-close_sma20_ratio'] = dataframe['%-close_sma20_ratio'].fillna(1)

        dataframe['%-close_sma50_ratio'] = dataframe['close'] / dataframe['%-sma_50']
        dataframe['%-close_sma50_ratio'] = dataframe['%-close_sma50_ratio'].fillna(1)

        dataframe['%-price_change'] = dataframe['close'].pct_change()
        dataframe['%-price_change'] = dataframe['%-price_change'].fillna(0)

        dataframe['%-high_low_ratio'] = dataframe['high'] / dataframe['low']
        dataframe['%-high_low_ratio'] = dataframe['%-high_low_ratio'].fillna(1)

        dataframe['%-sma_cross'] = np.where(dataframe['%-sma_20'] > dataframe['%-ema_20'], 1, -1)

        dataframe['%-di_cross'] = np.where(dataframe['%-plus_di'] > dataframe['%-minus_di'], 1, -1)

        dataframe['%-trend_strength'] = np.where(
            dataframe['%-adx'] > 25,
            (dataframe['%-adx'] - 25) / 50,
            0
        )
        dataframe['%-trend_strength'] = dataframe['%-trend_strength'].fillna(0)

        dataframe['%-hour'] = dataframe['date'].dt.hour
        dataframe['%-day_of_week'] = dataframe['date'].dt.dayofweek

        for i in range(1, 4):
            dataframe[f'%-rsi_shift_{i}'] = dataframe['%-rsi'].shift(i).fillna(50)
            dataframe[f'%-price_change_shift_{i}'] = dataframe['%-price_change'].shift(i).fillna(0)
            dataframe[f'%-volume_ratio_shift_{i}'] = dataframe['%-volume_ratio'].shift(i).fillna(1)
            dataframe[f'%-adx_shift_{i}'] = dataframe['%-adx'].shift(i).fillna(25)

        dataframe['%-adx_mean_5'] = dataframe['%-adx'].rolling(5).mean().fillna(25)
        dataframe['%-rsi_mean_5'] = dataframe['%-rsi'].rolling(5).mean().fillna(50)
        dataframe['%-volume_ratio_mean_5'] = dataframe['%-volume_ratio'].rolling(5).mean().fillna(1)

        dataframe.fillna(0, inplace=True)

        return dataframe

    def feature_engineering_expand_all(self, dataframe: DataFrame, period: int, **kwargs) -> DataFrame:
        dataframe[f"%-rsi-period_{period}"] = ta.RSI(dataframe, timeperiod=period)
        dataframe[f"%-rsi-period_{period}"] = dataframe[f"%-rsi-period_{period}"].fillna(50)

        dataframe[f"%-adx-period_{period}"] = ta.ADX(dataframe, timeperiod=period)
        dataframe[f"%-adx-period_{period}"] = dataframe[f"%-adx-period_{period}"].fillna(25)

        dataframe[f"%-mfi-period_{period}"] = ta.MFI(dataframe, timeperiod=period)
        dataframe[f"%-mfi-period_{period}"] = dataframe[f"%-mfi-period_{period}"].fillna(50)

        dataframe[f"%-sma-period_{period}"] = ta.SMA(dataframe['close'], timeperiod=period)
        dataframe[f"%-sma-period_{period}"] = dataframe[f"%-sma-period_{period}"].fillna(dataframe['close'])

        dataframe[f"%-ema-period_{period}"] = ta.EMA(dataframe['close'], timeperiod=period)
        dataframe[f"%-ema-period_{period}"] = dataframe[f"%-ema-period_{period}"].fillna(dataframe['close'])

        bollinger = ta.BBANDS(dataframe, timeperiod=period, nbdevup=2.2, nbdevdn=2.2, matype=0)
        dataframe[f"%-bb_lowerband-period_{period}"] = bollinger['lowerband'].fillna(dataframe['close'])
        dataframe[f"%-bb_middleband-period_{period}"] = bollinger['middleband'].fillna(dataframe['close'])
        dataframe[f"%-bb_upperband-period_{period}"] = bollinger['upperband'].fillna(dataframe['close'])

        dataframe[f"%-bb_width-period_{period}"] = (
            dataframe[f"%-bb_upperband-period_{period}"] -
            dataframe[f"%-bb_lowerband-period_{period}"]
        ) / dataframe[f"%-bb_middleband-period_{period}"]
        dataframe[f"%-bb_width-period_{period}"] = dataframe[f"%-bb_width-period_{period}"].fillna(0.1)

        dataframe[f"%-roc-period_{period}"] = ta.ROC(dataframe['close'], timeperiod=period)
        dataframe[f"%-roc-period_{period}"] = dataframe[f"%-roc-period_{period}"].fillna(0)

        stoch = ta.STOCH(dataframe, fastk_period=period, slowk_period=3, slowd_period=3)
        dataframe[f"%-slowk-period_{period}"] = stoch['slowk'].fillna(50)
        dataframe[f"%-slowd-period_{period}"] = stoch['slowd'].fillna(50)

        dataframe[f"%-willr-period_{period}"] = ta.WILLR(dataframe, timeperiod=period)
        dataframe[f"%-willr-period_{period}"] = dataframe[f"%-willr-period_{period}"].fillna(-50)

        dataframe[f"%-cci-period_{period}"] = ta.CCI(dataframe, timeperiod=period)
        dataframe[f"%-cci-period_{period}"] = dataframe[f"%-cci-period_{period}"].fillna(0)

        dataframe.fillna(0, inplace=True)

        return dataframe

    def feature_engineering_expand_basic(self, dataframe: DataFrame, **kwargs) -> DataFrame:
        dataframe['%-pct-change'] = dataframe['close'].pct_change()
        dataframe['%-pct-change'] = dataframe['%-pct-change'].fillna(0)

        dataframe['%-pct-change-abs'] = abs(dataframe['%-pct-change'])
        dataframe['%-pct-change-abs'] = dataframe['%-pct-change-abs'].fillna(0)

        dataframe['%-high-low-ratio'] = dataframe['high'] / dataframe['low']
        dataframe['%-high-low-ratio'] = dataframe['%-high-low-ratio'].fillna(1)

        dataframe['%-close-open-ratio'] = dataframe['close'] / dataframe['open']
        dataframe['%-close-open-ratio'] = dataframe['%-close-open-ratio'].fillna(1)

        dataframe['%-volume-mean'] = dataframe['volume'].rolling(20).mean()
        dataframe['%-volume-mean'] = dataframe['%-volume-mean'].fillna(dataframe['volume'])

        dataframe['%-volume-ratio'] = dataframe['volume'] / dataframe['%-volume-mean']
        dataframe['%-volume-ratio'] = dataframe['%-volume-ratio'].fillna(1)

        dataframe['%-volume-pct-change'] = dataframe['volume'].pct_change()
        dataframe['%-volume-pct-change'] = dataframe['%-volume-pct-change'].fillna(0)

        dataframe['%-raw_close'] = dataframe['close']
        dataframe['%-raw_open'] = dataframe['open']
        dataframe['%-raw_high'] = dataframe['high']
        dataframe['%-raw_low'] = dataframe['low']
        dataframe['%-raw_volume'] = dataframe['volume']

        dataframe['%-hour'] = dataframe['date'].dt.hour
        dataframe['%-day_of_week'] = dataframe['date'].dt.dayofweek
        dataframe['%-day_of_month'] = dataframe['date'].dt.day

        dataframe['%-atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['%-atr'] = dataframe['%-atr'].fillna(dataframe['close'] * 0.02)

        dataframe.fillna(0, inplace=True)

        return dataframe

    def set_freqai_targets(self, dataframe: DataFrame, **kwargs) -> DataFrame:
        dataframe["&-action"] = 0
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'enter_long'] = 0
        dataframe.loc[:, 'enter_short'] = 0

        if '&-action' in dataframe.columns:
            dataframe.loc[dataframe['&-action'] == 1, 'enter_long'] = 1
            dataframe.loc[dataframe['&-action'] == 2, 'enter_short'] = 1

            long_signals = (dataframe['enter_long'] == 1).sum()
            short_signals = (dataframe['enter_short'] == 1).sum()
            if long_signals > 0 or short_signals > 0:
                logger.info(f"RL Agent - Long entries: {long_signals}, Short entries: {short_signals}")

        else:
            logger.info("&-action not found, using trend-based fallback signals")

            long_condition = (
                (dataframe['adx'] > self.buy_adx.value) &
                (dataframe['plus_di'] > dataframe['minus_di']) &
                (dataframe['close'] > dataframe['sma_20']) &
                (dataframe['volume'] > 0) &
                (dataframe['rsi'] < 70) &
                (dataframe['rsi'] > 30)
            )

            short_condition = (
                (dataframe['adx'] > self.buy_adx.value) &
                (dataframe['minus_di'] > dataframe['plus_di']) &
                (dataframe['close'] < dataframe['sma_20']) &
                (dataframe['volume'] > 0) &
                (dataframe['rsi'] > 30) &
                (dataframe['rsi'] < 70)
            )

            dataframe.loc[long_condition, 'enter_long'] = 1
            dataframe.loc[short_condition, 'enter_short'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'exit_long'] = 0
        dataframe.loc[:, 'exit_short'] = 0

        if '&-action' in dataframe.columns:
            dataframe.loc[dataframe['&-action'] == 3, 'exit_long'] = 1
            dataframe.loc[dataframe['&-action'] == 4, 'exit_short'] = 1

            long_exits = (dataframe['exit_long'] == 1).sum()
            short_exits = (dataframe['exit_short'] == 1).sum()
            if long_exits > 0 or short_exits > 0:
                logger.info(f"RL Agent - Long exits: {long_exits}, Short exits: {short_exits}")

        return dataframe

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime,
                       current_rate: float, current_profit: float, **kwargs) -> float:
        if current_profit > 0.15:
            return -0.02
        elif current_profit > 0.12:
            return -0.03
        elif current_profit > 0.10:
            return -0.04
        elif current_profit > 0.08:
            return -0.05
        elif current_profit > 0.05:
            return -0.07
        elif current_profit > 0.03:
            return -0.10
        return -0.15

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                           time_in_force: str, current_time: datetime, entry_tag: Optional[str],
                           side: str, **kwargs) -> bool:
        return True
