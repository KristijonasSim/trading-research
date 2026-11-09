class TachyonUncoupledAtmosphericScrubbers(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2019, 1, 1)
        self.SetEndDate(2020, 8, 1)
        self.SetCash(1000000)
        
        self.AddEquity("SPY", Resolution.Minute)


    def OnData(self, data):
        if not self.Portfolio.Invested:
            self.SetHoldings("SPY", 1)