# found on QuantConnect 
# Inspired by the theory here:
# https://seekingalpha.com/article/4299701-leveraged-etfs-for-long-term-investing
# https://www.quantconnect.com/forum/discussion/7708/using-levered-etfs-in-ira-10-years-24-cagr-1-56-sharpe/p1
# 3x Long TQQQ TMF and UGLD. Using a QQQ SMA200 to determine allocations.

class TQQQTMFUGLwithQQQtimer(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2010, 3, 1)
        self.SetEndDate(2010, 6, 1)
        #self.SetEndDate(2010, 1, 1)
        self.SetCash(100000) 
        self.qqq = self.AddEquity("QQQ", Resolution.Hour)
        self.tlt = self.AddEquity("TLT", Resolution.Hour)
        self.AddEquity("TQQQ", Resolution.Hour)    # 3x QQQ
        self.AddEquity("TYD", Resolution.Hour)    # 3x 10 yr Treasury
        self.AddEquity("TMF", Resolution.Hour)      # 3x 20yr Treasury
        self.qqqstd = IndicatorExtensions.Of(StandardDeviation(100), self.ROC("QQQ", 100, Resolution.Daily))
        self.tltstd = IndicatorExtensions.Of(StandardDeviation(100), self.ROC("TLT", 100, Resolution.Daily))
        self.SetWarmUp(200, Resolution.Daily)      # warm up the indicator
        self.Schedule.On(self.DateRules.WeekStart("QQQ"), self.TimeRules.AfterMarketOpen("QQQ", 30), self.Rebalance)
        self.SetRiskManagement(MaximumUnrealizedProfitPercentPerSecurity(0.2))

    def OnData(self, data):
        if data.ContainsKey("QQQ") == False: return     # make sure we have data for trading symbols
        if data.ContainsKey("TQQQ") == False: return
        if data.ContainsKey("TLT") == False: return
    
        if self.IsWarmingUp:
            return
        self.Plot("STD", "QQQ", self.qqqstd.Current.Value)
        self.Plot("STD", "TLT", self.tltstd.Current.Value)
    
    def Rebalance(self):
        if self.qqqstd.Current.Value < self.tltstd.Current.Value:
            self.SetHoldings("TQQQ", 1)
            self.SetHoldings("TMF", 0)
            self.SetHoldings("TYD", 0)
            self.Debug("Bullish - TQQQ 100%")
        else:
            self.SetHoldings("TQQQ", 0.5)
            self.SetHoldings("TMF", 0.25)
            self.SetHoldings("TYD", 0.25)
            self.Debug("Bearish - TQQQ 50%, TMF 25%, TYD 25%")