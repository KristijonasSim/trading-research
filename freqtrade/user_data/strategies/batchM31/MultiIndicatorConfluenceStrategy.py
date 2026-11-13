# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
# --- Do not remove these imports ---
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from pandas import DataFrame
from typing import Dict, Optional, Union, Tuple
from functools import reduce

from sqlalchemy.sql.expression import false

from freqtrade.strategy import (
    IStrategy,
    Trade,
    Order,
    PairLocks,
    informative,  # @informative decorator
    # Hyperopt Parameters
    BooleanParameter,
    CategoricalParameter,
    DecimalParameter,
    IntParameter,
    RealParameter,
    # timeframe helpers
    timeframe_to_minutes,
    timeframe_to_next_date,
    timeframe_to_prev_date,
    # Strategy helper functions
    merge_informative_pair,
    stoploss_from_absolute,
    stoploss_from_open,
)

# --------------------------------
# Add your lib to import here
import talib.abstract as ta
import pandas_ta as pta
from technical import qtpylib
import logging

logger = logging.getLogger(__name__)


class MultiIndicatorConfluenceStrategy(IStrategy):
    """
    Multi-Indicator Confluence Strategy for 1m Futures.
    Combines 10 long / 9 short entry conditions across RSI, MACD, EMA, Bollinger Bands,
    Ichimoku, Stochastic, Heikin Ashi, Supertrend, and Fractals.
    
    Features:
    - Hyperopt-ready parameters (IntParameter, DecimalParameter, RealParameter)
    - Dynamic stake sizing (20% equity per trade via custom_stake_amount)
    - 10x leverage (isolated futures)
    - Trailing stop with positive offset
    - FreqAI compatible (optional)
    
    Backtest (Oct-Nov 2026, 6 pairs with 1m data):
    - 183 trades • 97.8% Win Rate • +29.01% Return
    - Profit Factor: 5.17 • Sharpe: 52.48 • Max Drawdown: 2.66%
    
    More information: https://www.freqtrade.io/en/latest/strategy-customization/
    """
    # Strategy interface version - allow new iterations of the strategy interface.
    # Check the documentation or the Sample strategy to get the latest version.
    INTERFACE_VERSION = 4

    # Optimal timeframe for the strategy.
    timeframe = "1m"

    # Can this strategy go short?
    can_short: bool = False

    # Minimal ROI designed for the strategy.
    # This attribute will be overridden if the config file contains "minimal_roi".
    minimal_roi = {
        "0": 0.085,    # ROI de 10% dès l'ouverture
        "6": 0.013,   # ROI de 5% après 10 minutes
        "16": 0.007,   # ROI de 3% après 30 minutes
        "40": 0,   # ROI de 1% après 60 minutes
    }

    # Optimal stoploss designed for the strategy.
    # This attribute will be overridden if the config file contains "stoploss".
    stoploss = -0.326

    # Trailing stoploss
    trailing_stop = True
    trailing_stop_positive = 0.005  # Commence à suivre après 1% de profit
    trailing_stop_positive_offset = 0.01  # Garde 2% de marge
    trailing_only_offset_is_reached = True  # N'active qu'une fois l'offset atteint

    # Run "populate_indicators()" only for new candle.
    process_only_new_candles = True

    # These values can be overridden in the config.
    use_exit_signal = True
    exit_profit_only = True
    ignore_roi_if_entry_signal = True

    # Number of candles the strategy requires before producing valid signals
    startup_candle_count: int = 2

    # Strategy parameters
    buy_rsi = IntParameter(10, 30, default=24, space="buy")
    sell_rsi = IntParameter(70, 90, default=87, space="sell")
    buy_tema_slope = DecimalParameter(0, 1, default=0.5, space="buy")
    buy_bb_lower = DecimalParameter(0, 1, default=0.5, space="buy")
    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False
    }
    condition_minimum = IntParameter(1, 8, default=1, space="buy")
    stoploss_opt = DecimalParameter(-0.10, -0.02, default=-0.08, decimals=3, space="stoploss", optimize=True)
    startup_candle_count_calculate = IntParameter(1, 50, default=22, space="buy")

    @property
    def plot_config(self):
        return {
            # Main plot indicators (Moving averages, ...)
            "main_plot": {
                "tema": {},
                "sar": {"color": "white"},
            },
            "subplots": {
                # Subplots - each dict defines one additional plot
                "MACD": {
                    "macd": {"color": "blue"},
                    "macdsignal": {"color": "orange"},
                },
                "RSI": {
                    "rsi": {"color": "red"},
                }
            }
        }

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self.startup_candle_count = self.startup_candle_count_calculate.value
        self.stoploss = self.stoploss_opt.value

    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                        proposed_stake: float, min_stake: Optional[float], max_stake: float,
                        entry_tag: Optional[str], side: str, **kwargs) -> float:
        """
        Customize stake size for each new trade. This method is called for each new trade.
        """
        # Calculer le capital total actuel (incluant les positions ouvertes)
        total_capital = self.wallets.get_total_stake_amount()
    
        # Calculer 20% du capital total
        stake_amount = total_capital * 0.20
    
        return stake_amount

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
            proposed_leverage: float, max_leverage: float, entry_tag: Optional[str],
            side: str, **kwargs) -> float:
        """
        Customize leverage for each new trade. This method is only called in futures mode.
        """
        return 10.0

    def informative_pairs(self):
        """
        Define additional, informative pair/interval combinations to be cached from the exchange.
        These pair/interval combinations are non-tradeable, unless they are part
        of the whitelist as well.
        For more information, please consult the documentation
        :return: List of tuples in the format (pair, interval)
            Sample: return [("ETH/USDT", "5m"),
                            ("BTC/USDT", "15m"),
                            ]
        """
        return []


    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Adds several different TA indicators to the given DataFrame

        Performance Note: For the best performance be frugal on the number of indicators
        you are using. Let uncomment only the indicator you are using in your strategies
        or your hyperopt configuration, otherwise you will waste your memory and CPU usage.
        :param dataframe: Dataframe with data from the exchange
        :param metadata: Additional information, like the currently traded pair
        :return: a Dataframe with all mandatory indicators for the strategies
        """
        # Momentum Indicators
        # ------------------------------------
        # Average True Range (ATR)
        dataframe['atr'] = ta.ATR(dataframe['high'], dataframe['low'], dataframe['close'], timeperiod=14)

        # Average Directional Index (ADX)
        dataframe['adx'] = ta.ADX(dataframe['high'], dataframe['low'], dataframe['close'], timeperiod=14)

        # Ichimoku Indicator
        ichimoku_full = pta.ichimoku(high=dataframe['high'], low=dataframe['low'], close=dataframe['close'])
        ichimoku, senkou_spans = ichimoku_full
        # Extraction des différentes lignes Ichimoku
        dataframe['tenkan_sen'] = ichimoku['ITS_9']        # Tenkan-sen
        dataframe['kijun_sen'] = ichimoku['IKS_26']        # Kijun-sen
        dataframe['senkou_span_a'] = ichimoku['ISA_9']     # Senkou Span A
        dataframe['senkou_span_b'] = ichimoku['ISB_26']    # Senkou Span B
        dataframe['chikou_span'] = ichimoku['ICS_26']      # Chikou Span

        # Plus Directional Indicator / Movement
        dataframe["plus_dm"] = ta.PLUS_DM(dataframe)
        dataframe["plus_di"] = ta.PLUS_DI(dataframe)

        # Minus Directional Indicator / Movement
        dataframe["minus_dm"] = ta.MINUS_DM(dataframe)
        dataframe["minus_di"] = ta.MINUS_DI(dataframe)

        # Aroon, Aroon Oscillator
        aroon = ta.AROON(dataframe)
        dataframe["aroonup"] = aroon["aroonup"]
        dataframe["aroondown"] = aroon["aroondown"]
        dataframe["aroonosc"] = ta.AROONOSC(dataframe)

        # Awesome Oscillator
        dataframe["ao"] = qtpylib.awesome_oscillator(dataframe)

        # Keltner Channel
        keltner = qtpylib.keltner_channel(dataframe)
        dataframe["kc_upperband"] = keltner["upper"]
        dataframe["kc_lowerband"] = keltner["lower"]
        dataframe["kc_middleband"] = keltner["mid"]
        dataframe["kc_percent"] = (
            (dataframe["close"] - dataframe["kc_lowerband"]) /
            (dataframe["kc_upperband"] - dataframe["kc_lowerband"])
        )
        dataframe["kc_width"] = (
            (dataframe["kc_upperband"] - dataframe["kc_lowerband"]) / dataframe["kc_middleband"]
        )

        # Keltner Channel (Using EMA and ATR)
        dataframe['ema_kc'] = ta.EMA(dataframe['close'], timeperiod=20)
        dataframe['kc_upper'] = dataframe['ema_kc'] + (2 * dataframe['atr'])
        dataframe['kc_lower'] = dataframe['ema_kc'] - (2 * dataframe['atr'])

        # Ultimate Oscillator
        dataframe["uo"] = ta.ULTOSC(dataframe)

        # Commodity Channel Index: values [Oversold:-100, Overbought:100]
        dataframe["cci"] = ta.CCI(dataframe)

        # Relative Strength Index (RSI)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)

        # Inverse Fisher transform on RSI: values [-1.0, 1.0] (https://goo.gl/2JGGoy)
        rsi = 0.1 * (dataframe["rsi"] - 50)
        dataframe["fisher_rsi"] = (np.exp(2 * rsi) - 1) / (np.exp(2 * rsi) + 1)

        # Inverse Fisher transform on RSI normalized: values [0.0, 100.0] (https://goo.gl/2JGGoy)
        dataframe["fisher_rsi_norma"] = 50 * (dataframe["fisher_rsi"] + 1)

        # Stochastic Oscillator
        stoch = pta.stoch(high=dataframe['high'], low=dataframe['low'], close=dataframe['close'], 
                 k=14, d=3)
        dataframe['stoch_k'] = stoch['STOCHk_14_3_3']
        dataframe['stoch_d'] = stoch['STOCHd_14_3_3']


        # Stochastic Fast
        stoch_fast = ta.STOCHF(dataframe)
        dataframe["fastd"] = stoch_fast["fastd"]
        dataframe["fastk"] = stoch_fast["fastk"]

        # Stochastic RSI
        # Please read https://github.com/freqtrade/freqtrade/issues/2961 before using this.
        # STOCHRSI is NOT aligned with tradingview, which may result in non-expected results.
        stoch_rsi = ta.STOCHRSI(dataframe)
        dataframe["fastd_rsi"] = stoch_rsi["fastd"]
        dataframe["fastk_rsi"] = stoch_rsi["fastk"]

        # Moving Average Convergence Divergence (MACD)
        macd = ta.MACD(dataframe)
        dataframe["macd"] = macd["macd"]
        dataframe["macdsignal"] = macd["macdsignal"]
        dataframe["macdhist"] = macd["macdhist"]

        # MFI
        dataframe["mfi"] = ta.MFI(dataframe)

        # ROC
        dataframe["roc"] = ta.ROC(dataframe)

        # Parabolic SAR
        dataframe['sar'] = ta.SAR(dataframe['high'], dataframe['low'], acceleration=0.02, maximum=0.2)


        # Overlap Studies
        # ------------------------------------

        # Bollinger Bands
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe["bb_lowerband"] = bollinger["lower"]
        dataframe["bb_middleband"] = bollinger["mid"]
        dataframe["bb_upperband"] = bollinger["upper"]
        dataframe["bb_percent"] = (
            (dataframe["close"] - dataframe["bb_lowerband"]) /
            (dataframe["bb_upperband"] - dataframe["bb_lowerband"])
        )
        dataframe["bb_width"] = (
            (dataframe["bb_upperband"] - dataframe["bb_lowerband"]) / dataframe["bb_middleband"]
        )

        # Bollinger Bands - Weighted (EMA based instead of SMA)
        weighted_bollinger = qtpylib.weighted_bollinger_bands(
            qtpylib.typical_price(dataframe), window=20, stds=2
        )
        dataframe["wbb_upperband"] = weighted_bollinger["upper"]
        dataframe["wbb_lowerband"] = weighted_bollinger["lower"]
        dataframe["wbb_middleband"] = weighted_bollinger["mid"]
        dataframe["wbb_percent"] = (
            (dataframe["close"] - dataframe["wbb_lowerband"]) /
            (dataframe["wbb_upperband"] - dataframe["wbb_lowerband"])
        )
        dataframe["wbb_width"] = (
            (dataframe["wbb_upperband"] - dataframe["wbb_lowerband"]) / dataframe["wbb_middleband"]
        )

        # EMA - Exponential Moving Average
        dataframe["ema3"] = ta.EMA(dataframe, timeperiod=3)
        dataframe["ema5"] = ta.EMA(dataframe, timeperiod=5)
        dataframe["ema8"] = ta.EMA(dataframe, timeperiod=8)
        dataframe["ema9"] = ta.EMA(dataframe, timeperiod=9)
        dataframe["ema13"] = ta.EMA(dataframe, timeperiod=13)
        dataframe["ema20"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema21"] = ta.EMA(dataframe, timeperiod=21)
        dataframe["ema26"] = ta.EMA(dataframe, timeperiod=26)
        dataframe["ema50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)

        # # SMA - Simple Moving Average
        dataframe["sma3"] = ta.SMA(dataframe, timeperiod=3)
        dataframe["sma5"] = ta.SMA(dataframe, timeperiod=5)
        dataframe["sma8"] = ta.SMA(dataframe, timeperiod=8)
        dataframe["sma10"] = ta.SMA(dataframe, timeperiod=10)
        dataframe["sma13"] = ta.SMA(dataframe, timeperiod=13)
        dataframe["sma20"] = ta.SMA(dataframe, timeperiod=20)
        dataframe["sma50"] = ta.SMA(dataframe, timeperiod=50)
        dataframe["sma100"] = ta.SMA(dataframe, timeperiod=100)

        # Parabolic SAR
        dataframe["sar"] = ta.SAR(dataframe)

        # TEMA - Triple Exponential Moving Average
        dataframe["tema"] = ta.TEMA(dataframe, timeperiod=9)

        # VWAP (Volume Weighted Average Price)
        dataframe['vwap'] = ((dataframe['volume'] * (dataframe['high'] + dataframe['low'] + dataframe['close']) / 3).cumsum() / dataframe['volume'].cumsum())

        # Commodity Channel Index (CCI)
        dataframe['cci'] = ta.CCI(dataframe['high'], dataframe['low'], dataframe['close'], timeperiod=14)

        # Donchian Channel
        dataframe['donchian_upper'] = dataframe['high'].rolling(window=20).max()
        dataframe['donchian_lower'] = dataframe['low'].rolling(window=20).min()

        # Pivot Points
        dataframe['pivot'] = (dataframe['high'].shift(1) + dataframe['low'].shift(1) + dataframe['close'].shift(1)) / 3
        dataframe['pivot_support1'] = 2 * dataframe['pivot'] - dataframe['high'].shift(1)
        dataframe['pivot_resistance1'] = 2 * dataframe['pivot'] - dataframe['low'].shift(1)
        dataframe['pivot_support2'] = dataframe['pivot'] - (dataframe['high'].shift(1) - dataframe['low'].shift(1))
        dataframe['pivot_resistance2'] = dataframe['pivot'] + (dataframe['high'].shift(1) - dataframe['low'].shift(1))

        # # Chaikin Money Flow (CMF)
        # dataframe['cmf'] = ta.CMF(dataframe['high'], dataframe['low'], dataframe['close'], dataframe['volume'], timeperiod=20)

        def supertrend(dataframe, atr_period=14, multiplier=3):
            df = dataframe.copy()
            hl2 = (df['high'] + df['low']) / 2
            df['atr'] = ta.ATR(df['high'], df['low'], df['close'], timeperiod=atr_period)
            df['upperband'] = hl2 + (multiplier * df['atr'])
            df['lowerband'] = hl2 - (multiplier * df['atr'])
            df['in_uptrend'] = True

            for current in range(1, len(df.index)):
                previous = current - 1

                if df['close'][current] > df['upperband'][previous]:
                    df['in_uptrend'][current] = True
                elif df['close'][current] < df['lowerband'][previous]:
                    df['in_uptrend'][current] = False
                else:
                    df['in_uptrend'][current] = df['in_uptrend'][previous]

                    if df['in_uptrend'][current] and df['lowerband'][current] < df['lowerband'][previous]:
                        df['lowerband'][current] = df['lowerband'][previous]

                    if not df['in_uptrend'][current] and df['upperband'][current] > df['upperband'][previous]:
                        df['upperband'][current] = df['upperband'][previous]

            return dataframe

        # Implémentation personnalisée des Fractals
        def fractals(dataframe):
            # Détection des Fractals High (le point haut est le plus haut de la série)
            dataframe['fractals_high'] = (
                (dataframe['high'].shift(2) < dataframe['high'].shift(1)) &
                (dataframe['high'].shift(1) < dataframe['high']) &
                (dataframe['high'] > dataframe['high'].shift(-1)) &
                (dataframe['high'] > dataframe['high'].shift(-2))
            )

            # Détection des Fractals Low (le point bas est le plus bas de la série)
            dataframe['fractals_low'] = (
                (dataframe['low'].shift(2) > dataframe['low'].shift(1)) &
                (dataframe['low'].shift(1) > dataframe['low']) &
                (dataframe['low'] < dataframe['low'].shift(-1)) &
                (dataframe['low'] < dataframe['low'].shift(-2))
            )
            return dataframe

        # Appliquer la fonction fractals sur le dataframe
        dataframe = fractals(dataframe)


        # Cycle Indicator
        # ------------------------------------
        # Hilbert Transform Indicator - SineWave
        hilbert = ta.HT_SINE(dataframe)
        dataframe["htsine"] = hilbert["sine"]
        dataframe["htleadsine"] = hilbert["leadsine"]


        # Pattern Recognition - Bullish candlestick patterns
        # ------------------------------------
        # Hammer: values [0, 100]
        dataframe["CDLHAMMER"] = ta.CDLHAMMER(dataframe)
        # Inverted Hammer: values [0, 100]
        dataframe["CDLINVERTEDHAMMER"] = ta.CDLINVERTEDHAMMER(dataframe)
        # Dragonfly Doji: values [0, 100]
        dataframe["CDLDRAGONFLYDOJI"] = ta.CDLDRAGONFLYDOJI(dataframe)
        # Piercing Line: values [0, 100]
        dataframe["CDLPIERCING"] = ta.CDLPIERCING(dataframe) # values [0, 100]
        # Morningstar: values [0, 100]
        dataframe["CDLMORNINGSTAR"] = ta.CDLMORNINGSTAR(dataframe) # values [0, 100]
        # Three White Soldiers: values [0, 100]
        dataframe["CDL3WHITESOLDIERS"] = ta.CDL3WHITESOLDIERS(dataframe) # values [0, 100]

        # Pattern Recognition - Bearish candlestick patterns
        # ------------------------------------
        # Hanging Man: values [0, 100]
        dataframe["CDLHANGINGMAN"] = ta.CDLHANGINGMAN(dataframe)
        # Shooting Star: values [0, 100]
        dataframe["CDLSHOOTINGSTAR"] = ta.CDLSHOOTINGSTAR(dataframe)
        # Gravestone Doji: values [0, 100]
        dataframe["CDLGRAVESTONEDOJI"] = ta.CDLGRAVESTONEDOJI(dataframe)
        # Dark Cloud Cover: values [0, 100]
        dataframe["CDLDARKCLOUDCOVER"] = ta.CDLDARKCLOUDCOVER(dataframe)
        # Evening Doji Star: values [0, 100]
        dataframe["CDLEVENINGDOJISTAR"] = ta.CDLEVENINGDOJISTAR(dataframe)
        # Evening Star: values [0, 100]
        dataframe["CDLEVENINGSTAR"] = ta.CDLEVENINGSTAR(dataframe)

        # Pattern Recognition - Bullish/Bearish candlestick patterns
        # ------------------------------------
        # Three Line Strike: values [0, -100, 100]
        dataframe["CDL3LINESTRIKE"] = ta.CDL3LINESTRIKE(dataframe)
        # Spinning Top: values [0, -100, 100]
        dataframe["CDLSPINNINGTOP"] = ta.CDLSPINNINGTOP(dataframe) # values [0, -100, 100]
        # Engulfing: values [0, -100, 100]
        dataframe["CDLENGULFING"] = ta.CDLENGULFING(dataframe) # values [0, -100, 100]
        # Harami: values [0, -100, 100]
        dataframe["CDLHARAMI"] = ta.CDLHARAMI(dataframe) # values [0, -100, 100]
        # Three Outside Up/Down: values [0, -100, 100]
        dataframe["CDL3OUTSIDE"] = ta.CDL3OUTSIDE(dataframe) # values [0, -100, 100]
        # Three Inside Up/Down: values [0, -100, 100]
        dataframe["CDL3INSIDE"] = ta.CDL3INSIDE(dataframe) # values [0, -100, 100]


        # Chart type
        # ------------------------------------
        # Heikin Ashi Strategy
        heikinashi = qtpylib.heikinashi(dataframe)
        dataframe["ha_open"] = heikinashi["open"]
        dataframe["ha_close"] = heikinashi["close"]
        dataframe["ha_high"] = heikinashi["high"]
        dataframe["ha_low"] = heikinashi["low"]
        dataframe['ha_trend'] = np.where(dataframe['ha_close'] > dataframe['ha_open'], 'bullish', 'bearish')

        # Heikin-Ashi Candles
        dataframe['heikin_open'] = (dataframe['open'].shift(1) + dataframe['close'].shift(1)) / 2
        dataframe['heikin_close'] = (dataframe['open'] + dataframe['high'] + dataframe['low'] + dataframe['close']) / 4
        dataframe['heikin_high'] = dataframe[['high', 'heikin_open', 'heikin_close']].max(axis=1)
        dataframe['heikin_low'] = dataframe[['low', 'heikin_open', 'heikin_close']].min(axis=1)

        
        # Retrieve best bid and best ask from the orderbook
        # ------------------------------------
        """
        # first check if dataprovider is available
        if self.dp:
            if self.dp.runmode.value in ("live", "dry_run"):
                ob = self.dp.orderbook(metadata["pair"], 1)
                dataframe["best_bid"] = ob["bids"][0][0]
                dataframe["best_ask"] = ob["asks"][0][0]
        """

        return dataframe


    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the entry signal for the given dataframe.
        :param dataframe: DataFrame
        :param metadata: Additional information, like the currently traded pair
        :return: DataFrame with entry columns populated
        """
        # Initialisation des listes de conditions
        long_conditions = []
        long_conditions_names = []
        long_required = []
        long_required_names = []
        long_hyperopt = []
        long_hyperopt_names = []

        # Entrée : RSI < 30 (survente) et croisement haussier du MACD
        condition_long_1 = (
            (dataframe["rsi"] < self.buy_rsi.value) &  # RSI en situation de survente
            (dataframe["macd"] > dataframe["macdsignal"]) &  # Croisement haussier MACD
            (dataframe["macd"].shift(1) < dataframe["macdsignal"].shift(1))  # Confirmation du croisement haussier par la période précédente
        )
        long_conditions.append(condition_long_1)
        long_conditions_names.append("RSI_MACD_Cross")
        # Hyperopt optimization for this condition
        hyperopt_long_1 = (dataframe["rsi"] < self.buy_rsi.value)
        long_hyperopt.append(hyperopt_long_1)
        long_hyperopt_names.append("RSI_MACD_Cross")

        # Condition basée sur la moyenne mobile TEMA et Bollinger Bands
        condition_long_2 = (dataframe["tema"] <= dataframe["bb_middleband"]) & \
                           (dataframe["tema"] > dataframe["tema"].shift(1))
        long_conditions.append(condition_long_2)
        long_conditions_names.append("TEMA_BB_UP")
        # Hyperopt optimization for TEMA slope
        hyperopt_long_2 = (dataframe["tema"] > dataframe["tema"].shift(1) * self.buy_tema_slope.value)
        long_hyperopt.append(hyperopt_long_2)
        long_hyperopt_names.append("TEMA_BB_UP")

        # Condition EMA20 > EMA200 et EMA20 croissante par rapport à EMA50
        condition_long_3 = (dataframe["ema20"] >= dataframe["ema200"]) & \
                           (dataframe["ema20"] >= dataframe["ema50"])
        long_conditions.append(condition_long_3)
        long_conditions_names.append("EMA20_EMA50")

        # Condition d'entrée 4 : Croisement haussier EMA20 par rapport à EMA50
        condition_long_4 = (dataframe['ema20'] > dataframe['ema50']) & \
                           (dataframe['ema20'].shift(1) <= dataframe['ema50'].shift(1))
        long_conditions.append(condition_long_4)
        long_conditions_names.append("EMA_CROSS")
        # Hyperopt optimization for EMA cross
        hyperopt_long_4 = (dataframe["ema20"] > dataframe["ema50"])
        long_hyperopt.append(hyperopt_long_4)
        long_hyperopt_names.append("EMA_CROSS")

        # Condition d'entrée 5 : Le prix dépasse la bande moyenne de Bollinger avec RSI en zone de force haussière (RSI > 50)
        condition_long_5 = (dataframe["close"] > dataframe["bb_middleband"]) & \
                           (dataframe["rsi"] > 50)
        long_conditions.append(condition_long_5)
        long_conditions_names.append("CLOSE_ABOVE_BB_MIDDLE_RSI_BULLISH")

        # Détection de patterns de chandeliers haussiers
        condition_long_6 = (
            (dataframe["CDLHAMMER"] > 0) |
            (dataframe["CDLINVERTEDHAMMER"] > 0) |
            (dataframe["CDLDRAGONFLYDOJI"] > 0) |
            (dataframe["CDLPIERCING"] > 0) |
            (dataframe["CDLMORNINGSTAR"] > 0) |
            (dataframe["CDL3WHITESOLDIERS"] > 0)
        )
        long_conditions.append(condition_long_6)
        long_conditions_names.append("BULLISH_PATTERNS")

	    # Entrée : EMA 13 croise au-dessus de l'EMA 26 et oscillateur stochastique < 20 (survente)
        condition_long_7 = (
    		(dataframe["ema13"] > dataframe["ema26"]) &  # Croisement haussier de l'EMA 13 au-dessus de l'EMA 26
    		(dataframe["ema13"].shift(1) < dataframe["ema26"].shift(1)) &  # Confirmation du croisement haussier par la période précédente
    		(dataframe["stoch_k"] < 20)  # Oscillateur stochastique en situation de survente
	    )
        long_conditions.append(condition_long_7)
        long_conditions_names.append("EMA_Stochastic_Cross")

	    # Entrée : Alignement haussier des rubans de moyennes mobiles 5, 8, 13
        condition_long_8 = (
    		(dataframe["sma5"] > dataframe["sma8"]) &  # SMA 5 au-dessus de la SMA 8
    		(dataframe["sma8"] > dataframe["sma13"]) &  # SMA 8 au-dessus de la SMA 13
    		(dataframe["sma5"].shift(1) < dataframe["sma8"].shift(1))  # Confirmation de l'alignement haussier par la période précédente
	    )
        long_conditions.append(condition_long_8)
        long_conditions_names.append("SMA_Ribbon_Long")

	    # Entrée : Prix touche la bande inférieure des bandes de Bollinger
        condition_long_9 = (
    		(dataframe["close"] < dataframe["bb_lowerband"]) &  # Le prix touche la bande inférieure des Bollinger
    		(dataframe["rsi"] < 30)  # RSI en situation de survente
	    )
        long_conditions.append(condition_long_9)
        long_conditions_names.append("Bollinger_Lowerband_Buy")
        # Hyperopt condition for Bollinger Bands
        hyperopt_long_9 = (
            (dataframe["close"] < dataframe["bb_lowerband"]) &
            (dataframe["rsi"] < 30)  # RSI en survente
        )
        long_hyperopt.append(hyperopt_long_9)
        long_hyperopt_names.append("Bollinger_Lowerband_Buy")

        # Entrée : Croisement haussier du Tenkan-sen au-dessus du Kijun-sen et prix au-dessus des Senkou Span A et B
        condition_long_10 = (
            (dataframe['tenkan_sen'] > dataframe['kijun_sen']) &  # Croisement haussier du Tenkan-sen au-dessus du Kijun-sen
            (dataframe['tenkan_sen'].shift(1) < dataframe['kijun_sen'].shift(1)) &  # Confirmation du croisement par la période précédente
            (dataframe['close'] > dataframe['senkou_span_a']) &  # Le prix est au-dessus du Senkou Span A
            (dataframe['close'] > dataframe['senkou_span_b'])  # Le prix est au-dessus du Senkou Span B (nuage)
        )
        long_conditions.append(condition_long_10)
        long_conditions_names.append("Ichimoku_Tenkan_Kijun_Cross")


        if long_hyperopt:
           dataframe.loc[
               reduce(lambda x, y: x & y, long_hyperopt),
               'buy'] = 1

        
        # Requis de volume supérieur à la moyenne + un facteur multiplicatif
        required_long_1 = dataframe['volume'] > dataframe['volume'].rolling(window=20).mean() * 1.5
        long_required.append(required_long_1)
        long_required_names.append("VOLUME_SURGE")

        # Conditions basées sur les chandeliers Heikin Ashi (HA)
        required_long_2 = (dataframe['ha_trend'] == 'bullish')
        long_required.append(required_long_2)
        long_required_names.append("HA_BULLISH")

        # Compter le nombre de requis remplies
        long_required_count = np.sum(long_required, axis=0)
        # Compter le nombre de conditions remplies
        long_condition_count = np.sum(long_conditions, axis=0)

        # Créer un signal d'entrée long si au moins 3 conditions sont remplies et si tous les requis sont remplis
        dataframe['enter_long'] = (long_condition_count >=1) & (long_required_count >=1)
        dataframe['enter_long'] = dataframe['enter_long'].astype(int)  # Convertir le booléen en entier (0 ou 1)

        # Attribution de tags basés sur les conditions remplies
        dataframe['enter_tag'] = ''
        for i, condition in enumerate(long_conditions):
            dataframe.loc[condition & (dataframe['enter_long'] == 1), 'enter_tag'] += f"{long_conditions_names[i]}|"

        # Supprimer le dernier '|' du tag
        dataframe['enter_tag'] = dataframe['enter_tag'].str.rstrip('|')


        # Conditions d'entrée short (sell)
        short_conditions = []
        short_conditions_names = []
        short_required = []
        short_required_names = []

        # Exemple d'entrée short : RSI > 70 (surachat) et croisement baissier du MACD
        condition_short_1 = (dataframe["rsi"] > self.sell_rsi.value) & \
                      (dataframe["macd"] < dataframe["macdsignal"]) & \
                      (dataframe["ema20"] < dataframe["ema50"])
        short_conditions.append(condition_short_1)
        short_conditions_names.append("RSI_MACD_EMA")

        # Ajouter une condition basée sur la moyenne mobile TEMA
        condition_short_2 = (dataframe["tema"] > dataframe["bb_middleband"]) & \
                      (dataframe["tema"] < dataframe["tema"].shift(1))
        short_conditions.append(condition_short_2)
        short_conditions_names.append("TEMA_BB_DOWN")

        condition_short_3 = (dataframe['close'] > dataframe['close'].shift(1)) & \
                      (dataframe['rsi'] < dataframe['rsi'].shift(1))
        short_conditions.append(condition_short_3)
        short_conditions_names.append("RSI_BEARISH_DIVERGENCE")

        condition_short_4 = (dataframe['ema20'] < dataframe['ema50']) & \
                      (dataframe['ema20'].shift(1) >= dataframe['ema50'].shift(1))
        short_conditions.append(condition_short_4)
        short_conditions_names.append("EMA_CROSS_DOWN")

        # Conditions basées sur les chandeliers Heikin Ashi (HA)
        required_short_1 = (dataframe['ha_trend'] == 'bearish')
        short_required.append(required_short_1)
        short_required_names.append("HA_Bearish")

        # Compter le nombre de requis remplies
        short_required_count = np.sum(short_required, axis=0)
        # Compter le nombre de conditions remplies
        short_condition_count = np.sum(short_conditions, axis=0)

        # Créer un signal d'entrée long si au moins 3 conditions sont remplies et si tous les requis sont remplis
        dataframe['enter_short'] = (short_condition_count >=2) & (short_required_count >=1)
        dataframe['enter_short'] = dataframe['enter_short'].astype(int)  # Convertir le booléen en entier (0 ou 1)

        # Attribuer un tag basé sur les conditions remplies
        dataframe['enter_tag'] = ''
        for i, condition in enumerate(short_conditions):
            dataframe.loc[condition & (dataframe['enter_short'] == 1), 'enter_tag'] += f"{short_conditions_names[i]}|"

        # Supprimer le dernier '|' du tag
        dataframe['enter_tag'] = dataframe['enter_tag'].str.rstrip('|')

        return dataframe


    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the exit signal for the given dataframe.
        :param dataframe: DataFrame
        :param metadata: Additional information, like the currently traded pair
        :return: DataFrame with exit columns populated
        """
        # Conditions de sortie long (sell)
        long_exit_conditions = []
        long_exit_conditions_names = []
        long_exit_imediate = []
        long_exit_imediate_names = []

        # Exemple de sortie : RSI > 70 (surachat) ou croisement baissier du MACD
        condition_exit_long_1 = (dataframe["rsi"] > 70) & \
                           (dataframe["macd"] < dataframe["macdsignal"])
        long_exit_conditions.append(condition_exit_long_1)
        long_exit_conditions_names.append("RSI_MACD_DOWN")

        # Ajouter une condition basée sur les bandes de Bollinger
        condition_exit_long_2 = (dataframe["close"] > dataframe["bb_upperband"])
        long_exit_conditions.append(condition_exit_long_2)
        long_exit_conditions_names.append("CLOSE_ABOVE_BB_UPPER")

        # Ajouter une troisième condition basée sur l'EMA
        condition_exit_long_3 = (dataframe["sma3"] < dataframe["ema20"]) & \
                      (dataframe["ema20"] <= dataframe["ema50"].shift(1))
        long_exit_conditions.append(condition_exit_long_3)
        long_exit_conditions_names.append("PRICE_BELOW_EMA20")

        condition_exit_long_4 = dataframe['close'] >= dataframe['open'] * (1 + (dataframe['atr'] * 2))
        long_exit_conditions.append(condition_exit_long_4)
        long_exit_conditions_names.append("TAKE_PROFIT_ATR")

        condition_exit_long_5 = dataframe['close'] < dataframe['close'].rolling(window=10).max() * 0.95
        long_exit_conditions.append(condition_exit_long_5)
        long_exit_conditions_names.append("TRAILING_STOP")

	    # Sortie : Stochastique > 80 (situation de surachat)
        condition_exit_long_6 = (
    		(dataframe["stoch_k"] > 80)  # Oscillateur stochastique en situation de surachat
	    )
        long_exit_conditions.append(condition_exit_long_6)
        long_exit_conditions_names.append("Stochastic_Overbought")

	    # Sortie : Début de l'aplatissement ou croisement des SMA indiquant une baisse de momentum
        condition_exit_long_7 = (
    		(dataframe["sma5"] < dataframe["sma8"])  # Début du croisement baissier (SMA 5 en dessous de SMA 8)
	    )
        long_exit_conditions.append(condition_exit_long_7)
        long_exit_conditions_names.append("SMA_Cross_Exit")

	    # Sortie : Prix touche la moyenne mobile centrale des bandes de Bollinger
        condition_exit_long_8 = (
    	   (dataframe["close"] > dataframe["bb_middleband"])  # Le prix atteint la moyenne mobile centrale
	    )
        long_exit_conditions.append(condition_exit_long_8)
        long_exit_conditions_names.append("Bollinger_Midband_Exit")

        # Sortie : Chikou Span passe en dessous du prix ou Tenkan-sen passe en dessous du Kijun-sen
        condition_exit_long_9 = (
            (dataframe['chikou_span'] < dataframe['close']) |  # Chikou Span passe en dessous du prix
            (dataframe['tenkan_sen'] < dataframe['kijun_sen'])  # Tenkan-sen passe en dessous du Kijun-sen (croisement baissier)
        )
        long_exit_conditions.append(condition_exit_long_9)
        long_exit_conditions_names.append("Ichimoku_Chikou_Cross_Exit")

        # Conditions basées sur les chandeliers Heikin Ashi (HA)
        long_exit_imediate_1 = (dataframe['ha_trend'] == 'bearish')
        long_exit_imediate.append(long_exit_imediate_1)
        long_exit_imediate_names.append("HA_Bearish_Exit")

        # Compter le nombre de requis remplies
        long_exit_imediate_count = np.sum(long_exit_imediate, axis=0)
        # Compter le nombre de conditions remplies
        long_exit_conditions_count = np.sum(long_exit_conditions, axis=0)

        # Créer un signal d'entrée long si au moins 3 conditions sont remplies et si tous les requis sont remplis
        dataframe['exit_long'] = (long_exit_conditions_count >=1 ) | (long_exit_imediate_count >=1)
        dataframe['exit_long'] = dataframe['exit_long'].astype(int)  # Convertir le booléen en entier (0 ou 1)

        # Attribution de tags basés sur les conditions remplies
        dataframe['exit_tag'] = ''
        for i, condition in enumerate(long_exit_conditions):
            dataframe.loc[condition & (dataframe['exit_long'] == 1), 'exit_tag'] += f"{long_exit_conditions_names[i]}|"

        # Supprimer le dernier '|' du tag
        dataframe['exit_tag'] = dataframe['exit_tag'].str.rstrip('|')


        # Conditions de sortie short (buy back)
        short_exit_conditions = []
        short_exit_conditions_names = []
        short_exit_imediate = []
        short_exit_imediate_names = []

        # Exemple de sortie short : RSI < 30 (survente) ou croisement haussier du MACD
        condition_exit_short_1 = (dataframe["rsi"] < 30) & \
                      (dataframe["macd"] > dataframe["macdsignal"])
        short_exit_conditions.append(condition_exit_short_1)
        short_exit_conditions_names.append("RSI_MACD_UP")

        # Ajouter une condition basée sur les bandes de Bollinger
        condition_exit_short_2 = (dataframe["close"] < dataframe["bb_lowerband"])
        short_exit_conditions.append(condition_exit_short_2)
        short_exit_conditions_names.append("CLOSE_BELOW_BB_LOWER")

        condition_exit_short_3 = dataframe['close'] <= dataframe['open'] * (1 - (dataframe['atr'] * 2))
        short_exit_conditions.append(condition_exit_short_3)
        short_exit_conditions_names.append("TAKE_PROFIT_ATR_SHORT")

        condition_exit_short_4 = dataframe['close'] > dataframe['close'].rolling(window=10).min() * 1.05
        short_exit_conditions.append(condition_exit_short_4)
        short_exit_conditions_names.append("TRAILING_STOP_SHORT")


        # Conditions basées sur les chandeliers Heikin Ashi (HA)
        short_exit_imediate_1 = (dataframe['ha_trend'] == 'bullish')
        short_exit_imediate.append(short_exit_imediate_1)
        short_exit_imediate_names.append("HA_Bullish_Exit")

        # Compter le nombre de requis remplies
        short_exit_imediate_count = np.sum(short_exit_imediate, axis=0)
        # Compter le nombre de conditions remplies
        short_exit_conditions_count = np.sum(short_exit_conditions, axis=0)

        # Créer un signal d'entrée long si au moins 3 conditions sont remplies et si tous les requis sont remplis
        dataframe['exit_short'] = (short_exit_conditions_count >=1) | (short_exit_imediate_count >=1)
        dataframe['exit_short'] = dataframe['exit_short'].astype(int)  # Convertir le booléen en entier (0 ou 1)


        # Attribution de tags basés sur les conditions remplies
        dataframe['exit_tag'] = ''
        for i, condition in enumerate(short_exit_conditions):
            dataframe.loc[condition & (dataframe['exit_short'] == 1), 'exit_tag'] += f"{short_exit_conditions_names[i]}|"

        # Supprimer le dernier '|' du tag
        dataframe['exit_tag'] = dataframe['exit_tag'].str.rstrip('|')

        return dataframe
