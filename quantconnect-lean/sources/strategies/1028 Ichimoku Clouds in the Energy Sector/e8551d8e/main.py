class CalibratedHorizontalFlange(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2020, 3, 23)
        self.SetEndDate(2020, 6, 8)
        self.SetCash(100000)
        
        self.AddEquity("XLE", Resolution.Minute)


    def OnData(self, data):
        if not self.Portfolio.Invested:
            self.SetHoldings("XLE", 1)