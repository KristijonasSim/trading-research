import logging
import numpy as np
from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta

logger = logging.getLogger(__name__)

class FreqaiStrategy_v2(IStrategy):
    can_short = True
    minimal_roi = {"5": 0.05, "15": 0.03, "30": 0.02, "60": 0}
    timeframe = "15m"
    process_only_new_candles = True
    startup_candle_count = 250

    def leverage(self, pair: str, current_time, current_rate, proposed_leverage, max_leverage, side, **kwargs) -> float:
        return 30.0

    def feature_engineering_expand_all(self, dataframe: DataFrame, period, **kwargs) -> DataFrame:
        dataframe[f"%-rsi-{period}"] = ta.RSI(dataframe, timeperiod=period)
        dataframe[f"%-sma-{period}"] = ta.SMA(dataframe, timeperiod=period)
        dataframe[f"%-atr-{period}"] = ta.ATR(dataframe, timeperiod=period)

        bb = ta.BBANDS(dataframe, timeperiod=period, nbdevup=2.0, nbdevdn=2.0)
        bb_upper = bb["upperband"]
        bb_lower = bb["lowerband"]
        dataframe[f"%-bb_pctb-{period}"] = (dataframe["close"] - bb_lower) / (bb_upper - bb_lower)

        macd = ta.MACD(dataframe, fastperiod=12, slowperiod=26, signalperiod=9)
        dataframe[f"%-macd_hist-{period}"] = macd["macdhist"]

        dataframe[f"%-adx-{period}"] = ta.ADX(dataframe, timeperiod=period)
        return dataframe

    def feature_engineering_standard(self, dataframe: DataFrame, **kwargs) -> DataFrame:
        dataframe["%-day_of_week"] = (dataframe["date"].dt.dayofweek + 1) / 7
        dataframe["%-hour_of_day"] = (dataframe["date"].dt.hour + 1) / 25
        dataframe["%-obv"] = ta.OBV(dataframe)
        ema_50 = ta.EMA(dataframe, timeperiod=50)
        ema_200 = ta.EMA(dataframe, timeperiod=200)
        dataframe["%-ema_50"] = ema_50
        dataframe["%-ema_200"] = ema_200
        dataframe["%-close_ema50_ratio"] = dataframe["close"] / ema_50
        dataframe["%-close_ema200_ratio"] = dataframe["close"] / ema_200

        candle_range = dataframe["high"] - dataframe["low"] + 0.0001
        dataframe["%-body_pct"] = abs(dataframe["close"] - dataframe["open"]) / candle_range
        dataframe["%-upper_wick_pct"] = (dataframe["high"] - np.maximum(dataframe["close"], dataframe["open"])) / candle_range
        dataframe["%-lower_wick_pct"] = (np.minimum(dataframe["close"], dataframe["open"]) - dataframe["low"]) / candle_range

        bb = ta.BBANDS(dataframe, timeperiod=20, nbdevup=2.0, nbdevdn=2.0)
        dataframe["%-bb_width"] = (bb["upperband"] - bb["lowerband"]) / bb["middleband"]

        dataframe["%-vol_sma_20"] = dataframe["volume"].rolling(window=20).mean()
        dataframe["%-vol_ratio"] = dataframe["volume"] / (dataframe["%-vol_sma_20"] + 0.0001)

        up_candle = (dataframe["close"] > dataframe["open"]).astype(float)
        dataframe["%-up_candle"] = up_candle
        dataframe["%-up_ratio_10"] = up_candle.rolling(window=10).mean()

        dataframe["%-ema50_slope"] = (ema_50 / ema_50.shift(5)) - 1
        return dataframe

    def set_freqai_targets(self, dataframe: DataFrame, **kwargs) -> DataFrame:
        future_price = dataframe["close"].shift(
            -self.freqai_info["feature_parameters"]["label_period_candles"]
        )
        dataframe["&-s_close"] = (future_price > dataframe["close"]).astype("float")
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = self.freqai.start(dataframe, metadata, self)
        return dataframe

    def adjust_trade_position(self, trade, current_time, current_rate, current_profit, min_stake, max_stake, **kwargs):
        if current_profit < 0.05:
            return None
        if trade.nr_of_successful_entries >= 2:
            return None
        if (current_time - trade.open_date_utc).total_seconds() > 900:
            return None
        return trade.stake_amount

    def custom_exit(self, pair: str, trade, current_time, current_rate, current_profit, **kwargs):
        if trade.amount == 0 and (current_time - trade.open_date_utc).total_seconds() > 300:
            return "cancel_unfilled"
        
        if (current_time - trade.open_date_utc).total_seconds() < 300:
            return None
        
        max_profit = getattr(trade, 'max_profit', current_profit)
        
        if current_profit > max_profit:
            trade.max_profit = current_profit
            max_profit = current_profit
        
        if max_profit > 0.02 and current_profit < (max_profit * 0.5):
            return "profit_reversal"
        
        if current_profit < -0.06:
            return "stop_loss_custom"
        
        if current_profit > 0.03:
            if current_profit < (max_profit - 0.008):
                return "trailing_aggressive"
        
        return None

    PAIR_DIRECTIONS = {
        "FET/USDT:USDT": "long",
        "HYPE/USDT:USDT": "both",
        "SOL/USDT:USDT": "both",
        "TAO/USDT:USDT": "short",
        "AVAX/USDT:USDT": "long",
        "DOGE/USDT:USDT": "short",
        "SUI/USDT:USDT": "long",
        "NEAR/USDT:USDT": "long",
        "TRUMP/USDT:USDT": "short",
        "XRP/USDT:USDT": "long",
    }

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair = metadata["pair"]
        direction = self.PAIR_DIRECTIONS.get(pair, "both")

        if direction in ("long", "both"):
            dataframe.loc[
                (
                    (dataframe['&-s_close'] > 0.65) &
                    (dataframe['volume'] > 0)
                ),
                'enter_long'] = 1

        if direction in ("short", "both"):
            dataframe.loc[
                (
                    (dataframe['&-s_close'] < 0.35) &
                    (dataframe['volume'] > 0)
                ),
                'enter_short'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        exit_long = (
            (dataframe['&-s_close'] < 0.40) &
            (dataframe['volume'] > 0)
        )

        exit_short = (
            (dataframe['&-s_close'] > 0.60) &
            (dataframe['volume'] > 0)
        )

        dataframe.loc[exit_long, 'exit_long'] = 1
        dataframe.loc[exit_short, 'exit_short'] = 1
        return dataframe
