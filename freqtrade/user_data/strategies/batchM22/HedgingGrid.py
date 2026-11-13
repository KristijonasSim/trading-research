# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
# --- Do not remove these imports ---
import numpy as np
import pandas as pd


from datetime import datetime, timedelta, timezone
from pandas import DataFrame
from typing import Optional, Union
import logging

logger = logging.getLogger(__name__)

from freqtrade.strategy import (
    IStrategy,
    Trade,
    Order,
    PairLocks,
    informative,  # @informative decorator
    # Hyperopt Parameters
    BooleanParameter,
    CategoricalParameter,
    DecimalParameter,
    IntParameter,
    RealParameter,
    # timeframe helpers
    timeframe_to_minutes,
    timeframe_to_next_date,
    timeframe_to_prev_date,
    # Strategy helper functions
    merge_informative_pair,
    stoploss_from_absolute,
    stoploss_from_open,
)

# --------------------------------
# Add your lib to import here
import talib.abstract as ta
from technical import qtpylib



# 单向网格，ATR捕捉潜在的反转点进行微型马丁加仓
class HedgingGrid(IStrategy):
    INTERFACE_VERSION = 3
    can_short: bool = True  # 支持做空
    
    minimal_roi = {    
        "0": 0.03,      # 初始目标 1% => 3%
        "60": 0.024,    # 60分钟后降至 0.8% => 2.4%
        "120": 0.015    # 120分钟后降至 0.5% => 1.5%
    }
    stoploss = -0.3  # 设置止损 30%
    trailing_stop = False
    timeframe = "5m"
    process_only_new_candles = True

    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    startup_candle_count: int = 200
    
    # 开启仓位调整（加仓功能）
    position_adjustment_enable = True

    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }
    order_time_in_force = {"entry": "GTC", "exit": "GTC"}


    # ==================== 策略参数 ====================
    # ATR 乘数，用于计算网格间距（突破距离）
    atr_multiplier = 1.0
    
    # 加仓状态追踪 
    # 做多: {'signal_active': bool, 'append_lowest': float, 'lowest_entry_price': float}
    # 做空: {'signal_active': bool, 'append_highest': float, 'highest_entry_price': float}
    position_adjust_state: dict = {}

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: str | None, side: str,
                 **kwargs) -> float:
        return 3.0

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """计算 ATR 和 EMA 指标"""
        # 清理已关闭交易的状态字典（每根K线清理一次）
        self._cleanup_closed_trades()
        
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["volume"] > 0) &
            (dataframe['close'] > dataframe['ema_200']),
            "enter_long",
        ] = 1

        dataframe.loc[
            (dataframe["volume"] > 0) &
            (dataframe['close'] < dataframe['ema_200']),
            "enter_short",
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        return dataframe

    def check_entry_timeout(self, pair: str, trade: Trade, order: Order,
                           current_time: datetime, **kwargs) -> bool:
        """
        检查入场/加仓订单是否超时
        返回 True 取消订单，并设置 pending_reentry 标志使下次循环直接重新下单
        """
        order_age = (current_time - order.order_date_utc).total_seconds()
        if order_age > 60:  # 60秒超时
            # 设置待重新入场标志，下次循环直接重新下单
            trade_id = trade.id
            if trade_id in self.position_adjust_state:
                logger.info(f"{pair} - 加仓订单超时 (Age: {order_age}s). 准备重新入场.")
                self.position_adjust_state[trade_id]['pending_reentry'] = True
            return True
        return False

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                           time_in_force: str, current_time: datetime, entry_tag: Optional[str],
                           side: str, **kwargs) -> bool:
        # 实时获取分析后的 dataframe
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe.empty or len(dataframe) < 14:
            return False
        
        # 获取信号K线（最后一根已完成的K线）
        last_candle = dataframe.iloc[-1]
        prev_close = last_candle['close']
        historical_atr = last_candle['atr']
        
        # 使用 ccxt 获取当前正在形成 K 线的实时 High/Low
        current_high = rate
        current_low = rate
        try:
            exchange = self.dp._exchange._api  # ccxt 同步客户端
            ohlcv = exchange.fetch_ohlcv(pair, self.timeframe, limit=1)
            
            if ohlcv and len(ohlcv) > 0:
                # ohlcv[0] = [timestamp, open, high, low, close, volume]
                current_high = ohlcv[0][2]
                current_low = ohlcv[0][3]
                                
                # 计算当前正在形成K线的实时 True Range
                current_tr = max(
                    current_high - current_low,
                    abs(current_high - prev_close),
                    abs(current_low - prev_close)
                )
            else:
                # 回退到使用历史数据
                logger.warning(f"获取实时K线为空: {pair}")
                current_tr = last_candle['high'] - last_candle['low']
        except Exception as e:
            logger.warning(f"获取实时K线失败: {e}, 使用历史ATR")
            current_tr = last_candle['high'] - last_candle['low']
        
        # 实时 ATR: Wilder 平滑方法
        atr_period = 14
        realtime_atr = (historical_atr * (atr_period - 1) + current_tr) / atr_period
        breakout_distance = realtime_atr * self.atr_multiplier
        
        # logger.warning(f"{pair} - 当前价格: {rate} 向上触发: {current_low + breakout_distance} 向下触发: {current_high - breakout_distance}")
        
        if side == 'long':
            # 做多突破单：当前价格需要突破当前K线Low + ATR * multiplier
            breakout_price = current_low + breakout_distance
            if rate >= breakout_price:
                logger.info(f"{pair} - 做多突破触发. Price: {rate:.4f}, Breakout(Low+ATR): {breakout_price:.4f}")
                return True
            else:
                return False
                
        elif side == 'short':
            # 做空突破单：当前价格需要跌破当前K线High - ATR * multiplier
            breakout_price = current_high - breakout_distance
            if rate <= breakout_price:
                logger.info(f"{pair} - 做空突破触发. Price: {rate:.4f}, Breakout(High-ATR): {breakout_price:.4f}")
                return True
            else:
                return False
        
        return False

    def order_filled(self, pair: str, trade: Trade, order: Order, current_time: datetime, **kwargs) -> None:
        """
        订单成交回调
        """
        # 记录初始投入金额 (仅首单或数据缺失时)
        # 注意: 期货交易中 order.cost 是名义价值(含杠杆)，需要除以杠杆得到真实保证金
        if trade.nr_of_successful_entries == 1 or trade.get_custom_data('initial_stake') is None:
            actual_stake = order.cost / trade.leverage
            trade.set_custom_data(key='initial_stake', value=actual_stake)
            logger.info(f"{pair} - 记录initial_stake: order.cost={order.cost:.4f}, leverage={trade.leverage}, actual_stake={actual_stake:.4f}")
        
        # 更新 Edge Entry
        # 获取当前记录的边缘价格
        current_edge = trade.get_custom_data('edge_entry')
        
        update_edge = False
        if current_edge is None:
            update_edge = True
        else:
            if not trade.is_short:
                if order.price < current_edge:
                    update_edge = True
            else:
                if order.price > current_edge:
                    update_edge = True
        
        if update_edge:
            trade.set_custom_data(key='edge_entry', value=order.price)
            # 同步更新内存状态
            if trade.id in self.position_adjust_state:
                self.position_adjust_state[trade.id]['edge_entry'] = order.price
            
            if trade.nr_of_successful_entries == 1:
                initial_stake = trade.get_custom_data('initial_stake')
                logger.info(f"{pair} - 首次开仓完成. initial_stake={initial_stake:.4f}, edge_entry={order.price:.4f}")
            else:
                logger.info(f"{pair} - 加仓成交，更新Edge Entry: {order.price:.4f}")

    def adjust_trade_position(self, trade: Trade, current_time: datetime,
                             current_rate: float, current_profit: float,
                             min_stake: Optional[float], max_stake: float,
                             current_entry_rate: float, current_exit_rate: float,
                             current_entry_profit: float, current_exit_profit: float,
                             **kwargs) -> Optional[float]:
        """
        加仓逻辑：
        1. 当价格跌破/突破 edge_entry +/- ATR*multiplier 时，进入信号激活状态
        2. 记录触发后的极值 append_lowest/append_highest
        3. 当价格反转突破极值 +/- ATR*multiplier 时执行加仓
        4. 根据加仓次数调整仓位倍数
        """
        # 获取当前 dataframe 和 ATR
        dataframe, _ = self.dp.get_analyzed_dataframe(trade.pair, self.timeframe)
        if dataframe.empty or len(dataframe) < 14:
            return None
        
        last_candle = dataframe.iloc[-1]
        historical_atr = last_candle['atr']
        
        # 使用 ccxt 获取当前正在形成 K 线的实时 High/Low
        current_high = current_rate
        current_low = current_rate
        try:
            exchange = self.dp._exchange._api
            ohlcv = exchange.fetch_ohlcv(trade.pair, self.timeframe, limit=1)
            
            if ohlcv and len(ohlcv) > 0:
                current_high = ohlcv[0][2]
                current_low = ohlcv[0][3]
                
                prev_close = last_candle['close']
                
                current_tr = max(
                    current_high - current_low,
                    abs(current_high - prev_close),
                    abs(current_low - prev_close)
                )
            else:
                current_tr = last_candle['high'] - last_candle['low']
        except Exception as e:
            logger.warning(f"获取实时K线失败: {e}, 使用历史ATR")
            current_tr = last_candle['high'] - last_candle['low']
        
        # 实时 ATR
        atr_period = 14
        realtime_atr = (historical_atr * (atr_period - 1) + current_tr) / atr_period
        breakout_distance = realtime_atr * self.atr_multiplier
        
        trade_id = trade.id
        
        # 初始化状态
        if trade_id not in self.position_adjust_state:
            # 1. 尝试从 Custom Data 获取状态
            edge_entry = trade.get_custom_data('edge_entry')
            initial_stake = trade.get_custom_data('initial_stake')
            
            # 2. 如果缺少 critical data (如老订单或者重启后丢失)，尝试回退计算，鲁棒性！！！
            if initial_stake is None:
                # 估算初始 Stake 
                initial_stake = (self.wallets.get_total_stake_amount() / self.config['max_open_trades']) if self.config['stake_amount'] == 'unlimited' else self.config['stake_amount']
            if edge_entry is None:
                # 从历史订单重建
                filled_entries = [
                    o for o in trade.orders 
                    if o.status == 'closed' and o.side == trade.entry_side
                ]
                if not trade.is_short:
                    edge_entry = min([o.price for o in filled_entries]) if filled_entries else trade.open_rate
                else:
                    edge_entry = max([o.price for o in filled_entries]) if filled_entries else trade.open_rate

            if not trade.is_short:
                # 做多状态
                self.position_adjust_state[trade_id] = {
                    'signal_active': False,
                    'append_lowest': None,
                    'edge_entry': edge_entry,
                    'initial_stake': initial_stake,
                    'pending_reentry': False,
                }
            else:
                # 做空状态
                self.position_adjust_state[trade_id] = {
                    'signal_active': False,
                    'append_highest': None,
                    'edge_entry': edge_entry,
                    'initial_stake': initial_stake,
                    'pending_reentry': False,
                }
        
        state = self.position_adjust_state[trade_id]
        
        # ========== 检查是否有待重新入场的订单 ==========
        if state.get('pending_reentry', False):
            # [Safety Fix] 必须确保当前没有未完成的订单
            # 如果之前的超时订单因为 Partial Fill 或其他原因取消失败，这里如果不检查就会导致无限重复下单耗尽资金
            if trade.open_orders:
                logger.warning(f"{trade.pair} - 超时订单取消失败 (Count: {len(trade.open_orders)})，暂停重新入场以避免资金耗尽。")
                return None

            state['pending_reentry'] = False  # 重置标志
            stake_amount = self._calculate_position_size(trade, state['initial_stake'])
            logger.info(f"{trade.pair} - 执行重新入场加仓 (Pending Re-entry). Stake: {stake_amount}")
            return stake_amount  # 直接重新下单
        
        # ========== 做多加仓逻辑 ==========
        if not trade.is_short:
            # 1. 检查是否触发加仓信号
            if not state['signal_active']:
                trigger_price = state['edge_entry'] - breakout_distance
                if current_rate <= trigger_price:
                    # 触发加仓信号
                    state['signal_active'] = True
                    state['append_lowest'] = current_rate
                    return None  # 本次不加仓，等待反弹
            
            # 2. 加仓信号已激活，追踪最低价
            if state['signal_active']:
                # 更新最低价
                if current_rate < state['append_lowest']:
                    state['append_lowest'] = current_rate
                
                # 检查是否反弹突破
                breakout_price = state['append_lowest'] + breakout_distance
                if current_rate >= breakout_price:
                    # 执行加仓
                    logger.info(f"{trade.pair} - 做多加仓触发. Price: {current_rate:.4f}, Breakout: {breakout_price:.4f}, Lowest: {state['append_lowest']:.4f}")
                    state['signal_active'] = False  # 重置信号
                    
                    if current_rate < state['edge_entry']:
                        state['edge_entry'] = current_rate
                    
                    # 计算加仓仓位（使用初始仓位）
                    stake_amount = self._calculate_position_size(trade, state['initial_stake'])
                    entry_count = trade.nr_of_successful_entries
                    multiplier = 1.0 if entry_count < 5 else (2.0 if entry_count < 10 else (3.0 if entry_count < 15 else 4.0))
                    logger.info(f"{trade.pair} - 做多加仓下单: entry_count={entry_count}, multiplier={multiplier}, initial_stake={state['initial_stake']:.4f}, stake_amount={stake_amount:.4f}")
                    return stake_amount
        
        # ========== 做空加仓逻辑 ==========
        else:
            # 1. 检查是否触发加仓信号（价格上涨触发）
            if not state['signal_active']:
                trigger_price = state['edge_entry'] + breakout_distance
                if current_rate >= trigger_price:
                    # 触发加仓信号
                    state['signal_active'] = True
                    state['append_highest'] = current_rate
                    return None  # 本次不加仓，等待回调
            
            # 2. 加仓信号已激活，追踪最高价
            if state['signal_active']:
                # 更新最高价
                if current_rate > state['append_highest']:
                    state['append_highest'] = current_rate
                
                # 检查是否回调突破
                breakout_price = state['append_highest'] - breakout_distance
                if current_rate <= breakout_price:
                    # 执行加仓
                    logger.info(f"{trade.pair} - 做空加仓触发. Price: {current_rate:.4f}, Breakout: {breakout_price:.4f}, Highest: {state['append_highest']:.4f} (Time: {state.get('highest_time', 'N/A')})")
                    state['signal_active'] = False  # 重置信号
                    
                    if current_rate > state['edge_entry']:
                        state['edge_entry'] = current_rate
                    
                    # 计算加仓仓位（使用初始仓位）
                    stake_amount = self._calculate_position_size(trade, state['initial_stake'])
                    entry_count = trade.nr_of_successful_entries
                    multiplier = 1.0 if entry_count < 5 else (2.0 if entry_count < 10 else (3.0 if entry_count < 15 else 4.0))
                    logger.info(f"{trade.pair} - 做空加仓下单: entry_count={entry_count}, multiplier={multiplier}, initial_stake={state['initial_stake']:.4f}, stake_amount={stake_amount:.4f}")
                    return stake_amount
        
        # 更新最大浮亏
        if current_profit < 0:
            # 1. 相对仓位浮亏
            max_dd_stake_pct = abs(current_profit) * 100
            current_max_stake = trade.get_custom_data(key='max_drawdown_stake_pct', default=0.0)
            if max_dd_stake_pct > current_max_stake:
                trade.set_custom_data(key='max_drawdown_stake_pct', value=max_dd_stake_pct)
                trade.set_custom_data(key='max_drawdown_stake_time', value=current_time.isoformat())
            
            # 2. 相对总资金浮亏 (需要考虑仓位变化)
            total_funds = self.wallets.get_total_stake_amount()
            if total_funds > 0:
                current_dd_total_pct = (abs(current_profit) * trade.stake_amount / total_funds) * 100
                current_max_total = trade.get_custom_data(key='max_drawdown_total_pct', default=0.0)
                if current_dd_total_pct > current_max_total:
                    trade.set_custom_data(key='max_drawdown_total_pct', value=current_dd_total_pct)
                    trade.set_custom_data(key='max_drawdown_total_time', value=current_time.isoformat())
        
        return None

    def _calculate_position_size(self, trade: Trade, initial_stake: float) -> float:
        """
        根据加仓次数计算仓位大小
        """
        # nr_of_successful_entries 包含初始开仓，所以加仓次数 = nr_of_successful_entries
        entry_count = trade.nr_of_successful_entries
        
        if entry_count < 5:
            multiplier = 1.0
        elif entry_count < 10:
            multiplier = 2.0
        elif entry_count < 15:
            multiplier = 3.0
        else:
            multiplier = 4.0
        
        return initial_stake * multiplier

    def confirm_trade_exit(self, pair: str, trade: Trade, order_type: str, amount: float,
                          rate: float, time_in_force: str, exit_reason: str,
                          current_time: datetime, **kwargs) -> bool:
        """
        确认平仓并发送最大浮亏信息到 Telegram,同时保存到本地 CSV
        """
        # 最后更新一次最大浮亏
        current_profit = trade.calc_profit_ratio(rate)
        if current_profit < 0:
            # 1. 相对仓位浮亏
            max_dd_stake_pct = abs(current_profit) * 100
            current_max_stake = trade.get_custom_data(key='max_drawdown_stake_pct', default=0.0)
            if max_dd_stake_pct > current_max_stake:
                trade.set_custom_data(key='max_drawdown_stake_pct', value=max_dd_stake_pct)
                trade.set_custom_data(key='max_drawdown_stake_time', value=current_time.isoformat())
            
            # 2. 相对总资金浮亏
            total_funds = self.wallets.get_total_stake_amount()
            if total_funds > 0:
                current_dd_total_pct = (abs(current_profit) * trade.stake_amount / total_funds) * 100
                current_max_total = trade.get_custom_data(key='max_drawdown_total_pct', default=0.0)
                if current_dd_total_pct > current_max_total:
                    trade.set_custom_data(key='max_drawdown_total_pct', value=current_dd_total_pct)
                    trade.set_custom_data(key='max_drawdown_total_time', value=current_time.isoformat())
        
        # 读取最大浮亏数据
        max_dd_stake_pct = trade.get_custom_data(key='max_drawdown_stake_pct', default=0.0)
        max_dd_stake_time = trade.get_custom_data(key='max_drawdown_stake_time', default='N/A')
        
        # 获取记录的总资金最大浮亏
        max_dd_total_pct = trade.get_custom_data(key='max_drawdown_total_pct', default=0.0)
        max_dd_total_time = trade.get_custom_data(key='max_drawdown_total_time', default='N/A')

        side_emoji = "🟢" if not trade.is_short else "🔴"
        side_text = "做多" if not trade.is_short else "做空"
        
        # 计算仓位占比
        total_funds = self.wallets.get_total_stake_amount()
        stake_ratio = (trade.stake_amount / total_funds) if total_funds > 0 else 0
        

        message = (
            f"{side_emoji} *交易平仓* - {pair}\n"
            f"方向: {side_text}\n"
            f"开仓价: {trade.open_rate:.8f}\n"
            f"平仓价: {rate:.8f}\n"
            f"加仓次数: {trade.nr_of_successful_entries}\n"
            f"最终盈亏: {current_profit*100:.2f}%\n"
            f"仓位占比: {stake_ratio*100:.2f}%\n"
            f"最大浮亏: {max_dd_stake_pct:.2f}%\n"
            f"时间: {max_dd_stake_time}\n"
            f"总资金最大浮亏: {max_dd_total_pct:.2f}%\n"
            f"时间: {max_dd_total_time}"
        )
        
        # 发送 Telegram 消息
        if self.dp:
            self.dp.send_msg(message)
        
        return True  # 确认平仓

    def _cleanup_closed_trades(self) -> None:
        """清理已关闭交易的状态字典"""
        active_trade_ids = {trade.id for trade in Trade.get_open_trades()}
        closed_trade_ids = [
            trade_id for trade_id in self.position_adjust_state.keys()
            if trade_id not in active_trade_ids
        ]
        for trade_id in closed_trade_ids:
            del self.position_adjust_state[trade_id]
