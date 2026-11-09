"""
v2.5 Dual Momentum with Out Days  by Vladimir

inspired by Peter Guenther, Tentor Testivis, Dan Whitnable, Thomas Chang and T Smith.
converted to QC Algorithm Framework (Alpha Model + Portfolio Construction Model) by Joao Antunes

based on Intersection of ROC comparison using OUT_DAY approach by Vladimir
modified parameters BASE_RET = 83;

https://www.quantconnect.com/forum/discussion/10039/dual-momentum-with-out-days/p1/comment-29928
"""
from itertools import groupby

from dual_momentum_with_out_days_alpha import DualMomentumWithOutDaysAlphaModel

VOLA = 126; BASE_RET = 83; RET = 252; EXCL = 21; LEV = 1.00;

class HorizontalQuantumCoil(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2008, 1, 1)
        self.SetEndDate(2020, 12, 31)
        self.SetCash(100_000)
        self.SetWarmUp(timedelta(350))
        # self.Portfolio.MarginCallModel = MarginCallModel.Null
        self.SetAlpha(DualMomentumWithOutDaysAlphaModel(self, VOLA, BASE_RET, Resolution.Daily))

        symbols = [
            Symbol.Create('QQQ', SecurityType.Equity, Market.USA),
            Symbol.Create('FDN', SecurityType.Equity, Market.USA),
            Symbol.Create('TLT', SecurityType.Equity, Market.USA),
            Symbol.Create('TLH', SecurityType.Equity, Market.USA),
        ]
        self.SetUniverseSelection(ManualUniverseSelectionModel(symbols))
        self.UniverseSettings.Resolution = Resolution.Hour
        self.SetPortfolioConstruction(OutDays(self, RET, EXCL, LEV, Resolution.Hour))

        self.createPlots("SPY")

    def createPlots(self, benchmark):
        self.__benchmark = benchmark

        self.__plot_every_n_days = 5
        self.__plot_every_n_days_i = 0
        plot = Chart('Performance')
        plot.AddSeries(Series(self.__benchmark, SeriesType.Line, 0, '%'))
        plot.AddSeries(Series("Algorithm", SeriesType.Line, 0, '%'))
        self.AddChart(plot)

        self.ResetPlot()

    def ResetPlot(self):
        self.year = self.Time.year
        self.__cost_portfolio = None
        self.__cost_benchmark = None

    def CalculateBenchmarkPerformance(self):
        price = self.Securities[self.__benchmark].Price
        if self.__cost_benchmark == None:
            self.__cost_benchmark = price
        return 100.0 * ((price / self.__cost_benchmark) - 1.0)

    def CalculatePortfolioPerformance(self):
        if self.__cost_portfolio == None:
            self.__cost_portfolio = self.Portfolio.TotalPortfolioValue
        return 100.0 * ((self.Portfolio.TotalPortfolioValue / self.__cost_portfolio) - 1.0)

    def OnEndOfDay(self):
        if self.IsWarmingUp or not self.Securities[self.__benchmark].HasData:
            return

        if self.Time.year != self.year:
            self.ResetPlot()
            self.__plot_every_n_days_i == -1

        self.__plot_every_n_days_i += 1
        if self.__plot_every_n_days_i % self.__plot_every_n_days != 0:
            return

        self.Plot('Performance', self.__benchmark, self.CalculateBenchmarkPerformance())
        self.Plot('Performance', "Algorithm", self.CalculatePortfolioPerformance())


class OutDays(PortfolioConstructionModel):
    def __init__(self,
                 algorithm,
                 RET=252,
                 EXCL=21,
                 LEV=1.00,
                 resolution = Resolution.Hour):
        self.algorithm = algorithm
        self.RET = RET
        self.EXCL = EXCL
        self.LEV = LEV
        self.STK1 = self.algorithm.AddEquity('QQQ', resolution).Symbol
        self.STK2 = self.algorithm.AddEquity('FDN', resolution).Symbol
        self.BND1 = self.algorithm.AddEquity('TLT', resolution).Symbol
        self.BND2 = self.algorithm.AddEquity('TLH', resolution).Symbol
        self.ASSETS = [self.STK1, self.STK2, self.BND1, self.BND2]

    def returns(self, symbol):
        prices = self.algorithm.History(symbol, TimeSpan.FromDays(self.RET + self.EXCL), Resolution.Daily).close
        return prices[-self.EXCL] / prices[0]

    def CreateTargets(self, algorithm, insights):
        if algorithm.IsWarmingUp:
            return []

        targets = []

        # We expect at most only one active insight since we only
        # generate insights for one equity.
        assert len(insights) <= 1
        if len(insights) == 1:
            insight = insights[0]
            self.bull = insight.Direction == InsightDirection.Up

            if self.bull:
                if self.returns(self.STK1) < self.returns(self.STK2):
                    selected = self.STK2
                else:
                    selected = self.STK1
            else:
                if self.returns(self.BND1) < self.returns(self.BND2):
                    selected = self.BND2
                else:
                    selected = self.BND1

            for asset in self.ASSETS:
                if asset != selected:
                    targets.append(PortfolioTarget.Percent(algorithm, asset, 0.0))
            targets.append(PortfolioTarget.Percent(algorithm, selected, 1.0))

        return targets