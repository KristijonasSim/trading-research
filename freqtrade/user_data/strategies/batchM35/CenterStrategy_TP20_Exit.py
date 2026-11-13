# pragma pylint: disable=missing-module-docstring, invalid-name, pointless-string-statement
from __future__ import annotations
import re
from datetime import datetime
from typing import Optional
import talib.abstract as ta
import pandas as pd
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from freqtrade.persistence import Trade

class CenterStrategy_TP20_Exit(IStrategy):
    """
    CenterStrategy_TP20_Exit
    Modification:
    - Global TP 15% (678 USDT)
    - Once reached:
      1. CLOSE ALL POSITIONS immediately (Lock Profit).
      2. STOP TRADING (Block New Entries).
    """
    INTERFACE_VERSION = 3
    timeframe = "5m"
    can_short = False
    
    # --- 1. Exit Mechanism (Unified) ---
    use_exit_signal = True # Enable for custom_exit
    exit_profit_only = False
    ignore_roi_if_entry_signal = False # Disable ROI (Set to huge value, only safety net)
    
    # --- Adaptive Thresholds ---
    initial_capital = 0.0
    target_profit_ratio = 0.20  # 20% growth target
    entry_cutoff_ratio = 0.15   # Stop entering new trades at 15% growth

    # --- Adaptive Stake Settings ---
    stake_ratio = 0.15  # 15% for Entry
    so_ratio = 0.07     # 7% for DCA

    minimal_roi = {
        "0": 100.0
    }
    
    # Disable Trailing Stop (Interferes with Grid)
    trailing_stop = False
    
    # Stoploss (Emergency only)
    stoploss = -0.30
    
    # Enable Position Adjustment
    position_adjustment_enable = True
    max_entry_position_adjustment = 30
    
    # --- Capital ---
    max_capital_usage_pct = 0.95
    min_free_cash_quote = 250.0
    max_trade_exposure_quote = 5000.0
    
    # --- Hyperopt Params ---
    # Buy Step: 0.6% - 1.2%
    buy_grid_step = DecimalParameter(0.006, 0.015, default=0.008, space='buy', optimize=True)
    
    # Sell Step: Must be > Buy Step + 0.003 (Enforced in logic, here just param)
    sell_grid_step = DecimalParameter(0.010, 0.030, default=0.015, space='sell', optimize=True)
    
    # SCALED FOR 5000 USDT (High Entry, Low DCA)
    max_so_count = IntParameter(5, 20, default=12, space='buy', optimize=True)
    so_quote_amount = DecimalParameter(50.0, 500.0, default=150.0, space='buy', optimize=True)
    
    # --- Grid Config ---
    base_order_quote = 150.0
    max_tp_levels = 5
    tp_reduce_fraction = 0.20 # Reduce 20% per TP level
    
    # Order types
    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }
    
    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                            proposed_stake: float, min_stake: float, max_stake: float, 
                            leverage: float, entry_tag: Optional[str], side: str,
                            **kwargs) -> float:
        
        try:
            total_capital = self.wallets.get_total_stake_amount()
            # Calculate dynamic stake: 15% of Total Capital
            dynamic_stake = total_capital * self.stake_ratio
            return min(max(dynamic_stake, min_stake), max_stake)
        except:
            return proposed_stake

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        # Volatility & Trend
        dataframe['adx'] = ta.ADX(dataframe)
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['atr_pct'] = dataframe['atr'] / dataframe['close']
        
        dataframe['ema200'] = ta.EMA(dataframe, timeperiod=200)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # --- Entry Gates (Strict) ---
        # No entry if ADX > 25 (Strong Trend) OR ATR > 1.5% (High Vol)
        dataframe['block_entry'] = (
            (dataframe['adx'] > 25) | 
            (dataframe['atr_pct'] > 0.015)
        ).astype(int)
        
        # --- DCA Gates (Slightly looser) ---
        # Allow DCA up to ADX 30 or ATR 1.8%
        dataframe['block_dca'] = (
            (dataframe['adx'] > 30) | 
            (dataframe['atr_pct'] > 0.018)
        ).astype(int)
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        dataframe['enter_long'] = 0
        
        # --- GLOBAL STOP CHECK ---
        # If Total Equity >= 1200, DO NOT ENTER NEW TRADES
        try:
            # We can't access wallet easily in populate_entry_trend (vectorized).
            # But we can check in confirm_trade_entry.
            # Here we just generate signals as usual.
            pass
        except:
            pass
        
        # 1. Bull Dip (EMA200 support)
        dataframe.loc[
            (
                (dataframe['block_entry'] == 0) &
                (dataframe['close'] > dataframe['ema200']) &
                (dataframe['rsi'] < 55) 
            ),
            'enter_long'] = 1
            
        # 2. Bear Reversion (Deep oversold)
        dataframe.loc[
            (
                (dataframe['block_entry'] == 0) &
                (dataframe['close'] < dataframe['ema200']) &
                (dataframe['rsi'] < 35) &
                (dataframe['close'] > dataframe['ema200'] * 0.85) # Don't buy crashes > 15% below EMA
            ),
            'enter_long'] = 1
            
        return dataframe
    
    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                            time_in_force: str, current_time: datetime, entry_tag: Optional[str],
                            **kwargs) -> bool:
        """
        Check if we hit the Global Take Profit Target (Adaptive).
        If so, reject new entries.
        """
        try:
            total_realized_capital = self.wallets.get_total_stake_amount()
            
            # Initialize capital snapshot if not set
            if self.initial_capital == 0.0:
                 self.initial_capital = total_realized_capital

            # Calculate adaptive threshold: Initial * (1 + 15%)
            stop_entry_threshold = self.initial_capital * (1.0 + self.entry_cutoff_ratio)

            # If we are already above threshold, stop trading.
            if total_realized_capital >= stop_entry_threshold:
                return False
        except:
            pass
        
        return True

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        return dataframe
    
    # --- Custom Helpers ---
    def _get_cd(self, trade: Trade) -> dict:
        cd = trade.get_custom_data("grid_state")
        if not isinstance(cd, dict): cd = {}
        return cd
    
    def _set_cd(self, trade: Trade, cd: dict) -> None:
        trade.set_custom_data("grid_state", cd)
    
    # --- Core: Adjust Position (DCA + TP) ---
    def adjust_trade_position(self, trade: Trade, current_time: datetime, current_rate: float, 
                              current_profit: float, min_stake: float, max_stake: float, **kwargs) -> Optional[float]:
        
        # --- Update Enter Tag with Amount for UI ---
        try:
            tag = trade.enter_tag or ""
            amt_str = f"Amt:{trade.stake_amount:.1f}"
            
            if "Amt:" in tag:
                # Update existing
                new_tag = re.sub(r"Amt:[\d\.]+", amt_str, tag)
            else:
                # Append new
                new_tag = f"{tag} {amt_str}".strip()
            
            # Limit length to avoid DB errors (usually 255 chars)
            if len(new_tag) > 255:
                new_tag = new_tag[:255]

            if tag != new_tag:
                trade.enter_tag = new_tag
        except Exception:
            pass

        if self.dp:
            dataframe, _ = self.dp.get_analyzed_dataframe(trade.pair, self.timeframe)
            if dataframe is None or len(dataframe) < 1: return None
            last_candle = dataframe.iloc[-1]
        else:
            return None

        # Throttle: 1 adjustment per candle
        cd = self._get_cd(trade)
        last_adj_time = cd.get("last_adj_time", 0)
        current_candle_time = int(last_candle['date'].timestamp())
        
        if last_adj_time == current_candle_time:
            return None # Already adjusted in this candle

        # Initialize
        if "base_price" not in cd:
            cd["base_price"] = float(trade.open_rate)
            cd["so_count"] = 0
            cd["tp_count"] = 0
            
            # Enforce Spread Constraint: Sell Step >= Buy Step + 0.006 (Updated Buffer)
            buy_step = self.buy_grid_step.value
            sell_step = max(self.sell_grid_step.value, buy_step + 0.006) # Hard Buffer 0.6%
            
            cd["buy_step"] = buy_step
            cd["sell_step"] = sell_step
            
            cd["next_buy"] = cd["base_price"] * (1.0 - buy_step)
            cd["next_sell"] = cd["base_price"] * (1.0 + sell_step)
            
            cd["last_adj_time"] = current_candle_time
            self._set_cd(trade, cd)
            return None
            
        # --- CRITICAL FIX: Reset next_sell if Average Price Moved ---
        sell_step = cd["sell_step"]
        target_sell_price = float(trade.open_rate) * (1.0 + sell_step)
        
        if cd["next_sell"] > target_sell_price:
            cd["next_sell"] = target_sell_price
        
        buy_step = cd["buy_step"]
        
        # 1. DCA (Safety Order)
        so_count = cd["so_count"]
        next_buy = cd["next_buy"]
        
        if current_rate <= next_buy and so_count < self.max_so_count.value:
            # Check Gates
            if last_candle['block_dca'] == 1:
                return None # Market too dangerous for DCA
                
            # Equal Amount DCA (Linear)
            # so_stake = self.so_quote_amount.value
            
            # --- ADAPTIVE DCA: 3% of Total Capital ---
            try:
                total_capital = self.wallets.get_total_stake_amount()
                so_stake = total_capital * self.so_ratio
            except:
                so_stake = self.so_quote_amount.value

            # Update State
            cd["so_count"] += 1
            cd["next_buy"] = next_buy * (1.0 - buy_step)
            
            # Important: Update last_adj
            cd["last_adj_time"] = current_candle_time
            self._set_cd(trade, cd)
            return so_stake
            
        # 2. TP (Partial Reduce)
        tp_count = cd["tp_count"]
        next_sell = cd["next_sell"]
        
        if current_rate >= next_sell and tp_count < self.max_tp_levels:
            # Reduce
            current_value = trade.amount * current_rate
            reduce_amt = current_value * self.tp_reduce_fraction
            
            if reduce_amt < min_stake: return None
            
            # Update State
            cd["tp_count"] += 1
            cd["next_sell"] = next_sell * (1.0 + sell_step)
            
            # Trailing Buy: Pull up buy level to follow price
            new_buy = current_rate * (1.0 - buy_step)
            if new_buy > cd["next_buy"]:
                cd["next_buy"] = new_buy
                
            cd["last_adj_time"] = current_candle_time
            self._set_cd(trade, cd)
            return -reduce_amt
            
        return None
        
    # --- Final Exit (Cleanup) ---
    def custom_exit(self, pair: str, trade: Trade, current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs):
        
        # --- NEW: Portfolio Level Take Profit (Adaptive Target) ---
        try:
            # 1. Calculate Unrealized Profit of current trade
            current_value = trade.amount * current_rate
            cost_basis = trade.amount * trade.open_rate
            current_profit_abs = current_value - cost_basis
            
            # 2. Get Total Realized Capital (Wallet Balance)
            total_realized_capital = self.wallets.get_total_stake_amount()
            
            # Initialize capital snapshot if not set (Safety)
            if self.initial_capital == 0.0:
                 self.initial_capital = total_realized_capital
            
            # 3. Calculate Total Equity
            total_equity = total_realized_capital + current_profit_abs
            
            # 4. Check Adaptive Target (Initial * 1.20)
            target_equity = self.initial_capital * (1.0 + self.target_profit_ratio)
            
            if total_equity >= target_equity:
                return "portfolio_tp_adaptive_stop"
                
        except Exception:
            pass

        cd = self._get_cd(trade)
        tp_count = cd.get("tp_count", 0)
        
        # 1. Finished Task: Max TP levels reached
        if tp_count >= self.max_tp_levels and current_profit > 0.005:
            return "grid_finished"
            
        # 2. Mean Reversion Complete: Price back above EMA200
        # Only if we hold significant bag (so_count > 0)
        if self.dp:
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            last_candle = dataframe.iloc[-1]
            if (
                cd.get("so_count", 0) > 2 and 
                current_rate > last_candle['ema200'] and 
                current_profit > 0.01
            ):
                return "grid_mean_reversion_done"
                
        # 3. Zombie Cleanup (Optional)
        # If held > 48h and profit > 0 (breakeven), exit to free capital
        duration_hrs = (current_time - trade.open_date_utc).total_seconds() / 3600
        if duration_hrs > 48 and current_profit > 0.002:
            return "zombie_cleanup"
            
        return None
