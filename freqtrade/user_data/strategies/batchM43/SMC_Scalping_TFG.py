# ==============================================================================
# ESTRATEGIA TFG: SMC + FREQAI (HÍBRIDO REAL)
# Fase 2: Integración del Cerebro Artificial
# ==============================================================================

import numpy as np
import pandas as pd
from pandas import DataFrame
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
import talib.abstract as ta
import pandas_ta as pta

class SMC_Scalping_TFG(IStrategy):
    
    # --- CONFIGURACIÓN GENERAL ---
    INTERFACE_VERSION = 3
    timeframe = '5m'
    startup_candle_count = 200
    
    # --- GESTIÓN DE RIESGO ---
    stoploss = -0.02
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02
    
    # ROI (Take Profit Escalonado)
    minimal_roi = {
        "0": 0.05,
        "10": 0.03,
        "20": 0.015,
        "60": 0.005
    }

    # DCA (Promediación)
    position_adjustment_enable = True
    max_entry_position_adjustment = 2

    # ==========================================================================
    # 🧠 PARTE 1: FREQAI - INGENIERÍA DE CARACTERÍSTICAS
    # Aquí es donde enseñamos a la IA qué debe mirar para aprender
    # ==========================================================================
    
    def feature_engineering_expand_all(self, dataframe: DataFrame, period, metadata, **kwargs):
        """
        Esta función crea los datos que la IA usará para entrenar.
        Le damos los indicadores SMC para que aprenda patrones sobre ellos.
        """
        # 1. INDICADORES BÁSICOS
        dataframe["%s-rsi" % period] = ta.RSI(dataframe, timeperiod=14)
        dataframe["%s-adx" % period] = ta.ADX(dataframe, timeperiod=14)
        
        # 2. INDICADORES INSTITUCIONALES (SMC)
        # Enseñamos a la IA a detectar huecos (FVG)
        dataframe["%s-fvg_gap" % period] = (dataframe['high'].shift(2) - dataframe['low']) / dataframe['close']
        
        # Enseñamos a la IA la volatilidad (Bandas de Bollinger)
        bollinger = ta.BBANDS(dataframe, timeperiod=20)
        dataframe["%s-bb_width" % period] = (bollinger['upperband'] - bollinger['lowerband']) / bollinger['middleband']

        return dataframe

    def feature_engineering_expand_basic(self, dataframe: DataFrame, metadata, **kwargs):
        """
        Características que no dependen del tiempo (ej: día de la semana)
        """
        dataframe["day_of_week"] = dataframe["date"].dt.dayofweek
        return dataframe

    def feature_engineering_standard(self, dataframe: DataFrame, metadata, **kwargs):
        """
        Función obligatoria para FreqAI, aunque usemos expand_all.
        """
        return dataframe

    def set_freqai_targets(self, dataframe: DataFrame, metadata, **kwargs):
        """
        Aquí definimos qué es "ÉXITO" para la IA.
        Le decimos: "Aprende a predecir si el precio subirá un 2% en las próximas 20 velas".
        """
        dataframe["&s-up_candle"] = (dataframe["close"].shift(-20) > dataframe["close"] * 1.02).astype('int')
        return dataframe

    # ==========================================================================
    # 📐 PARTE 2: LÓGICA TRADICIONAL (FILTROS HUMANOS)
    # ==========================================================================

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        
        # Recalculamos indicadores para uso inmediato (no IA)
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        dataframe['ema_200'] = ta.EMA(dataframe, timeperiod=200)

        # FVG (Fair Value Gap) - Lógica Humana
        dataframe['fvg_bullish'] = (
            (dataframe['low'] > dataframe['high'].shift(2)) & 
            (dataframe['close'] > dataframe['open'])
        )
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        
        dataframe.loc[:, 'enter_long'] = 0

        # --- SEÑAL HÍBRIDA (LO MEJOR DE LOS DOS MUNDOS) ---
        # Entramos SI:
        # 1. La IA predice subida (do_predict=1)
        # 2. O BIEN hay una estructura SMC clara (FVG + Tendencia)
        
        # A. Señal de la IA (Predicción)
        # Nota: La IA añadirá una columna 'do_predict' automáticamente
        if 'do_predict' in dataframe.columns:
            ai_signal = (dataframe['do_predict'] == 1)
        else:
            ai_signal = (dataframe['volume'] < 0) # Falso si no hay IA aún

        # B. Señal SMC (Humana)
        smc_signal = (
            (dataframe['adx'] > 25) &
            (dataframe['close'] > dataframe['ema_200']) &
            (dataframe['fvg_bullish'] == True)
        )

        # C. Combinación (O una O la otra)
        # Esto asegura que el bot opere tanto por instinto matemático (SMC) como por predicción (IA)
        dataframe.loc[
            (ai_signal | smc_signal),
            'enter_long'
        ] = 1

        dataframe.loc[ai_signal, 'enter_tag'] = 'AI_Prediction'
        dataframe.loc[smc_signal, 'enter_tag'] = 'SMC_Sniper'

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, 'exit_long'] = 0
        
        # Salida simple por RSI sobrecomprado
        dataframe.loc[
            (dataframe['rsi'] > 80),
            'exit_long'
        ] = 1
        
        return dataframe