# region imports
from AlgorithmImports import *
# endregion

# region imports
from AlgorithmImports import *
# endregion
# Import packages
import numpy as np
import pandas as pd
import scipy as sc 

class CalculatingRedTapir(QCAlgorithm):

    def Initialize(self):

        self.SetStartDate(2021, 1, 1)  # Set Start Date
        self.SetEndDate(2022, 1, 1)
        self.SetCash(100000)  # Set Strategy Cash
        self.UniverseSettings.Resolution = Resolution.Daily
        res = Resolution.Minute
        #self.SetBenchmark("SPY")
        # stock selection
        #self.STKSEL = self.AddEquity('SOXX', res).Symbol
        self.rebalanceTime = datetime.min
        self.activeStocks = set()
        self.AddUniverse(self.CoarseFilter, self.FineFilter)
        self.UniverseSettings.Resolution = Resolution.Hour
        self.portfolioTargets = []

        # Feed-in constants
        self.INI_WAIT_DAYS = 9  # out for 3 trading weeks
        #outmarket choices
        self.TLT = self.AddEquity('MJIN', res).Symbol
        self.IEF = self.AddEquity('TBF', res).Symbol


        # Market and list of signals based on ETFs
        res = Resolution.Minute
        self.MRKT = self.AddEquity('SPY', res).Symbol
        self.PRDC = self.AddEquity('XLI', res).Symbol  # production (industrials)
        self.METL = self.AddEquity('DBB', res).Symbol  # input prices (metals)
        self.NRES = self.AddEquity('IGE', res).Symbol  # input prices (natural res)
        self.DEBT = self.AddEquity('SHY', res).Symbol  # cost of debt (bond yield)
        self.USDX = self.AddEquity('UUP', res).Symbol  # safe haven (USD)
        self.GOLD = self.AddEquity('GLD', res).Symbol  # gold
        self.SLVA = self.AddEquity('SLV', res).Symbol  # VS silver
        self.UTIL = self.AddEquity('XLU', res).Symbol  # utilities
        self.SHCU = self.AddEquity('FXF', res).Symbol  # safe haven (CHF)
        self.RICU = self.AddEquity('FXA', res).Symbol  # risk currency (AUD)
        self.INDU = self.PRDC  # vs industrials

        self.FORPAIRS = [self.GOLD, self.SLVA, self.UTIL, self.SHCU, self.RICU]
        self.SIGNALS = [self.PRDC, self.METL, self.NRES, self.DEBT, self.USDX]

        # 'In' and 'out' holdings incl. weights
        #self.HLD_IN = self.portfolioTargets
        self.HLD_OUT = {self.TLT: .5, self.IEF: .5}

        # Initialize variables
        ## 'In'/'out' indicator
        self.be_in = 1
        ## Day count variables
        self.dcount = 0  # count of total days since start
        self.outday = 0  # dcount when self.be_in=0
        ## Flexi wait days
        self.WDadjvar = self.INI_WAIT_DAYS


        self.Schedule.On(
            self.DateRules.EveryDay(),
            self.TimeRules.AfterMarketOpen('SPY', 120),
            self.rebalance_when_out_of_the_market
        )


        self.Schedule.On(
            self.DateRules.WeekEnd(),
            self.TimeRules.AfterMarketOpen('SPY', 120),
            self.rebalance_when_in_the_market
        )

    # functions for universe
    def CoarseFilter(self, coarse):
        # Rebalancing monthly
        if self.Time <= self.rebalanceTime:
            return self.Universe.Unchanged
        self.rebalanceTime = self.Time + timedelta(30)
        
        sortedByDollarVolume = sorted(coarse, key=lambda x: x.DollarVolume, reverse=True)
        return [x.Symbol for x in sortedByDollarVolume if x.Price > 10 and x.HasFundamentalData][:200]
    
    def FineFilter(self, fine):
        sortedByPE = sorted(fine, key=lambda x: x.MarketCap)
        return [x.Symbol for x in sortedByPE if x.MarketCap > 0][:5]

    def OnSecuritiesChanged(self, changes):
         # close positions in removed securities
        for x in changes.RemovedSecurities:
            self.Debug(f"{self.Time}: Removed {x.Symbol}")
            self.Liquidate(x.Symbol)
            self.activeStocks.remove(x.Symbol)
            
        
        # can't open positions here since data might not be added correctly yet
        for x in changes.AddedSecurities:
            self.Debug(f"{self.Time}: Added {x.Symbol}")
            self.activeStocks.add(x.Symbol)   

        # adjust targets if universe has changed
        self.portfolioTargets = [PortfolioTarget(symbol, 1/len(self.activeStocks)) 
                            for symbol in self.activeStocks]
    
    def OnData(self, data):
        if self.portfolioTargets == []:
            return
        
        for symbol in self.activeStocks:
            if symbol not in data:
                return
          
    def rebalance_when_out_of_the_market(self):

        # Returns sample to detect extreme observations
        hist = self.History(
            self.SIGNALS + [self.MRKT] + self.FORPAIRS, 252, Resolution.Daily)['close'].unstack(level=0).dropna()

        #hist_shift = hist.rolling(66).apply(lambda x: x[:11].mean())

        hist_shift = hist.apply(lambda x: (x.shift(65) + x.shift(64) + x.shift(63) + x.shift(62) + x.shift(
            61) + x.shift(60) + x.shift(59) + x.shift(58) + x.shift(57) + x.shift(56) + x.shift(55)) / 11)

        returns_sample = (hist / hist_shift - 1)
        # Reverse code USDX: sort largest changes to bottom
        returns_sample[self.USDX] = returns_sample[self.USDX] * (-1)
        # For pairs, take returns differential, reverse coded
        returns_sample['G_S'] = -(returns_sample[self.GOLD] - returns_sample[self.SLVA])
        returns_sample['U_I'] = -(returns_sample[self.UTIL] - returns_sample[self.INDU])
        returns_sample['C_A'] = -(returns_sample[self.SHCU] - returns_sample[self.RICU])    
        self.pairlist = ['G_S', 'U_I', 'C_A']

        # Extreme observations; statist. significance = 1%
        pctl_b = np.nanpercentile(returns_sample, 1, axis=0)
        extreme_b = returns_sample.iloc[-1] < pctl_b

        # Determine waitdays empirically via safe haven excess returns, 50% decay
        self.WDadjvar = int(
            max(0.50 * self.WDadjvar,
                self.INI_WAIT_DAYS * max(1,
                                         #returns_sample[self.GOLD].iloc[-1] / returns_sample[self.SLVA].iloc[-1],
                                         #returns_sample[self.UTIL].iloc[-1] / returns_sample[self.INDU].iloc[-1],
                                         #returns_sample[self.SHCU].iloc[-1] / returns_sample[self.RICU].iloc[-1]
                                         np.where((returns_sample[self.GOLD].iloc[-1]>0) & (returns_sample[self.SLVA].iloc[-1]<0) & (returns_sample[self.SLVA].iloc[-2]>0), self.INI_WAIT_DAYS, 1),
                                         np.where((returns_sample[self.UTIL].iloc[-1]>0) & (returns_sample[self.INDU].iloc[-1]<0) & (returns_sample[self.INDU].iloc[-2]>0), self.INI_WAIT_DAYS, 1),
                                         np.where((returns_sample[self.SHCU].iloc[-1]>0) & (returns_sample[self.RICU].iloc[-1]<0) & (returns_sample[self.RICU].iloc[-2]>0), self.INI_WAIT_DAYS, 1)
                                         ))
        )
        adjwaitdays = min(60, self.WDadjvar)

        #self.Debug('{}'.format(self.WDadjvar))

        # Determine whether 'in' or 'out' of the market
        if (extreme_b[self.SIGNALS + self.pairlist]).any():
            self.be_in = False
            self.outday = self.dcount
        if self.dcount >= self.outday + adjwaitdays:
            self.be_in = True
        self.dcount += 1

        #self.be_in = True # for testing, sets to always in
        #self.TLT = self.AddEquity('MJIN', res).Symbol
        #self.IEF = self.AddEquity('TBF', res).Symbol
        #self.HLD_OUT = {self.TLT: .5, self.IEF: .5}

        # Swap to 'out' assets if applicable
        if not self.be_in:
            for x in self.portfolioTargets:
                self.SetHoldings(x.Symbol, 0)
            for asset, weight in self.HLD_OUT.items():
                self.SetHoldings(asset, weight)

        self.Plot("In Out", "in_market", int(self.be_in))
        self.Plot("In Out", "num_out_signals", extreme_b[self.SIGNALS + self.pairlist].sum())
        self.Plot("Wait Days", "waitdays", adjwaitdays)

    def rebalance_when_in_the_market(self):
        #res = Resolution.Minute
        #self.TLT = self.AddEquity('MJIN', res).Symbol
        #self.IEF = self.AddEquity('TBF', res).Symbol
        #self.HLD_OUT = {self.TLT: .5, self.IEF: .5}
        # Swap to 'in' assets if applicable
        if self.be_in:
            # Close 'Out' holdings
            for asset, weight in self.HLD_OUT.items():
                self.SetHoldings(asset, 0)
       
        self.SetHoldings(self.portfolioTargets)
        #self.Debug(self.portfolioTargets)
        self.portfolioTargets = []            
            
            