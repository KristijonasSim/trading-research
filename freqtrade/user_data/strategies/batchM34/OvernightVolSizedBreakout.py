# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
import numpy as np
import pandas as pd
import talib.abstract as ta
from freqtrade.strategy import IStrategy


class OvernightVolSizedBreakout(IStrategy):
    """
    Overnight Session Breakout + Volatility-Aware Position Sizing.
    Lineage: Dujava (2024), Zarattini et al. (2025), Chan, Kaufman.
    """

    INTERFACE_VERSION = 3
    timeframe = '1h'
    can_short = False

    # Spec called for 2160 (90 days). OKX hardcodes per-call limit at 300 candles,
    # so freqtrade caps startup at 5*300-1 = 1499. The rolling(2160) vol calc still
    # works once 2160 candles accumulate into IS (~27 days in). Until then,
    # custom_stake_amount falls back to proposed_stake.
    startup_candle_count: int = 1499

    stoploss = -0.99
    minimal_roi = {"0": 100}

    @property
    def protections(self):
        return [
            {"method": "CooldownPeriod", "stop_duration_candles": 5},
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 240,
                "trade_limit": 5,
                "stop_duration_candles": 24,
                "max_allowed_drawdown": 0.15,
            },
        ]

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

        if pd.isna(current_candle['realized_vol_90d']) or current_candle['realized_vol_90d'] <= 0:
            return proposed_stake

        v_target = 0.25
        vol_scale = v_target / current_candle['realized_vol_90d']

        max_leverage = 1.0
        weight = min(max_leverage, vol_scale)

        total_capital = self.wallets.get_total_stake_amount()
        return total_capital * weight

    def custom_stoploss(self, pair: str, trade, current_time, current_rate: float,
                        current_profit: float, after_fill: bool, **kwargs) -> float:
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        current_candle = dataframe.iloc[-1].squeeze()

        atr_pct = (current_candle['atr'] / current_rate)

        return max(-0.15, -(atr_pct * 3.0))
