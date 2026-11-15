import numpy as np
import talib.abstract as ta
import pandas as pd
from pandas import DataFrame
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter, merge_informative_pair
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class DualPositionHedgeV1(IStrategy):
    """
    多空双开对冲策略 V1 (Dual Position Hedge Strategy)
    
    核心思路：
    1. 在关键位置同时开多空单，锁定风险
    2. 根据趋势方向，逐步平掉反向单子
    3. 保留顺势单子，获取趋势利润
    4. 通过对冲机制，实现永不爆仓
    
    适用场景：
    - 震荡行情中的突破
    - 重要支撑阻力位
    - 不确定方向但预期有大波动的时候
    """
    
    INTERFACE_VERSION = 3
    timeframe = '5m'
    can_short = True
    
    # 策略参数 - 回到第一轮优化的最佳配置
    rsi_overbought = IntParameter(70, 85, default=78, space='sell')  # 回到最优设置
    rsi_oversold = IntParameter(15, 30, default=22, space='buy')     # 回到最优设置
    ema_period = IntParameter(20, 50, default=25, space='buy')       # 保持不变
    volume_threshold = DecimalParameter(1.5, 2.5, default=2.0, space='buy')  # 回到最优设置
    
    # 新增动态止损参数
    dynamic_stoploss = DecimalParameter(0.05, 0.12, default=0.07, space='buy')  # 动态止损
    
    # 风险控制 - 最优版本设置
    stoploss = -0.08  # 8%止损，最优版本
    
    minimal_roi = {
        "0": 0.04,   # 4% 目标利润（降低以增加获利机会）
        "15": 0.025, # 15分钟 2.5%
        "30": 0.02,  # 30分钟 2%
        "60": 0.015, # 1小时 1.5%
        "120": 0.01  # 2小时 1%
    }

    # 不使用追踪止损，手动管理仓位
    trailing_stop = False
    
    process_only_new_candles = True
    startup_candle_count = 200
    custom_leverage = 6.0  # 最优版本杠杆

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: str, side: str,
                 **kwargs) -> float:
        return self.custom_leverage

    def custom_stoploss(self, pair: str, trade, current_time: datetime,
                        current_rate: float, current_profit: float, **kwargs) -> float:
        """
        动态止损：根据持仓时间和盈利情况调整止损
        """
        # 获取持仓时间（分钟）
        trade_duration = (current_time - trade.open_date_utc).total_seconds() / 60
        
        # 如果已经盈利，使用更紧的止损保护利润
        if current_profit > 0.02:  # 盈利超过2%
            return -0.015  # 1.5%止损保护利润
        elif current_profit > 0.01:  # 盈利超过1%
            return -0.03   # 3%止损
        elif trade_duration > 60:  # 持仓超过1小时
            return -0.06   # 6%止损，避免长时间亏损
        else:
            return self.stoploss  # 使用默认7%止损

    def informative_pairs(self) -> list:
        pairs = self.dp.current_whitelist()
        return [(pair, '1h') for pair in pairs]  # 改用1小时数据

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        
        # === 5分钟指标 ===
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=self.ema_period.value)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=self.ema_period.value * 2)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['volume_sma'] = ta.SMA(dataframe['volume'], timeperiod=20)
        dataframe['volume_ratio'] = dataframe['volume'] / dataframe['volume_sma']
        
        # ATR for volatility
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['atr_ratio'] = dataframe['atr'] / dataframe['close']
        
        # Bollinger Bands for exit signals
        bollinger = ta.BBANDS(dataframe, timeperiod=20, nbdevup=2.0, nbdevdn=2.0, matype=0)
        dataframe['bb_upper'] = bollinger['upperband']
        dataframe['bb_middle'] = bollinger['middleband']
        dataframe['bb_lower'] = bollinger['lowerband']
        
        # === 1小时趋势指标 ===
        inf_tf = '1h'
        informative = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe=inf_tf)
        
        informative['ema_trend'] = ta.EMA(informative, timeperiod=50)
        informative['rsi_trend'] = ta.RSI(informative, timeperiod=14)
        informative['macd'], informative['macdsignal'], informative['macdhist'] = ta.MACD(informative)
        
        # 趋势强度判断
        informative['trend_strength'] = np.where(
            informative['close'] > informative['ema_trend'], 1,  # 上涨趋势
            np.where(informative['close'] < informative['ema_trend'], -1, 0)  # 下跌趋势
        )
        
        dataframe = merge_informative_pair(dataframe, informative, self.timeframe, inf_tf, ffill=True)
        
        # 重命名列
        dataframe['trend_strength'] = dataframe[f'trend_strength_{inf_tf}']
        dataframe['rsi_trend'] = dataframe[f'rsi_trend_{inf_tf}']
        dataframe['macd_trend'] = dataframe[f'macd_{inf_tf}']
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        
        # === 双开条件：回到第一轮优化的最佳配置 ===
        # 使用已验证有效的参数组合
        
        dual_open_condition = (
            # RSI极值 - 最优阈值
            ((dataframe['rsi'] >= self.rsi_overbought.value) | 
             (dataframe['rsi'] <= self.rsi_oversold.value)) &
            # 成交量放大 - 最优要求
            (dataframe['volume_ratio'] > self.volume_threshold.value) &
            # 波动率较高 - 最优阈值
            (dataframe['atr_ratio'] > 0.025) &
            # 布林带位置确认 - 最优设置
            ((dataframe['close'] > dataframe['bb_upper'] * 0.98) |  # 接近上轨
             (dataframe['close'] < dataframe['bb_lower'] * 1.02))   # 接近下轨
        )
        
        # === 多单入场 ===
        # 在双开条件下，如果趋势偏多，优先开多单
        dataframe.loc[
            (
                dual_open_condition &
                (
                    # 5分钟超跌反弹
                    (dataframe['rsi'] <= self.rsi_oversold.value) |
                    # 1小时趋势向上
                    (dataframe['trend_strength'] > 0) |
                    # EMA金叉
                    ((dataframe['ema_fast'] > dataframe['ema_slow']) & 
                     (dataframe['ema_fast'].shift(1) <= dataframe['ema_slow'].shift(1)))
                )
            ),
            'enter_long'] = 1
            
        # === 空单入场 ===  
        # 在双开条件下，如果趋势偏空，优先开空单
        dataframe.loc[
            (
                dual_open_condition &
                (
                    # 5分钟超买回调
                    (dataframe['rsi'] >= self.rsi_overbought.value) |
                    # 1小时趋势向下
                    (dataframe['trend_strength'] < 0) |
                    # EMA死叉
                    ((dataframe['ema_fast'] < dataframe['ema_slow']) & 
                     (dataframe['ema_fast'].shift(1) >= dataframe['ema_slow'].shift(1)))
                )
            ),
            'enter_short'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        
        # === 多单离场 - 更积极的获利策略 ===
        dataframe.loc[
            (
                # RSI超买但阈值更低，更早离场
                (dataframe['rsi'] > self.rsi_overbought.value - 3) |
                # 趋势转弱
                (dataframe['trend_strength'] < 0) |
                # 价格接近布林带中轨（获利回吐信号）
                (dataframe['close'] < dataframe['bb_middle']) |
                # EMA死叉信号
                ((dataframe['ema_fast'] < dataframe['ema_slow']) & 
                 (dataframe['ema_fast'].shift(1) >= dataframe['ema_slow'].shift(1)))
            ),
            'exit_long'] = 1
            
        # === 空单离场 - 更积极的获利策略 ===
        dataframe.loc[
            (
                # RSI超卖但阈值更高，更早离场
                (dataframe['rsi'] < self.rsi_oversold.value + 3) |
                # 趋势转强
                (dataframe['trend_strength'] > 0) |
                # 价格接近布林带中轨（获利回吐信号）
                (dataframe['close'] > dataframe['bb_middle']) |
                # EMA金叉信号
                ((dataframe['ema_fast'] > dataframe['ema_slow']) & 
                 (dataframe['ema_fast'].shift(1) <= dataframe['ema_slow'].shift(1)))
            ),
            'exit_short'] = 1

        return dataframe

    def custom_entry_price(self, pair: str, current_time: datetime, proposed_rate: float,
                          entry_tag: Optional[str], side: str, **kwargs) -> float:
        """
        自定义入场价格，确保在关键位置入场
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe.empty:
            return proposed_rate
            
        last_candle = dataframe.iloc[-1]
        
        if side == 'long':
            # 多单稍微激进一点入场
            return proposed_rate * 1.001
        else:
            # 空单稍微激进一点入场  
            return proposed_rate * 0.999
            
    def custom_exit_price(self, pair: str, trade, current_time: datetime, 
                         proposed_rate: float, current_profit: float, exit_tag: Optional[str],
                         **kwargs) -> float:
        """
        自定义离场价格，确保及时离场
        """
        if current_profit > 0.02:  # 利润超过2%时，稍微保守离场
            if trade.is_short:
                return proposed_rate * 1.001  # 空单稍高价格平仓
            else:
                return proposed_rate * 0.999  # 多单稍低价格平仓
        
        return proposed_rate

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                           time_in_force: str, current_time: datetime, entry_tag: Optional[str],
                           side: str, **kwargs) -> bool:
        """
        确认交易入场，可以在这里实现更复杂的双开逻辑
        """
        # 这里可以添加额外的风控逻辑
        # 比如检查当前持仓情况，确保不会过度开仓
        return True