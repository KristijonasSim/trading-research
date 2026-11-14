# Jesse pavyzdinė strategija SimpleBollinger (jesse-ai/example-strategies): long kai uždarymas virš viršutinės BB(20,2), išeiti kai žemiau vidurinės.
# papers/94_jesse_examples. Signalas žvakės uždarymu, įėjimas kitos žvakės atidarymu.
from freqtrade.strategy import IStrategy


class SimpleBollinger(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "1d"
    can_short = False
    minimal_roi = {"0": 100}
    stoploss = -0.99
    startup_candle_count = 30
    N, K = 20, 2.0

    def populate_indicators(self, df, metadata):
        m = df["close"].rolling(self.N).mean(); sd = df["close"].rolling(self.N).std()
        df["bb_mid"], df["bb_up"] = m, m + self.K * sd
        return df

    def populate_entry_trend(self, df, metadata):
        df.loc[df["close"] > df["bb_up"], "enter_long"] = 1
        return df

    def populate_exit_trend(self, df, metadata):
        df.loc[df["close"] < df["bb_mid"], "exit_long"] = 1
        return df
