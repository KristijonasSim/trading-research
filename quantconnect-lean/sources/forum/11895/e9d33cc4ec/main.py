class SmoothAsparagusKoala(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2021, 1, 21)
        self.SetCash(100000) 
        self.spy = self.AddEquity("SPY", Resolution.Hour).Symbol

    def OnData(self, data):
        if data.ContainsKey(self.spy) and self.spy not in data.Bars:
            self.Debug("Non trade data avaialble at "+str(self.Time))
            self.Quit()