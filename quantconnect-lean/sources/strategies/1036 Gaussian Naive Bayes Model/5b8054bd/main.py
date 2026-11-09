class TachyonUncoupledAtmosphericScrubbers(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2015, 10, 1)
        self.SetEndDate(2020, 10, 13)
        self.SetCash(1000000)
        
        self.AddEquity("SPY", Resolution.Daily)


    def OnData(self, data):
        if not self.Portfolio.Invested:
            self.SetHoldings("SPY", 1)