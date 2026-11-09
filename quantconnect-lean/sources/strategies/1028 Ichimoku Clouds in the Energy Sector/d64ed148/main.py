class TransdimensionalNadionFlange(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2020, 2, 19)  # Set Start Date
        self.SetEndDate(2020, 3, 23)
        self.SetCash(1000000)  # Set Strategy Cash
        
        self.AddEquity("XLE", Resolution.Minute)


    def OnData(self, data):
        if not self.Portfolio.Invested:
            self.SetHoldings("XLE", 1)