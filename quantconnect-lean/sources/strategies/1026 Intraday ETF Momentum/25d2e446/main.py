class DynamicHorizontalFlange(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2015, 1, 1)
        self.SetEndDate(2020, 8, 16)
        self.SetCash(100000)  # Set Strategy Cash
        self.AddEquity("SPY", Resolution.Minute)


    def OnData(self, data):
        if not self.Portfolio.Invested:
            self.SetHoldings("SPY", 1)