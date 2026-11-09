"""
SEL(stock selection part)
Based on the 'Momentum Strategy with Market Cap and EV/EBITDA' strategy introduced by Jing Wu, 6 Feb 2018
adapted and recoded by Jack Simonson, Goldie Yalamanchi, Vladimir, Peter Guenther, Leandro Maia and Simone Pantaleoni
https://www.quantconnect.com/forum/discussion/3377/momentum-strategy-with-market-cap-and-ev-ebitda/p1
https://www.quantconnect.com/forum/discussion/9678/quality-companies-in-an-uptrend/p1
https://www.quantconnect.com/forum/discussion/9632/amazing-returns-superior-stock-selection-strategy-superior-in-amp-out-strategy/p1

I/O(in & out part)
The Distilled Bear in & out algo
based on Dan Whitnable's 22 Oct 2020 algo on Quantopian. 
Dan's original notes: 
"This is based on Peter Guenther great “In & Out” algo.
Included Tentor Testivis recommendation to use volatility adaptive calculation of WAIT_DAYS and RET.
Included Vladimir's ideas to eliminate fixed constants
Help from Thomas Chang"

https://www.quantopian.com/posts/new-strategy-in-and-out
https://www.quantconnect.com/forum/discussion/9597/the-in-amp-out-strategy-continued-from-quantopian/
"""

from QuantConnect.Data.UniverseSelection import *
import math
import numpy as np
import pandas as pd
import scipy as sp

class EarningsFactorWithMomentum_InOut(QCAlgorithm):

    def Initialize(self):

        self.SetStartDate(2008, 1, 1)  #Set Start Date
        self.cap = 100000
        self.SetCash(self.cap)
        
        self.averages = { }
        res = Resolution.Hour
        
        # Holdings
        ### 'Out' holdings and weights
        self.BND1 = self.AddEquity('TLT', res).Symbol #TLT; TMF for 3xlev
        self.HLD_OUT = {self.BND1: 1}
        ### 'In' holdings and weights (static stock selection strategy)
        ##### These are determined flexibly via sorting on fundamentals
        
        ##### In & Out parameters #####
        # Feed-in constants
        self.INI_WAIT_DAYS = 15  # out for 3 trading weeks
        self.wait_days = self.INI_WAIT_DAYS
        
        # Market and list of signals based on ETFs
        self.MRKT = self.AddEquity('SPY', res).Symbol  # market
        self.GOLD = self.AddEquity('GLD', res).Symbol  # gold
        self.SLVA = self.AddEquity('SLV', res).Symbol  # vs silver
        self.UTIL = self.AddEquity('XLU', res).Symbol  # utilities
        self.INDU = self.AddEquity('XLI', res).Symbol  # vs industrials
        self.METL = self.AddEquity('DBB', res).Symbol  # input prices (metals)
        self.USDX = self.AddEquity('UUP', res).Symbol  # safe haven (USD)
        
        self.FORPAIRS = [self.GOLD, self.SLVA, self.UTIL, self.INDU, self.METL, self.USDX]

        # Specific variables
        self.DISTILLED_BEAR = 999
        self.BE_IN = 999
        self.BE_IN_PRIOR = 0
        self.VOLA_LOOKBACK = 126
        self.WAITD_CONSTANT = 85
        self.DCOUNT = 0 # count of total days since start
        self.OUTDAY = (-self.INI_WAIT_DAYS+1) # dcount when self.be_in=0, initial setting ensures trading right away
        
        # set a warm-up period to initialize the indicator
        self.SetWarmUp(timedelta(350))
        
        ##### Momentum & fundamentals strategy parameters #####
        #self.UniverseSettings.Resolution = Resolution.Daily
        self.UniverseSettings.Resolution = res
        self.AddUniverse(self.UniverseCoarseFilter, self.UniverseFundamentalsFilter)
        self.num_screener = 15
        self.num_stocks = 10
        self.formation_days = 126
        self.lowmom = False
        self.data = {}
        self.setrebalancefreq = 60 # X days, update universe and momentum calculation
        self.updatefinefilter = 0
        self.symbols = None
        self.reb_count = 0
        
        self.Schedule.On(
            self.DateRules.EveryDay(),
            self.TimeRules.AfterMarketOpen('SPY', 90),
            self.rebalance_when_out_of_the_market
        )
        
        self.Schedule.On(
            self.DateRules.EveryDay(), 
            self.TimeRules.BeforeMarketClose('SPY', 0), 
            self.record_vars
        )  
        
        # Setup daily consolidation
        symbols = [self.MRKT] + self.FORPAIRS
        for symbol in symbols:
            self.consolidator = TradeBarConsolidator(timedelta(days=1))
            self.consolidator.DataConsolidated += self.consolidation_handler
            self.SubscriptionManager.AddConsolidator(symbol, self.consolidator)
        
        # Warm up history
        self.lookback = 252
        self.history = self.History(symbols, self.lookback, Resolution.Daily)
        if self.history.empty or 'close' not in self.history.columns:
            return
        self.history = self.history['close'].unstack(level=0).dropna()
        self.update_history_shift()
        
        # Benchmark = record SPY
        self.spy = []

 
    def UniverseCoarseFilter(self, coarse):
        # Update at the beginning (by setting self.OUTDAY = -self.INI_WAIT_DAYS), every X days (rebalance frequency), and one day before waitdays are up
        if not (((self.DCOUNT-self.reb_count)==self.setrebalancefreq) or (self.DCOUNT == self.OUTDAY + self.wait_days - 1)):
            self.updatefinefilter = 0
            return Universe.Unchanged
        
        self.updatefinefilter = 1 
        
        # drop stocks which have no fundamental data or have too low prices
        #selected = [x for x in coarse if (x.HasFundamentalData) and (float(x.Price) > 5)]
        selected = [x for x in coarse if (x.HasFundamentalData) and (float(x.Price) > 2)]

        # We are going to use a dictionary to refer the object that will keep the moving averages
        for cf in selected:
            symbol = cf.Symbol
            if cf.Symbol not in self.averages:
                self.averages[cf.Symbol] = SymbolDataVolume(cf.Symbol, 21, 5, 504)

            # Updates the SymbolData object with current EOD price
            avg = self.averages[cf.Symbol]
            avg.update(cf.EndTime, cf.AdjustedPrice, cf.DollarVolume)

        # Filter the values of the dict: we only want up-trending securities

        values = list(filter(lambda sd: sd.smaw.Current.Value > 0, self.averages.values()))

        values.sort(key=lambda x: (x.smaw.Current.Value), reverse=True)

        # we need to return only the symbol objects
        return [ x.symbol for x in values[:100] ]
        
        
    def UniverseFundamentalsFilter(self, fundamental):
        if self.updatefinefilter == 0:
            return Universe.Unchanged
            
        filtered_fundamental = [x for x in fundamental if (x.ValuationRatios.EVToEBITDA > 0) 
                                        and (x.EarningReports.BasicAverageShares.ThreeMonths > 0) 
                                        and float(x.EarningReports.BasicAverageShares.ThreeMonths) * x.Price > 2e9]


        top = sorted(filtered_fundamental, key = lambda x: x.ValuationRatios.EVToEBITDA, reverse=True)[:self.num_screener]
        self.symbols = [x.Symbol for x in top]
        self.updatefinefilter = 0
        self.reb_count = self.DCOUNT
        return self.symbols

    
    def OnSecuritiesChanged(self, changes):
        
        for security in changes.RemovedSecurities:
            symbol_data = self.data.pop(security.Symbol, None)
            if symbol_data:
                symbol_data.dispose()
        
        for security in changes.AddedSecurities:
            if security.Symbol not in self.data:
                self.data[security.Symbol] = SymbolData(security.Symbol, self.formation_days, self)
    
    def consolidation_handler(self, sender, consolidated):
        self.history.loc[consolidated.EndTime, consolidated.Symbol] = consolidated.Close
        self.history = self.history.iloc[-self.lookback:]
        self.update_history_shift()
        
    def update_history_shift(self):
        self.history_shift = self.history.rolling(11, center=True).mean().shift(60)

    def derive_vola_waitdays(self):
        volatility = np.log1p(self.history[[self.MRKT]].pct_change()).std() * np.sqrt(252)
        wait_days = int(volatility * self.WAITD_CONSTANT)
        returns_lookback = int((1.0 - volatility) * self.WAITD_CONSTANT)
        return wait_days, returns_lookback
 
        
    def rebalance_when_out_of_the_market(self):
        self.wait_days, returns_lookback = self.derive_vola_waitdays()
        
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
            self.trade({**dict.fromkeys(self.Portfolio.Keys, 0), **self.HLD_OUT})
        if (self.DCOUNT >= self.OUTDAY + self.wait_days):
            self.BE_IN = True
        
        # Update stock ranking/holdings, when swithing from 'out' to 'in' plus every X days when 'in' (set rebalance frequency)
        if (self.BE_IN and not self.BE_IN_PRIOR) or (self.BE_IN and (self.DCOUNT==self.reb_count)):
            self.rebalance()
                
        self.BE_IN_PRIOR = self.BE_IN
        self.DCOUNT += 1


    def rebalance(self):
        #self.Debug(str(self.Time) + "rebalance: be_in:" + str(self.be_in) + " flip_flag:" + str(self.flip_flag))
            
        if self.symbols is None: return
        symbols = self.calc_return(self.symbols)
        
        weight = 0.99/len(symbols)
        self.trade({**dict.fromkeys(symbols, weight), 
                    **dict.fromkeys(list(dict.fromkeys(set([x.Symbol for x in self.Portfolio.Values if x.Invested]) - set(symbols))), 0), 
                    **dict.fromkeys(self.HLD_OUT, 0)})
        
        
    def calc_return(self, stocks):
        ready = [self.data[symbol] for symbol in stocks if self.data[symbol].Roc.IsReady]
        sorted_by_roc = sorted(ready, key=lambda x: x.Roc.Current.Value, reverse = not self.lowmom)
        return [symbol_data.Symbol for symbol_data in sorted_by_roc[:self.num_stocks] ]
       
        
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
 
        
    def record_vars(self): 
        self.spy.append(self.history[self.MRKT].iloc[-1])
        spy_perf = self.spy[-1] / self.spy[0] * self.cap
        self.Plot('Strategy Equity', 'SPY', spy_perf)
        
        account_leverage = self.Portfolio.TotalHoldingsValue / self.Portfolio.TotalPortfolioValue
        self.Plot('Holdings', 'leverage', round(account_leverage, 2))
    
        
class SymbolData(object):
    def __init__(self, symbol, roc_period, algorithm):
        self.Symbol = symbol
        self.Roc = RateOfChange(roc_period)
        self.algorithm = algorithm
        
        self.consolidator = algorithm.ResolveConsolidator(symbol, Resolution.Daily)
        algorithm.RegisterIndicator(symbol, self.Roc, self.consolidator)
        
        # Warm up ROC
        history = algorithm.History(symbol, roc_period, Resolution.Daily)
        if history.empty or 'close' not in history.columns:
            return
        for index, row in history.loc[symbol].iterrows():
            self.Roc.Update(index, row['close'])
    
    def dispose(self):
        self.algorithm.SubscriptionManager.RemoveConsolidator(self.Symbol, self.consolidator)
        
        
class SymbolDataVolume(object):
    def __init__(self, symbol, period, periodw, periodlt):
        self.symbol = symbol
        #self.tolerance = 1.01
        self.tolerance = 0.95
        self.fast = ExponentialMovingAverage(10)
        self.slow = ExponentialMovingAverage(21)
        self.is_uptrend = False
        self.scale = 0
        self.volume = 0
        self.volume_ratio = 0
        self.volume_ratiow = 0
        self.volume_ratiol = 0
        self.sma = SimpleMovingAverage(period)
        self.smaw = SimpleMovingAverage(periodw)
        self.smalt = SimpleMovingAverage(periodlt)

    def update(self, time, value, volume):
        self.volume = volume


        if self.smaw.Update(time, volume):
            # get ratio of this volume bar vs previous 10 before it.
            if self.smaw.Current.Value != 0:
                self.volume_ratiow = volume / self.smaw.Current.Value
        if self.sma.Update(time, volume):
            # get ratio of this volume bar vs previous 10 before it.
            if self.sma.Current.Value != 0:
                self.volume_ratio = self.smaw.Current.Value / self.sma.Current.Value

        if self.smalt.Update(time, volume):
            if self.smalt.Current.Value != 0 and self.smaw.Current.Value != 0:
                self.volume_ratiol = self.smaw.Current.Value / self.smalt.Current.Value

            
        if self.fast.Update(time, value) and self.slow.Update(time, value):
            fast = self.fast.Current.Value
            slow = self.slow.Current.Value
            #self.is_uptrend = fast > slow * self.tolerance
            self.is_uptrend = (fast > (slow * self.tolerance)) and (value > (fast * self.tolerance))

        if self.is_uptrend:
            self.scale = (fast - slow) / ((fast + slow) / 2.0)