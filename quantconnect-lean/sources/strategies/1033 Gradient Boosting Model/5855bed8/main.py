class DynamicHorizontalFlange(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2015, 9, 1)  # Set Start Date
        self.SetEndDate(2020, 9, 17)
        self.SetCash(1000000)  # Set Strategy Cash
        self.AddEquity("SPY", Resolution.Minute)


    def OnData(self, data):
        if not self.Portfolio.Invested:
            self.SetHoldings("SPY", 1)