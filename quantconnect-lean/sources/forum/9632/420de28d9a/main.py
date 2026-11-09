"""
SEL(stock selection part)
Qual Up
Based on the 'Quality Companies in an Uptrand' strategy introduced by Chris Cain, 22 Nov 2019
adapted and recoded by Jonathon Tzu and Peter Guenther

https://www.quantconnect.com/forum/discussion/9678/quality-companies-in-an-uptrend/p1
https://www.quantconnect.com/forum/discussion/9632/amazing-returns-superior-stock-selection-strategy-superior-in-amp-out-strategy/p2

I/O(in & out part)
Option 1: The In & Out algo
Based on the 'In & Out' strategy introduced by Peter Guenther, 4 Oct 2020
expanded/inspired by Tentor Testivis, Dan Whitnable (Quantopian), Vladimir, Thomas Chang, 
Mateusz Pulka, Derek Melchin (QuantConnect), Nathan Swenson, Goldie Yalamanchi, and Sudip Sil

https://www.quantopian.com/posts/new-strategy-in-and-out
https://www.quantconnect.com/forum/discussion/9597/the-in-amp-out-strategy-continued-from-quantopian/p1

Option 2: The Distilled Bear in & out algo
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

class QualUp_inout(QCAlgorithm):

    def Initialize(self):

        self.SetStartDate(2008, 1, 1)  #Set Start Date
        #self.SetEndDate(2010, 12, 31)  #Set End Date
        self.cap = 100000
        self.SetCash(self.cap)
        
        res = Resolution.Hour
        
        # Holdings
        ### 'Out' holdings and weights
        self.BND1 = self.AddEquity('TLT', res).Symbol #TLT; TMF for 3xlev
        self.quantity = {self.BND1: 0}
        
        # Choose in & out algo
        self.go_inout_vs_dbear = 1 # 1=In&Out, 0=DistilledBear
        
        ##### In & Out parameters #####
        # Feed-in constants
        self.INI_WAIT_DAYS = 15  # out for 3 trading weeks
        self.wait_days = self.INI_WAIT_DAYS
        
        # Market and list of signals based on ETFs
        self.MRKT = self.AddEquity('SPY', res).Symbol  # market
        self.PRDC = self.AddEquity('XLI', res).Symbol  # production (industrials)
        self.METL = self.AddEquity('DBB', res).Symbol  # input prices (metals)
        self.NRES = self.AddEquity('IGE', res).Symbol  # input prices (natural res)
        self.DEBT = self.AddEquity('SHY', res).Symbol  # cost of debt (bond yield)
        self.USDX = self.AddEquity('UUP', res).Symbol  # safe haven (USD)
        self.GOLD = self.AddEquity('GLD', res).Symbol  # gold
        self.SLVA = self.AddEquity('SLV', res).Symbol  # vs silver
        #self.INFL = self.AddEquity('RINF', res).Symbol  # disambiguate GPLD/SLVA pair via inflaction expectations
        self.TIPS = self.AddEquity('TIP', res).Symbol  # disambiguate GPLD/SLVA pair via inflaction expectations; Treasury Yield = TIPS Yield + Expected Inflation
        self.UTIL = self.AddEquity('XLU', res).Symbol  # utilities
        self.INDU = self.PRDC  # vs industrials
        self.SHCU = self.AddEquity('FXF', res).Symbol  # safe haven currency (CHF)
        self.RICU = self.AddEquity('FXA', res).Symbol  # vs risk currency (AUD)

        self.FORPAIRS = [self.GOLD, self.SLVA, self.UTIL, self.SHCU, self.RICU, self.TIPS] #self.INFL
        self.SIGNALS = [self.PRDC, self.METL, self.NRES, self.DEBT, self.USDX]
        self.pairlist = ['G_S', 'U_I', 'C_A']
        
        # Initialize variables
        ## 'In'/'out' indicator
        self.be_in = 1 #-1 #initially, set to an arbitrary value different from 1 (in) and 0 (out)
        self.be_in_prior = 0 #-1 #initially, set to an arbitrary value different from 1 (in) and 0 (out)
        ## Day count variables
        self.dcount = 0  # count of total days since start
        self.outday = (-self.INI_WAIT_DAYS+1)  # setting ensures universe updating at algo start
        ## Flexi wait days
        self.WDadjvar = self.INI_WAIT_DAYS
        self.adjwaitdays = self.INI_WAIT_DAYS
        ## For inflation gauge
        self.debt1st = []
        self.tips1st = []
        
        ##### Distilled Bear parameters (note: some signals shared with In & Out) #####
        self.DISTILLED_BEAR = 1 #-1
        self.VOLA_LOOKBACK = 126
        self.WAITD_CONSTANT = 85
        
        # set a warm-up period to initialize the indicator
        self.SetWarmUp(timedelta(350))
        
        ##### Valuation Rockets parameters #####
        self.UniverseSettings.Resolution = res
        self.AddUniverse(self.UniverseCoarseFilter, self.UniverseFundamentalsFilter)
        self.num_coarse = 500
        self.num_screener = 250
        self.num_stocks = 20
        self.formation_days = 126
        self.lowmom = False
        self.data = {}
        self.setrebalancefreq = 60 # X days, update universe and momentum calculation
        self.updatefinefilter = 0
        self.symbols = None
        self.reb_count = 0
        
        self.Schedule.On(
            self.DateRules.EveryDay(),
            self.TimeRules.AfterMarketOpen('SPY', 30),
            self.rebalance_when_out_of_the_market)
        
        self.Schedule.On(
            self.DateRules.EveryDay(), 
            self.TimeRules.BeforeMarketClose('SPY', 0), 
            self.record_vars)  
        
        # Benchmarks
        self.QQQ = self.AddEquity('QQQ', res).Symbol
        self.benchmarks = []
        self.year = self.Time.year #for resetting benchmarks annually if applicable
        
        # Setup daily consolidation
        symbols = [self.MRKT] + self.SIGNALS + self.FORPAIRS + [self.QQQ]
        for symbol in symbols:
            self.consolidator = TradeBarConsolidator(timedelta(days=1))
            self.consolidator.DataConsolidated += self.consolidation_handler
            self.SubscriptionManager.AddConsolidator(symbol, self.consolidator)
        
        # Warm up history
        if self.go_inout_vs_dbear==1: self.lookback = 252
        if self.go_inout_vs_dbear==0: self.lookback = 126
        self.history = self.History(symbols, self.lookback, Resolution.Daily)
        if self.history.empty or 'close' not in self.history.columns:
            return
        self.history = self.history['close'].unstack(level=0).dropna()
        
    def UniverseCoarseFilter(self, coarse):
        if not (((self.dcount-self.reb_count)==self.setrebalancefreq) or (self.dcount == self.outday + self.adjwaitdays - 1)):
            self.updatefinefilter = 0
            return Universe.Unchanged
        
        self.updatefinefilter = 1
            
        # drop stocks which have no fundamental data or have too low prices
        selected = [x for x in coarse if (x.HasFundamentalData) and (float(x.Price) > 5)]
        # rank the stocks by dollar volume 
        filtered = sorted(selected, key=lambda x: x.DollarVolume, reverse=True)
        return [x.Symbol for x in filtered[:self.num_coarse]]
        
        
    def UniverseFundamentalsFilter(self, fundamental):
        if self.updatefinefilter == 0:
            return Universe.Unchanged
            
        rank_cash_return = sorted(fundamental, key=lambda x: x.ValuationRatios.CashReturn, reverse=True)
        rank_fcf_yield  = sorted(fundamental, key=lambda x: x.ValuationRatios.FCFYield, reverse=True)
        rank_roic = sorted(fundamental, key=lambda x: x.OperationRatios.ROIC.Value, reverse=True)
        rank_ltd_to_eq = sorted(fundamental, key=lambda x: x.OperationRatios.LongTermDebtEquityRatio.Value, reverse=True)
        
        combo_rank = {}
        for i,ele in enumerate(rank_cash_return):
            rank1 = i
            rank2 = rank_fcf_yield.index(ele)
            score = sum([rank1*0.5,rank2*0.5])
            combo_rank[ele] = score
        
        rank_value = dict(sorted(combo_rank.items(), key=lambda item:item[1], reverse=False))
        
        stock_dict = {}
        
        # assign a score to each stock, you can also change the rule of scoring here.
        for i,ele in enumerate(rank_roic):
            rank1 = i
            rank2 = rank_ltd_to_eq.index(ele)
            rank3 = list(rank_value.keys()).index(ele)
            score = sum([rank1*0.33,rank2*0.33,rank3*0.33])
            stock_dict[ele] = score
        
        # sort the stocks by their scores
        self.sorted_stock = sorted(stock_dict.items(), key=lambda d:d[1],reverse=True)
        self.sorted_symbol = [self.sorted_stock[i][0] for i in range(len(self.sorted_stock))]
        top= self.sorted_symbol[:self.num_screener]
        self.symbols = [x.Symbol for x in top]
        
        #self.Log("100 fine-filtered stocks\n" + str(sorted([str(i.Value) for i in self.symbols])))
        self.updatefinefilter = 0
        self.reb_count = self.dcount
        return self.symbols

    
    def OnSecuritiesChanged(self, changes):
        
        addedSymbols = []
        for security in changes.AddedSecurities:
            addedSymbols.append(security.Symbol)
            if security.Symbol not in self.data:
                self.data[security.Symbol] = SymbolData(security.Symbol, self.formation_days, self)
   
        if len(addedSymbols) > 0:
            history = self.History(addedSymbols, 1 + self.formation_days, Resolution.Daily).loc[addedSymbols]
            for symbol in addedSymbols:
                try:
                    self.data[symbol].Warmup(history.loc[symbol])
                except:
                    self.Debug(str(symbol))
                    continue
    
    def consolidation_handler(self, sender, consolidated):
        self.history.loc[consolidated.EndTime, consolidated.Symbol] = consolidated.Close
        self.history = self.history.iloc[-self.lookback:]
        if self.go_inout_vs_dbear==1: self.update_history_shift()
    
    def update_history_shift(self):
        self.history_shift = self.history.rolling(11, center=True).mean().shift(60)
        
    def derive_vola_waitdays(self):
        volatility = 0.6 * np.log1p(self.history[[self.MRKT]].pct_change()).std() * np.sqrt(252)
        wait_days = int(volatility * self.WAITD_CONSTANT)
        returns_lookback = int((1.0 - volatility) * self.WAITD_CONSTANT)
        return wait_days, returns_lookback
    
    def signalcheck_inout(self):
        ##### In & Out signal check logic #####
        
        # Returns sample to detect extreme observations
        returns_sample = (self.history / self.history_shift - 1)
        # Reverse code USDX: sort largest changes to bottom
        returns_sample[self.USDX] = returns_sample[self.USDX] * (-1)
        # For pairs, take returns differential, reverse coded
        returns_sample['G_S'] = -(returns_sample[self.GOLD] - returns_sample[self.SLVA])
        returns_sample['U_I'] = -(returns_sample[self.UTIL] - returns_sample[self.INDU])
        returns_sample['C_A'] = -(returns_sample[self.SHCU] - returns_sample[self.RICU])   

        # Extreme observations; statist. significance = 1%
        pctl_b = np.nanpercentile(returns_sample, 1, axis=0)
        extreme_b = returns_sample.iloc[-1] < pctl_b
        
        # Re-assess/disambiguate double-edged signals
        if self.dcount==0:
            self.debt1st = self.history[self.DEBT]
            self.tips1st = self.history[self.TIPS]
        self.history['INFL'] = (self.history[self.DEBT]/self.debt1st - self.history[self.TIPS]/self.tips1st)
        median = np.nanmedian(self.history, axis=0)
        abovemedian = self.history.iloc[-1] > median
        ### Interest rate expectations (cost of debt) may increase because the economic outlook improves (showing in rising input prices) = actually not a negative signal
        extreme_b.loc[[self.DEBT]] = np.where((extreme_b.loc[[self.DEBT]].any()) & (abovemedian[[self.METL, self.NRES]].any()), False, extreme_b.loc[[self.DEBT]])
        ### GOLD/SLVA differential may increase due to inflation expectations which actually suggest an economic improvement = actually not a negative signal
        extreme_b.loc['G_S'] = np.where((extreme_b.loc[['G_S']].any()) & (abovemedian.loc[['INFL']].any()), False, extreme_b.loc['G_S'])

        # Determine waitdays empirically via safe haven excess returns, 50% decay
        self.WDadjvar = int(
            max(0.50 * self.WDadjvar,
                self.INI_WAIT_DAYS * max(1,
                                         np.where((returns_sample[self.GOLD].iloc[-1]>0) & (returns_sample[self.SLVA].iloc[-1]<0) & (returns_sample[self.SLVA].iloc[-2]>0), self.INI_WAIT_DAYS, 1),
                                         np.where((returns_sample[self.UTIL].iloc[-1]>0) & (returns_sample[self.INDU].iloc[-1]<0) & (returns_sample[self.INDU].iloc[-2]>0), self.INI_WAIT_DAYS, 1),
                                         np.where((returns_sample[self.SHCU].iloc[-1]>0) & (returns_sample[self.RICU].iloc[-1]<0) & (returns_sample[self.RICU].iloc[-2]>0), self.INI_WAIT_DAYS, 1)
                                         ))
        )
        self.adjwaitdays = min(60, self.WDadjvar)
        
        return (extreme_b[self.SIGNALS + self.pairlist]).any()
    
    def signalcheck_dbear(self):
        ##### Distilled Bear signal check logic #####
        
        self.adjwaitdays, returns_lookback = self.derive_vola_waitdays()
        
        ## Check for Bears
        returns = self.history.pct_change(returns_lookback).iloc[-1]
    
        silver_returns = returns[self.SLVA]
        gold_returns = returns[self.GOLD]
        industrials_returns = returns[self.INDU]
        utilities_returns = returns[self.UTIL]
        metals_returns = returns[self.METL]
        dollar_returns = returns[self.USDX]
        
        DISTILLED_BEAR = (((gold_returns > silver_returns) and
                       (utilities_returns > industrials_returns)) and 
                       (metals_returns < dollar_returns)
                       )
        
        return DISTILLED_BEAR
    
        
    def rebalance_when_out_of_the_market(self):
        
        if self.go_inout_vs_dbear==1: out_signal = self.signalcheck_inout()
        if self.go_inout_vs_dbear==0: out_signal = self.signalcheck_dbear()
            
        ##### Determine whether 'in' or 'out' of the market. Perform out trading if applicable #####
        
        if out_signal:
            self.be_in = False
            self.outday = self.dcount
            
            if self.quantity[self.BND1] == 0:
                for symbol in self.quantity.copy().keys():
                    if symbol == self.BND1: continue
                    self.Order(symbol, - self.quantity[symbol])
                    self.Debug([str(self.Time), str(symbol), str(-self.quantity[symbol])])
                    del self.quantity[symbol]
                quantity = self.Portfolio.TotalPortfolioValue / self.Securities[self.BND1].Close
                self.quantity[self.BND1] = math.floor(quantity)
                self.Order(self.BND1, self.quantity[self.BND1])
                self.Debug([str(self.Time), str(self.BND1), str(self.quantity[self.BND1])])
        
        if (self.dcount >= self.outday + self.adjwaitdays):
            self.be_in = True
        
        # Update stock ranking/holdings, when swithing from 'out' to 'in' plus every X days when 'in' (set rebalance frequency)
        if (self.be_in and not self.be_in_prior) or (self.be_in and (self.dcount==self.reb_count)):
            self.rebalance()
                
        self.be_in_prior = self.be_in
        self.dcount += 1


    def rebalance(self):
            
        if self.symbols is None: return
        chosen_df = self.calc_return(self.symbols)
        chosen_df = chosen_df.iloc[:self.num_stocks]
        
        if self.quantity[self.BND1] > 0:
            self.Order(self.BND1, - self.quantity[self.BND1])
            self.Debug([str(self.Time), str(self.BND1), str(-self.quantity[self.BND1])])
            self.quantity[self.BND1] = 0
            
        weight = 1 / self.num_stocks
        for symbol in self.quantity.copy().keys():
            if symbol == self.BND1: continue
            if not self.CurrentSlice.ContainsKey(symbol) or self.CurrentSlice[symbol] is None:
                continue
            if symbol not in chosen_df.index:
                self.Order(symbol, - self.quantity[symbol])
                self.Debug([str(self.Time), str(symbol), str(-self.quantity[symbol])])
                del self.quantity[symbol]
            else:
                quantity = self.Portfolio.TotalPortfolioValue * weight / self.Securities[symbol].Close
                if math.floor(quantity) != self.quantity[symbol]:
                    self.Order(symbol, math.floor(quantity) - self.quantity[symbol])
                    self.Debug([str(self.Time), str(symbol), str(math.floor(quantity) -self.quantity[symbol])])
                    self.quantity[symbol] = math.floor(quantity)
        
        for symbol in chosen_df.index:
            if not self.CurrentSlice.ContainsKey(symbol) or self.CurrentSlice[symbol] is None:
                continue
            if symbol not in self.quantity.keys():
                quantity = self.Portfolio.TotalPortfolioValue * weight / self.Securities[symbol].Close
                self.quantity[symbol] = math.floor(quantity)
                self.Order(symbol, self.quantity[symbol])
                self.Debug([str(self.Time), str(symbol), str(self.quantity[symbol])])
 
        
    def calc_return(self, stocks):
        
        ret = {}
        for symbol in stocks:
            try:
                ret[symbol] = self.data[symbol].Roc.Current.Value
            except:
                self.Debug(str(symbol))
                continue
            
        df_ret = pd.DataFrame.from_dict(ret, orient='index')
        df_ret.columns = ['return']
        sort_return = df_ret.sort_values(by = ['return'], ascending = self.lowmom)
        
        return sort_return
    
        
    def record_vars(self): 
        
        if self.dcount==1: self.benchmarks = [self.history[self.MRKT].iloc[-2], self.Portfolio.TotalPortfolioValue, self.history[self.QQQ].iloc[-2]]
        # reset portfolio value and qqq benchmark annually
        if self.Time.year!=self.year: self.benchmarks = [self.benchmarks[0], self.Portfolio.TotalPortfolioValue, self.history[self.QQQ].iloc[-2]]
        self.year = self.Time.year
        
        # SPY benchmark for main chart
        spy_perf = self.history[self.MRKT].iloc[-1] / self.benchmarks[0] * self.cap
        self.Plot('Strategy Equity', 'SPY', spy_perf)
        
        # Leverage gauge: cash level
        self.Plot('Cash level', 'cash', round(self.Portfolio.Cash+self.Portfolio.UnsettledCash, 0))
        
        # Annual saw tooth return comparison: Portfolio VS QQQ
        saw_portfolio_return = self.Portfolio.TotalPortfolioValue / self.benchmarks[1] - 1
        saw_qqq_return = self.history[self.QQQ].iloc[-1] / self.benchmarks[2] - 1
        self.Plot('Annual Saw Tooth Returns: Portfolio VS QQQ', 'Annual portfolio return', round(saw_portfolio_return, 4))
        self.Plot('Annual Saw Tooth Returns: Portfolio VS QQQ', 'Annual QQQ return', round(float(saw_qqq_return), 4))
        
        ### IN/Out indicator and wait days
        self.Plot("In Out", "in_market", int(self.be_in))
        self.Plot("Wait Days", "waitdays", self.adjwaitdays)
   
        
class SymbolData(object):
    def __init__(self, symbol, roc, algorithm):
        self.Symbol = symbol
        self.Roc = RateOfChange(roc)
        self.algorithm = algorithm
        
        self.consolidator = algorithm.ResolveConsolidator(symbol, Resolution.Daily)
        algorithm.RegisterIndicator(symbol, self.Roc, self.consolidator)
        
    def Warmup(self, history):
        for index, row in history.iterrows():
            self.Roc.Update(index, row['close'])