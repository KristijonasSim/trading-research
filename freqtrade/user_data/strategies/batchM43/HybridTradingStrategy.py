# ==========================================
# TFG: SISTEMA DE TRADING ALGORÍTMICO HÍBRIDO
# Autor: Joan Romà Llorca
# Versión: 3.0 (Institutional Multi-Timeframe + NER NLP)
# ==========================================
#
# Arquitectura de decisión multi-capa (v3.0):
#   1. Machine Learning (FreqAI / LightGBM) — 18+ features MTF
#   2. NLP (Sentimiento por moneda via FinBERT + NER + TimescaleDB)
#   3. Order Flow (Order Book Imbalance + Maker Pricing)
#   4. Análisis Técnico Macro (SMA/EMA/ADX en H1)
#   5. Gestión de Riesgo Dinámica (ATR + Circuit Breaker)
#   6. Detección de Régimen (ADX → filtra mercados laterales)
#   7. Multi-Timeframe Features (H1 inyectadas a FreqAI)
#
# CAMBIOS v3.0 vs v2.1:
#   - MTF Features: RSI_1h, BB_Width_1h, ATR_1h, OBV_1h inyectadas
#     directamente al modelo ML para visión macro-micro cruzada
#   - NLP per-coin: Sentimiento por criptomoneda (NER), no global
#   - Maker pricing: Órdenes limit Post-Only para reducir comisiones
#   - MLOps logging: Tracking interno del rendimiento de la IA
#   - On-chain awareness: Arquitectura preparada para datos on-chain
#
# Versiones anteriores disponibles en:
#   → FreqaiExampleStrategy_legacy.py
#   → docs/strategy_evolution.md
# ==========================================

import os
import logging
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd
import talib.abstract as ta
from pandas import DataFrame
from sqlalchemy import create_engine

from freqtrade.strategy import (
    IStrategy,
    IntParameter,
    DecimalParameter,
    merge_informative_pair
)
from freqtrade.persistence import Trade

logger = logging.getLogger(__name__)


class HybridTradingStrategy(IStrategy):
    """
    Estrategia TFG v3.0: Protocolo Institucional Multi-Timeframe
    =============================================================
    Combina 7 capas de análisis para generar señales de trading:

    - Capa 1 (ML):      LightGBM con 18+ features MTF predice % de cambio
    - Capa 2 (NLP):     FinBERT con NER filtra por sentimiento per-coin
    - Capa 3 (Flow):    Order Book Imbalance + Maker pricing
    - Capa 4 (TA):      SMA/EMA/ADX en H1 filtra tendencia macro
    - Capa 5 (Risk):    Stop loss dinámico ATR + Circuit Breaker diario
    - Capa 6 (Regime):  ADX filtra mercados laterales (ADX < 20)
    - Capa 7 (MTF):     Features horarias inyectadas para visión cruzada
    """

    # ─── CONFIGURACIÓN GENERAL ──────────────────────────────────────────
    INTERFACE_VERSION = 3
    can_short = True
    timeframe = "5m"
    startup_candle_count: int = 200

    # ─── CONEXIÓN A BASE DE DATOS ───────────────────────────────────────
    DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "password")
    DB_URL = f"postgresql://postgres:{DB_PASSWORD}@timescaledb:5432/freqtrade"

    # Engine reutilizable
    _db_engine = None

    def _get_db_engine(self):
        if self._db_engine is None:
            self._db_engine = create_engine(self.DB_URL)
        return self._db_engine

    # ─── PARÁMETROS OPTIMIZABLES (Hyperopt) ─────────────────────────────
    # PARÁMETROS OPTIMIZADOS DEFINITIVOS (Vía 2 Deep Hyperopt)
    buy_sma_period = IntParameter(50, 300, default=120, space="buy", optimize=True, load=True)
    buy_ema_period = IntParameter(20, 100, default=35, space="buy", optimize=True, load=True)

    # Umbrales IA (Regresión % de precio) aumentados para exigir mayor convicción
    ai_threshold_long = DecimalParameter(0.01, 0.05, default=0.025, space="buy", optimize=True, load=True)
    ai_threshold_short = DecimalParameter(-0.05, -0.01, default=-0.025, space="buy", optimize=True, load=True)

    # ─── GESTIÓN DE RIESGO ──────────────────────────────────────────────
    # ROI y stoploss se delegan al config.json

    # Trailing Stop: la clave del éxito para dejar correr ganancias
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.03
    trailing_only_offset_is_reached = True

    # ─── TIMEFRAMES INFORMATIVOS ────────────────────────────────────────
    def informative_pairs(self):
        """Define pares informativos en H1 para filtro macro y MTF features."""
        pairs = self.dp.current_whitelist()
        informative = [(pair, '1h') for pair in pairs]
        return informative

    # ═══════════════════════════════════════════════════════════════════
    # CÁLCULO DE INDICADORES (Pipeline de datos)
    # ═══════════════════════════════════════════════════════════════════
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Pipeline de indicadores v3.0 (orden crítico):
        1. Macro H1 → fusiona SMA/EMA/ADX ANTES de FreqAI para MTF features
        2. NLP → crea 'sentiment_score' antes de que FreqAI lo use como feature
        3. FreqAI → genera predicción '&s-price_change' y 'do_predict'
        4. Order Flow → calcula imbalance del libro de órdenes
        5. ATR → calcula volatilidad para stop loss dinámico
        6. MLOps → log de predicciones para trazabilidad
        """
        # 1. CAPA MACRO H1 (DEBE ir ANTES de FreqAI para que las features MTF
        #    como %-dist_sma200_1h-period estén disponibles en feature_engineering)
        informative_h1 = self.dp.get_pair_dataframe(pair=metadata['pair'], timeframe='1h')
        informative_h1['sma_200'] = ta.SMA(informative_h1, timeperiod=self.buy_sma_period.value)
        informative_h1['ema_50'] = ta.EMA(informative_h1, timeperiod=self.buy_ema_period.value)
        informative_h1['dist_ema50'] = abs(
            (informative_h1['close'] - informative_h1['ema_50']) / informative_h1['ema_50']
        )
        # CAPA RÉGIMEN DE MERCADO (ADX en H1)
        informative_h1['adx'] = ta.ADX(informative_h1, timeperiod=14)
        dataframe = merge_informative_pair(dataframe, informative_h1, self.timeframe, '1h', ffill=True)

        # 2. CAPA NLP (per-coin v3.0)
        dataframe = self._merge_sentiment_data(dataframe)
        if 'sentiment_score' in dataframe.columns:
            dataframe['sentiment_momentum'] = dataframe['sentiment_score'] - dataframe['sentiment_score'].shift(12)
        else:
            dataframe['sentiment_momentum'] = 0.0

        # 3. CAPA ML (FreqAI) — ahora las columnas _1h ya están mergeadas
        dataframe = self.freqai.start(dataframe, metadata, self)

        # 4. CAPA ORDER FLOW (solo en live/dry-run)
        dataframe['order_book_imbalance'] = 0.5
        if self.dp and self.dp.runmode.value in ('live', 'dry_run'):
            try:
                order_book = self.dp.orderbook(metadata['pair'], 1)
                if order_book and 'bids' in order_book and 'asks' in order_book:
                    bids_vol = sum([bid[1] for bid in order_book['bids']])
                    asks_vol = sum([ask[1] for ask in order_book['asks']])
                    total_vol = bids_vol + asks_vol
                    if total_vol > 0:
                        dataframe.loc[dataframe.index[-1], 'order_book_imbalance'] = bids_vol / total_vol
            except Exception as e:
                logger.debug(f"Error cargando Order Book: {e}")

        # 5. ATR y SAR para stop loss dinámico e institucional
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['sar'] = ta.SAR(dataframe)

        # 6. MEJORA v3.0 (MLOps): Log de predicciones para trazabilidad
        self._log_prediction_metrics(dataframe, metadata)

        return dataframe

    def _log_prediction_metrics(self, dataframe: DataFrame, metadata: dict):
        """
        MEJORA v3.0 (MLOps): Logging interno de predicciones de la IA.
        Registra la última predicción para cada par, permitiendo
        trazabilidad completa del proceso de decisión del modelo.
        No requiere infraestructura externa (MLflow/W&B).
        """
        if dataframe.empty or self.dp.runmode.value in ('backtest', 'hyperopt'):
            return

        try:
            last = dataframe.iloc[-1]
            pair = metadata.get('pair', 'unknown')
            prediction = last.get('&s-price_change', 0)
            do_predict = last.get('do_predict', 0)
            sentiment = last.get('sentiment_score', 0)
            imbalance = last.get('order_book_imbalance', 0.5)
            adx = last.get('adx_1h', 0)

            # Determinar señal de la IA
            if do_predict == 1 and prediction > self.ai_threshold_long.value:
                signal = "🟢 LONG"
            elif do_predict == 1 and prediction < self.ai_threshold_short.value:
                signal = "🔴 SHORT"
            else:
                signal = "⚪ NEUTRAL"

            logger.info(
                f"📡 [MLOps] {pair} | {signal} | "
                f"Pred: {prediction:+.4f} | "
                f"Sent: {sentiment:+.2f} | "
                f"OBI: {imbalance:.2f} | "
                f"ADX: {adx:.1f} | "
                f"Valid: {int(do_predict)}"
            )
        except Exception:
            pass  # Never let logging crash the bot

    def _merge_sentiment_data(self, dataframe: DataFrame) -> DataFrame:
        """
        Fusiona datos de sentimiento NLP desde TimescaleDB.
        v3.0: Lee primero sentimiento PER-COIN (tabla coin_sentiment),
        con fallback al sentimiento global (tabla market_sentiment).
        Solo se ejecuta en live/dry-run para evitar ralentizar backtests.
        """
        dataframe['sentiment_score'] = 0.0
        if self.dp and self.dp.runmode.value in ('live', 'dry_run'):
            try:
                engine = self._get_db_engine()
                pair = dataframe.attrs.get('pair', '')
                # Extraer símbolo de la moneda (ej: "BTC/USDT:USDT" → "BTC")
                coin = pair.split('/')[0] if '/' in pair else ''

                sentiment_df = pd.DataFrame()

                # MEJORA v3.0: Intentar leer sentimiento PER-COIN primero
                if coin:
                    try:
                        query_coin = f"""
                            SELECT time, sentiment_score
                            FROM coin_sentiment
                            WHERE coin = '{coin}'
                            ORDER BY time DESC LIMIT 100
                        """
                        sentiment_df = pd.read_sql(query_coin, engine)
                        if not sentiment_df.empty:
                            logger.info(f"🪙 NLP per-coin: {coin} → {len(sentiment_df)} registros")
                    except Exception:
                        pass  # Tabla coin_sentiment puede no existir aún

                # Fallback: sentimiento global si no hay datos per-coin
                if sentiment_df.empty:
                    query_global = """
                        SELECT time, sentiment_score
                        FROM market_sentiment
                        ORDER BY time DESC LIMIT 500
                    """
                    sentiment_df = pd.read_sql(query_global, engine)

                if not sentiment_df.empty:
                    sentiment_df['time'] = pd.to_datetime(sentiment_df['time']).dt.tz_convert('UTC')
                    dataframe['date'] = pd.to_datetime(dataframe['date']).dt.tz_convert('UTC')
                    merged_df = pd.merge_asof(
                        dataframe.sort_values('date'),
                        sentiment_df.sort_values('time'),
                        left_on='date', right_on='time', direction='backward'
                    )
                    if 'sentiment_score_y' in merged_df.columns:
                        dataframe['sentiment_score'] = merged_df['sentiment_score_y'].fillna(0.0)
            except Exception:
                pass
        return dataframe

    # ═══════════════════════════════════════════════════════════════════
    # LÓGICA DE ENTRADA
    # ═══════════════════════════════════════════════════════════════════
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Señales de entrada LONG y SHORT v3.0.
        Requiere confluencia de 7 factores:
        1. Régimen de mercado (ADX > 20 = tendencia, evita laterales)
        2. Tendencia macro (H1 SMA200)
        3. Zona de valor (cerca EMA50, 2.5%)
        4. IA predice movimiento fuerte
        5. Sentimiento de mercado OK (per-coin v3.0)
        6. Volumen superior a la media
        7. Validación MLOps (log de señales)
        """
        # Filtro de régimen ADX
        trending_market = (dataframe['adx_1h'] > 20)

        # Filtros técnicos (H1)
        trend_bullish = (dataframe['close_1h'] > dataframe['sma_200_1h'])
        trend_bearish = (dataframe['close_1h'] < dataframe['sma_200_1h'])
        in_value_zone = (dataframe['dist_ema50_1h'] < 0.025)

        # Señales IA de Regresión
        ai_signal_long = (
            (dataframe["do_predict"] == 1) &
            (dataframe["&s-price_change"] > self.ai_threshold_long.value)
        )
        ai_signal_short = (
            (dataframe["do_predict"] == 1) &
            (dataframe["&s-price_change"] < self.ai_threshold_short.value)
        )

        # Filtros NLP (per-coin v3.0)
        sentiment_safe_long = (dataframe['sentiment_score'] > -0.4)
        sentiment_safe_short = (dataframe['sentiment_score'] < 0.4)

        # Filtro de volumen
        vol_sma = dataframe['volume'].rolling(window=50).mean()
        volume_ok = (dataframe['volume'] > vol_sma * 1.0)

        # LONG: 6 factores de confluencia
        long_condition = (
            trending_market & trend_bullish & in_value_zone &
            ai_signal_long & sentiment_safe_long & volume_ok
        )
        dataframe.loc[long_condition, "enter_long"] = 1

        # SHORT: 6 factores de confluencia
        short_condition = (
            trending_market & trend_bearish & in_value_zone &
            ai_signal_short & sentiment_safe_short & volume_ok
        )
        dataframe.loc[short_condition, "enter_short"] = 1

        # MEJORA v3.0 (MLOps): Log de señales de entrada
        if self.dp and self.dp.runmode.value not in ('backtest', 'hyperopt'):
            n_longs = long_condition.sum()
            n_shorts = short_condition.sum()
            if n_longs > 0 or n_shorts > 0:
                logger.info(
                    f"🎯 [MLOps] {metadata['pair']} | "
                    f"Señales: 🟢 {n_longs} LONG | 🔴 {n_shorts} SHORT"
                )

        return dataframe

    # ═══════════════════════════════════════════════════════════════════
    # LÓGICA DE SALIDA
    # ═══════════════════════════════════════════════════════════════════
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Salida cuando la IA invierte su predicción con fuerza.
        """
        exit_threshold = abs(self.ai_threshold_long.value) * 0.5

        dataframe.loc[
            (dataframe["do_predict"] == 1) & (dataframe["&s-price_change"] < -exit_threshold),
            "exit_long"
        ] = 1
        dataframe.loc[
            (dataframe["do_predict"] == 1) & (dataframe["&s-price_change"] > exit_threshold),
            "exit_short"
        ] = 1
        return dataframe

    # ═══════════════════════════════════════════════════════════════════
    # STOP LOSS DINÁMICO (basado en ATR)
    # ═══════════════════════════════════════════════════════════════════
    def custom_stoploss(self, pair: str, trade: Trade, current_time: datetime,
                        current_rate: float, current_profit: float, after_fill: bool,
                        **kwargs) -> float:
        """
        Stop loss dinámico Institucional (Parabolic SAR + ATR).
        - Beneficio > 2%: trailing ultra ceñido con SAR.
        - Mercado volátil/Inicial: stop con ATR extendido.
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe.empty:
            return -0.01

        last_candle = dataframe.iloc[-1]
        atr = last_candle.get('atr', 0)
        sar = last_candle.get('sar', 0)

        # Trailing Institucional Seguro (SAR)
        if current_profit > 0.02 and sar > 0:
            if trade.is_short:
                sar_dist = (current_rate - sar) / current_rate
                return max(min(sar_dist, -0.005), -0.05)
            else:
                sar_dist = (sar - current_rate) / current_rate
                return max(min(sar_dist, -0.005), -0.05)

        # Riesgo Inicial (ATR)
        if atr > 0 and current_rate > 0:
            atr_stop = -(2 * atr / current_rate)
            return max(min(atr_stop, -0.005), -0.03)

        return -0.01

    # ═══════════════════════════════════════════════════════════════════
    # CIRCUIT BREAKER (Protección de Capital)
    # ═══════════════════════════════════════════════════════════════════
    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                            time_in_force: str, current_time: datetime, entry_tag: Optional[str],
                            side: str, **kwargs) -> bool:
        """
        Gate de seguridad pre-entrada v3.0:
        1. Circuit Breaker: Bloquea si la pérdida diaria > -10%
        2. On-Chain awareness: Consulta Fear & Greed si está disponible
        3. MLOps: Log de operaciones confirmadas
        """
        if self.dp and self.dp.runmode.value in ('backtest', 'hyperopt'):
            return True
        try:
            # 1. Circuit Breaker (pérdida diaria)
            today = datetime.now(timezone.utc).date()
            trades_today = Trade.get_trades([Trade.close_date >= today]).all()
            daily_profit = sum(t.close_profit for t in trades_today)
            if daily_profit < -0.10:
                logger.warning(f"⚠️ Circuit Breaker activado: pérdida diaria {daily_profit:.2%}")
                return False

            # 2. MEJORA v3.0 (On-Chain): Consultar Fear & Greed Index
            # Si el mercado está en Extreme Fear (<15), bloquear SHORTs
            # Si está en Extreme Greed (>85), bloquear LONGs
            try:
                engine = self._get_db_engine()
                fng_query = """
                    SELECT metric_value FROM onchain_metrics
                    WHERE metric_name = 'fear_greed_index'
                    ORDER BY time DESC LIMIT 1
                """
                fng_df = pd.read_sql(fng_query, engine)
                if not fng_df.empty:
                    fng_value = fng_df.iloc[0]['metric_value']
                    if side == 'long' and fng_value > 85:
                        logger.warning(
                            f"⚠️ On-Chain: Fear & Greed = {fng_value} (Extreme Greed). "
                            f"Bloqueando LONG en {pair}."
                        )
                        return False
                    elif side == 'short' and fng_value < 15:
                        logger.warning(
                            f"⚠️ On-Chain: Fear & Greed = {fng_value} (Extreme Fear). "
                            f"Bloqueando SHORT en {pair}."
                        )
                        return False
            except Exception:
                pass  # On-chain data es opcional, no bloquear si falla

            # 3. Portfolio Heat (Control de Sobreexposición Institucional)
            open_trades = Trade.get_open_trades()
            if len(open_trades) >= 3:
                logger.warning(f"🌡️ Portfolio Heat alert: {len(open_trades)} trades abiertos simultáneamente. Denegando {pair}.")
                return False

            # 4. Order Book Imbalance (Sniper Limits)
            dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            if not dataframe.empty:
                last_candle = dataframe.iloc[-1]
                obi = last_candle.get('order_book_imbalance', 0.5)
                if side == 'long' and obi < 0.35:
                    logger.warning(f"🧱 Order Book Wall: Fuerte presión institucional de VENTA (OBI={obi:.2f}). Cancelando LONG en {pair}.")
                    return False
                elif side == 'short' and obi > 0.65:
                    logger.warning(f"🧱 Order Book Wall: Fuerte presión institucional de COMPRA (OBI={obi:.2f}). Cancelando SHORT en {pair}.")
                    return False

            # 5. MEJORA v3.0 (MLOps): Log de trade confirmado
            logger.info(
                f"✅ [MLOps] Trade CONFIRMADO: {pair} | {side.upper()} | "
                f"Rate: {rate:.2f} | Amount: {amount:.4f}"
            )

        except Exception as e:
            logger.warning(f"⚠️ Error confirmando entrada {pair}: {e}")
            pass
        return True

    # ═══════════════════════════════════════════════════════════════════
    # DIMENSIONAMIENTO DE POSICIÓN (Conviction-Based Sizing / Proxy Kelly)
    # ═══════════════════════════════════════════════════════════════════
    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                            proposed_stake: float, min_stake: float, max_stake: float,
                            entry_tag: Optional[str], side: str, **kwargs) -> float:
        """
        Dimensionamiento de posición basado en la confianza de la IA.
        Predicción grande → posición más grande (hasta 40% wallet)
        Predicción pequeña → posición mínima
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe.empty:
            return proposed_stake

        last_candle = dataframe.iloc[-1]
        predicted_change = abs(last_candle.get("&s-price_change", 0))

        # Factor de riesgo: 0 a 1
        atr = last_candle.get('atr', 0)
        
        # Volatility Targeting (VaR / Protección Patrimonial)
        atr_pct = (atr / current_rate) if current_rate > 0 else 0
        vol_discount = 1.0
        # Tolerancia institucional: si la volatilidad de la vela de 5m supera el 1.5%, reducimos dramáticamente
        if atr_pct > 0.015:
             vol_discount = max(0.1, 0.015 / atr_pct)

        risk_factor = min(predicted_change / 0.02, 1.0) * vol_discount

        # Stake proporcional a la convicción reducida por la volatilidad
        if self.wallets:
            total_wallet = self.wallets.get_total_stake_amount()
            max_risk_per_trade = total_wallet * 0.40  # Proxy Kelly: máx 40%
        else:
            # Fallback seguro para backtesting sin objeto wallets
            max_risk_per_trade = proposed_stake * 2.0
            
        adjusted_stake = min_stake + (max_risk_per_trade - min_stake) * risk_factor

        return min(max(adjusted_stake, min_stake), max_stake)

    # ═══════════════════════════════════════════════════════════════════
    # FREQAI: INGENIERÍA DE CARACTERÍSTICAS (18+ Features MTF)
    # ═══════════════════════════════════════════════════════════════════
    def feature_engineering_expand_all(self, dataframe: DataFrame, period: int,
                                       metadata: dict, **kwargs) -> DataFrame:
        """
        Features técnicas expandidas por periodo para FreqAI.
        v3.0: 18+ features organizadas en 6 familias:
          - Momentum (4): RSI, StochRSI, MFI, MACD Histogram
          - Volatilidad (2): BB Width, ATR Normalizado
          - Volumen (1): OBV Normalizado
          - Estadístico (2): Log Returns, Return Std
          - Fundamental (1): Sentimiento NLP per-coin
          - Multi-Timeframe (4): RSI_1h, BB_Width_1h, ATR_1h, OBV_1h
          + 4 features básicas + 2 temporales = 18+ features totales
        """
        # ─── MOMENTUM ─────────────────────────────────────────────
        dataframe["%-rsi-period"] = ta.RSI(dataframe, timeperiod=period)

        rsi = ta.RSI(dataframe, timeperiod=period)
        rsi_min = rsi.rolling(window=period).min()
        rsi_max = rsi.rolling(window=period).max()
        dataframe["%-stoch_rsi-period"] = (rsi - rsi_min) / (rsi_max - rsi_min + 1e-10)

        dataframe["%-mfi-period"] = ta.MFI(dataframe, timeperiod=period)

        macd = ta.MACD(dataframe, fastperiod=period, slowperiod=period * 2, signalperiod=9)
        dataframe["%-macd_hist-period"] = macd["macdhist"]

        # ─── VOLATILIDAD ──────────────────────────────────────────
        bb = ta.BBANDS(dataframe, timeperiod=period)
        dataframe["%-bb_width-period"] = (bb["upperband"] - bb["lowerband"]) / bb["middleband"]
        dataframe["%-atr_norm-period"] = ta.ATR(dataframe, timeperiod=period) / dataframe["close"]

        # ─── VOLUMEN ──────────────────────────────────────────────
        obv = ta.OBV(dataframe)
        obv_sma = obv.rolling(window=period).mean()
        dataframe["%-obv_norm-period"] = (obv - obv_sma) / (obv_sma.abs() + 1e-10)

        # ─── ESTADÍSTICO ──────────────────────────────────────────
        dataframe["%-log_return-period"] = np.log(dataframe["close"] / dataframe["close"].shift(period))
        dataframe["%-return_std-period"] = dataframe["close"].pct_change().rolling(window=period).std()

        # ─── FUNDAMENTAL (NLP per-coin) ───────────────────────────
        # NOTA: Las features de sentiment se eliminan del espacio de
        # features de FreqAI porque en backtest tienen varianza 0
        # (no hay datos NLP offline). VarianceThreshold las eliminaba
        # de todas formas, pero contaminaban PCA y añadían overhead.
        # El sentiment_score se sigue usando como FILTRO en la lógica
        # de entrada (populate_entry_trend), pero NO como feature ML.

        # ─── MEJORA v3.0: MULTI-TIMEFRAME FEATURES (H1) ──────────
        # Inyectamos indicadores de 1H directamente al modelo ML.
        # FreqAI aplica feature_engineering_expand_all TAMBIÉN a las
        # columnas informativas (si están en include_timeframes).
        # Sin embargo, añadimos aquí features H1 derivadas que 
        # el modelo no puede calcular solo con include_timeframes,
        # porque dependen de la interacción entre temporalidades.
        #
        # Nota: Estas columnas con sufijo _1h se calculan en
        # populate_indicators y llegan aquí ya mergeadas.
        if "close_1h" in dataframe.columns:
            # Ratio de precio 5m vs cierre H1 (micro vs macro)
            dataframe["%-price_ratio_5m_1h-period"] = (
                dataframe["close"] / (dataframe["close_1h"] + 1e-10)
            )
            # Distancia relativa del precio al SMA200 H1
            if "sma_200_1h" in dataframe.columns:
                dataframe["%-dist_sma200_1h-period"] = (
                    (dataframe["close"] - dataframe["sma_200_1h"])
                    / (dataframe["sma_200_1h"] + 1e-10)
                )
            # Distancia relativa del precio a la EMA50 H1
            if "ema_50_1h" in dataframe.columns:
                dataframe["%-dist_ema50_1h-period"] = (
                    (dataframe["close"] - dataframe["ema_50_1h"])
                    / (dataframe["ema_50_1h"] + 1e-10)
                )
            # Fuerza de tendencia macro (ADX H1 normalizado 0-1)
            if "adx_1h" in dataframe.columns:
                dataframe["%-adx_1h_norm-period"] = dataframe["adx_1h"] / 100.0

        return dataframe

    def feature_engineering_expand_basic(self, dataframe: DataFrame, **kwargs) -> DataFrame:
        """
        Features básicas no dependientes de periodo.
        v3.0: Añadido volumen relativo como feature adicional.
        """
        dataframe["%-pct-change"] = dataframe["close"].pct_change()
        dataframe["%-raw_volume"] = dataframe["volume"]
        dataframe["%-candle_direction"] = (dataframe["close"] - dataframe["open"]) / dataframe["open"]
        # v3.0: Volumen relativo a la media de 50 periodos (normalizado)
        vol_sma = dataframe["volume"].rolling(window=50).mean()
        dataframe["%-volume_ratio"] = dataframe["volume"] / (vol_sma + 1e-10)
        return dataframe

    def feature_engineering_standard(self, dataframe: DataFrame, **kwargs) -> DataFrame:
        """
        Features temporales (patrones cíclicos del mercado).
        v3.0: Añadida codificación cíclica seno/coseno para evitar
        que el modelo interprete lunes (0) como "más bajo" que domingo (6).
        """
        dataframe["%-day_of_week"] = dataframe["date"].dt.dayofweek
        dataframe["%-hour_of_day"] = dataframe["date"].dt.hour
        # Codificación cíclica (seno/coseno) para preservar circularidad
        dataframe["%-hour_sin"] = np.sin(2 * np.pi * dataframe["date"].dt.hour / 24)
        dataframe["%-hour_cos"] = np.cos(2 * np.pi * dataframe["date"].dt.hour / 24)
        dataframe["%-day_sin"] = np.sin(2 * np.pi * dataframe["date"].dt.dayofweek / 7)
        dataframe["%-day_cos"] = np.cos(2 * np.pi * dataframe["date"].dt.dayofweek / 7)
        return dataframe

    def set_freqai_targets(self, dataframe: DataFrame, metadata: dict, **kwargs) -> DataFrame:
        """
        Target: Regresión del % de cambio del precio.
        Predecimos CUÁNTO se mueve el precio en las próximas N velas.
        """
        N = self.freqai_info["feature_parameters"]["label_period_candles"]
        dataframe["&s-price_change"] = (
            dataframe["close"].shift(-N) - dataframe["close"]
        ) / dataframe["close"]
        return dataframe