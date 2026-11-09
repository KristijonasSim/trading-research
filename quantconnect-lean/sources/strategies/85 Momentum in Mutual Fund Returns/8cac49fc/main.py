class DynamicHorizontalFlange(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2020, 2, 19)
        self.SetEndDate(2020, 3, 23)
        self.SetCash(1000000)  # Set Strategy Cash
        self.AddEquity("SPY", Resolution.Minute)


    def OnData(self, data):
        if not self.Portfolio.Invested:
            self.SetHoldings("SPY", 1)