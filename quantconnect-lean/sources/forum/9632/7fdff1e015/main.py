"""
SEL(stock selection part)
Based on the 'Quality Companies in an Uptrand' strategy introduced by Chris Cain, 22 Nov 2019
adapted and recoded by Jonathon Tzu and Peter Guenther
https://www.quantconnect.com/forum/discussion/9678/quality-companies-in-an-uptrend/p1
https://www.quantconnect.com/forum/discussion/9632/amazing-returns-superior-stock-selection-strategy-superior-in-amp-out-strategy/p2

I/O(in & out part)
Based on the 'In & Out' strategy introduced by Peter Guenther, 4 Oct 2020
expanded/inspired by Tentor Testivis, Dan Whitnable (Quantopian), Vladimir, Thomas Chang, 
Mateusz Pulka, Derek Melchin (QuantConnect), Nathan Swenson, Goldie Yalamanchi, and Sudip Sil
https://www.quantopian.com/posts/new-strategy-in-and-out
https://www.quantconnect.com/forum/discussion/9597/the-in-amp-out-strategy-continued-from-quantopian/p1
code version: In_out_flex_v5_disambiguate_v3
"""

from QuantConnect.Data.UniverseSelection import *
import math
import numpy as np
import pandas as pd
import scipy as sp

class QualUp_InOut(QCAlgorithm):

    def Initialize(self):

        self.SetStartDate(2008, 1, 1)  #Set Start Date
        #self.SetEndDate(2009, 12, 31)  #Set End Date
        self.cap = 100000
        self.SetCash(self.cap)
        
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
        
        
        # Market and list of signals based on ETFs
        self.MRKT = self.AddEquity('SPY', res).Symbol  # market
        self.PRDC = self.AddEquity('XLI', res).Symbol  # production (industrials)
        self.METL = self.AddEquity('DBB', res).Symbol  # input prices (metals)
        self.NRES = self.AddEquity('IGE', res).Symbol  # input prices (natural res)
        self.DEBT = self.AddEquity('SHY', res).Symbol  # cost of debt (bond yield)
        self.USDX = self.AddEquity('UUP', res).Symbol  # safe haven (USD)
        self.GOLD = self.AddEquity('GLD', res).Symbol  # gold
        self.SLVA = self.AddEquity('SLV', res).Symbol  # vs silver
        self.INFL = self.AddEquity('RINF', res).Symbol  # disambiguate GPLD/SLVA pair via inflaction expectations
        self.UTIL = self.AddEquity('XLU', res).Symbol  # utilities
        self.INDU = self.PRDC  # vs industrials
        self.SHCU = self.AddEquity('FXF', res).Symbol  # safe haven currency (CHF)
        self.RICU = self.AddEquity('FXA', res).Symbol  # vs risk currency (AUD)

        self.FORPAIRS = [self.GOLD, self.SLVA, self.UTIL, self.SHCU, self.RICU, self.INFL]
        self.SIGNALS = [self.PRDC, self.METL, self.NRES, self.DEBT, self.USDX]
        self.pairlist = ['G_S', 'U_I', 'C_A']

        # Initialize variables
        ## 'In'/'out' indicator
        self.be_in = 999 #initially, set to an arbitrary value different from 1 (in) and 0 (out)
        self.be_in_prior = 0
        ## Day count variables
        self.dcount = 0  # count of total days since start
        self.outday = -self.INI_WAIT_DAYS+1  # dcount when self.be_in=0
        ## Flexi wait days
        self.WDadjvar = self.INI_WAIT_DAYS
        self.adjwaitdays = self.INI_WAIT_DAYS
        
        # set a warm-up period to initialize the indicator
        self.SetWarmUp(timedelta(350))
        
        ##### Qual-Up strategy parameters #####
        self.UniverseSettings.Resolution = Resolution.Hour
        self.AddUniverse(self.UniverseCoarseFilter, self.UniverseFundamentalsFilter)
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
            self.TimeRules.AfterMarketOpen('SPY', 90),
            self.rebalance_when_out_of_the_market
        )
        
        self.Schedule.On(
            self.DateRules.EveryDay(), 
            self.TimeRules.BeforeMarketClose('SPY', 0), 
            self.record_vars
        )  
        
        # Setup daily consolidation
        symbols = self.SIGNALS + [self.MRKT] + self.FORPAIRS
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
        if not ((self.be_in and ((self.dcount-self.reb_count)==self.setrebalancefreq)) or (self.dcount==self.outday+self.adjwaitdays-1)):
            self.updatefinefilter = 0
            return Universe.Unchanged
        self.updatefinefilter = 1   
        # drop stocks which have no fundamental data or have too low prices
        selected = [x for x in coarse if (x.HasFundamentalData) and (float(x.Price) > 5)]
        # rank the stocks by dollar volume 
        filtered = sorted(selected, key=lambda x: x.DollarVolume, reverse=True)
        return [x.Symbol for x in filtered[:500]]

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
        #self.sorted_stock = sorted(stock_dict.items(), key=lambda d:d[1],reverse=False)
        #sorted_symbol = [x[0] for x in self.sorted_stock]
        self.sorted_stock = sorted(stock_dict.items(), key=lambda d:d[1],reverse=True)
        self.sorted_symbol = [self.sorted_stock[i][0] for i in range(len(self.sorted_stock))]
        top= self.sorted_symbol[:self.num_screener]
        self.symbols = [x.Symbol for x in top]
        
        #self.Log("100 fine-filtered stocks\n" + str(sorted([str(i.Value) for i in self.symbols])))
        self.updatefinefilter = 0
        self.reb_count = self.dcount
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

    def rebalance_when_out_of_the_market(self):
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
        median = np.nanmedian(returns_sample, axis=0)
        abovemedian = returns_sample.iloc[-1] > median
        ### Interest rate expectations (cost of debt) may increase because the economic outlook improves (showing in rising input prices) = actually not a negative signal
        extreme_b.loc[[self.DEBT]] = np.where((extreme_b.loc[[self.DEBT]].any()) & (abovemedian[[self.METL, self.NRES]].any()), False, extreme_b.loc[[self.DEBT]])
        ### GOLD/SLVA differential may increase due to inflation expectations which actually suggest an economic improvement = actually not a negative signal
        try:
            extreme_b.loc['G_S'] = np.where((extreme_b.loc[['G_S']].any()) & (abovemedian.loc[[self.INFL]].any()), False, extreme_b.loc['G_S'])
        except:
            pass

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

        # Determine whether 'in' or 'out' of the market
        if (extreme_b[self.SIGNALS + self.pairlist]).any():
            self.be_in = False
            self.outday = self.dcount
            self.trade({**dict.fromkeys(self.Portfolio.Keys, 0), **self.HLD_OUT})
        if self.dcount >= self.outday + self.adjwaitdays:
            self.be_in = True
        
        # Update stock ranking/holdings, when swithing from 'out' to 'in' plus every X days when 'in' (set rebalance frequency)
        if (self.be_in and not self.be_in_prior) or (self.be_in and (self.dcount==self.reb_count)):
            self.rebalance()
            
        #self.Plot("In Out", "in_market", int(self.be_in))
        #self.Plot("In Out", "num_out_signals", extreme_b[self.SIGNALS + self.pairlist].sum())
        #self.Plot("Wait Days", "waitdays", self.adjwaitdays)
        
        self.be_in_prior = self.be_in
        self.dcount += 1


    def rebalance(self):
        #self.Debug(str(self.Time) + "rebalance: be_in:" + str(self.be_in) + " flip_flag:" + str(self.flip_flag))
            
        if self.symbols is None: return
        symbols = self.calc_return(self.symbols)
        
        #self.Log("The 10 selected stocks:\n" + str(sorted([str(i) for i in symbols])), end ="-")
        #self.Log("Sell the following current holdings:\n" + str(sorted([str(i) for i in list(dict.fromkeys(set([x.Symbol for x in self.Portfolio.Values if x.Invested]) - set(symbols)))])), end ="-")
        
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