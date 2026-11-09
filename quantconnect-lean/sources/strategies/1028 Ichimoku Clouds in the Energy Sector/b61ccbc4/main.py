class TransdimensionalNadionFlange(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2015, 8, 10)  # Set Start Date
        self.SetEndDate(2015, 10, 10)
        self.SetCash(1000000)  # Set Strategy Cash
        
        self.AddEquity("XLE", Resolution.Minute)


    def OnData(self, data):
        if not self.Portfolio.Invested:
            self.SetHoldings("XLE", 1)