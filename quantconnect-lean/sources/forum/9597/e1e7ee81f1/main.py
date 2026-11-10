"""
SEL(stock selection part)
SPY or QQQ

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
import operator

class InOut_DBear(QCAlgorithm):

    def Initialize(self):

        self.SetStartDate(2008, 1, 1)  #Set Start Date
        #self.SetEndDate(2008, 2, 1)  #Set End Date
        self.cap = 100000
        self.SetCash(self.cap)
        
        res = Resolution.Hour
        
        ##### Stock/Bond selection parameters #####
        EQY_VEC = ['QQQ'] 
        self.EQY_VEC = []
        cntr = 1
        for i in EQY_VEC:
            exec(f'self.EQY{cntr} =  self.AddEquity("{i}", Resolution.Hour).Symbol')
            exec(f'self.EQY_VEC.append(self.EQY{cntr})')
            cntr += 1
        
        ALT_VEC = ['TLT']
        self.ALT_VEC = []
        cntr = 1
        for i in ALT_VEC:
            exec(f'self.ALT{cntr} =  self.AddEquity("{i}", Resolution.Hour).Symbol')
            exec(f'self.ALT_VEC.append(self.ALT{cntr})')
            cntr += 1
        
        self.holdings_quants = dict.fromkeys(self.EQY_VEC+self.ALT_VEC, 0)
        self.eqy_sel = []; self.alt_sel = []
        self.mom_lookback = 126
        
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
        self.TIPS = self.AddEquity('TIP', res).Symbol  # disambiguate GPLD/SLVA pair via inflaction expectations; Treasury Yield = TIPS Yield + Expected Inflation
        self.UTIL = self.AddEquity('XLU', res).Symbol  # utilities
        self.INDU = self.PRDC  # vs industrials
        self.SHCU = self.AddEquity('FXF', res).Symbol  # safe haven currency (CHF)
        self.RICU = self.AddEquity('FXA', res).Symbol  # vs risk currency (AUD)

        self.FORPAIRS = [self.GOLD, self.SLVA, self.UTIL, self.SHCU, self.RICU, self.TIPS, self.INFL]
        self.SIGNALS = [self.PRDC, self.METL, self.NRES, self.DEBT, self.USDX]
        self.pairlist = ['G_S', 'U_I', 'SC_RC']
        
        # Initialize variables
        ## 'In'/'out' indicator
        self.be_in_inout = 1; self.be_in_inout_prior = 0
        ## Day count variables
        self.dcount = 0  # count of total days since start
        self.outday_inout = (-self.INI_WAIT_DAYS+1)  # setting ensures universe updating at algo start
        ## Flexi wait days
        self.WDadjvar = self.INI_WAIT_DAYS
        self.waitdays_inout = self.INI_WAIT_DAYS
        ## For inflation gauge
        self.debt1st = []
        self.tips1st = []
        
        ##### Distilled Bear parameters (note: shares signals with In & Out) #####
        self.DISTILLED_BEAR = 1
        self.VOLA_LOOKBACK = 126
        self.WAITD_CONSTANT = 85
        self.waitdays_dbear = self.INI_WAIT_DAYS
        self.be_in_dbear = 1; self.be_in_dbear_prior = 0
        self.outday_dbear = (-self.INI_WAIT_DAYS+1)
        
        ##### For comparing the in & out algos returns #####
        self.weight_inout_vs_dbear = 1 #weight determined via returns comparison; 1(fully In&Out) <--> 0(fully DistilledBear)
        self.io_mom_lookback = 10 #compare returns of in & outs in past X days
        self.setrebalancefreq = 1 #rebalance every X days according to new in & outs weighting
        self.symbols = None
        self.reb_count = 0 #save day count of last rebalancing
        self.signals_inout = []; self.signals_dbear = [] #save past in & out signals
        
        # set a warm-up period to initialize the indicator
        self.SetWarmUp(timedelta(350))
        self.data = {}
        
        # Scheduling
        self.Schedule.On(
            self.DateRules.EveryDay(),
            self.TimeRules.AfterMarketOpen('SPY', 30),
            self.rebalance)
        
        # Benchmarks
        self.QQQ = self.AddEquity('QQQ', res).Symbol
        self.benchmarks = []
        self.year = self.Time.year #for resetting benchmarks annually if applicable
        
        # Setup daily consolidation
        symbols = [self.MRKT] + self.SIGNALS + self.FORPAIRS + [self.QQQ] + self.EQY_VEC + self.ALT_VEC
        for symbol in symbols:
            self.consolidator = TradeBarConsolidator(timedelta(days=1))
            self.consolidator.DataConsolidated += self.consolidation_handler
            self.SubscriptionManager.AddConsolidator(symbol, self.consolidator)
        
        # Warm up history
        self.lookback_inout = 252
        self.lookback_dbear = 126
        self.history = self.History(symbols, max(self.lookback_inout+1, self.lookback_dbear+1, self.io_mom_lookback+1), Resolution.Daily)
        if self.history.empty or 'close' not in self.history.columns:
            return
        self.history = self.history['close'].unstack(level=0).dropna()

    
    def OnSecuritiesChanged(self, changes):
        
        addedSymbols = []
        for security in changes.AddedSecurities:
            addedSymbols.append(security.Symbol)
            if security.Symbol not in self.data:
                self.data[security.Symbol] = SymbolData(security.Symbol, self.mom_lookback+1, self)
   
        if len(addedSymbols) > 0:
            history = self.History(addedSymbols, 1 + max(self.lookback_inout+1, self.lookback_dbear+1, self.io_mom_lookback+1), Resolution.Daily).loc[addedSymbols]
            for symbol in addedSymbols:
                try:
                    self.data[symbol].Warmup(history.loc[symbol])
                except:
                    self.Debug(str(symbol))
                    continue
    
    def consolidation_handler(self, sender, consolidated):
        self.history.loc[consolidated.EndTime, consolidated.Symbol] = consolidated.Close
        self.history = self.history.iloc[-max(self.lookback_inout+1, self.lookback_dbear+1, self.io_mom_lookback+1):]
        self.update_history_shift()
    
    def update_history_shift(self):
        self.history_shift = self.history.rolling(11, center=True).mean().shift(60)
        
    def derive_vola_waitdays(self):
        volatility = 0.6 * np.log1p(self.history[[self.MRKT]].iloc[-self.lookback_dbear:].pct_change()).std() * np.sqrt(252)
        wait_days = int(volatility * self.WAITD_CONSTANT)
        returns_lookback = int((1.0 - volatility) * self.WAITD_CONSTANT)
        return wait_days, returns_lookback
    
    def signalcheck_inout(self):
        ##### In & Out signal check logic #####
        
        # Returns sample to detect extreme observations
        returns_sample = (self.history.iloc[-self.lookback_inout:] / self.history_shift.iloc[-self.lookback_inout:] - 1)
        # Reverse code USDX: sort largest changes to bottom
        returns_sample[self.USDX] = returns_sample[self.USDX] * (-1)
        # For pairs, take returns differential, reverse coded
        returns_sample['G_S'] = -(returns_sample[self.GOLD] - returns_sample[self.SLVA])
        returns_sample['U_I'] = -(returns_sample[self.UTIL] - returns_sample[self.INDU])
        returns_sample['SC_RC'] = -(returns_sample[self.SHCU] - returns_sample[self.RICU])   

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
        self.waitdays_inout = min(60, self.WDadjvar)
        
        if (extreme_b[self.SIGNALS + self.pairlist]).any():
            self.be_in_inout = False
            self.outday_inout = self.dcount
        if (self.dcount >= self.outday_inout + self.waitdays_inout):
            self.be_in_inout = True
            
        self.signals_inout.append(int(self.be_in_inout))
        
    
    def signalcheck_dbear(self):
        ##### Distilled Bear signal check logic #####
        
        waitdays_dbear, returns_lookback = self.derive_vola_waitdays()
        
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
        
        if DISTILLED_BEAR:
            self.be_in_dbear = False
            self.outday_dbear = self.dcount
        if (self.dcount >= self.outday_dbear + self.waitdays_dbear):
            self.be_in_dbear = True
        
        self.signals_dbear.append(int(self.be_in_dbear))
    
        
    def rebalance(self):
        
        self.signalcheck_inout()
        self.signalcheck_dbear()
        
        ##### Return comparison of in & outs to determine relative weight #####
        past_inouts = np.array(self.signals_inout[-self.io_mom_lookback:])
        past_dbears = np.array(self.signals_dbear[-self.io_mom_lookback:])
        length = len(past_inouts)
        past_eqy_ret = np.concatenate(np.array(self.history[[self.eqy_sel]].iloc[-min(length+1, (self.io_mom_lookback+1)):].pct_change())[-min(length, self.io_mom_lookback):], axis=None)
        past_alt_ret = np.concatenate(np.array(self.history[[self.alt_sel]].iloc[-min(length+1, (self.io_mom_lookback+1)):].pct_change())[-min(length, self.io_mom_lookback):], axis=None) 
        returns_inout = np.product(past_inouts*past_eqy_ret+np.absolute(past_inouts-1)*past_alt_ret+1)
        returns_dbear = np.product(past_dbears*past_eqy_ret+np.absolute(past_dbears-1)*past_alt_ret+1)
        weight_inout_vs_dbear = max(0, min(1, 0.5+(returns_inout-returns_dbear)/(np.std(past_inouts*past_eqy_ret+np.absolute(past_inouts-1)*past_alt_ret)*length/15)))
        weighted_be_in = weight_inout_vs_dbear*self.be_in_inout + (1-weight_inout_vs_dbear)*self.be_in_dbear
        
        ##### Update stock ranking/holdings on out<>in switches and every X days when in (rebalance frequency) #####
        if (self.be_in_inout!=self.be_in_inout_prior) or (self.be_in_dbear!=self.be_in_dbear_prior) or ((self.dcount-self.reb_count)==self.setrebalancefreq):
            self.eqy_sel = self.calc_best_mom_asset(self.EQY_VEC)
            self.alt_sel = self.calc_best_mom_asset(self.ALT_VEC)
            self.order_exec(weighted_be_in)
            self.reb_count = self.dcount
                
        self.be_in_inout_prior = self.be_in_inout; self.be_in_dbear_prior = self.be_in_dbear
        self.dcount += 1
        
        self.charting(weight_inout_vs_dbear, weighted_be_in)

    def calc_best_mom_asset(self, asset_vec):
            
        asset_ret = {}
        for symbol in asset_vec:
            if not self.CurrentSlice.ContainsKey(symbol) or self.CurrentSlice[symbol] is None:
                asset_ret[symbol] = -100
                continue
            try:
                asset_ret[symbol] = self.data[symbol].Roc.Current.Value
            except:
                self.Debug(str(symbol))
                continue
        self.Debug("Selected asset: " +str(max(asset_ret, key=asset_ret.get)))
        
        return max(asset_ret, key=asset_ret.get)

    def order_exec(self, weighted_be_in):
        
        invest_pct = (1-(40/self.Portfolio.TotalPortfolioValue))
        
        dict_weights = dict.fromkeys((self.EQY_VEC+self.ALT_VEC) , 0)
        dict_weights[self.eqy_sel] = weighted_be_in
        dict_weights[self.alt_sel] = 1-weighted_be_in
        
        # sell and buy assets if applicable
        for symbol, weight in dict_weights.items():
            quantity = self.Portfolio.TotalPortfolioValue * invest_pct * weight / self.Securities[symbol].Close 
            if math.floor(quantity) != self.holdings_quants[symbol]:
                self.Order(symbol, math.floor(quantity) - self.holdings_quants[symbol])
                self.Debug([str(self.Time), str(symbol), str(math.floor(quantity) -self.holdings_quants[symbol])])
                self.holdings_quants[symbol] = math.floor(quantity)
    
        
    def charting(self, weight_inout_vs_dbear, weighted_be_in): 
        
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
        self.Plot("In Out", "inout", int(self.be_in_inout))
        self.Plot("In Out", "dbear", int(self.be_in_dbear))
        self.Plot("In Out", "rel_w_inout", float(weight_inout_vs_dbear))
        self.Plot("In Out", "pct_in_market", float(weighted_be_in))
        self.Plot("Wait Days", "waitdays", self.waitdays_inout)
   
        
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