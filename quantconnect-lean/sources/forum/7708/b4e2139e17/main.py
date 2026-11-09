from QuantConnect.Data.Custom.CBOE import *

class AIMPortfoliosFireandForget(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2011, 1, 1) #TQQQ Latest Inception Date --> February 9, 2010
        self.SetEndDate(2021, 3, 18)
        self.SetCash(1000000000)
        self.SetWarmUp(180)
        self.SetBenchmark('SPY')
        self.dayCounter = 0
        self.AddEquity('QQQ', Resolution.Minute)
        self.AddEquity('SPY', Resolution.Minute)
        self.AddEquity('IWM', Resolution.Minute)
        #self.AddEquity('UVXY', Resolution.Minute)
        #self.AddEquity('URTY', Resolution.Minute)
        self.AddEquity('SCO', Resolution.Minute)
        self.AddEquity('GLD', Resolution.Minute)
        self.AddEquity('TLT', Resolution.Minute)
        #self.AddEquity('TQQQ', Resolution.Minute)
        #self.AddEquity('UPRO', Resolution.Minute)
        self.AddEquity('TMF', Resolution.Minute)
        
        self.Schedule.On (self.DateRules.EveryDay("QQQ"), self.TimeRules.AfterMarketOpen("QQQ", 30), self.Rebalance)
        self.leverageA = 1
        
    def OnData(self, data):
            if self.IsWarmingUp:
                return
    
    def Rebalance(self):
        if not self.Securities['QQQ'].Invested:
            self.SetHoldings('QQQ', 0.24)
            self.SetHoldings('SPY', 0.24)
            self.SetHoldings('IWM', 0.14)
            self.SetHoldings('SCO', 0.11)
            self.SetHoldings('GLD', 0.11)
            self.SetHoldings('TMF', 0.16)
            #self.SetHoldings('UVXY', 0.04)
            self.dayCounter = 0
        elif self.dayCounter is 6:
            self.SetHoldings('QQQ', 0.24)
            self.SetHoldings('SPY', 0.24)
            self.SetHoldings('IWM', 0.14)
            self.SetHoldings('SCO', 0.11)
            self.SetHoldings('GLD', 0.11)
            self.SetHoldings('TMF', 0.16)
            #self.SetHoldings('UVXY', 0.025)
            self.dayCounter = 0
        else:
            self.dayCounter = self.dayCounter+1