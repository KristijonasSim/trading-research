import numpy as np
import pandas as pd

class TransdimensionalOptimizedAtmosphericScrubbers(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2015, 4, 29)  # Set Start Date
        self.SetCash(100000)  # Set Strategy Cash

        res = Resolution.Minute

        self.STOCK = self.AddEquity('QQQ', res).Symbol
        self.BONDS = [self.AddEquity(ticker, res).Symbol for ticker in ['TLT', 'IEF']]
        self.XLI, self.XLU, self.UUP =  [self.AddEquity(ticker, res).Symbol for ticker in ['XLI', 'XLU', 'UUP'] ]

        self.VOLA = 126;
        self.BULL = 1;
        self.COUNT = 0;
        self.OUT_DAY = 0;
        self.RET_INITIAL = 80;
        self.LEV = 1.00;

        self.Schedule.On(self.DateRules.EveryDay(), self.TimeRules.AfterMarketOpen('QQQ', 140), self.daily_check)
        
        self.mkt_closes = RollingWindow[float](self.VOLA + 1)
        history = self.History([self.STOCK], self.VOLA + 1, Resolution.Daily)
        if not history.empty and 'close' in history.columns:
            for time, close in history.loc[self.STOCK].close.iteritems():
                self.mkt_closes.Add(close)
        
        # Setup consolidator
        self.consolidator = TradeBarConsolidator(1)
        self.consolidator.DataConsolidated += self.DailyHandler
        self.SubscriptionManager.AddConsolidator(self.STOCK, self.consolidator)
    
    def DailyHandler(self, sender, consolidated):
        self.mkt_closes.Add(consolidated.Close)
            

    def daily_check(self):
        if not self.mkt_closes.IsReady:
            return
        vola = pd.Series(self.mkt_closes).iloc[::-1].pct_change().std() * np.sqrt(252)
        
        WAIT_DAYS = int(vola * self.RET_INITIAL)
        RET = int((1.0 - vola) * self.RET_INITIAL)

        P = self.History([self.XLI, self.XLU, self.UUP], RET + 2, Resolution.Daily)['close'].unstack(level=0).iloc[:-1].dropna()
        if (len(P.columns) < 2):
            return
        ratio = (P[self.XLI].iloc[-1] / P[self.XLI].iloc[0]) / (P[self.XLU].iloc[-1] / P[self.XLU].iloc[0])

        exit = ratio < 1.0
        if exit:
            self.BULL = 0;
            self.OUT_DAY = self.COUNT;
        elif (self.COUNT >= self.OUT_DAY + WAIT_DAYS):
            self.BULL = 1
        self.COUNT += 1

        wt_stk = self.LEV if self.BULL else 0;
        wt_bnd = 0 if self.BULL else self.LEV;

        wt = {}

        wt[self.STOCK] = wt_stk

        for sec in self.BONDS:
            wt[sec] = wt_bnd / len(self.BONDS)

        for sec, weight in wt.items():
            self.SetHoldings(sec, weight)