import logging
from functools import reduce
import numpy as np
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IStrategy, merge_informative_pair
from freqtrade.persistence import Trade
try:
    from technical import qtpylib
except ImportError:
    import freqtrade.vendor.qtpylib.indicators as qtpylib

logger = logging.getLogger(__name__)


class FreqaiReinforcementStrategy(IStrategy):
    """
    FreqAI Reinforcement Learning Strategy (Stable-Baselines3)
    Designed for adaptive trading on 30 USDT pairs with realistic fee & slippage modeling.
    """
    # Strategy parameters optimized for positive Risk-to-Reward (RR > 1:1.6)
    minimal_roi = {
        "0": 0.05,
        "30": 0.035,
        "60": 0.02,
        "120": 0.015
    }

    # Stoploss tightened to -2.5% to preserve capital
    stoploss = -0.025

    # Trailing Stoploss & Break-Even Locking
    trailing_stop = True
    trailing_stop_positive = 0.012         # Activate trailing stop when profit hits +1.2%
    trailing_stop_positive_offset = 0.020  # Trigger offset when profit hits +2.0%
    trailing_only_offset_is_reached = True # Keep SL active until offset is reached

    # Optimal timeframe for AI feature extraction
    timeframe = '5m'

    # Process 30 pairs with up to 4 open trades concurrently
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # Startup candle count required for FreqAI feature engineering (500 5m candles = ~1.7 days)
    startup_candle_count: int = 500

    def custom_stake_amount(self, pair: str, current_time, current_rate: float,
                            proposed_stake: float, min_stake: float | None, max_stake: float,
                            leverage: float, entry_tag: str | None, side: str,
                            **kwargs) -> float:
        """
        Dynamic stake calculation based on 24h Volume Rank Tier & Total Wallet Balance:
        - Tier 1 (Rank 1-10): 16% of capital (~$160 for $1000 wallet)
        - Tier 2 (Rank 11-20): 5.5% of capital (~$55 for $1000 wallet)
        - Tier 3 (Rank 21-30): 3.5% of capital (~$35 for $1000 wallet)
        Autocompounds automatically as wallet grows.
        """
        try:
            total_wallet = self.wallets.get_total_stake_amount()
            whitelist = self.dp.current_whitelist()
            
            rank = 99
            if pair in whitelist:
                rank = whitelist.index(pair) + 1
                
            if rank <= 10:
                stake_ratio = 0.160
            elif rank <= 20:
                stake_ratio = 0.055
            else:
                stake_ratio = 0.035
                
            calculated_stake = total_wallet * stake_ratio
            if min_stake is not None:
                calculated_stake = max(calculated_stake, min_stake)
            return min(calculated_stake, max_stake)
        except Exception as e:
            logger.warning(f"Error calculating custom stake for {pair}: {e}")
            return 50.0

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                            time_in_force: str, current_time, entry_tag: str | None,
                            side: str, **kwargs) -> bool:
        """
        Enforces maximum concurrent position slots per volume tier:
        - Top 1-10 (Mega Cap): Max 5 concurrent trades
        - Top 11-30 (Altcoins): Max 10 concurrent trades
        Total Max Open Trades across all pairs: 12
        """
        try:
            # Use Trade.get_open_trades() — correct API for Freqtrade 2026.x
            open_trades = Trade.get_open_trades()
            whitelist = self.dp.current_whitelist()
            
            rank = 99
            if pair in whitelist:
                rank = whitelist.index(pair) + 1
                
            top10_open_count = 0
            altcoin_open_count = 0
            
            for trade in open_trades:
                trade_rank = 99
                if trade.pair in whitelist:
                    trade_rank = whitelist.index(trade.pair) + 1
                if trade_rank <= 10:
                    top10_open_count += 1
                else:
                    altcoin_open_count += 1

            if rank <= 10 and top10_open_count >= 5:
                logger.info(f"Rejecting entry for {pair}: Top 10 max slots limit reached ({top10_open_count}/5).")
                return False
                
            if rank > 10 and altcoin_open_count >= 10:
                logger.info(f"Rejecting entry for {pair}: Altcoin max slots limit reached ({altcoin_open_count}/10).")
                return False

            return True
        except Exception as e:
            logger.warning(f"Error in confirm_trade_entry for {pair}: {e}")
            return True

    def custom_entry_price(self, pair: str, current_time, proposed_rate: float,
                           entry_tag: str | None, side: str, **kwargs) -> float:
        """
        Calculates 100% dynamic orderbook entry execution price based on live orderbook depth asks queue.
        Calculates weighted average price to reflect real market orderbook slippage.
        """
        try:
            ob_depth = self.dp.orderbook(pair, 5)
            asks = ob_depth.get('asks', [])
            
            if asks and len(asks) > 0:
                best_ask = asks[0][0]
                total_cost = 0.0
                total_qty = 0.0
                for price, qty in asks[:5]:
                    total_cost += price * qty
                    total_qty += qty
                
                if total_qty > 0:
                    weighted_avg = total_cost / total_qty
                    realized_price = (best_ask * 0.70) + (weighted_avg * 0.30)
                    return max(proposed_rate, realized_price)
            return proposed_rate
        except Exception as e:
            return proposed_rate

    def custom_exit_price(self, pair: str, trade, current_time, proposed_rate: float,
                          current_profit: float, exit_tag: str | None, **kwargs) -> float:
        """
        Calculates 100% dynamic orderbook exit execution price based on live orderbook depth bids queue.
        """
        try:
            ob_depth = self.dp.orderbook(pair, 5)
            bids = ob_depth.get('bids', [])
            
            if bids and len(bids) > 0:
                best_bid = bids[0][0]
                total_cost = 0.0
                total_qty = 0.0
                for price, qty in bids[:5]:
                    total_cost += price * qty
                    total_qty += qty
                
                if total_qty > 0:
                    weighted_avg = total_cost / total_qty
                    realized_price = (best_bid * 0.70) + (weighted_avg * 0.30)
                    return min(proposed_rate, realized_price)
            return proposed_rate
        except Exception as e:
            return proposed_rate

    def feature_engineering_expand_all(self, dataframe: DataFrame, period: int, metadata: dict, **kwargs) -> DataFrame:
        """
        Calculates indicators for FreqAI feature engineering.
        """
        # RSI
        dataframe[f"%-rsi-period_{period}"] = ta.RSI(dataframe, timeperiod=period)
        
        # MFI (Money Flow Index)
        dataframe[f"%-mfi-period_{period}"] = ta.MFI(dataframe, timeperiod=period)
        
        # EMA ratio
        ema = ta.EMA(dataframe, timeperiod=period)
        dataframe[f"%-ema_ratio-period_{period}"] = dataframe['close'] / ema - 1.0

        # Bollinger Bands ratio
        bollinger = qtpylib.bollinger_bands(dataframe['close'], window=period, stds=2)
        dataframe[f"%-bb_lowerbound-period_{period}"] = bollinger['lower']
        dataframe[f"%-bb_upperbound-period_{period}"] = bollinger['upper']
        dataframe[f"%-bb_width-period_{period}"] = (bollinger['upper'] - bollinger['lower']) / bollinger['mid']

        # ATR / Close (Volatility)
        dataframe[f"%-atr_ratio-period_{period}"] = ta.ATR(dataframe, timeperiod=period) / dataframe['close']

        return dataframe

    def feature_engineering_expand_basic(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        """
        Basic single-period features
        """
        dataframe["%-pct_change"] = dataframe["close"].pct_change()
        dataframe["%-raw_volume"] = dataframe["volume"]
        dataframe["%-raw_close"] = dataframe["close"]
        return dataframe

    def feature_engineering_standard(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        """
        Calculates standard features across multiple periods
        """
        for period in [5, 14, 30]:
            dataframe = self.feature_engineering_expand_all(dataframe, period, metadata, **kwargs)

        dataframe = self.feature_engineering_expand_basic(dataframe, metadata, **kwargs)
        return dataframe

    def set_freqai_targets(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        """
        Defines the target variable for FreqAI (Future Return over 12 candles)
        """
        dataframe["&-target"] = (
            dataframe["close"].shift(-12) / dataframe["close"] - 1.0
        )
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populates indicators and executes FreqAI feature pipeline.
        """
        try:
            # FreqAI feature population
            dataframe = self.freqai.start(dataframe, metadata, self)
        except Exception as e:
            logger.warning(f"FreqAI calculation skipped for pair {metadata.get('pair')}: {e}")
            dataframe['&-target'] = 0.0
            dataframe['do_predict'] = 0

        # Basic indicators for fallback / confirmation
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['ema_50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Entry signals based on FreqAI model prediction
        """
        enter_long_conditions = [
            # FreqAI prediction target return > 0.0008 (expected > +0.08% return over 12 candles)
            # Dilonggarkan dari 0.0015 agar lebih banyak sinyal lolos setelah DI filtering
            dataframe['&-target'] > 0.0008,
            # Data is valid & not outlier
            dataframe['do_predict'] == 1,
            dataframe['volume'] > 0
        ]

        if enter_long_conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, enter_long_conditions),
                'enter_long'
            ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Exit signals based on FreqAI prediction or risk limits
        """
        exit_long_conditions = [
            # Prediction turns negative (target return < -0.005)
            dataframe['&-target'] < -0.005,
            dataframe['do_predict'] == 1
        ]

        if exit_long_conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, exit_long_conditions),
                'exit_long'
            ] = 1

        return dataframe
