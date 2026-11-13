"""
E0V1E_LongShort Strategy (Improved)
====================================
Based on E0V1E + E0V1EN backtest results analysis:
- buy_new performed better than buy_1 (+15% vs -23% in 2024)
- Added time-based exits from E0V1EN
- Added 24h price change filter
- Refined short entry conditions
- Added CooldownPeriod protection

Long Entry: RSI oversold + price below SMA (mean reversion)
Short Entry: RSI overbought + price above SMA (mean reversion)
"""

from datetime import datetime, timedelta
import talib.abstract as ta
import pandas_ta as pta
from freqtrade.persistence import Trade
from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
from freqtrade.strategy import DecimalParameter, IntParameter
from functools import reduce
import warnings

warnings.simplefilter(action="ignore", category=RuntimeWarning)


class E0V1E_LongShort(IStrategy):
    minimal_roi = {"0": 1}
    timeframe = '5m'
    process_only_new_candles = True
    startup_candle_count = 300  # 288 for 24h + buffer

    can_short = True

    order_types = {
        'entry': 'market',
        'exit': 'market',
        'emergency_exit': 'market',
        'force_entry': 'market',
        'force_exit': "market",
        'stoploss': 'market',
        'stoploss_on_exchange': False,
        'stoploss_on_exchange_interval': 60,
        'stoploss_on_exchange_market_ratio': 0.99
    }

    # Tighter stoploss than original -25% (reduces big losses)
    stoploss = -0.15
    trailing_stop = True
    trailing_stop_positive = 0.002
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True

    # ============ LONG PARAMETERS ============
    # Based on buy_new success (better than buy_1)
    is_optimize_long = True
    buy_rsi_fast = IntParameter(20, 50, default=34, space='buy', optimize=is_optimize_long)
    buy_rsi_min = IntParameter(15, 40, default=28, space='buy', optimize=is_optimize_long)
    buy_sma15 = DecimalParameter(0.93, 0.99, default=0.96, decimals=3, space='buy', optimize=is_optimize_long)
    buy_cti = DecimalParameter(-1, 1, default=0.69, decimals=2, space='buy', optimize=is_optimize_long)

    # 24h price change filter (from E0V1EN)
    buy_24h_min_pct = DecimalParameter(-30.0, 0.0, default=-15.0, decimals=1, space='buy', optimize=True)
    buy_24h_max_pct = DecimalParameter(0.0, 100.0, default=50.0, decimals=1, space='buy', optimize=True)

    # ============ SHORT PARAMETERS ============
    # Stricter conditions to only short in true overbought zones
    is_optimize_short = True
    sell_rsi_fast = IntParameter(65, 90, default=75, space='sell', optimize=is_optimize_short)
    sell_rsi_min = IntParameter(55, 80, default=65, space='sell', optimize=is_optimize_short)  # Add RSI lower bound
    sell_rsi_max = IntParameter(70, 90, default=80, space='sell', optimize=is_optimize_short)
    sell_sma15 = DecimalParameter(1.02, 1.10, default=1.05, decimals=3, space='sell', optimize=is_optimize_short)
    sell_cti_min = DecimalParameter(0.0, 0.8, default=0.3, decimals=2, space='sell', optimize=is_optimize_short)  # CTI positive range only

    # 24h price change filter for shorts
    sell_24h_min_pct = DecimalParameter(-50.0, 50.0, default=10.0, decimals=1, space='sell', optimize=True)
    sell_24h_max_pct = DecimalParameter(50.0, 200.0, default=100.0, decimals=1, space='sell', optimize=True)

    # ============ EXIT PARAMETERS ============
    exit_fastx_long = IntParameter(50, 100, default=84, space='sell', optimize=True)
    exit_fastx_short = IntParameter(0, 50, default=16, space='sell', optimize=True)

    exit_cci_long = IntParameter(50, 150, default=80, space='sell', optimize=True)
    exit_cci_short = IntParameter(-150, -50, default=-80, space='sell', optimize=True)

    @property
    def protections(self):
        return [
            {
                "method": "CooldownPeriod",
                "stop_duration_candles": 96  # 8 hours cooldown
            }
        ]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # RSI indicators
        dataframe['sma_15'] = ta.SMA(dataframe, timeperiod=15)
        dataframe['cti'] = pta.cti(dataframe["close"], length=20)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['rsi_fast'] = ta.RSI(dataframe, timeperiod=4)
        dataframe['rsi_slow'] = ta.RSI(dataframe, timeperiod=20)

        # 24h price change (288 candles = 24h for 5m timeframe)
        dataframe['24h_change_pct'] = (dataframe['close'].pct_change(periods=288) * 100)

        # Exit indicators
        stoch_fast = ta.STOCHF(dataframe, 5, 3, 0, 3, 0)
        dataframe['fastk'] = stoch_fast['fastk']
        dataframe['cci'] = ta.CCI(dataframe, timeperiod=20)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'enter_tag'] = ''

        # ============ LONG ENTRY ============
        # Based on buy_new logic (performed better in backtest)
        long_conditions = (
            (dataframe['rsi_slow'] < dataframe['rsi_slow'].shift(1)) &  # RSI declining (momentum weakening)
            (dataframe['rsi_fast'] < self.buy_rsi_fast.value) &         # Fast RSI oversold
            (dataframe['rsi'] > self.buy_rsi_min.value) &               # But not too extreme (avoid falling knife)
            (dataframe['close'] < dataframe['sma_15'] * self.buy_sma15.value) &  # Price below SMA
            (dataframe['cti'] < self.buy_cti.value) &                   # CTI filter
            (dataframe['24h_change_pct'] > self.buy_24h_min_pct.value) &  # 24h change filter
            (dataframe['24h_change_pct'] < self.buy_24h_max_pct.value)
        )

        dataframe.loc[long_conditions, 'enter_long'] = 1
        dataframe.loc[long_conditions, 'enter_tag'] = 'long_mean_reversion'

        # ============ SHORT ENTRY ============
        # Stricter conditions: only short in true overbought zones
        short_conditions = (
            (dataframe['rsi_slow'] > dataframe['rsi_slow'].shift(1)) &  # RSI rising (momentum increasing)
            (dataframe['rsi_fast'] > self.sell_rsi_fast.value) &        # Fast RSI overbought (75+)
            (dataframe['rsi'] > self.sell_rsi_min.value) &              # RSI lower bound (65+) - confirm overbought
            (dataframe['rsi'] < self.sell_rsi_max.value) &              # RSI upper bound (80-) - avoid extremes
            (dataframe['close'] > dataframe['sma_15'] * self.sell_sma15.value) &  # Price above SMA (5%+)
            (dataframe['cti'] > self.sell_cti_min.value) &              # CTI positive range only (0.3+)
            (dataframe['24h_change_pct'] > self.sell_24h_min_pct.value) &  # 24h filter for shorts
            (dataframe['24h_change_pct'] < self.sell_24h_max_pct.value)
        )

        dataframe.loc[short_conditions, 'enter_short'] = 1
        dataframe.loc[short_conditions, 'enter_tag'] = 'short_mean_reversion'

        return dataframe

    def custom_exit(self, pair: str, trade: Trade, current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs):
        dataframe, _ = self.dp.get_analyzed_dataframe(pair=pair, timeframe=self.timeframe)
        current_candle = dataframe.iloc[-1].squeeze()

        if trade.is_short:
            # ============ SHORT EXIT LOGIC ============
            # Take profit when oversold (price likely to bounce)
            if current_profit > 0:
                if current_candle["fastk"] < self.exit_fastx_short.value:
                    return "fastk_profit_exit_short"

            # CCI exit for shorts (oversold = time to cover)
            if current_profit > -0.03:
                if current_candle["cci"] < self.exit_cci_short.value:
                    return "cci_exit_short"

            # Time-based exits for shorts (from E0V1EN)
            if current_time - timedelta(hours=7) > trade.open_date_utc:
                if current_profit >= -0.05:
                    return "time_exit_short_7h"

            if current_time - timedelta(hours=10) > trade.open_date_utc:
                if current_profit >= -0.10:
                    return "time_exit_short_10h"

        else:
            # ============ LONG EXIT LOGIC ============
            # Take profit when overbought
            if current_profit > 0:
                if current_candle["fastk"] > self.exit_fastx_long.value:
                    return "fastk_profit_exit_long"

            # CCI exit for longs (overbought = time to sell)
            if current_profit > -0.03:
                if current_candle["cci"] > self.exit_cci_long.value:
                    return "cci_exit_long"

            # Time-based exits for longs (from E0V1EN)
            if current_time - timedelta(hours=7) > trade.open_date_utc:
                if current_profit >= -0.05:
                    return "time_exit_long_7h"

            if current_time - timedelta(hours=10) > trade.open_date_utc:
                if current_profit >= -0.10:
                    return "time_exit_long_10h"

        return None

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'exit_long'] = 0
        dataframe.loc[:, 'exit_short'] = 0
        return dataframe
