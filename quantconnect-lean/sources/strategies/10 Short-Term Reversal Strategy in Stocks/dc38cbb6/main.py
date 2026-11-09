class TachyonUncoupledAtmosphericScrubbers(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2016, 1, 1)
        self.SetEndDate(2021, 1, 1)
        self.SetCash(1000000)
        
        self.AddEquity("SPY", Resolution.Daily)


    def OnData(self, data):
        if not self.Portfolio.Invested:
            self.SetHoldings("SPY", 1)