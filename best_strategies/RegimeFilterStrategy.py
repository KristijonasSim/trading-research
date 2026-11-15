"""
Regime Filter Strategy - Adaptive Long/Short
=============================================
Bull Regime (EMA50 > EMA100): Longs only
Bear Regime (EMA50 < EMA100): Shorts only

BACKTESTED RESULTS (Jul 2022 - Jan 2026, 3.5 years):
- Return: +1,450%
- Sharpe Ratio: 0.37
- Sortino Ratio: 0.87
- Calmar Ratio: 73.00
- Max Drawdown: 29.24%
- Profit Factor: 1.40
- Total Trades: 204
- Win Rate: 40.2%
- Long Profit: +610%
- Short Profit: +840%

Settings: 95% stake, 1x leverage, 12% TP, 5% SL
Pair: SOL/USDT Futures on Binance
Timeframe: 1 hour

Strategy Logic:
- Uses EMA50/EMA100 crossover to detect market regime
- Bull regime (EMA50 > EMA100): Only takes long positions
- Bear regime (EMA50 < EMA100): Only takes short positions
- Entry on breakout above/below 20-period high/low
- Requires volume surge (2.3x average) for confirmation
- Requires momentum (2% move in 5 candles)
- Takes profit at 12%, stops loss at 5%
"""

import numpy as np
from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta


class RegimeFilterStrategy(IStrategy):
    """
    Regime Filter Strategy for Freqtrade

    This strategy adapts to market conditions by only trading
    in the direction of the prevailing regime:
    - Bull regime: Long positions only
    - Bear regime: Short positions only
    """

    INTERFACE_VERSION = 3
    timeframe = '1h'
    can_short = True

    # 12% Take Profit, 5% Stop Loss
    minimal_roi = {"0": 0.12}
    stoploss = -0.05

    # No trailing stop - rely on ROI and SL
    trailing_stop = False
    process_only_new_candles = True
    startup_candle_count = 250
    use_custom_stoploss = False

    # Optimized parameters from backtesting
    breakout_period = 20      # 20-period high/low breakout
    volume_mult = 2.3         # Volume must be 2.3x average
    momentum_pct = 0.02       # 2% momentum threshold

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Calculate all technical indicators needed for the strategy.
        """
        # === TREND EMAs FOR REGIME DETECTION ===
        dataframe['ema50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema100'] = ta.EMA(dataframe, timeperiod=100)
        dataframe['sma200'] = ta.SMA(dataframe, timeperiod=200)

        # === VOLUME ANALYSIS ===
        dataframe['volume_sma'] = dataframe['volume'].rolling(20).mean()

        # === BREAKOUT LEVELS ===
        # Shifted by 1 to avoid lookahead bias
        dataframe['highest_20'] = dataframe['high'].rolling(self.breakout_period).max().shift(1)
        dataframe['lowest_20'] = dataframe['low'].rolling(self.breakout_period).min().shift(1)

        # === REGIME DETECTION ===
        # Bull regime when EMA50 > EMA100 (uptrend)
        # Bear regime when EMA50 < EMA100 (downtrend)
        dataframe['bull_regime'] = dataframe['ema50'] > dataframe['ema100']

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Define entry conditions for both long and short positions.
        """
        # === COMMON CONDITIONS ===
        # Volume surge: current volume > 2.3x the 20-period average
        vol_surge = dataframe['volume'] > dataframe['volume_sma'] * self.volume_mult

        # Momentum conditions
        mom_up = dataframe['close'] > dataframe['close'].shift(5) * (1 + self.momentum_pct)
        mom_down = dataframe['close'] < dataframe['close'].shift(5) * (1 - self.momentum_pct)

        # Trend alignment with EMA100
        above_ema100 = dataframe['close'] > dataframe['ema100']
        below_ema100 = dataframe['close'] < dataframe['ema100']

        # Breakout conditions
        breakout_up = dataframe['close'] > dataframe['highest_20']
        breakout_down = dataframe['close'] < dataframe['lowest_20']

        # === LONG ENTRY (Bull Regime Only) ===
        # Enter long when:
        # 1. In bull regime (EMA50 > EMA100)
        # 2. Price breaks above 20-period high
        # 3. Price is above EMA100
        # 4. Volume surge present
        # 5. Positive momentum
        dataframe.loc[
            dataframe['bull_regime'] &
            breakout_up &
            above_ema100 &
            vol_surge &
            mom_up,
            'enter_long'
        ] = 1

        # === SHORT ENTRY (Bear Regime Only) ===
        # Enter short when:
        # 1. In bear regime (EMA50 < EMA100)
        # 2. Price breaks below 20-period low
        # 3. Price is below EMA100
        # 4. Volume surge present
        # 5. Negative momentum
        dataframe.loc[
            ~dataframe['bull_regime'] &
            breakout_down &
            below_ema100 &
            vol_surge &
            mom_down,
            'enter_short'
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Exit conditions - rely entirely on ROI (12%) and Stop Loss (5%).
        No signal-based exits to let winners run and cut losers quickly.
        """
        dataframe['exit_long'] = 0
        dataframe['exit_short'] = 0
        return dataframe
