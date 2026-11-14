# ==========================================
# TFG: ARCHIVO HISTÓRICO DE VERSIONES ANTERIORES
# ==========================================
# Este archivo contiene las versiones anteriores de la estrategia,
# preservadas para referencia y posible reutilización futura.
#
# VERSIONES INCLUIDAS:
#   - v1.0 (Gold Master - Institutional Grade)
#   - v1.1 (Final Release - Optimized for Hyperopt)
#
# La versión activa (v1.2) se encuentra en FreqaiExampleStrategy.py
# ==========================================


# ==========================================
# VERSIÓN 1.0 (Gold Master - Institutional Grade)
# ==========================================
# Características principales:
# - Primer diseño con 7 capas completas
# - Incluía custom_stake_amount con Kelly Criterion
# - Circuit Breaker con umbral -3%
# - Order Flow con filtro de imbalance > 0.4
# - ROC como feature adicional en FreqAI
# ==========================================

import logging
from functools import reduce
from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame
from sqlalchemy import create_engine, text

from freqtrade.strategy import (
    IStrategy,
    IntParameter,
    DecimalParameter,
    merge_informative_pair
)
from freqtrade.persistence import Trade

logger = logging.getLogger(__name__)

class FreqaiExampleStrategy_v1(IStrategy):
    """
    Estrategia TFG: Protocolo Híbrido Avanzado
    ------------------------------------------
    Integra:
    1. Análisis Técnico (Tendencia Estructural + Zona de Valor)
    2. Machine Learning (LightGBM / FreqAI)
    3. NLP (Sentimiento de Mercado - FinBERT)
    4. Order Flow (Análisis del Libro de Órdenes en Tiempo Real)
    5. Gestión Monetaria Avanzada (Criterio de Kelly Dinámico)
    6. Seguridad (Circuit Breaker Diario)
    """

    # --- CONFIGURACIÓN DEL BOT ---
    INTERFACE_VERSION = 3
    can_short = True
    timeframe = "5m" 
    
    # Periodo de arranque (Startup) para calcular indicadores previos
    startup_candle_count: int = 200 

    # --- INFRAESTRUCTURA DE DATOS ---
    DB_URL = "postgresql://postgres:password@timescaledb:5432/freqtrade"

    # --- 1. PARÁMETROS GENÉTICOS (HYPEROPT) ---
    stoploss_opt = DecimalParameter(-0.05, -0.005, default=-0.01, space="sell", optimize=True, load=True)
    buy_sma_period = IntParameter(100, 300, default=200, space="buy", optimize=True, load=True)
    buy_ema_period = IntParameter(20, 100, default=50, space="buy", optimize=True, load=True)
    ai_confidence_long = DecimalParameter(0.5, 0.9, default=0.55, space="buy", optimize=True, load=True)
    ai_confidence_short = DecimalParameter(0.1, 0.5, default=0.45, space="buy", optimize=True, load=True)

    minimal_roi = {
        "0": 0.10,
        "40": 0.02,
        "20": 0.01,
    }

    stoploss = -0.01

    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.011
    trailing_only_offset_is_reached = True

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        informative_pairs = [(pair, '1h') for pair in pairs]
        if self.config.get("freqai", {}).get("enabled", False):
            informative_pairs += self.freqai.start(self.dataframe, self.metadata, self)
        return informative_pairs

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = self.freqai.start(dataframe, metadata, self)
        dataframe = self.merge_sentiment_data(dataframe)

        dataframe['order_book_imbalance'] = 0.5
        if self.dp and self.dp.runmode.value in ('live', 'dry_run'):
            try:
                order_book = self.dp.market(metadata['pair']).fetch_order_book(limit=10)
                bids_vol = sum([bid[1] for bid in order_book['bids']])
                asks_vol = sum([ask[1] for ask in order_book['asks']])
                total_vol = bids_vol + asks_vol
                if total_vol > 0:
                    imbalance = bids_vol / total_vol
                    dataframe.loc[dataframe.index[-1], 'order_book_imbalance'] = imbalance
            except Exception:
                pass

        informative_h1 = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe='1h')
        informative_h1['sma_200'] = ta.SMA(informative_h1, timeperiod=self.buy_sma_period.value)
        informative_h1['ema_50'] = ta.EMA(informative_h1, timeperiod=self.buy_ema_period.value)
        informative_h1['dist_ema50'] = abs(
            (informative_h1['close'] - informative_h1['ema_50']) / informative_h1['ema_50']
        )
        dataframe = merge_informative_pair(dataframe, informative_h1, self.timeframe, '1h', ffill=True)
        return dataframe

    def merge_sentiment_data(self, dataframe: DataFrame) -> DataFrame:
            """ Fusión asíncrona de datos de sentimiento desde TimescaleDB """
            dataframe['sentiment_score'] = 0.0
            try:
                engine = create_engine(self.DB_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)
                query = "SELECT time, sentiment_score FROM market_sentiment ORDER BY time DESC LIMIT 500"
                sentiment_df = pd.read_sql(query, engine)
                engine.dispose()
                if not sentiment_df.empty:
                    sentiment_df['time'] = pd.to_datetime(sentiment_df['time']).dt.tz_convert('UTC')
                    dataframe['date'] = pd.to_datetime(dataframe['date']).dt.tz_convert('UTC')
                    sentiment_df = sentiment_df.sort_values('time')
                    merged_df = pd.merge_asof(dataframe, sentiment_df, left_on='date', right_on='time', direction='backward')
                    if 'sentiment_score_y' in merged_df.columns:
                        dataframe['sentiment_score'] = merged_df['sentiment_score_y'].fillna(0.0)
            except Exception:
                pass
            return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        if "sentiment_score" not in dataframe.columns: dataframe["sentiment_score"] = 0.0
        
        trend_bullish = (dataframe['close_1h'] > dataframe['sma_200_1h'])
        in_value_zone = (dataframe['dist_ema50_1h'] < 0.015) 
        ai_signal_long = (dataframe["do_predict"] == 1) & (dataframe["&s-up_or_down"] > self.ai_confidence_long.value)
        sentiment_safe = (dataframe['sentiment_score'] > -0.2)
        order_flow_safe = (dataframe['order_book_imbalance'] > 0.4)

        enter_long_cond = [trend_bullish, in_value_zone, ai_signal_long, sentiment_safe, order_flow_safe, (dataframe['volume'] > 0)]
        if enter_long_cond:
            dataframe.loc[reduce(lambda x, y: x & y, enter_long_cond), "enter_long"] = 1

        trend_bearish = (dataframe['close_1h'] < dataframe['sma_200_1h'])
        ai_signal_short = (dataframe["do_predict"] == 1) & (dataframe["&s-up_or_down"] < self.ai_confidence_short.value)
        enter_short_cond = [trend_bearish, in_value_zone, ai_signal_short, (dataframe['sentiment_score'] < 0.2), (dataframe['volume'] > 0)]
        if enter_short_cond:
            dataframe.loc[reduce(lambda x, y: x & y, enter_short_cond), "enter_short"] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        exit_long_cond = [dataframe["do_predict"] == 1, dataframe["&s-up_or_down"] < 0.40]
        if exit_long_cond: dataframe.loc[reduce(lambda x, y: x & y, exit_long_cond), "exit_long"] = 1

        exit_short_cond = [dataframe["do_predict"] == 1, dataframe["&s-up_or_down"] > 0.60]
        if exit_short_cond: dataframe.loc[reduce(lambda x, y: x & y, exit_short_cond), "exit_short"] = 1

        return dataframe

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                            proposed_stake: float, min_stake: float, max_stake: float,
                            entry_tag: Optional[str], side: str, **kwargs) -> float:
        """
        Dimensionamiento de Posición Dinámico basado en la Confianza de la IA (Kelly Criterion).
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe.empty: return proposed_stake
        
        last_candle = dataframe.iloc[-1]
        ai_confidence = last_candle.get("&s-up_or_down", 0.5)
        risk_factor = max(0, (ai_confidence - 0.5) * 2) 
        
        total_wallet = self.wallets.get_total_stake_amount()
        max_risk_per_trade = total_wallet * 0.05
        adjusted_stake = min_stake + (max_risk_per_trade - min_stake) * risk_factor
        
        if adjusted_stake < min_stake: return min_stake
        if adjusted_stake > max_stake: return max_stake
        return adjusted_stake

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                                time_in_force: str, current_time: datetime, entry_tag: Optional[str],
                                side: str, **kwargs) -> bool:
            """Circuit Breaker: Bloquea entradas si pérdida diaria > -3%"""
            if self.dp and self.dp.runmode.value in ('backtest', 'hyperopt'):
                return True
            try:
                today = datetime.now(timezone.utc).date()
                trades_today = Trade.get_trades([Trade.close_date >= today]).all()
                daily_profit_pct = sum(t.close_profit for t in trades_today)
                if daily_profit_pct < -0.03:
                    return False 
            except Exception:
                pass
            return True

    def feature_engineering_expand_all(self, dataframe: DataFrame, period: int, metadata: dict, **kwargs) -> DataFrame:
        dataframe["%-rsi-period"] = ta.RSI(dataframe, timeperiod=period)
        dataframe["%-roc-period"] = ta.ROC(dataframe, timeperiod=period)
        dataframe["%-bb_width-period"] = (ta.BBANDS(dataframe, timeperiod=period)["upperband"] - ta.BBANDS(dataframe, timeperiod=period)["lowerband"]) / ta.BBANDS(dataframe, timeperiod=period)["middleband"]
        if "sentiment_score" not in dataframe.columns: dataframe["sentiment_score"] = 0.0
        dataframe["%-sentiment"] = dataframe["sentiment_score"]
        return dataframe

    def feature_engineering_expand_basic(self, dataframe: DataFrame, **kwargs) -> DataFrame:
        dataframe["%-pct-change"] = dataframe["close"].pct_change()
        dataframe["%-raw_volume"] = dataframe["volume"]
        return dataframe

    def feature_engineering_standard(self, dataframe: DataFrame, **kwargs) -> DataFrame:
        dataframe["%-day_of_week"] = dataframe["date"].dt.dayofweek
        dataframe["%-hour_of_day"] = dataframe["date"].dt.hour
        return dataframe

    def set_freqai_targets(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        dataframe["&s-up_or_down"] = np.where(dataframe["close"].shift(-self.freqai_info["feature_parameters"]["label_period_candles"]) > dataframe["close"], 1, 0)
        return dataframe


# ==========================================
# VERSIÓN 1.1 (Optimized for Hyperopt)
# ==========================================
# Cambios respecto a v1.0:
# - Parámetros optimizados por Hyperopt:
#     buy_sma_period: 200 → 160
#     buy_ema_period: 50 → 79
#     ai_confidence_long: 0.55 → 0.864
#     ai_confidence_short: 0.45 → 0.125
#     stoploss: -0.01 → -0.215
#     minimal_roi revisado
# - Order Flow sin filtro de imbalance en entry
# - merge_sentiment_data solo en live/dry_run
# - Eliminado ROC de features
# ==========================================

class FreqaiExampleStrategy_v1_1(IStrategy):
    """
    Estrategia TFG: Protocolo Híbrido Avanzado
    Arquitectura Institucional con parámetros optimizados por Hyperopt.
    """

    INTERFACE_VERSION = 3
    can_short = True
    timeframe = "5m" 
    startup_candle_count: int = 200 

    DB_URL = "postgresql://postgres:password@timescaledb:5432/freqtrade"

    stoploss_opt = DecimalParameter(-0.05, -0.005, default=-0.05, space="sell", optimize=True, load=True)
    buy_sma_period = IntParameter(100, 300, default=160, space="buy", optimize=True, load=True)
    buy_ema_period = IntParameter(20, 100, default=79, space="buy", optimize=True, load=True)
    ai_confidence_long = DecimalParameter(0.5, 0.9, default=0.864, space="buy", optimize=True, load=True)
    ai_confidence_short = DecimalParameter(0.1, 0.5, default=0.125, space="buy", optimize=True, load=True)

    minimal_roi = {
        "0": 0.1,
        "33": 0.061,
        "76": 0.023,
        "145": 0
    }

    stoploss = -0.215

    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.011
    trailing_only_offset_is_reached = True

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        return [(pair, '1h') for pair in pairs]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = self.merge_sentiment_data(dataframe)
        dataframe = self.freqai.start(dataframe, metadata, self)

        dataframe['order_book_imbalance'] = 0.5
        if self.dp and self.dp.runmode.value in ('live', 'dry_run'):
            try:
                order_book = self.dp.market(metadata['pair']).fetch_order_book(limit=10)
                bids_vol = sum([bid[1] for bid in order_book['bids']])
                asks_vol = sum([ask[1] for ask in order_book['asks']])
                total_vol = bids_vol + asks_vol
                if total_vol > 0:
                    dataframe.loc[dataframe.index[-1], 'order_book_imbalance'] = bids_vol / total_vol
            except Exception as e:
                logger.debug(f"Error cargando Order Book: {e}")

        informative_h1 = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe='1h')
        informative_h1['sma_200'] = ta.SMA(informative_h1, timeperiod=self.buy_sma_period.value)
        informative_h1['ema_50'] = ta.EMA(informative_h1, timeperiod=self.buy_ema_period.value)
        informative_h1['dist_ema50'] = abs((informative_h1['close'] - informative_h1['ema_50']) / informative_h1['ema_50'])
        dataframe = merge_informative_pair(dataframe, informative_h1, self.timeframe, '1h', ffill=True)
        return dataframe

    def merge_sentiment_data(self, dataframe: DataFrame) -> DataFrame:
        dataframe['sentiment_score'] = 0.0
        if self.dp and self.dp.runmode.value in ('live', 'dry_run'):
            try:
                engine = create_engine(self.DB_URL)
                query = "SELECT time, sentiment_score FROM market_sentiment ORDER BY time DESC LIMIT 500"
                sentiment_df = pd.read_sql(query, engine)
                engine.dispose()
                if not sentiment_df.empty:
                    sentiment_df['time'] = pd.to_datetime(sentiment_df['time']).dt.tz_convert('UTC')
                    dataframe['date'] = pd.to_datetime(dataframe['date']).dt.tz_convert('UTC')
                    merged_df = pd.merge_asof(dataframe.sort_values('date'), sentiment_df.sort_values('time'), left_on='date', right_on='time', direction='backward')
                    if 'sentiment_score_y' in merged_df.columns:
                        dataframe['sentiment_score'] = merged_df['sentiment_score_y'].fillna(0.0)
            except Exception: pass
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        trend_bullish = (dataframe['close_1h'] > dataframe['sma_200_1h'])
        trend_bearish = (dataframe['close_1h'] < dataframe['sma_200_1h'])
        in_value_zone = (dataframe['dist_ema50_1h'] < 0.015) 
        
        ai_signal_long = (dataframe["do_predict"] == 1) & (dataframe["&s-up_or_down"] > self.ai_confidence_long.value)
        ai_signal_short = (dataframe["do_predict"] == 1) & (dataframe["&s-up_or_down"] < self.ai_confidence_short.value)
        
        sentiment_safe_long = (dataframe['sentiment_score'] > -0.2)
        sentiment_safe_short = (dataframe['sentiment_score'] < 0.2)

        enter_long_cond = [trend_bullish, in_value_zone, ai_signal_long, sentiment_safe_long, (dataframe['volume'] > 0)]
        if enter_long_cond:
            dataframe.loc[reduce(lambda x, y: x & y, enter_long_cond), "enter_long"] = 1

        enter_short_cond = [trend_bearish, in_value_zone, ai_signal_short, sentiment_safe_short, (dataframe['volume'] > 0)]
        if enter_short_cond:
            dataframe.loc[reduce(lambda x, y: x & y, enter_short_cond), "enter_short"] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[(dataframe["do_predict"] == 1) & (dataframe["&s-up_or_down"] < 0.40), "exit_long"] = 1
        dataframe.loc[(dataframe["do_predict"] == 1) & (dataframe["&s-up_or_down"] > 0.60), "exit_short"] = 1
        return dataframe

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                            proposed_stake: float, min_stake: float, max_stake: float,
                            entry_tag: Optional[str], side: str, **kwargs) -> float:
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe.empty: return proposed_stake
        ai_confidence = dataframe.iloc[-1].get("&s-up_or_down", 0.5)
        risk_factor = max(0, (ai_confidence - 0.5) * 2) 
        total_wallet = self.wallets.get_total_stake_amount()
        max_risk_per_trade = total_wallet * 0.05
        adjusted_stake = min_stake + (max_risk_per_trade - min_stake) * risk_factor
        return min(max(adjusted_stake, min_stake), max_stake)

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                            time_in_force: str, current_time: datetime, entry_tag: Optional[str],
                            side: str, **kwargs) -> bool:
        if self.dp and self.dp.runmode.value in ('backtest', 'hyperopt'):
            return True
        try:
            today = datetime.now(timezone.utc).date()
            trades_today = Trade.get_trades([Trade.close_date >= today]).all()
            daily_profit = sum(t.close_profit for t in trades_today)
            if daily_profit < -0.03:
                logger.warning(f"Circuit Breaker activado: {daily_profit:.2%}")
                return False
        except Exception: pass
        return True

    def feature_engineering_expand_all(self, dataframe: DataFrame, period: int, metadata: dict, **kwargs) -> DataFrame:
            dataframe["%-rsi-period"] = ta.RSI(dataframe, timeperiod=period)
            dataframe["%-bb_width-period"] = (ta.BBANDS(dataframe, timeperiod=period)["upperband"] - ta.BBANDS(dataframe, timeperiod=period)["lowerband"]) / ta.BBANDS(dataframe, timeperiod=period)["middleband"]
            if "sentiment_score" not in dataframe.columns:
                dataframe["sentiment_score"] = 0.0
            dataframe["%-sentiment"] = dataframe["sentiment_score"]
            return dataframe

    def feature_engineering_expand_basic(self, dataframe: DataFrame, **kwargs) -> DataFrame:
        dataframe["%-pct-change"] = dataframe["close"].pct_change()
        dataframe["%-raw_volume"] = dataframe["volume"]
        return dataframe

    def feature_engineering_standard(self, dataframe: DataFrame, **kwargs) -> DataFrame:
        dataframe["%-day_of_week"] = dataframe["date"].dt.dayofweek
        dataframe["%-hour_of_day"] = dataframe["date"].dt.hour
        return dataframe

    def set_freqai_targets(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        dataframe["&s-up_or_down"] = np.where(dataframe["close"].shift(-self.freqai_info["feature_parameters"]["label_period_candles"]) > dataframe["close"], 1, 0)
        return dataframe
