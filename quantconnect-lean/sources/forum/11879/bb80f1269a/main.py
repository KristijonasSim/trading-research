class SleepyFluorescentYellowCat(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2012, 1, 1)
        self.SetCash(100000) 
        self.AddEquity('SVXY',Resolution.Minute)
        res=Resolution.Daily
        self.uvxy=self.AddEquity('UVXY',res).Symbol
        self.bb=self.BB(self.uvxy,10,2,res)
        self.sma=self.SMA(self.uvxy,4,res)
        self.rc=self.RC(self.uvxy,6,0.3,res)
        self.trigger=False
        self.buy=False
        self.hold=False
        self.sell=False

    def OnData(self, data):

        if self.bb.IsReady and data.ContainsKey(self.uvxy) and self.sma.IsReady:
            vix=data[self.uvxy].Close
            if self.rc.UpperChannel.Current.Value<vix:
                self.trigger=True

            if self.trigger and self.sma.Current.Value>vix:
                self.buy=True

            if self.hold and (vix<(self.bb.MiddleBand.Current.Value-self.bb.StandardDeviation.Current.Value)):
                self.sell=True
                
            
        if self.buy and data.ContainsKey('SVXY'):
            self.SetHoldings('SVXY',1)
            self.trigger=False
            self.buy=False
            self.hold=True

        if data.ContainsKey('SVXY') and (self.sell or self.Portfolio['SVXY'].UnrealizedProfitPercent<-0.04):
            self.SetHoldings('SVXY',0)
            self.hold=False
            self.sell=False
