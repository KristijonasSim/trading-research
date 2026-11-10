"""
The Distilled Bear in & out-type algo
based on Dan Whitnable's 22 Oct 2020 algo on Quantopian. 
Dan's original notes: 
"This is based on Peter Guenther great “In & Out” algo.
Included Tentor Testivis recommendation to use volatility adaptive calculation of WAIT_DAYS and RET.
Included Vladimir's ideas to eliminate fixed constants
Help from Thomas Chang"

https://www.quantopian.com/posts/new-strategy-in-and-out
https://www.quantconnect.com/forum/discussion/9597/the-in-amp-out-strategy-continued-from-quantopian/
"""

# Import packages
import numpy as np
import pandas as pd
import scipy as sc


class InOut(QCAlgorithm):

    def Initialize(self):
        
        self.SetStartDate(2008, 1, 1)  # Set Start Date
        self.SetCash(100000)  # Set Strategy Cash
        self.UniverseSettings.Resolution = Resolution.Daily
        res = Resolution.Minute
        
        # Holdings
        ### 'Out' holdings and weights
        self.BND1 = self.AddEquity('TLT', res).Symbol #TLT; TMF for 3xlev
        self.BND2 = self.AddEquity('IEF', res).Symbol #IEF; TYD for 3xlev
        self.HLD_OUT = {self.BND1: .5, self.BND2: .5}
        ### 'In' holdings and weights (static stock selection strategy)
        self.STKS = self.AddEquity('QQQ', res).Symbol #SPY or QQQ; TQQQ for 3xlev
        self.HLD_IN = {self.STKS: 1}
        
        # Market and list of signals based on ETFs
        self.MRKT = self.AddEquity('SPY', res).Symbol  # market
        self.GOLD = self.AddEquity('GLD', res).Symbol  # gold
        self.SLVA = self.AddEquity('SLV', res).Symbol  # vs silver
        self.UTIL = self.AddEquity('XLU', res).Symbol  # utilities
        self.INDU = self.AddEquity('XLI', res).Symbol  # vs industrials
        self.METL = self.AddEquity('DBB', res).Symbol  # input prices (metals)
        self.USDX = self.AddEquity('UUP', res).Symbol  # safe haven (USD)
        
        self.FORPAIRS = [self.GOLD, self.SLVA, self.UTIL, self.INDU, self.METL, self.USDX]
        
        # set a warm-up period to initialize the indicators
        self.SetWarmUp(timedelta(350))
        
        # Specific variables
        self.DISTILLED_BEAR = 999
        self.BE_IN = 999
        self.VOLA_LOOKBACK = 126
        self.WAITD_CONSTANT = 85
        self.DCOUNT = 0 # count of total days since start
        self.OUTDAY = 0 # dcount when self.be_in=0
        
        self.Schedule.On(
            self.DateRules.EveryDay(),
            self.TimeRules.AfterMarketOpen('SPY', 120),
            self.rebalance
        )        
        
        # Setup daily consolidation
        symbols = [self.MRKT] + self.FORPAIRS
        for symbol in symbols:
            self.consolidator = TradeBarConsolidator(timedelta(days=1))
            self.consolidator.DataConsolidated += self.consolidation_handler
            self.SubscriptionManager.AddConsolidator(symbol, self.consolidator)
        
        # Warm up history
        self.history = self.History(symbols, self.VOLA_LOOKBACK+1, Resolution.Daily)
        if self.history.empty or 'close' not in self.history.columns:
            return
        self.history = self.history['close'].unstack(level=0).dropna()
        self.derive_vola_waitdays()
        
    def consolidation_handler(self, sender, consolidated):
        self.history.loc[consolidated.EndTime, consolidated.Symbol] = consolidated.Close
        self.history = self.history.iloc[-(self.VOLA_LOOKBACK+1):]
        self.derive_vola_waitdays()

    def derive_vola_waitdays(self):
        volatility = np.log1p(self.history[[self.MRKT]].pct_change()).std() * np.sqrt(252)
        wait_days = int(volatility * self.WAITD_CONSTANT)
        returns_lookback = int((1.0 - volatility) * self.WAITD_CONSTANT)
        return wait_days, returns_lookback
        
    def rebalance(self):
        wait_days, returns_lookback = self.derive_vola_waitdays()
        
        ## Check for Bear
        returns = self.history.pct_change(returns_lookback).iloc[-1]
    
        silver_returns = returns[self.SLVA]
        gold_returns = returns[self.GOLD]
        industrials_returns = returns[self.INDU]
        utilities_returns = returns[self.UTIL]
        metals_returns = returns[self.METL]
        dollar_returns = returns[self.USDX]
        
        self.DISTILLED_BEAR = (((gold_returns > silver_returns) and
                       (utilities_returns > industrials_returns)) and 
                       (metals_returns < dollar_returns)
                       )
        
        # Determine whether 'in' or 'out' of the market
        if self.DISTILLED_BEAR:
            self.BE_IN = False
            self.OUTDAY = self.DCOUNT
        if self.DCOUNT >= self.OUTDAY + wait_days:
            self.BE_IN = True
        self.DCOUNT += 1
        
        # Determine holdings
        if not self.BE_IN:
            # Only trade when changing from in to out
            self.trade({**dict.fromkeys(self.HLD_IN, 0), **self.HLD_OUT})
        elif self.BE_IN:
            # Only trade when changing from out to in
            self.trade({**self.HLD_IN, **dict.fromkeys(self.HLD_OUT, 0)})
            
    def trade(self, weight_by_sec):
        buys = []
        for sec, weight in weight_by_sec.items():
            # Check that we have data in the algorithm to process a trade
            if not self.CurrentSlice.ContainsKey(sec) or self.CurrentSlice[sec] is None:
                continue
            cond1 = weight == 0 and self.Portfolio[sec].IsLong
            cond2 = weight > 0 and not self.Portfolio[sec].Invested
            if cond1 or cond2:
                quantity = self.CalculateOrderQuantity(sec, weight)
                if quantity > 0:
                    buys.append((sec, quantity))
                elif quantity < 0:
                    self.Order(sec, quantity)
        for sec, quantity in buys:
            self.Order(sec, quantity)