# Inspired by the theory here:
# https://seekingalpha.com/article/4299701-leveraged-etfs-for-long-term-investing
# https://www.quantconnect.com/forum/discussion/7708/using-levered-etfs-in-ira-10-years-24-cagr-1-56-sharpe/p1

class MultidimensionalTransdimensionalPrism(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2010, 2, 1)               # Earliest start date for all ETFs in universe 2/1/10
        self.SetEndDate(2020, 3, 27)
        self.SetCash(100000) 
        self.AddEquity("TQQQ", Resolution.Hour)    # 3x QQQ
        self.AddEquity("UBT", Resolution.Hour)     # 3x 20yr Treasury
        self.AddEquity("UST", Resolution.Hour)     # 3x 10yr Treasury
        self.AddEquity("TVIX", Resolution.Hour)
        self.tkr = ["TQQQ", "UBT", "UST", "TVIX"]
        
        self.Schedule.On(
            self.DateRules.MonthStart("UST"),
            self.TimeRules.AfterMarketOpen("UST", 150),
            self.Rebalance
        )
    def OnData(self, data):
        pass        
    def Rebalance(self):
        for stock in self.tkr:
            if stock =='TVIX':
                weight = 0.05
            else:
                weight = 0.315
            self.SetHoldings(stock, weight)