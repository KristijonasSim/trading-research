# https://www.quantifiedstrategies.com/free-swing-trading-strategies/
# QQQ Strategy #4

class WellDressedBlackBat(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2000, 1, 1)  # Set Start Date
        self.SetCash(100000)  # Set Strategy Cash
        self.eq = 'QQQ'
        self.AddEquity(self.eq, Resolution.Minute)
        
        self.Schedule.On(self.DateRules.Every(DayOfWeek.Monday, DayOfWeek.Tuesday),self.TimeRules.BeforeMarketClose(self.eq, 20),self.checktrade)
        self.Schedule.On(self.DateRules.Every(DayOfWeek.Monday, DayOfWeek.Tuesday),self.TimeRules.AfterMarketOpen(self.eq,1),self.getprices)
        self.Schedule.On(self.DateRules.Every(DayOfWeek.Wednesday, DayOfWeek.Thursday, DayOfWeek.Friday),self.TimeRules.BeforeMarketClose(self.eq, 20),self.checkexit)
        self.trade, self.tracko, self.trackhl, self.exit = [False, False, False, False]
        
    def checktrade(self):
        self.trade = True
        
    def getprices(self):
        self.tracko = True
        self.trackhl = True
        
    def checkexit(self):
        self.exit = True
        
    def OnData(self, data):
        '''OnData event is the primary entry point for your algorithm. Each new data point will be pumped in here.
            Arguments:
                data: Slice object keyed by symbol containing the stock data
        '''
        if self.tracko:
            p = self.Securities[self.eq].Price
            self.h = p
            self.l = p
            self.tracko = False
        
        if self.trackhl:
            p = self.Securities[self.eq].Price
            self.h = max(self.h,p)
            self.l = min(self.l,p)
            
        if self.trade:
            p = self.Securities[self.eq].Price
            ibs = (p-self.l)/(self.h-self.l)
            
            if not self.Portfolio.Invested:
                if ibs <= .15:
                    self.SetHoldings(self.eq, 1)
            else:
                h = self.History([self.eq],1,Resolution.Daily)
                yh = h['high'].values
                if p >= yh:
                    self.Liquidate()
            
            self.trackhl, self.trade =[False,False]

        if self.exit:
            p = self.Securities[self.eq].Price
            h = self.History([self.eq],1,Resolution.Daily)
            yh = h['high'].values
            if p >= yh:
                self.Liquidate()
                
            self.exit = False