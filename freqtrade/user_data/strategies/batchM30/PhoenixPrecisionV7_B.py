import talib.abstract as ta
from datetime import datetime, timezone
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from pandas import DataFrame
from functools import reduce
import numpy as np
import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logger = logging.getLogger(__name__)


class PhoenixPrecisionV7_B(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "5m"
    startup_candle_count = 100
    process_only_new_candles = False
    can_short = True
    position_adjustment_enable = False

    minimal_roi = {}

    stoploss = -0.036
    use_custom_stoploss = True

    trailing_stop = False

    max_open_trades = 10

    buy_params = {
        "adx_threshold": 20,
        "ema_fast": 7,
        "ema_slow": 14,
        "volume_factor": 1.5,
        "stake_base_pct": 0.10,
    }

    ema_fast = IntParameter(5, 10, default=7, space="buy")
    ema_slow = IntParameter(12, 22, default=15, space="buy")
    adx_threshold = IntParameter(18, 25, default=20, space="buy")
    volume_factor = DecimalParameter(1.2, 2.0, default=1.5, space="buy")
    stake_base_pct = DecimalParameter(0.05, 0.20, default=0.10, space="buy")

    def informative_pairs(self):
        return []

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self._consecutive_losses = 0
        self._current_trading_day = None
        self._last_regime_str = "unknown"
        self._meta_auc = 0.0
        self._meta_model_loaded = False
        self._trade_count = 0
        self._signal_performance = {}
        self._start_time = datetime.now(timezone.utc)
        self._kalman_last_train = {}
        self._kalman_cache = {}
        self._hmm_last_train = {}
        self._hmm_cache = {}

        try:
            from core.meta_labeler import load_meta_labeler, meta_labeler_loaded
            self._meta_model_loaded = load_meta_labeler()
            if self._meta_model_loaded:
                from core.meta_labeler import _metadata
                self._meta_auc = _metadata.get("auc", 0) if _metadata else 0
                logger.info(f'Meta-labeler loaded (AUC={self._meta_auc:.4f})')
        except Exception as e:
            logger.warning(f'Meta-labeler not available: {e}')

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair_key = metadata.get('pair', 'default')
        current_time = datetime.now()

        for period in range(5, 11):
            dataframe[f"rsi_{period}"] = ta.RSI(dataframe, timeperiod=period)
        dataframe["rsi_14"] = ta.RSI(dataframe, timeperiod=14)

        for period in [7, 14, 21, 50]:
            dataframe[f"ema_{period}"] = ta.EMA(dataframe, timeperiod=period)

        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)
        dataframe["plus_di"] = ta.PLUS_DI(dataframe, timeperiod=14)
        dataframe["minus_di"] = ta.MINUS_DI(dataframe, timeperiod=14)

        macd = ta.MACD(dataframe, fastperiod=8, slowperiod=17, signalperiod=5)
        dataframe["macd"] = macd["macd"]
        dataframe["macdsignal"] = macd["macdsignal"]
        dataframe["macdhist"] = macd["macdhist"]

        bb = ta.BBANDS(dataframe, timeperiod=20, nbdevup=2.0, nbdevdn=2.0)
        dataframe["bb_upper"] = bb["upperband"]
        dataframe["bb_middle"] = bb["middleband"]
        dataframe["bb_lower"] = bb["lowerband"]
        dataframe["bb_width"] = (dataframe["bb_upper"] - dataframe["bb_middle"]) / (dataframe["bb_middle"] + 1e-10)
        dataframe["bb_width_sma"] = ta.SMA(dataframe["bb_width"], timeperiod=20)

        dataframe["volume_ema"] = ta.EMA(dataframe["volume"], timeperiod=10)
        dataframe["volume_ratio"] = dataframe["volume"] / (dataframe["volume_ema"] + 1e-10)
        dataframe["vwap"] = (dataframe["close"] * dataframe["volume"]).rolling(20).sum() / dataframe["volume"].rolling(20).sum()

        dataframe["atr"] = ta.ATR(dataframe, timeperiod=14)
        dataframe["atr_pct"] = dataframe["atr"] / (dataframe["close"] + 1e-10)

        try:
            last_kf = self._kalman_last_train.get(pair_key, datetime.min)
            kf_stale = (current_time - last_kf).total_seconds() > 86400
            if kf_stale or pair_key not in self._kalman_cache:
                from ml.kalman_filter import compute_kalman_features
                kf_features = compute_kalman_features(
                    dataframe['close'].values,
                    dataframe['atr_pct'].values,
                    dataframe['volume_ratio'].values
                )
                self._kalman_cache[pair_key] = kf_features
                self._kalman_last_train[pair_key] = current_time
            else:
                kf_features = self._kalman_cache[pair_key]
            for col, vals in kf_features.items():
                aligned = np.resize(vals, len(dataframe)) if len(vals) != len(dataframe) else vals
                dataframe[col] = np.nan_to_num(aligned, nan=0.0)
        except Exception:
            for col in ['kf_price', 'kf_trend', 'kf_prediction', 'kf_confidence',
                        'kf_direction', 'kf_innovation', 'kf_price_momentum',
                        'kf_trend_acceleration', 'kf_prediction_error', 'kf_regime_score',
                        'kf_vol_of_trend', 'kf_atr_ratio']:
                if col not in dataframe.columns:
                    dataframe[col] = 0.0

        try:
            last_hmm = self._hmm_last_train.get(pair_key, datetime.min)
            hmm_stale = (current_time - last_hmm).total_seconds() > 86400
            if hmm_stale or pair_key not in self._hmm_cache:
                from ml.hmm_regime import compute_hmm_features
                returns = np.log(dataframe['close'] / dataframe['close'].shift(1)).fillna(0)
                vol = returns.rolling(10).std().fillna(0)
                volume_change = dataframe['volume_ratio'].pct_change().fillna(0)
                hmm_features = compute_hmm_features(returns.values, vol.values, volume_change.values)
                self._hmm_cache[pair_key] = hmm_features
                self._hmm_last_train[pair_key] = current_time
            else:
                hmm_features = self._hmm_cache[pair_key]
            for col, vals in hmm_features.items():
                aligned = np.resize(vals, len(dataframe)) if len(vals) != len(dataframe) else vals
                dataframe[col] = np.nan_to_num(aligned, nan=0.0)

            last_row = dataframe.iloc[-1] if len(dataframe) > 0 else None
            if last_row is not None:
                if last_row.get('hmm_p_bull', 0) > 0.6 and last_row.get('hmm_trend_strength', 0) > 1.2:
                    self._last_regime_str = "strong_bull"
                elif last_row.get('hmm_p_bear', 0) > 0.6:
                    self._last_regime_str = "strong_bear"
                else:
                    self._last_regime_str = "sideways"
        except Exception:
            for col in ['hmm_regime', 'hmm_p_bull', 'hmm_p_range', 'hmm_p_bear',
                        'hmm_regime_stability', 'hmm_transition_risk', 'hmm_vol_regime',
                        'hmm_trend_strength']:
                if col not in dataframe.columns:
                    dataframe[col] = 0.0

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0
        dataframe["enter_tag"] = ""

        # Trend mode: breakout when ADX >= 20
        conditions_breakout = [
            dataframe["close"] > dataframe["high"].rolling(5).max().shift(1),
            dataframe["volume_ratio"] > self.volume_factor.value,
            dataframe["adx"] >= self.adx_threshold.value,
            dataframe["close"] > dataframe[f"ema_{self.ema_slow.value}"],
            dataframe[f"ema_{self.ema_fast.value}"] > dataframe[f"ema_{self.ema_slow.value}"],
            dataframe["macdhist"] > 0,
            dataframe["close"] > dataframe["bb_middle"],
            dataframe["plus_di"] > dataframe["minus_di"],
            dataframe["volume"] > 0,
        ]
        sig_breakout = reduce(lambda x, y: x & y, conditions_breakout)

        # Reversion mode: buy pullback when ADX < 20 (ranging)
        conditions_reversion = [
            dataframe["close"] < dataframe["bb_lower"],
            dataframe["rsi_7"] < 30,
            dataframe["adx"] < self.adx_threshold.value,
            dataframe["close"] > dataframe["ema_50"],
            dataframe["volume_ratio"] > 0.5,
            dataframe["volume"] > 0,
        ]
        sig_reversion = reduce(lambda x, y: x & y, conditions_reversion)

        df = dataframe
        df.loc[sig_breakout, ["enter_long", "enter_tag"]] = (1, "breakout_long")
        df.loc[sig_reversion, ["enter_long", "enter_tag"]] = (1, "reversion_long")

        return df

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe

    def custom_exit(self, pair: str, trade, current_time: datetime,
                    current_rate: float, current_profit: float, **kwargs):
        if trade.enter_tag == "reversion_long" and current_profit > 0:
            try:
                dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
                if dataframe is not None and len(dataframe) > 0:
                    last = dataframe.iloc[-1]
                    if last["close"] >= last["bb_middle"]:
                        return "reversion_target"
            except Exception:
                pass
        return None

    def custom_stoploss(self, pair: str, trade, current_time: datetime,
                        current_rate: float, current_profit: float,
                        after_fill: bool, **kwargs) -> float:
        if after_fill:
            return -0.99
        elapsed = (current_time - trade.open_date_utc).total_seconds() / 60
        if elapsed < 5:
            return -0.99
        profit_asset = current_profit / trade.leverage
        if elapsed < 15:
            trail_threshold_asset = 0.0005
        else:
            trail_threshold_asset = 0.0015
        if profit_asset > trail_threshold_asset:
            dynamic_ratio = max(0.10, 0.30 - profit_asset * 20)
            lock_distance = max(profit_asset * dynamic_ratio, trail_threshold_asset * 0.3)
            return -(lock_distance)
        if elapsed < 15:
            return -0.003
        return -0.002

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: str | None,
                 side: str, **kwargs) -> float:
        return 10.0

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                            proposed_stake: float, min_stake: float, max_stake: float,
                            entry_tag: str | None, side: str, **kwargs) -> float:
        wallet = self.wallets.get_total_stake_amount()
        base_pct = float(self.stake_base_pct.value)

        if self._meta_model_loaded and self._meta_auc > 0.55:
            try:
                dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
                if dataframe is not None and len(dataframe) > 0:
                    from core.meta_labeler import _extract_meta_features, _model
                    features = _extract_meta_features(dataframe.iloc[[-1]])
                    proba = _model.predict(features)[0]
                    if proba > 0.7:
                        base_pct = min(base_pct * 1.5, 0.18)
                    elif proba < 0.4:
                        base_pct = base_pct * 0.5
            except Exception as e:
                logger.debug(f'Meta-labeler stake override failed: {e}')

        return max(min_stake, min(wallet * base_pct, max_stake))

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                            time_in_force: str, current_time: datetime, entry_tag: str | None,
                            side: str, **kwargs) -> bool:
        today = current_time.date()
        if self._current_trading_day != today:
            self._current_trading_day = today
            self._consecutive_losses = 0
        if self._consecutive_losses >= 5:
            logger.info(f'Loss breaker active ({self._consecutive_losses} consecutive), rejecting {pair}')
            return False

        if self._last_regime_str == "strong_bear" and side == "long":
            logger.info(f'Regime {self._last_regime_str} blocks LONG {pair}')
            return False

        if self._meta_model_loaded and self._meta_auc > 0.55:
            try:
                dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
                if dataframe is not None and len(dataframe) > 0:
                    from core.meta_labeler import _extract_meta_features, _model
                    features = _extract_meta_features(dataframe.iloc[[-1]])
                    proba = _model.predict(features)[0]
                    if proba < 0.35:
                        logger.info(f'Meta-labeler blocks {pair} (confidence={proba:.3f})')
                        return False
            except Exception as e:
                logger.debug(f'Meta-labeler gate failed: {e}')

        return True

    def confirm_trade_exit(self, pair: str, trade, order_type: str, amount: float,
                           rate: float, time_in_force: str, exit_reason: str,
                           current_time: datetime, **kwargs) -> bool:
        profit_pct = trade.calc_profit_ratio(rate=rate) * 100
        today = current_time.date()
        if self._current_trading_day != today:
            self._current_trading_day = today
            self._consecutive_losses = 0
        if profit_pct < 0:
            self._consecutive_losses += 1
        else:
            self._consecutive_losses = 0
        return True