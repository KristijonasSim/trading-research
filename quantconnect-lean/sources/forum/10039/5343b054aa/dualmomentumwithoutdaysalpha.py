"""
v2.5 Dual Momentum with Out Days  by Vladimir

inspired by Peter Guenther, Tentor Testivis, Dan Whitnable, Thomas Chang and T Smith.
converted to QC Algorithm Framework (Alpha Model + Portfolio Construction Model) by Joao Antunes

based on Intersection of ROC comparison using OUT_DAY approach by Vladimir
modified parameters BASE_RET = 83;

https://www.quantconnect.com/forum/discussion/10039/dual-momentum-with-out-days/p1/comment-29928
"""
import numpy as np


class DualMomentumWithOutDaysAlphaModel(AlphaModel):

    def __init__(self,
                 algorithm,
                 VOLA = 126,
                 BASE_RET = 83,
                 resolution = Resolution.Daily):
        self.VOLA = VOLA
        self.BASE_RET = BASE_RET
        self.resolution = resolution
        self.MKT = algorithm.AddEquity('SPY', resolution).Symbol
        self.SLV = algorithm.AddEquity('SLV', resolution).Symbol
        self.GLD = algorithm.AddEquity('GLD', resolution).Symbol
        self.XLI = algorithm.AddEquity('XLI', resolution).Symbol
        self.XLU = algorithm.AddEquity('XLU', resolution).Symbol
        self.DBB = algorithm.AddEquity('DBB', resolution).Symbol
        self.UUP = algorithm.AddEquity('UUP', resolution).Symbol

        self.count = 0

        pairs = [self.MKT, self.SLV, self.GLD, self.XLI, self.XLU, self.DBB, self.UUP]
        for symbol in pairs:
            self.consolidator = TradeBarConsolidator(timedelta(days=1))
            self.consolidator.DataConsolidated += self.consolidation_handler
            algorithm.SubscriptionManager.AddConsolidator(symbol, self.consolidator)

        self.history = algorithm.History(pairs, self.VOLA + 1, resolution)
        self.history = self.history['close'].unstack(level=0).dropna()

        self.predictionInterval = Time.Multiply(Extensions.ToTimeSpan(self.resolution), 30)
        resolutionString = Extensions.GetEnumString(resolution, Resolution)
        self.Name = f"{self.__class__.__name__}({resolutionString})"

        # Force alpha to only produce insights daily at 11.10am
        self.set_flag = False
        algorithm.Schedule.On(algorithm.DateRules.EveryDay(),
                              algorithm.TimeRules.AfterMarketOpen('SPY', 100),
                              self.SetFlag)

    def SetFlag(self):
        self.set_flag = True

    def consolidation_handler(self, sender, consolidated):
        self.history.loc[consolidated.EndTime, consolidated.Symbol] = consolidated.Close
        self.history = self.history.iloc[-(self.VOLA + 1):]

    def Update(self, algorithm, _data):
        if algorithm.IsWarmingUp or not self.set_flag:
            return []

        self.set_flag = False
        insights = []

        vola = self.history[self.MKT].pct_change().std() * np.sqrt(252)
        wait_days = int(vola * self.BASE_RET)
        period = int((1.0 - vola) * self.BASE_RET)
        r = self.history.pct_change(period).iloc[-1]
        exit_market = r[self.SLV] < r[self.GLD] and r[self.XLI] < r[self.XLU] and r[self.DBB] < r[self.UUP]

        direction = InsightDirection.Down
        if exit_market:
            self.count = 0
        else:
            self.count += 1
            if self.count >= wait_days:
                direction = InsightDirection.Up

        insights.append(Insight.Price(self.MKT, self.predictionInterval, direction))

        return insights