# Inspired by the theory here:
# https://seekingalpha.com/article/4299701-leveraged-etfs-for-long-term-investing

class MultidimensionalTransdimensionalPrism(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2010, 2, 1)               # Earliest start date for all ETFs in universe 2/1/10
        self.SetEndDate(2020, 3, 27)
        self.SetCash(100000) 
        self.AddEquity("TQQQ", Resolution.Hour)    # 3x QQQ
        self.AddEquity("UBT", Resolution.Hour)     # 3x 20yr Treasury
        self.AddEquity("UST", Resolution.Hour)     # 3x 10yr Treasury
        self.tkr = ["TQQQ", "UBT", "UST"]
        
        self.rebal = 2                              # Rebalance every 2 weeks
        self.rebalTimer = self.rebal - 1            # Initialize to trigger first week
        self.flag1 = 0                              # Flag to initate trades
        
        # Increment rebalance timer at every week start
        self.Schedule.On(self.DateRules.WeekStart("UST"), self.TimeRules.AfterMarketOpen("UST", 150), self.Rebalance)


    def OnData(self, data):
        # If ready to rebalance, set each holding at 1/3
        if self.flag1 == 1:                     
            for stock in self.tkr:
                self.SetHoldings(stock, 0.33)
            self.rebalTimer = 0                     # Reset rebalance timer
        self.flag1 = 0          
        
    def Rebalance(self):
        self.rebalTimer +=1
        if self.rebalTimer == self.rebal:
            self.flag1 = 1