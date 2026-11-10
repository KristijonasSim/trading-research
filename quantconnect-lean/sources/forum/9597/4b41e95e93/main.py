'''
Intersection of ROC comparison using OUT_DAY approach by Vladimir v1.1 (diversified static lists)

inspired by Peter Guenther, Tentor Testivis, Dan Whitnable, Thomas Chang.
'''
import numpy as np
# -------------------------------------------------------------------------------------------
STOCKS = ['QQQ','MSFT','NFLX','AMZN','TSLA']; BONDS = ['TLT','TLH']; VOLA = 126; BASE_RET = 85; LEV = 0.99; 
# -------------------------------------------------------------------------------------------

class ROC_Comparison_IN_OUT(QCAlgorithm):

    def Initialize(self):

        self.SetStartDate(2008, 1, 1)
        # self.SetEndDate(2021, 1, 1)
        self.cap = 100000  
        
        
        self.STOCKS = [self.AddEquity('QQQ', Resolution.Minute).Symbol,
                       self.AddEquity('MSFT', Resolution.Minute).Symbol,
                       self.AddEquity('NFLX', Resolution.Minute).Symbol,
                       self.AddEquity('AMZN', Resolution.Minute).Symbol,
                    self.AddEquity('TSLA', Resolution.Minute).Symbol]
        
        self.mom_lookback = 6*21
        self.stock_selection = None
        self.ret_reb_month = 0
        
        self.BONDS = [self.AddEquity(ticker, Resolution.Minute).Symbol for ticker in BONDS]

        self.ASSETS = [self.STOCKS, self.BONDS]

        self.SLV = self.AddEquity('SLV', Resolution.Daily).Symbol  
        self.GLD = self.AddEquity('GLD', Resolution.Daily).Symbol  
        self.XLI = self.AddEquity('XLI', Resolution.Daily).Symbol 
        self.XLU = self.AddEquity('XLU', Resolution.Daily).Symbol
        self.DBB = self.AddEquity('DBB', Resolution.Daily).Symbol  
        self.UUP = self.AddEquity('UUP', Resolution.Daily).Symbol  
        self.MKT = self.AddEquity('SPY', Resolution.Daily).Symbol 

        self.pairs = [self.SLV, self.GLD, self.XLI, self.XLU, self.DBB, self.UUP]
        
        self.bull = 1        
        self.count = 0 
        self.outday = 0        
        self.wt = {}
        self.real_wt = {}
        self.mkt = []
        self.SetWarmUp(timedelta(350))

        self.Schedule.On(self.DateRules.EveryDay(), self.TimeRules.AfterMarketOpen('SPY', 60),
            self.daily_check)
        self.Schedule.On(self.DateRules.EveryDay(), self.TimeRules.AfterMarketOpen('SPY', 120),
            self.trade)    
            
        symbols = [self.MKT] + self.pairs + self.STOCKS + self.BONDS
        for symbol in symbols:
            self.consolidator = TradeBarConsolidator(timedelta(days=1))
            self.consolidator.DataConsolidated += self.consolidation_handler
            self.SubscriptionManager.AddConsolidator(symbol, self.consolidator)
        
        self.history = self.History(symbols, VOLA + 1, Resolution.Daily)
        if self.history.empty or 'close' not in self.history.columns:
            return
        self.history = self.history['close'].unstack(level=0).dropna()
        
        
    def consolidation_handler(self, sender, consolidated):
        self.history.loc[consolidated.EndTime, consolidated.Symbol] = consolidated.Close
        self.history = self.history.iloc[-(max(VOLA, self.mom_lookback)+1):] 
        

    def daily_check(self):
        
        vola = self.history[[self.MKT]].iloc[-(VOLA+1):].pct_change().std() * np.sqrt(252)
        wait_days = int(vola * BASE_RET)
        period = int((1.0 - vola) * BASE_RET)        
        r = self.history.pct_change(period).iloc[-1]

        exit = ((r[self.SLV] < r[self.GLD]) and (r[self.XLI] < r[self.XLU]) and (r[self.DBB] < r[self.UUP]))

        if exit:
            self.bull = 0
            self.outday = self.count
        if self.count >= self.outday + wait_days:
            self.bull = 1
        self.count += 1
        
        
    def trade(self):
        if self.ret_reb_month!=self.Time.month:
            self.stock_selection = self.calc_return(self.STOCKS, 1)
            self.ret_reb_month = self.Time.month
        
        for sec in self.STOCKS: 
            self.wt[sec] = LEV/len(self.stock_selection) if self.bull and (sec in self.stock_selection) else 0;
        for sec in self.BONDS: 
            self.wt[sec] = 0 if self.bull else LEV/len(self.BONDS);

        for sec, weight in self.wt.items():
            if weight == 0 and self.Portfolio[sec].IsLong:
                self.Liquidate(sec)
                
            cond1 = weight == 0 and self.Portfolio[sec].IsLong
            cond2 = weight > 0 and not self.Portfolio[sec].Invested
            if cond1 or cond2:
                self.SetHoldings(sec, weight)
   
   
    def calc_return(self, stocks, num):
        ret = {}
        
        for symbol in stocks:
            try:
                ret[symbol] = (self.history[[symbol]].iloc[-1] / self.history[[symbol]].iloc[-(self.mom_lookback)] - 1).iloc[0]
            except:
                self.Debug(str(symbol))
                continue
        
        ret = sorted(ret, key = ret.get, reverse = True)[:num]
        
        return ret
        
                    
    def OnEndOfDay(self): 
        
        mkt_price = self.Securities[self.MKT].Close
        self.mkt.append(mkt_price)
        mkt_perf = self.mkt[-1] / self.mkt[0] * self.cap
        self.Plot('Strategy Equity', 'SPY', mkt_perf)
        
        account_leverage = self.Portfolio.TotalHoldingsValue / self.Portfolio.TotalPortfolioValue
        self.Plot('Holdings', 'leverage', round(account_leverage, 1))
        for sec, weight in self.wt.items(): 
            self.real_wt[sec] = round(self.ActiveSecurities[sec].Holdings.Quantity * self.Securities[sec].Price / self.Portfolio.TotalPortfolioValue,4)
            self.Plot('Holdings', self.Securities[sec].Symbol, round(self.real_wt[sec], 3))