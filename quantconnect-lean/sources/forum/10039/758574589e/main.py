"""
DUAL MOMENTUM IN OUT with static parameters v2.2 by Vladimir

inspired by Peter Guenther, Tentor Testivis, Dan Whitnable, Thomas Chang and T Smith.

"""
import numpy as np

class DualMomentumInOut(QCAlgorithm):

    def Initialize(self):

        self.SetStartDate(2008, 1, 1)
        # self.SetEndDate(2020, 11, 27)
        self.cap = 100000        
        
        self.STK1 = self.AddEquity('QQQ', Resolution.Minute).Symbol
        self.STK2 = self.AddEquity('FDN', Resolution.Minute).Symbol
        self.BND1 = self.AddEquity('TLT', Resolution.Minute).Symbol
        self.BND2 = self.AddEquity('TLH', Resolution.Minute).Symbol
        
        self.ASSETS = [self.STK1, self.STK2, self.BND1, self.BND2]
        
        self.XLI = self.AddEquity('XLI', Resolution.Daily).Symbol 
        self.XLU = self.AddEquity('XLU', Resolution.Daily).Symbol 
        self.SLV = self.AddEquity('SLV', Resolution.Daily).Symbol 
        self.GLD = self.AddEquity('GLD', Resolution.Daily).Symbol

        self.PAIRS = [self.XLI, self.XLU, self.SLV, self.GLD]
        
        self.MKT = self.AddEquity('SPY', Resolution.Daily).Symbol 
        
        self.RETURN = 85
        self.WAIT_DAYS = 17
        self.RET = 126
        self.EXCL = 5
        
        self.selected_bond = self.BND1
        self.selected_stock = self.STK1
        self.bull = 1 
        self.count = 0 
        self.outday = 0
        self.spy = []
        self.wt = {}
        self.real_wt = {}
        self.SetWarmUp(self.RET)

        self.Schedule.On(self.DateRules.EveryDay(), self.TimeRules.AfterMarketOpen('SPY', 100),
            self.calculate_signal)

        self.Schedule.On(self.DateRules.EveryDay(), self.TimeRules.AfterMarketOpen('SPY', 120),
            self.trade_out)
            
        self.Schedule.On(self.DateRules.WeekEnd(), self.TimeRules.AfterMarketOpen('SPY', 120),
            self.trade_in)    
            
        self.Schedule.On(self.DateRules.EveryDay(), self.TimeRules.BeforeMarketClose('SPY', 0), 
            self.record_vars) 
            

    def returns(self, symbol, period, excl):
        prices = self.History(symbol, period + excl, Resolution.Daily).close
        return prices[-excl] / prices[0]
        
        
    def calculate_signal(self):
        P = self.History(self.PAIRS, self.RETURN + 1, Resolution.Daily)['close'].unstack(level = 0).dropna()
        if (len(P.columns) < 2):
            return
  
        diff_iu = (P[self.XLI].iloc[-1] / P[self.XLI].iloc[0]) - (P[self.XLU].iloc[-1] / P[self.XLU].iloc[0])
        diff_sg = (P[self.SLV].iloc[-1] / P[self.SLV].iloc[0]) - (P[self.GLD].iloc[-1] / P[self.GLD].iloc[0])

        exit = (diff_iu < 0 and diff_sg < 0)
                     
        if exit:
            self.bull = 0;
            self.outday = self.count;
        if (self.count >= self.outday + self.WAIT_DAYS):
            self.bull = 1
        self.count += 1

        if self.returns(self.BND1, self.RET, self.EXCL) < self.returns(self.BND2, self.RET, self.EXCL):
            self.selected_bond = self.BND2
            
        elif self.returns(self.BND1, self.RET, self.EXCL) > self.returns(self.BND2, self.RET, self.EXCL):
            self.selected_bond = self.BND1
            
        if self.returns(self.STK1, self.RET, self.EXCL) < self.returns(self.STK2, self.RET, self.EXCL):
            self.selected_stock = self.STK2
            
        elif self.returns(self.STK1, self.RET, self.EXCL) > self.returns(self.STK2, self.RET, self.EXCL):
            self.selected_stock = self.STK1
            
                    
    def trade_out(self):
        
        if not self.bull:
            for sec in self.ASSETS:    
                self.wt[sec] = 0.99 if sec is self.selected_bond else 0 if sec is self.selected_bond else 0
            self.trade() 
            
            
    def trade_in(self):
        
        if self.bull:    
            for sec in self.ASSETS:
                self.wt[sec] = 0.99 if sec is self.selected_stock else 0
            self.trade()            

                    
    def trade(self):

        for sec, weight in self.wt.items():
            if weight == 0 and self.Portfolio[sec].IsLong:
                self.Liquidate(sec)
                
            cond1 = weight == 0 and self.Portfolio[sec].IsLong
            cond2 = weight > 0 and not self.Portfolio[sec].Invested
            if cond1 or cond2:
                self.SetHoldings(sec, weight)
            
                    
    def record_vars(self):                
                
        hist = self.History([self.MKT], 2, Resolution.Daily)['close'].unstack(level= 0).dropna() 
        self.spy.append(hist[self.MKT].iloc[-1])
        spy_perf = self.spy[-1] / self.spy[0] * self.cap
        self.Plot("Strategy Equity", "SPY", spy_perf)
        
        account_leverage = self.Portfolio.TotalHoldingsValue / self.Portfolio.TotalPortfolioValue
        self.Plot('Holdings', 'leverage', round(account_leverage, 1))
        for sec, weight in self.wt.items(): 
            self.real_wt[sec] = round(self.ActiveSecurities[sec].Holdings.Quantity * self.Securities[sec].Price / self.Portfolio.TotalPortfolioValue,4)
            self.Plot('Holdings', self.Securities[sec].Symbol, round(self.real_wt[sec], 3))