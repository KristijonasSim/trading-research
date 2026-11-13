import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import IStrategy


class RSIVol(IStrategy):
    can_short = True
    timeframe = '15m'
    stoploss = -0.99

    position_adjustment_enable = True
    max_open_trades = 10

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # generate values for technical analysis indicators
        dataframe["RSI"] = ta.RSI(dataframe["close"], timeperiod=14)
        dataframe["VolMA"] = ta.SMA(dataframe["volume"], timeperiod=20)

        dataframe["long_signal"] = (dataframe["RSI"] < 30) & (dataframe["volume"] > dataframe["VolMA"])
        dataframe["short_signal"] = (dataframe["RSI"] > 70) & (dataframe["volume"] > dataframe["VolMA"])


        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # generate entry signals based on indicator values
        dataframe.loc[
            (dataframe["long_signal"]),
            'enter_long'] = 1

        dataframe.loc[
            (dataframe["short_signal"]),
            'enter_short'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # generate exit signals based on indicator values
        dataframe.loc[
            (dataframe["RSI"] > 50),
            'exit_long'] = 1

        dataframe.loc[
            (dataframe["RSI"] < 50),
            'exit_short'] = 1

        return dataframe

    def adjust_trade_position(self, trade, current_time, current_rate, current_profit, **kwargs):
        # Adjust the position size based on the current profit
        if trade.nr_of_successful_entries == 1:
            pass#return None

        dataframe, _ = self.dp.get_analyzed_dataframe(
            trade.pair,
            self.timeframe
        )

        if dataframe.empty:
            return None

        last_candle = dataframe.iloc[-1]

        # Add to an existing LONG
        if not trade.is_short and last_candle["long_signal"]:
            return trade.stake_amount

        # Add to an existing SHORT
        if trade.is_short and last_candle["short_signal"]:
            return trade.stake_amount

        return None

