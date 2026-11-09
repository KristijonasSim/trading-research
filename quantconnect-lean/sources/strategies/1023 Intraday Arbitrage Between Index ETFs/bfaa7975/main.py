class ParticleTransdimensionalRadiator(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2015, 8, 11)  # Set Start Date
        self.SetEndDate(2020, 8, 11)
        self.SetCash(50000)  # Set Strategy Cash
        
        self.AddEquity("SPY", Resolution.Minute)


    def OnData(self, data):
        if not self.Portfolio.Invested:
            self.SetHoldings("SPY", 1)