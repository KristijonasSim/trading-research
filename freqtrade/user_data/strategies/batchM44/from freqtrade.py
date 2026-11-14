from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta

class MaStrategieRSI(IStrategy):
    # --- Paramètres globaux ---
    timeframe = '1d'  # Ton backtest était sur des données journalières
    startup_candle_count = 20

    # --- Gestion du risque (Traduction de ton script) ---
    stoploss = -0.02  # Ton stop loss initial de 2%
    
    # --- Configuration du Trailing Stop ---
    trailing_stop = True
    trailing_stop_positive = 0.01  # Ton trail_pct de 1%
    trailing_stop_positive_offset = 0.01 # Se déclenche après 1% de profit

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Calcul du RSI(14)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Signal d'ACHAT (LONG) : RSI < 35
        dataframe.loc[
            (dataframe['rsi'] < 35) &
            (dataframe['volume'] > 0),
            'enter_long'] = 1
        
        # Signal de VENTE (SHORT) : RSI > 65
        dataframe.loc[
            (dataframe['rsi'] > 65) &
            (dataframe['volume'] > 0),
            'enter_short'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # La sortie est gérée automatiquement par le stoploss et le trailing stop.
        return dataframe