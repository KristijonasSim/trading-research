# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
import numpy as np
import pandas as pd
import talib.abstract as ta
from freqtrade.strategy import IStrategy, informative


class BTCOvernightVolTarget(IStrategy):
    """
    BTC Overnight Vol Target.
    - Entry: 10-day rolling-max breakout on Mon/Tue/Fri at 20:00 UTC (16:00 EST)
    - Daily regime filter: only enter when daily EMA50 > EMA200 AND close > EMA50_1d
    - Exit: Mon/Tue/Wed at 14:00 UTC (10:00 EST)
    - Position sizing: inverse 90-day realized vol, V_target=25%, cap 1x for spot
    - Stoploss: ATR-based trailing (3x ATR, floored at -15%)
    """

    INTERFACE_VERSION = 3
    timeframe = '1h'
    can_short = False
    use_custom_stoploss = True

    # OKX hard-caps single-call candle history at 300, so freqtrade limits
    # startup to 5x-1 = 1499. The rolling(2160) vol calc returns NaN for the
    # first ~27 days of IS; custom_stake_amount falls back to proposed_stake
    # during that period.
    startup_candle_count: int = 1499

    stoploss = -0.99  # placeholder; real stop is custom_stoploss
    minimal_roi = {"0": 100}  # trend-following: let winners run

    @property
    def protections(self):
        return [
            {"method": "CooldownPeriod", "stop_duration_candles": 5},
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 24 * 7,
                "trade_limit": 3,
                "stop_duration_candles": 24,
                "only_per_pair": True,
            },
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 240,
                "trade_limit": 5,
                "stop_duration_candles": 24,
                "max_allowed_drawdown": 0.15,
            },
            {
                "method": "LowProfitPairs",
                "lookback_period_candles": 24 * 30,
                "trade_limit": 5,
                "stop_duration_candles": 24,
                "required_profit": 0.0,
            },
        ]

    @informative('1d')
    def populate_indicators_1d(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        dataframe['ema50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema200'] = ta.EMA(dataframe, timeperiod=200)
        return dataframe

    def populate_indicators(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        dataframe['rolling_max_10d'] = dataframe['high'].rolling(window=240).max().shift(1)

        dataframe['log_returns'] = np.log(dataframe['close'] / dataframe['close'].shift(1))
        dataframe['realized_vol_90d'] = (
            dataframe['log_returns'].rolling(window=2160).std() * np.sqrt(365 * 24)
        )

        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        dataframe.loc[
            (
                (dataframe['close'] >= dataframe['rolling_max_10d'])
                & (dataframe['date'].dt.hour == 20)
                & (dataframe['date'].dt.dayofweek.isin([0, 1, 4]))
                # Daily regime filter (from informative_1d via @informative decorator)
                & (dataframe['ema50_1d'] > dataframe['ema200_1d'])
                & (dataframe['close'] > dataframe['ema50_1d'])
                & (dataframe['volume'] > 0)
            ),
            'enter_long',
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: pd.DataFrame, metadata: dict) -> pd.DataFrame:
        dataframe.loc[
            (
                (dataframe['date'].dt.hour == 14)
                & (dataframe['date'].dt.dayofweek.isin([0, 1, 2]))
                & (dataframe['volume'] > 0)
            ),
            'exit_long',
        ] = 1
        return dataframe

    def custom_stake_amount(self, pair: str, current_time, current_rate: float,
                            proposed_stake: float, min_stake: float, max_stake: float,
                            leverage: float, entry_tag: str, side: str, **kwargs) -> float:
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        current_candle = dataframe.iloc[-1].squeeze()

        rv = current_candle['realized_vol_90d']
        if pd.isna(rv) or rv <= 0:
            return proposed_stake

        v_target = 0.25
        weight = min(1.0, v_target / rv)
        total_capital = self.wallets.get_total_stake_amount()
        return total_capital * weight

    def custom_stoploss(self, pair: str, trade, current_time, current_rate: float,
                        current_profit: float, after_fill: bool, **kwargs) -> float:
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        current_candle = dataframe.iloc[-1].squeeze()
        if pd.isna(current_candle['atr']) or current_candle['atr'] <= 0:
            return -0.15
        atr_pct = current_candle['atr'] / current_rate
        return max(-0.15, -(atr_pct * 3.0))
