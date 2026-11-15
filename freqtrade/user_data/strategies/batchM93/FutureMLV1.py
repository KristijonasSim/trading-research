from freqtrade.strategy import IStrategy
from pandas import DataFrame
import numpy as np
import pandas as pd
import talib.abstract as ta
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import os


class FutureMLV1(IStrategy):
    timeframe = '5m'
    max_open_trades = 5
    stake_amount = 0.20
    startup_candle_count = 500

    minimal_roi = {
        "0": 0.02,
        "60": 0.015,
        "180": 0.01,
        "360": 0.005
    }

    stoploss = -0.02
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.015
    trailing_only_offset_is_reached = True

    order_types = {
        'entry': 'market',
        'exit': 'market',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    unfilledtimeout = {
        'entry': 10,
        'exit': 10,
        'unit': 'seconds'
    }

    model_path = '/freqtrade/user_data/ml_models'
    confidence_threshold = 0.55

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = None
        self.scaler = None
        self.feature_names = None
        os.makedirs(self.model_path, exist_ok=True)

    def informative_pairs(self) -> list:
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        df = dataframe.copy()

        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        df['rsi'] = ta.RSI(df['close'].values, timeperiod=14)
        df['rsi_6'] = ta.RSI(df['close'].values, timeperiod=6)
        df['rsi_24'] = ta.RSI(df['close'].values, timeperiod=24)

        df['ema_9'] = ta.EMA(df['close'].values, timeperiod=9)
        df['ema_21'] = ta.EMA(df['close'].values, timeperiod=21)
        df['ema_50'] = ta.EMA(df['close'].values, timeperiod=50)
        df['ema_200'] = ta.EMA(df['close'].values, timeperiod=200)

        macd = ta.MACD(df['close'].values)
        df['macd'] = macd[0]
        df['macd_signal'] = macd[1]
        df['macd_hist'] = macd[2]

        df['bb_upper'] = ta.BBANDS(df['close'].values)[0]
        df['bb_middle'] = ta.BBANDS(df['close'].values)[1]
        df['bb_lower'] = ta.BBANDS(df['close'].values)[2]

        df['atr'] = ta.ATR(df['high'].values, df['low'].values, df['close'].values, timeperiod=14)

        df['volume_sma'] = ta.SMA(df['volume'].values, timeperiod=20)

        close_arr = df['close'].values

        df['momentum'] = close_arr / np.roll(close_arr, 12) - 1
        df['momentum_6'] = close_arr / np.roll(close_arr, 6) - 1
        df['momentum_3'] = close_arr / np.roll(close_arr, 3) - 1

        df['ema_trend'] = (df['ema_9'] - df['ema_50']) / close_arr
        df['ema_trend_2'] = (df['ema_21'] - df['ema_50']) / close_arr

        df['rsi_trend'] = df['rsi'] - np.roll(df['rsi'], 6)

        df['volatility'] = pd.Series(close_arr).pct_change().rolling(12).std().values

        df['price_position'] = close_arr / df['ema_200'] - 1

        df['candle_range'] = (df['high'] - df['low']) / close_arr

        df['return_1'] = pd.Series(close_arr).pct_change(1).values
        df['return_3'] = pd.Series(close_arr).pct_change(3).values
        df['return_6'] = pd.Series(close_arr).pct_change(6).values

        df['volume_ratio'] = df['volume'] / df['volume_sma']

        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        df['bb_position'] = (close_arr - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])

        df['atr_percent'] = df['atr'] / close_arr

        return df

    def create_features(self, df: DataFrame) -> tuple:
        feature_columns = [
            'rsi', 'rsi_6', 'rsi_24',
            'ema_trend', 'ema_trend_2',
            'macd', 'macd_signal', 'macd_hist',
            'bb_position', 'bb_width',
            'atr_percent',
            'volume_ratio',
            'momentum', 'momentum_6', 'momentum_3',
            'rsi_trend',
            'volatility',
            'price_position',
            'candle_range',
            'return_1', 'return_3', 'return_6'
        ]

        available_cols = [c for c in feature_columns if c in df.columns]
        df_features = df[available_cols].copy()

        df_features = df_features.replace([np.inf, -np.inf], np.nan)
        df_features = df_features.fillna(0)

        return df_features.values, available_cols

    def create_labels(self, df: DataFrame, lookahead: int = 3) -> np.ndarray:
        close = df['close'].values
        future = close[lookahead:]
        current = close[:-lookahead]

        returns = (future - current) / current

        labels = np.zeros(len(returns))
        labels[returns > 0.003] = 1
        labels[returns < -0.003] = -1

        return labels

    def train_model(self, df: DataFrame):
        features, feature_names = self.create_features(df)
        labels = self.create_labels(df)

        valid_idx = np.isfinite(features).all(axis=1) & np.isfinite(labels)
        features = features[valid_idx]
        labels = labels[valid_idx]

        if len(features) < 100:
            return False

        self.scaler = StandardScaler()
        features_scaled = self.scaler.fit_transform(features)

        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=20,
            min_samples_leaf=10,
            random_state=42,
            n_jobs=-1
        )

        self.model.fit(features_scaled, labels)
        self.feature_names = feature_names

        return True

    def predict(self, df: DataFrame) -> tuple:
        if self.model is None:
            return 0.5, 0

        features, _ = self.create_features(df)
        features = features[-1:]

        if not np.isfinite(features).all():
            return 0.5, 0

        try:
            features_scaled = self.scaler.transform(features)
        except:
            return 0.5, 0

        try:
            proba = self.model.predict_proba(features_scaled)[0]
        except:
            return 0.5, 0

        if len(proba) < 3:
            return 0.5, 0

        up_prob = proba[2] if len(proba) == 3 else proba[1]
        down_prob = proba[0] if len(proba) == 3 else proba[0]

        confidence = abs(up_prob - down_prob)
        signal = 1 if up_prob > down_prob else -1

        return confidence, signal

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['enter_long'] = 0

        if len(dataframe) < self.startup_candle_count:
            return dataframe

        try:
            if self.model is None:
                df_train = dataframe.iloc[:-10].copy()
                self.train_model(df_train)

            confidence, signal = self.predict(dataframe)

            strong_buy = (confidence > self.confidence_threshold) & (signal == 1)
            dataframe.loc[strong_buy, 'enter_long'] = 1

        except Exception:
            pass

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['exit'] = 0

        if len(dataframe) < self.startup_candle_count:
            return dataframe

        try:
            if self.model is None:
                return dataframe

            confidence, signal = self.predict(dataframe)

            strong_sell = (confidence > self.confidence_threshold) & (signal == -1)
            dataframe.loc[strong_sell, 'exit'] = 1

            if 'rsi' in dataframe.columns:
                overbought = dataframe['rsi'] > 80
                dataframe.loc[overbought, 'exit'] = 1

        except Exception:
            pass

        return dataframe
