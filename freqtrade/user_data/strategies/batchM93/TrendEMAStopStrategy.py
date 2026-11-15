from freqtrade.strategy import IStrategy
from pandas import DataFrame
import pandas as pd
import talib.abstract as ta
from datetime import datetime, timedelta
import numpy as np


class TrendEMAStopStrategy(IStrategy):
    """
    趋势EMA止损策略

    核心逻辑：
    1. 趋势过滤：5EMA、20EMA、60EMA 排列 + ADX > 20
    2. 开仓：多头排列+RSI超卖做多；空头排列+RSI超买做空
    3. 止损止盈：2%止损、4%止盈（2:1盈亏比）
    4. 保本止损：盈利≥3%时移动止损至开仓价
    5. 风控：连续亏损5笔暂停
    """

    # ========== 基础参数 ==========
    timeframe = '5m'  # 5分钟K线，适合捕捉趋势
    max_open_trades = 3  # 最多同时持仓3个交易对
    startup_candle_count = 100  # 需要足够K线计算指标

    # 止盈止损设置
    minimal_roi = {
        "0": 0.20,  # ROI止盈20%，防止持仓太久
    }
    stoploss = -0.08  # 8%止损作为底线保护
    trailing_stop = False  # 不使用追踪止损

    # 订单类型
    order_types = {
        'entry': 'market',
        'exit': 'market',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    unfilledtimeout = {
        'entry': 60,
        'exit': 60,
        'unit': 'seconds'
    }

    # 杠杆配置
    leverage_config = {
        'BTC/USDT:USDT': 5.0,
        'ETH/USDT:USDT': 4.0,
        'SOL/USDT:USDT': 4.0,
        'XRP/USDT:USDT': 3.0,
        'DOGE/USDT:USDT': 3.0
    }

    # ========== 策略参数 ==========
    # 趋势过滤参数
    EMA_SHORT = 5
    EMA_MIDDLE = 20
    EMA_LONG = 60
    ADX_PERIOD = 14
    ADX_THRESHOLD = 20  # ADX > 20 表示趋势明确

    # RSI参数
    RSI_PERIOD = 14
    RSI_OVERSOLD = 35  # 超卖，做多信号
    RSI_OVERBOUGHT = 65  # 超买，做空信号

    # 止损止盈参数（点数，每个点10美元）
    STOP_LOSS_POINTS = 40
    TAKE_PROFIT_POINTS = 80
    BREAK_EVEN_POINTS = 50  # 盈利超过此点数时移动止损至开仓价

    # 风控参数
    MAX_CONSECUTIVE_LOSSES = 5  # 连续亏损5笔
    LOSS_PAUSE_HOURS = 1  # 暂停开仓1小时

    # ========== 风控状态 ==========
    def __init__(self, config: dict = {}):
        super().__init__(config)
        self.consecutive_losses = {}  # 每个交易对的连续亏损次数
        self.last_loss_time = {}  # 最后亏损时间
        self.trade_entry_prices = {}  # 记录每个交易的开仓价

    def informative_pairs(self) -> list:
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()

        # ========== 趋势指标 ==========
        # EMA组合
        df['ema_5'] = ta.EMA(df['close'], timeperiod=self.EMA_SHORT)
        df['ema_20'] = ta.EMA(df['close'], timeperiod=self.EMA_MIDDLE)
        df['ema_60'] = ta.EMA(df['close'], timeperiod=self.EMA_LONG)

        # ADX趋势强度
        df['adx'] = ta.ADX(df['high'], df['low'], df['close'], timeperiod=self.ADX_PERIOD)

        # RSI
        df['rsi'] = ta.RSI(df['close'], timeperiod=self.RSI_PERIOD)

        # ========== 趋势排列判断 ==========
        # 多头排列：5EMA > 20EMA > 60EMA
        df['bullish_trend'] = (df['ema_5'] > df['ema_20']) & (df['ema_20'] > df['ema_60'])

        # 空头排列：5EMA < 20EMA < 60EMA
        df['bearish_trend'] = (df['ema_5'] < df['ema_20']) & (df['ema_20'] < df['ema_60'])

        # 趋势明确：ADX > 阈值
        df['strong_trend'] = df['adx'] > self.ADX_THRESHOLD

        # RSI超买超卖
        df['rsi_oversold'] = df['rsi'] < self.RSI_OVERSOLD
        df['rsi_overbought'] = df['rsi'] > self.RSI_OVERBOUGHT

        return df

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 current_profit: float = 0.0, min_stops: float = 0.0,
                 max_stops: float = 0.0, current_time_rows: DataFrame = None,
                 **kwargs) -> float:
        """返回固定杠杆配置"""
        return self.leverage_config.get(pair, 3.0)

    def check_risk_controls(self, pair: str, current_time: datetime, current_rate: float) -> bool:
        """检查风控条件，返回是否允许开仓"""

        # 检查连续亏损
        if pair in self.consecutive_losses and self.consecutive_losses[pair] >= self.MAX_CONSECUTIVE_LOSSES:
            last_loss_time = self.last_loss_time.get(pair)
            if last_loss_time:
                pause_end_time = last_loss_time + timedelta(hours=self.LOSS_PAUSE_HOURS)
                if current_time < pause_end_time:
                    return False
                else:
                    self.consecutive_losses[pair] = 0

        return True

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        df['enter_long'] = 0
        df['enter_short'] = 0

        if len(df) < self.startup_candle_count:
            return df

        # ========== 多头开仓信号 ==========
        long_conditions = (
            # 趋势过滤
            df['bullish_trend'] &  # 多头排列
            df['strong_trend'] &  # 趋势明确
            # RSI超卖（适合做多）
            df['rsi_oversold']
        )

        df.loc[long_conditions, 'enter_long'] = 1

        # ========== 空头开仓信号 ==========
        short_conditions = (
            # 趋势过滤
            df['bearish_trend'] &  # 空头排列
            df['strong_trend'] &  # 趋势明确
            # RSI超买（适合做空）
            df['rsi_overbought']
        )

        df.loc[short_conditions, 'enter_short'] = 1

        return df

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()
        df['exit_long'] = 0
        df['exit_short'] = 0

        # 基础退出逻辑（由custom_exit处理）
        return df

    def custom_entry(self, pair: str, current_time: datetime, current_rate: float,
                     **kwargs) -> bool:
        """自定义开仓风控检查"""

        # 检查风控条件
        if not self.check_risk_controls(pair, current_time, current_rate):
            return False

        return True

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                           time_in_force: str, current_time: datetime, **kwargs) -> bool:
        """开仓确认时记录开仓价格"""
        self.trade_entry_prices[pair] = rate
        return True

    def custom_exit(self, pair: str, current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs) -> bool:
        """
        自定义退出逻辑

        止损止盈规则：
        1. 固定止损：2%
        2. 固定止盈：4%
        3. 保本止损：盈利≥3%时移动止损至开仓价
        """

        # 获取开仓价格
        entry_price = self.trade_entry_prices.get(pair)
        if entry_price is None:
            return False

        # 获取交易方向（从kwargs获取）
        is_short = kwargs.get('is_short', False)

        # 调整后的止盈止损百分比
        STOP_LOSS_PCT = 0.02  # 2%止损
        TAKE_PROFIT_PCT = 0.04  # 4%止盈
        BREAK_EVEN_PCT = 0.03  # 3%保本

        if is_short:
            # 空单止损：价格上涨2%
            if current_profit < -STOP_LOSS_PCT:
                self.record_loss(pair, current_time)
                return True

            # 空单止盈：价格下跌4%
            if current_profit > TAKE_PROFIT_PCT:
                return True

            # 空单保本止损：盈利≥3%且价格回到开仓价附近
            if current_profit > BREAK_EVEN_PCT and current_profit < 0.01:
                # 如果价格回到开仓价附近（±0.5%），触发保本止损
                if abs(current_profit) < 0.005:
                    return True
        else:
            # 多单止损：价格下跌2%
            if current_profit < -STOP_LOSS_PCT:
                self.record_loss(pair, current_time)
                return True

            # 多单止盈：价格上涨4%
            if current_profit > TAKE_PROFIT_PCT:
                return True

            # 多单保本止损：盈利≥3%且价格回到开仓价附近
            if current_profit > BREAK_EVEN_PCT and current_profit < 0.01:
                # 如果价格回到开仓价附近（±0.5%），触发保本止损
                if abs(current_profit) < 0.005:
                    return True

        return False

    def record_loss(self, pair: str, current_time: datetime):
        """记录亏损，用于连续亏损风控"""
        if pair not in self.consecutive_losses:
            self.consecutive_losses[pair] = 0

        self.consecutive_losses[pair] += 1
        self.last_loss_time[pair] = current_time

    def confirm_trade_exit(self, pair: str, order_type: str, amount: float, rate: float,
                          time_in_force: str, exit_reason: str, current_time: datetime,
                          **kwargs) -> bool:
        """平仓确认时清理状态"""
        if pair in self.trade_entry_prices:
            del self.trade_entry_prices[pair]
        return True
