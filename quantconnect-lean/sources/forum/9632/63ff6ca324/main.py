"""
SEL(stock selection part)
Based on the 'Momentum Strategy with Market Cap and EV/EBITDA' strategy introduced by Jing Wu, 6 Feb 2018
adapted and recoded by Jack Simonson, Goldie Yalamanchi, Vladimir, Peter Guenther, Leandro Maia, Simone Pantaleoni, Mirko Vari(Strongs)
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
        #self.SetEndDate(2021, 5, 1)  #Set Start Date
        self.cap = 10000
        self.SetCash(self.cap)
        
        self.averages = { }
        res = Resolution.Hour
        
        # Holdings
        ### 'Out' holdings and weights
        self.BND1 = self.AddEquity('TLT', res).Symbol #TLT; TMF for 3xlev
        self.quantity = {self.BND1: 0}
        
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
        self.DISTILLED_BEAR = 1#999
        self.BE_IN = 1#999
        self.BE_IN_PRIOR = 0
        self.VOLA_LOOKBACK = 126
        self.WAITD_CONSTANT = 85
        self.DCOUNT = 0 # count of total days since start
        self.OUTDAY = (-self.INI_WAIT_DAYS+1) # dcount when self.be_in=0, initial setting ensures trading right away
        
        # set a warm-up period to initialize the indicator
        self.SetWarmUp(timedelta(350))
        
        ##### Momentum & fundamentals strategy parameters #####
        self.UniverseSettings.Resolution = res
        self.AddUniverse(self.UniverseCoarseFilter, self.UniverseFundamentalsFilter)
        self.num_coarse = 100#200
        self.num_screener = 20#100  # changed from 15
        self.num_stocks = 10 # lowered from 10
        self.formation_days = 126
        self.lowmom = False
        self.data = {}
        self.setrebalancefreq = 60 # X days, update universe and momentum calculation
        self.updatefinefilter = 0
        self.symbols = None
        self.reb_count = 0
        
        self.Schedule.On(
            self.DateRules.EveryDay(),
            self.TimeRules.AfterMarketOpen('SPY', 30), # reduced time 
            self.rebalance_when_out_of_the_market)
        
        self.Schedule.On(
            self.DateRules.EveryDay(), 
            self.TimeRules.BeforeMarketClose('SPY', 0), 
            self.record_vars)  
        
        # Benchmark = record SPY
        self.spy = []
        
        # Setup daily consolidation
        symbols = [self.MRKT] + self.FORPAIRS
        for symbol in symbols:
            self.consolidator = TradeBarConsolidator(timedelta(days=1))
            self.consolidator.DataConsolidated += self.consolidation_handler
            self.SubscriptionManager.AddConsolidator(symbol, self.consolidator)
        
        # Warm up history
        self.lookback = 126
        self.history = self.History(symbols, self.lookback, Resolution.Daily)
        if self.history.empty or 'close' not in self.history.columns:
            return
        self.history = self.history['close'].unstack(level=0).dropna()
        
    '''def UniverseCoarseFilter(self, coarse):
        
        if not (((self.DCOUNT-self.reb_count)==self.setrebalancefreq) or (self.DCOUNT == self.OUTDAY + self.wait_days - 1)):
            self.updatefinefilter = 0
            return Universe.Unchanged
        
        self.updatefinefilter = 1
            
        # drop stocks which have no fundamental data or have too low prices
        selected = [x for x in coarse if (x.HasFundamentalData) and (float(x.Price) > 5)]
        # rank the stocks by dollar volume 
        filtered = sorted(selected, key=lambda x: x.DollarVolume, reverse=True)
        return [x.Symbol for x in filtered[:self.num_coarse]]'''
        
        
    def UniverseCoarseFilter(self, coarse):
        # Update at the beginning (by setting self.OUTDAY = -self.INI_WAIT_DAYS), every X days (rebalance frequency), and one day before waitdays are up
        if not (((self.DCOUNT-self.reb_count)==self.setrebalancefreq) or (self.DCOUNT == self.OUTDAY + self.wait_days - 1)):
            self.updatefinefilter = 0
            return Universe.Unchanged
        
        self.updatefinefilter = 1 
        
        # drop stocks which have no fundamental data or have too low prices
        selected = [x for x in coarse if (x.HasFundamentalData) and (float(x.Price) > 5)]

        # We are going to use a dictionary to refer the object that will keep the moving averages
        for cf in selected:
            symbol = cf.Symbol
            if cf.Symbol not in self.averages:
                self.averages[cf.Symbol] = SymbolDataVolume(cf.Symbol, 21, 5, 504)

            # Updates the SymbolData object with current EOD price
            avg = self.averages[cf.Symbol]
            avg.update(cf.EndTime, cf.AdjustedPrice, cf.DollarVolume)

        # Filter the values of the dict: we only want up-trending securities

        #values = list(filter(lambda sd: sd.smaw.Current.Value > 0, self.averages.values()))
        values = list(filter(lambda sd: sd.smaw.Current.Value > 0, self.averages.values()))

        values.sort(key=lambda x: (x.smaw.Current.Value), reverse=True)
        #values.sort(key=lambda x: (x.volume_ratiol), reverse=True)

        # we need to return only the symbol objects
        return [ x.symbol for x in values[:self.num_coarse] ]        
        
    def UniverseFundamentalsFilter(self, fundamental):
        if self.updatefinefilter == 0:
            return Universe.Unchanged
             
        filtered_fundamental = [x for x in fundamental if  
                                 x.FinancialStatements.IncomeStatement.NetIncome.TwelveMonths and
                                 x.FinancialStatements.CashFlowStatement.CashFlowFromContinuingOperatingActivities.TwelveMonths and
                                 x.OperationRatios.ROA.ThreeMonths and x.OperationRatios.ROA.OneYear and
                                 x.FinancialStatements.BalanceSheet.ShareIssued.ThreeMonths and x.FinancialStatements.BalanceSheet.ShareIssued.TwelveMonths and
                                 x.OperationRatios.GrossMargin.ThreeMonths and x.OperationRatios.GrossMargin.OneYear and
                                 x.OperationRatios.LongTermDebtEquityRatio.ThreeMonths and x.OperationRatios.LongTermDebtEquityRatio.OneYear and 
                                 x.OperationRatios.CurrentRatio.ThreeMonths and x.OperationRatios.CurrentRatio.OneYear and 
                                 x.OperationRatios.AssetsTurnover.ThreeMonths and x.OperationRatios.AssetsTurnover.OneYear and x.ValuationRatios.NormalizedPERatio]
                                 
        sortedByfactor1 = [x for x in fundamental if FScore(x.FinancialStatements.IncomeStatement.NetIncome.TwelveMonths,
                            x.FinancialStatements.CashFlowStatement.CashFlowFromContinuingOperatingActivities.TwelveMonths,
                            x.OperationRatios.ROA.ThreeMonths, x.OperationRatios.ROA.OneYear,
                            x.FinancialStatements.BalanceSheet.ShareIssued.ThreeMonths, x.FinancialStatements.BalanceSheet.ShareIssued.TwelveMonths,  
                            x.OperationRatios.GrossMargin.ThreeMonths, x.OperationRatios.GrossMargin.OneYear,
                            x.OperationRatios.LongTermDebtEquityRatio.ThreeMonths, x.OperationRatios.LongTermDebtEquityRatio.OneYear,
                            x.OperationRatios.CurrentRatio.ThreeMonths, x.OperationRatios.CurrentRatio.OneYear,
                            x.OperationRatios.AssetsTurnover.ThreeMonths, x.OperationRatios.AssetsTurnover.OneYear).ObjectiveScore() > 6]                        
         
        top = sorted(sortedByfactor1, key = lambda x: x.ValuationRatios.NormalizedPERatio, reverse=False)[:self.num_screener]
        self.symbols = [x.Symbol for x in top]
        self.updatefinefilter = 0
        self.reb_count = self.DCOUNT
        return self.symbols

    
    def OnSecuritiesChanged(self, changes):
        
        #for security in changes.RemovedSecurities:
        #    symbol_data = self.data.pop(security.Symbol, None)
        #    if symbol_data:
        #        symbol_data.dispose()
        
        #for security in changes.AddedSecurities:
        #    if security.Symbol not in self.data:
        #        self.data[security.Symbol] = SymbolData(security.Symbol, self.formation_days, self)
    
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

        
    def derive_vola_waitdays(self):
        volatility = 0.6 * np.log1p(self.history[[self.MRKT]].pct_change()).std() * np.sqrt(252)
        wait_days = int(volatility * self.WAITD_CONSTANT)
        returns_lookback = int((1.0 - volatility) * self.WAITD_CONSTANT)
        return wait_days, returns_lookback
 
        
    def rebalance_when_out_of_the_market(self):
        self.wait_days, returns_lookback = self.derive_vola_waitdays()
        
        ## Check for Bears
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
        
            
        if (self.DCOUNT >= self.OUTDAY + self.wait_days):
            self.BE_IN = True
        
        # Update stock ranking/holdings, when swithing from 'out' to 'in' plus every X days when 'in' (set rebalance frequency)
        if (self.BE_IN and not self.BE_IN_PRIOR) or (self.BE_IN and (self.DCOUNT==self.reb_count)):
            self.rebalance()
                
        self.BE_IN_PRIOR = self.BE_IN
        self.DCOUNT += 1


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
        #ready = [self.data[symbol] for symbol in stocks if self.data[symbol].Roc.IsReady]
        #sorted_by_roc = sorted(ready, key=lambda x: x.Roc.Current.Value, reverse = not self.lowmom)
        #return [symbol_data.Symbol for symbol_data in sorted_by_roc[:self.num_stocks] ]

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
        self.spy.append(self.history[self.MRKT].iloc[-1])
        spy_perf = self.spy[-1] / self.spy[0] * self.cap
        self.Plot('Strategy Equity', 'SPY', spy_perf)
        
        account_leverage = self.Portfolio.TotalHoldingsValue / self.Portfolio.TotalPortfolioValue
        self.Plot('Holdings', 'leverage', round(account_leverage, 0))
    
        
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
            
class FScore(object):
    def __init__(self, netincome, operating_cashflow, roa_current,
                 roa_past, issued_current, issued_past, grossm_current, grossm_past,
                 longterm_current, longterm_past, curratio_current, curratio_past,
                 assetturn_current, assetturn_past):
        self.netincome = netincome
        self.operating_cashflow = operating_cashflow
        self.roa_current = roa_current
        self.roa_past = roa_past
        self.issued_current = issued_current
        self.issued_past = issued_past
        self.grossm_current = grossm_current
        self.grossm_past = grossm_past
        self.longterm_current = longterm_current
        self.longterm_past = longterm_past
        self.curratio_current = curratio_current
        self.curratio_past = curratio_past
        self.assetturn_current = assetturn_current
        self.assetturn_past = assetturn_past

    def ObjectiveScore(self):
        fscore = 0
        fscore += np.where(self.netincome > 0, 1, 0)
        fscore += np.where(self.operating_cashflow > 0, 1, 0)
        fscore += np.where(self.roa_current > self.roa_past, 1, 0)
        fscore += np.where(self.operating_cashflow > self.roa_current, 1, 0)
        fscore += np.where(self.longterm_current <= self.longterm_past, 1, 0)
        fscore += np.where(self.curratio_current >= self.curratio_past, 1, 0)
        fscore += np.where(self.issued_current <= self.issued_past, 1, 0)
        fscore += np.where(self.grossm_current >= self.grossm_past, 1, 0)
        fscore += np.where(self.assetturn_current >= self.assetturn_past, 1, 0)
        return fscore