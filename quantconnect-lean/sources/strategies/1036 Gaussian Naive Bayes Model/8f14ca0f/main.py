class TachyonUncoupledAtmosphericScrubbers(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2020, 3, 23)
        self.SetEndDate(2020, 6, 8)
        self.SetCash(1000000)
        
        self.AddEquity("SPY", Resolution.Daily)


    def OnData(self, data):
        if not self.Portfolio.Invested:
            self.SetHoldings("SPY", 1)