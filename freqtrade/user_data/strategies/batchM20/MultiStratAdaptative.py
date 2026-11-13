#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MultiStratAdaptive — stratégie compilée et adaptative pour Freqtrade

Combine Supertrend, RSI/EMA (v4 & v5) et un module simple de price-action.
Bascule automatiquement selon le régime de marché détecté en 1h (trend/range).
Utilise merge_informative_pair pour fiabiliser l'alignement 5m ⇄ 1h.
"""
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from pandas import DataFrame, Series

from freqtrade.strategy import (
    IStrategy,
    IntParameter,
    DecimalParameter,
    CategoricalParameter,
    merge_informative_pair,
)
import talib.abstract as ta


class MultiStratAdaptive(IStrategy):
    timeframe = '5m'
    informative_timeframe = '1h'
    startup_candle_count: int = 240

    # ROI/SL — on gère réellement via custom_stoploss
    minimal_roi = {"0": 1000}
    stoploss = -0.20

    # Trailing doux (affiné dans custom_stoploss)
    trailing_stop = True
    trailing_only_offset_is_reached = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02

    # Hyperparams simples (hyperoptables)
    atr_mult_sl = DecimalParameter(1.0, 3.0, default=1.8, space='sell', decimals=1)
    adx_trend = IntParameter(15, 30, default=20, space='buy')
    bb_width_range = DecimalParameter(0.05, 0.12, default=0.08, space='buy', decimals=3)

    BAD_PAIRS: List[str] = [
        'AI16Z/USDT', 'FARTCOIN/USDT', 'XTZ/USDT', 'DOGE/USDT', 'TRUMP/USDT'
    ]

    MAX_CONSECUTIVE_LOSSES = 3
    DISABLE_FOR_HOURS = 6

    custom_info: Dict = {}
    use_custom_stoploss = True

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        return [(p, self.informative_timeframe) for p in pairs]

    def populate_indicators(self, df: DataFrame, metadata: dict) -> DataFrame:
        pair = metadata['pair']

        # Flag paires à éviter
        df['bad_pair'] = pair in self.BAD_PAIRS

        # === Indicateurs 5m ===
        df['ema50'] = ta.EMA(df, timeperiod=50)
        df['ema200'] = ta.EMA(df, timeperiod=200)
        df['rsi'] = ta.RSI(df, timeperiod=14)
        df['atr'] = ta.ATR(df, timeperiod=14)
        df['adx'] = ta.ADX(df, timeperiod=14)

        # Supertrend (implémentation simple)
        atr10 = ta.ATR(df, timeperiod=10)
        factor = 3.0
        hl2 = (df['high'] + df['low']) / 2
        basic_ub = hl2 + factor * atr10
        basic_lb = hl2 - factor * atr10
        final_ub = basic_ub.copy()
        final_lb = basic_lb.copy()
        st = Series(index=df.index, dtype=float)
        for i in range(len(df)):
            if i == 0:
                st.iloc[i] = basic_lb.iloc[i]
                continue
            final_ub.iloc[i] = min(basic_ub.iloc[i], final_ub.iloc[i-1]) if df['close'].iloc[i-1] > final_ub.iloc[i-1] else basic_ub.iloc[i]
            final_lb.iloc[i] = max(basic_lb.iloc[i], final_lb.iloc[i-1]) if df['close'].iloc[i-1] < final_lb.iloc[i-1] else basic_lb.iloc[i]
            if st.iloc[i-1] == final_ub.iloc[i-1] and df['close'].iloc[i] <= final_ub.iloc[i]:
                st.iloc[i] = final_ub.iloc[i]
            elif st.iloc[i-1] == final_ub.iloc[i-1] and df['close'].iloc[i] > final_ub.iloc[i]:
                st.iloc[i] = final_lb.iloc[i]
            elif st.iloc[i-1] == final_lb.iloc[i-1] and df['close'].iloc[i] >= final_lb.iloc[i]:
                st.iloc[i] = final_lb.iloc[i]
            elif st.iloc[i-1] == final_lb.iloc[i-1] and df['close'].iloc[i] < final_lb.iloc[i]:
                st.iloc[i] = final_ub.iloc[i]
            else:
                st.iloc[i] = final_lb.iloc[i]
        df['supertrend'] = st
        df['supertrend_long'] = df['close'] > df['supertrend']

        # === Informative 1h (robuste avec merge_informative_pair) ===
        inf = self.dp.get_pair_dataframe(pair=pair, timeframe=self.informative_timeframe)
        if inf is None or inf.empty:
            for c in ['ema200_1h','ema50_1h','adx_1h','bb_width_1h','ema200_slope_1h']:
                df[c] = np.nan
        else:
            # TA-Lib renvoie des numpy.ndarray — éviter .replace sur ndarray
            inf['ema200'] = ta.EMA(inf, timeperiod=200)
            inf['ema50']  = ta.EMA(inf, timeperiod=50)
            inf['adx']    = ta.ADX(inf, timeperiod=14)
            up, mid, lo   = ta.BBANDS(inf['close'], timeperiod=20, nbdevup=2.0, nbdevdn=2.0)
            mid_safe = np.where(mid == 0, np.nan, mid)
            # bb_width = (upper - lower) / middle
            inf['bb_width'] = (up - lo) / mid_safe
            inf['ema200_slope'] = inf['ema200'].diff()

            df = merge_informative_pair(
                df,
                inf[['date','ema200','ema50','adx','bb_width','ema200_slope']],
                self.timeframe,
                self.informative_timeframe,
                ffill=True,
            )

        # Régime de marché depuis les colonnes suffixées _1h
        df['is_trend'] = (df.get('adx_1h', np.nan) >= self.adx_trend.value) & (df.get('ema200_slope_1h', np.nan) > 0)
        df['is_range'] = (df.get('bb_width_1h', np.nan) <= self.bb_width_range.value)

        # Price-action basique
        df['bull_engulf'] = (
            (df['close'] > df['open']) & (df['open'].shift(1) > df['close'].shift(1)) &
            (df['close'] >= df['open'].shift(1)) & (df['open'] <= df['close'].shift(1))
        )
        body = (df['close'] - df['open']).abs()
        wick_up = df['high'] - df[['open', 'close']].max(axis=1)
        wick_down = df[['open', 'close']].min(axis=1) - df['low']
        df['bull_pin'] = (wick_down > body * 2) & (df['close'] > df['open'])

        # Momentum RSI/EMA (v4/v5)
        df['ema_fast'] = ta.EMA(df, timeperiod=12)
        df['ema_slow'] = ta.EMA(df, timeperiod=26)
        df['ema_cross_up'] = (df['ema_fast'] > df['ema_slow']) & (df['ema_fast'].shift(1) <= df['ema_slow'].shift(1))
        df['ema_trend_up'] = df['ema_fast'] > df['ema_slow']
        df['rsi_lt_50'] = df['rsi'] < 50
        df['rsi_lt_45'] = df['rsi'] < 45
        df['rsi_rebound'] = (df['rsi'].shift(1) < 30) & (df['rsi'] > df['rsi'].shift(1))

        return df

    def populate_entry_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        disabled_tags = self._get_disabled_tags(metadata['pair'])

        # Supertrend (trend only)
        df.loc[
            (
                (df['is_trend']) &
                (~df['bad_pair']) &
                (df['supertrend_long']) &
                (df['close'] > df['ema50']) & (df['ema50'] > df['ema200']) &
                ('ST' not in disabled_tags)
            ),
            ['enter_long', 'enter_tag']
        ] = (1, 'ST')

        # RSI/EMA v5 (trend stricte)
        df.loc[
            (
                (df['is_trend']) &
                (~df['bad_pair']) &
                (df['ema_cross_up']) &
                (df['rsi'] > 50) &
                ('RSIEMA_V5' not in disabled_tags)
            ),
            ['enter_long', 'enter_tag']
        ] = (1, 'RSIEMA_V5')

        # RSI/EMA v4 (fallback range / hors-trend)
        df.loc[
            (
                (df['is_range'] | ~df['is_trend']) &
                (~df['bad_pair']) &
                (df['ema_trend_up']) &
                (df['rsi'] > 45) &
                ('RSIEMA_V4' not in disabled_tags)
            ),
            ['enter_long', 'enter_tag']
        ] = (1, 'RSIEMA_V4')

        # Patterns en range
        df.loc[
            (
                (df['is_range']) &
                (~df['bad_pair']) &
                (df['bull_engulf'] | df['bull_pin']) &
                ('PATTERN' not in disabled_tags)
            ),
            ['enter_long', 'enter_tag']
        ] = (1, 'PATTERN')

        return df

    def populate_exit_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        df.loc[
            (
                (df['rsi'] > 70) |
                ((df['is_trend']) & (df['close'] < df['ema50'])) |
                ((df['is_range']) & (df['rsi'] < 40))
            ),
            'exit_long'
        ] = 1
        return df

    def custom_stoploss(self, pair: str, trade, current_time: pd.Timestamp, current_rate: float,
                        current_profit: float, **kwargs) -> float:
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if df is None or df.empty:
            return 1.0
        atr = df['atr'].iloc[-1] if 'atr' in df.columns else None
        if atr is None or np.isnan(atr):
            return 1.0
        sl_distance = float(self.atr_mult_sl.value) * float(atr)
        sl_pct = sl_distance / max(current_rate, 1e-9)
        if current_profit > 0.02:
            sl_pct = min(sl_pct, max(0.01, current_profit * 0.6))
        return float(max(0.01, min(0.20, sl_pct)))

    # ===== Kill-switch =====
    def _get_disabled_tags(self, pair: str) -> set:
        key = f"disabled_tags::{pair}"
        # Always work with tz-aware UTC timestamps
        now_utc = pd.Timestamp.now(tz='UTC')
        default_until = pd.Timestamp.min.tz_localize('UTC')
        info = self.custom_info.get(key, {"tags": set(), "until": default_until})
        # Reactivate tags if the disable window expired
        if now_utc > info.get('until', default_until):
            info['tags'] = set()
            info['until'] = default_until
        self.custom_info[key] = info
        return info['tags']

    def _disable_tag(self, pair: str, tag: str):
        key = f"disabled_tags::{pair}"
        now_utc = pd.Timestamp.now(tz='UTC')
        until = now_utc + pd.Timedelta(hours=self.DISABLE_FOR_HOURS)
        info = self.custom_info.get(key, {"tags": set(), "until": until})
        info['tags'].add(tag)
        info['until'] = until
        self.custom_info[key] = info
        self.logger.warning(f"[KILL] Désactivation temporaire du tag {tag} sur {pair} jusqu'au {until}")

    def on_trade_closed(self, trade, order, **kwargs) -> None:
        try:
            pair = trade.pair
            tag = (trade.enter_tag or '').upper()
            if not tag:
                return
            df_hist = self._get_trade_history(pair, tag, limit=10)
            if df_hist is None or df_hist.empty:
                return
            consec_losses = 0
            for p in df_hist['close_profit'].iloc[::-1]:
                if p <= 0:
                    consec_losses += 1
                else:
                    break
            if consec_losses >= self.MAX_CONSECUTIVE_LOSSES:
                self._disable_tag(pair, tag)
        except Exception as e:
            self.logger.warning(f"on_trade_closed error: {e}")

    def _get_trade_history(self, pair: str, tag: str, limit: int = 20) -> Optional[DataFrame]:
        try:
            trades = self.dp.get_trade_history(pair=pair, limit=limit)
            if not trades:
                return None
            rows = []
            for t in trades:
                if (t.enter_tag or '').upper() == tag.upper():
                    rows.append({'close_profit': t.close_profit, 'close_date': t.close_date})
            if not rows:
                return None
            return pd.DataFrame(rows).sort_values('close_date')
        except Exception:
            return None

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                             time_in_force: str, enter_tag: str, **kwargs) -> bool:
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if df is not None and not df.empty and bool(df['bad_pair'].iloc[-1]):
            return False
        disabled = self._get_disabled_tags(pair)
        if enter_tag and enter_tag.upper() in disabled:
            return False
        return True

    # def custom_stake_amount(self, pair: str, current_price: float, proposed_stake: float, **kwargs) -> float:
    #     return proposed_stake
