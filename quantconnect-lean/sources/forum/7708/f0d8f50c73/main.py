#take the paper "Leverage For The Long Run", use a 200 SMA on SPY to generate weekly buy/sell signals to either go long multiple 3x leveraged assets, or go to "AGG".

class LeverageForTheLongRunDiversifiedWeekly(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2010,3, 1)  #Set Start Date
        self.SetEndDate(2020,8,20)    #Set End Date
        self.SetCash(100000)           #Set Strategy Cash
        self.spy = self.AddEquity("SPY", Resolution.Daily)
        self.tqqq = self.AddEquity("TQQQ", Resolution.Daily)
        self.ubt = self.AddEquity("UBT", Resolution.Daily)
        self.ust = self.AddEquity("UST", Resolution.Daily)
        self.agg = self.AddEquity("AGG", Resolution.Daily) # general bond fund as cash replacement
        self.etfs = ["TQQQ","UST","UBT"]
        self.sma = self.SMA("SPY", 200)
        self.SetWarmUp(200)      # warm up the indicator
        self.Settings.FreePortfolioValuePercentage = 0.05
        
        # Rebalancing logic
        self.rebal = 1                              # Rebalance every 1 week
        self.rebalTimer = self.rebal - 1            # Initialize to trigger first week
        self.flag1 = 0                              # Flag to initate trades
        
        # Increment rebalance timer at every week start
        self.Schedule.On(self.DateRules.WeekStart("SPY"), self.TimeRules.AfterMarketOpen("SPY", 30), self.Rebalance)
        
    def OnData(self, data):
        
        if not self.sma.IsReady: return
        if data.ContainsKey("SPY") == False: return     # make sure we have data for trading symbols
        if data.ContainsKey("TQQQ") == False: return
        if data.ContainsKey("UBT") == False: return
        if data.ContainsKey("UST") == False: return
        
        # If ready to rebalance, set each holding at 1/3
        if self.flag1 == 1:                     
            if not self.Portfolio.Invested and data[self.spy.Symbol].Close>self.sma.Current.Value: # if holdings are empty and SPY>200SMA
                for stock in self.etfs:
                    if stock =='TQQQ':
                        weight = 0.5
                    else:
                        weight = 0.25
                    self.SetHoldings(stock, weight)
        else:
            if self.Portfolio.Invested and data[self.spy.Symbol].Close<self.sma.Current.Value: # if holdings are full and SPY<200SMA
                for stock in self.etfs:
                    self.SetHoldings(stock, 0)
            self.rebalTimer = 0                     # Reset rebalance timer
        self.flag1 = 0          
        
    def Rebalance(self):
        self.rebalTimer +=1
        if self.rebalTimer == self.rebal:
            self.flag1 = 1