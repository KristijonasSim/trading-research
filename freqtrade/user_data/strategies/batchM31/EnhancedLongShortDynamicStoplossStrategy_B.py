# user_data/strategies/EnhancedLongShortDynamicStoplossStrategy_B.py

import logging
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

import talib.abstract as ta
import pandas as pd
import numpy as np
from datetime import datetime
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from typing import Dict, List, Optional, Tuple, Union
from pandas import DataFrame
from freqtrade.persistence import Trade

logger = logging.getLogger(__name__)

class EnhancedLongShortDynamicStoplossStrategy_B(IStrategy):
    """
    增强型多空动态止损策略 - B 版本: 整合 Hyperopt 400/400 + atr_ratio=0.035 优化
    """
    
    INTERFACE_VERSION = 3
    can_short = True
    timeframe = '1h'
    
    # 静态参数（Hyperopt 400/400 + 优化）
    minimal_roi = {
        "0": 0.478,
        "219": 0.209,
        "769": 0.073,
        "1290": 0
    }
    
    stoploss = -0.32
    
    trailing_stop = True
    trailing_stop_positive = 0.015
    trailing_stop_positive_offset = 0.04
    trailing_only_offset_is_reached = True
    
    # Hyperopt 参数 (基于 epoch 400 + 优化)
    # Buy space
    buy_rsi_level = IntParameter(55, 58, default=57, space='buy', optimize=True, load=True)  # 收紧
    buy_volume_threshold_high = DecimalParameter(0.2, 0.25, default=0.22, decimals=2, space='buy', optimize=True, load=True)  # 放宽
    buy_min_adx = IntParameter(9, 10, default=9, space='buy', optimize=True, load=True)  # 收紧
    buy_macd_threshold = DecimalParameter(0.00003, 0.00005, default=3e-05, decimals=5, space='buy', optimize=True, load=True)
    
    short_rsi_level = IntParameter(30, 40, default=30, space='buy', optimize=True, load=True)
    short_volume_threshold = DecimalParameter(0.12, 0.16, default=0.12, decimals=2, space='buy', optimize=True, load=True)
    short_min_adx = IntParameter(9, 10, default=9, space='buy', optimize=True, load=True)  # 收紧
    short_macd_threshold = DecimalParameter(0.00016, 0.00020, default=0.00017, decimals=5, space='buy', optimize=True, load=True)
    
    # Sell space
    sell_rsi_exit_long = IntParameter(70, 72, default=71, space='sell', optimize=True, load=True)  # 收紧
    sell_rsi_exit_short = IntParameter(28, 30, default=28, space='sell', optimize=True, load=True)  # 收紧
    sell_macd_exit_threshold = DecimalParameter(0.0017, 0.0019, default=0.0018, decimals=4, space='sell', optimize=True, load=True)
    
    # ROI space
    roi_0 = DecimalParameter(0.4, 0.6, default=0.478, space='roi', optimize=True, load=True)
    roi_219 = DecimalParameter(0.15, 0.25, default=0.209, space='roi', optimize=True, load=True)
    roi_769 = DecimalParameter(0.05, 0.10, default=0.073, space='roi', optimize=True, load=True)
    roi_1290 = DecimalParameter(0.0, 0.01, default=0.0, space='roi', optimize=True, load=True)
    
    # Stoploss space
    stoploss_val = DecimalParameter(-0.32, -0.25, default=-0.32, space='stoploss', optimize=True, load=True)
    
    # Trailing space
    trailing_stop_positive_val = DecimalParameter(0.01, 0.02, default=0.013, space='trailing', optimize=True, load=True)
    trailing_stop_offset_val = DecimalParameter(0.04, 0.06, default=0.047, space='trailing', optimize=True, load=True)
    
    # Protection space
    protection_max_drawdown = DecimalParameter(0.05, 0.08, default=0.079, space='protection', optimize=True, load=True)
    protection_low_profit = DecimalParameter(-0.07, -0.05, default=-0.061, space='protection', optimize=True, load=True)
    
    # 固定参数
    max_open_trades = 10
    process_throttle_secs = 5
    
    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }
    
    order_time_in_force = {
        'entry': 'GTC',
        'exit': 'GTC'
    }
    
    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self.minimal_roi = self.dynamic_roi()
        self.stoploss = float(self.stoploss_val.value)
        self.trailing_stop_positive = float(self.trailing_stop_positive_val.value)
        self.trailing_stop_positive_offset = float(self.trailing_stop_offset_val.value)
        self.protections = self.dynamic_protections()
        logger.info("Initializing EnhancedLongShortDynamicStoplossStrategy_B (Hyperopt 400/400 + atr_ratio=0.03 optimized)")
    
    def informative_pairs(self):
        return []
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        try:
            dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
            dataframe['macd'], dataframe['macd_signal'], dataframe['macd_hist'] = ta.MACD(dataframe['close'], fastperiod=12, slowperiod=26, signalperiod=9)
            dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
            dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=12)
            dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=26)
            dataframe['sma50'] = ta.SMA(dataframe, timeperiod=50)
            dataframe['volume_sma'] = ta.SMA(dataframe['volume'], timeperiod=20)
            dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_sma']
            bollinger = ta.BBANDS(dataframe, timeperiod=20, nbdevup=2.0, nbdevdn=2.0)
            dataframe['bb_upper'] = bollinger['upperband']
            dataframe['bb_lower'] = bollinger['lowerband']
            dataframe['bb_middle'] = bollinger['middleband']
            dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
            dataframe['atr_ratio'] = dataframe['atr'] / dataframe['close']
        except Exception as e:
            logger.error(f"Error in populate_indicators: {e}")
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        try:
            dataframe.loc[:, 'enter_long'] = 0
            dataframe.loc[:, 'enter_short'] = 0
            dataframe.loc[:, 'enter_tag'] = ''
            macd_diff = dataframe['macd'] - dataframe['macd_signal']
            long_conditions = (
                (dataframe['rsi'] < self.buy_rsi_level.value) &
                (macd_diff > self.buy_macd_threshold.value) &
                (dataframe['macd_hist'] > 0.002) &  # 增强多仓趋势确认
                (dataframe['adx'] > self.buy_min_adx.value) &
                (dataframe['atr_ratio'] < 0.03) &  # 您的要求：0.03
                (dataframe['ema_fast'] > dataframe['sma50']) &  # 保持长期趋势确认
                (dataframe['adx'] > 10) &  # 新增：多仓趋势确认
                ((dataframe['volume_ratio'] > self.buy_volume_threshold_high.value) |
                 (dataframe['ema_fast'] > dataframe['ema_slow']) |
                 (dataframe['close'] < dataframe['bb_lower']))
            )
            short_conditions = (
                (dataframe['rsi'] > self.short_rsi_level.value) &
                (macd_diff < -self.short_macd_threshold.value) &
                (dataframe['macd_hist'] < -0.002) &  # 增强空仓趋势确认
                (dataframe['adx'] > self.short_min_adx.value) &
                (dataframe['atr_ratio'] < 0.03) &  # 您的要求：0.03
                ((dataframe['volume_ratio'] > self.short_volume_threshold.value) |
                 (dataframe['ema_fast'] < dataframe['ema_slow']) |
                 (dataframe['close'] > dataframe['bb_upper']))
            )
            dataframe.loc[long_conditions, 'enter_long'] = 1
            dataframe.loc[long_conditions, 'enter_tag'] = 'hyperopt_long'
            dataframe.loc[short_conditions, 'enter_short'] = 1
            dataframe.loc[short_conditions, 'enter_tag'] = 'hyperopt_short'
        except Exception as e:
            logger.error(f"Error in populate_entry_trend: {e}")
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        try:
            dataframe.loc[:, 'exit_long'] = 0
            dataframe.loc[:, 'exit_short'] = 0
            macd_diff = dataframe['macd'] - dataframe['macd_signal']
            long_exit_conditions = (
                (dataframe['rsi'] > self.sell_rsi_exit_long.value) |
                (macd_diff < -self.sell_macd_exit_threshold.value) |
                (dataframe['macd_hist'] < -0.001) |
                (dataframe['close'] > dataframe['bb_upper'])
            )
            short_exit_conditions = (
                (dataframe['rsi'] < self.sell_rsi_exit_short.value) |
                (macd_diff > self.sell_macd_exit_threshold.value) |
                (dataframe['macd_hist'] > 0.001) |
                (dataframe['close'] < dataframe['bb_lower'])
            )
            dataframe.loc[long_exit_conditions, 'exit_long'] = 1
            dataframe.loc[short_exit_conditions, 'exit_short'] = 1
        except Exception as e:
            logger.error(f"Error in populate_exit_trend: {e}")
        return dataframe
    
    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                proposed_leverage: float, max_leverage: float, 
                entry_tag: Optional[str], side: str, **kwargs) -> float:
        try:
            if self.dp:
                analyzed_pair = self.dp.get_analyzed_dataframe(pair, self.timeframe)
                if analyzed_pair and not analyzed_pair[0].empty:
                    atr_ratio = analyzed_pair[0]['atr_ratio'].iloc[-1]
                else:
                    atr_ratio = 0.01
            else:
                atr_ratio = 0.01
            if atr_ratio > 0.025:
                return min(1.8, max_leverage)
            else:
                return min(3.0, max_leverage)
        except Exception as e:
            logger.error(f"Error in leverage: {e}")
            return min(2.0, max_leverage)
    
    def adjust_trade_position(self, trade: Trade, current_time: datetime,
                             current_rate: float, current_profit: float,
                             min_stake: Optional[float], max_stake: float,
                             current_entry_rate: float, current_exit_rate: float,
                             current_entry_profit: float, current_exit_profit: float,
                             **kwargs) -> Optional[float]:
        """动态调整仓位大小"""
        try:
            if self.dp:
                dataframe, _ = self.dp.get_analyzed_dataframe(trade.pair, self.timeframe)
                if dataframe is not None and not dataframe.empty:
                    atr_ratio = dataframe['atr_ratio'].iloc[-1]
                    if atr_ratio > 0.05:
                        adjusted_stake = trade.stake_amount * 0.35  # 极高波动减仓65%
                        logger.info(f"Adjusted stake for {trade.pair} due to extreme volatility (atr_ratio={atr_ratio:.4f}): {adjusted_stake:.2f}")
                        return adjusted_stake
                    elif atr_ratio > 0.03:
                        adjusted_stake = trade.stake_amount * 0.5  # 高波动减仓50%
                        logger.info(f"Adjusted stake for {trade.pair} due to high volatility (atr_ratio={atr_ratio:.4f}): {adjusted_stake:.2f}")
                        return adjusted_stake
            return None
        except Exception as e:
            logger.error(f"Error in adjust_trade_position: {e}")
            return None
    
    def dynamic_roi(self):
        try:
            return {
                "0": float(self.roi_0.value),
                "219": float(self.roi_219.value),
                "769": float(self.roi_769.value),
                "1290": float(self.roi_1290.value)
            }
        except Exception as e:
            logger.error(f"Error in dynamic_roi: {e}")
            return {
                "0": 0.478,
                "219": 0.209,
                "769": 0.073,
                "1290": 0
            }
    
    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float, **kwargs) -> float:
        """动态止损 - 基于ATR调整"""
        try:
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            if dataframe is not None and not dataframe.empty:
                atr_ratio = dataframe['atr_ratio'].iloc[-1]
                adjusted_stoploss = float(self.stoploss_val.value) * (1 + atr_ratio)
                return max(adjusted_stoploss, -0.05)  # 收紧上限
            return float(self.stoploss_val.value)
        except Exception as e:
            logger.error(f"Error in custom_stoploss: {e}")
            return float(self.stoploss_val.value)
    
    def dynamic_protections(self):
        """动态保护机制"""
        return [
            {
                "method": "CooldownPeriod",
                "stop_duration_candles": 2
            },
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 24,
                "trade_limit": 20,
                "stop_duration_candles": 4,
                "max_allowed_drawdown": float(self.protection_max_drawdown.value)
            },
            {
                "method": "LowProfitPairs",
                "lookback_period_candles": 200,
                "trade_limit": 1,
                "stop_duration_candles": 60,
                "required_profit": float(self.protection_low_profit.value)
            }
        ]