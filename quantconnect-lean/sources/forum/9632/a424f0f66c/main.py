# self.wt[self.IEF] = 0

# self.wt[self.IEF] = 0

"""
Based on 'In & Out' strategy by Peter Guenther 4 Oct 2020
expanded/inspired by Tentor Testivis, Dan Whitnable (Quantopian), Vladimir, and Thomas Chang.

https://www.quantopian.com/posts/new-strategy-in-and-out
https://www.quantconnect.com/forum/discussion/9597/the-in-amp-out-strategy-continued-from-quantopian/p1
"""

# Import packages
import numpy as np
import pandas as pd
import scipy as sc


class InOut(QCAlgorithm):

    def Initialize(self):
        self.SetBrokerageModel(BrokerageName.InteractiveBrokersBrokerage, AccountType.Cash)
        self.DefaultOrderProperties = InteractiveBrokersOrderProperties()
        self.DefaultOrderProperties.FaGroup = "TestGroupEQ"
        self.DefaultOrderProperties.FaMethod = "EqualQuantity"
        self.SetWarmup(200)
        self.SetStartDate(2010, 1, 1)  # Set Start Date
        self.SetCash(5000)  # Set Strategy Cash
        self.UniverseSettings.Resolution = Resolution.Daily
        res = Resolution.Minute
        self.signals = []
        
        # Feed-in constants
        self.INI_WAIT_DAYS = 15  # out for 3 trading weeks
        
        # Holdings
        ### 'Out' holdings and weights
        self.TLT = self.AddEquity('TMF', res).Symbol
        # self.IEF = self.AddEquity('TYD', res).Symbol
        self.HLD_OUT = {self.TLT: 1}
        ### 'In' holdings and weights (static stock selection strategy)
        self.STKS = self.AddEquity('TQQQ', res).Symbol
        self.HLD_IN = {self.STKS: 1}
        ### combined holdings dictionary
        self.wt = {**self.HLD_IN, **self.HLD_OUT}
        # self.wt = {self.STKS: 1, self.SPDN:0}

        # Market and list of signals based on ETFs
        self.MRKT = self.AddEquity('SPY', res).Symbol  # market
        self.PRDC = self.AddEquity('XLI', res).Symbol  # production (industrials)
        self.METL = self.AddEquity('DBB', res).Symbol  # input prices (metals)
        self.NRES = self.AddEquity('IGE', res).Symbol  # input prices (natural res)
        self.DEBT = self.AddEquity('SHY', res).Symbol  # cost of debt (bond yield)
        self.USDX = self.AddEquity('UUP', res).Symbol  # safe haven (USD)
        self.GOLD = self.AddEquity('GLD', res).Symbol  # gold
        self.SLVA = self.AddEquity('SLV', res).Symbol  # VS silver
        self.UTIL = self.AddEquity('XLU', res).Symbol  # utilities
        self.INDU = self.PRDC  # vs industrials
        self.SHCU = self.AddEquity('FXF', res).Symbol  # safe haven currency (CHF)
        self.RICU = self.AddEquity('FXA', res).Symbol  # vs risk currency (AUD)

        self.FORPAIRS = [self.GOLD, self.SLVA, self.UTIL, self.SHCU, self.RICU]
        self.SIGNALS = [self.PRDC, self.METL, self.NRES, self.DEBT, self.USDX]

        # Initialize variables
        ## 'In'/'out' indicator
        self.be_in = True
        ## Day count variables
        self.dcount = 0  # count of total days since start
        self.outday = 0  # dcount when self.be_in=0
        ## Flexi wait days
        self.WDadjvar = self.INI_WAIT_DAYS

        self.Schedule.On(
            self.DateRules.EveryDay(),
            self.TimeRules.AfterMarketOpen('SPY', 1),
            self.calculateSignal
        )
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
        
    def calculateSignal(self):
         # Returns sample to detect extreme observations
        hist = self.History(
            self.SIGNALS + [self.MRKT] + self.FORPAIRS, 252, Resolution.Daily)['close'].unstack(level=0).dropna()
            
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
                                         np.where((returns_sample[self.GOLD].iloc[-1]>0) & (returns_sample[self.SLVA].iloc[-1]<0) & (returns_sample[self.SLVA].iloc[-2]>0), self.INI_WAIT_DAYS, 1),
                                         np.where((returns_sample[self.UTIL].iloc[-1]>0) & (returns_sample[self.INDU].iloc[-1]<0) & (returns_sample[self.INDU].iloc[-2]>0), self.INI_WAIT_DAYS, 1),
                                         np.where((returns_sample[self.SHCU].iloc[-1]>0) & (returns_sample[self.RICU].iloc[-1]<0) & (returns_sample[self.RICU].iloc[-2]>0), self.INI_WAIT_DAYS, 1)
                                         ))
        )
        adjwaitdays = min(60, self.WDadjvar)

        # self.Debug('{}'.format(self.WDadjvar))

        # Determine whether 'in' or 'out' of the market
        if (extreme_b[self.SIGNALS + self.pairlist]).any():
            self.be_in = False
            self.outday = self.dcount
        if self.dcount >= self.outday + adjwaitdays:
            self.be_in = True
        self.dcount += 1
        #self.be_in = True # for testing; sets the algo to being always in

        #we add first signal to list of signals
        if len(self.signals) == 0:
            self.signals.append(self.be_in)
        else:
            #when last signal is different from last signal we add it to the list
            if self.signals[-1] != self.be_in:
                self.signals.append(self.be_in)
                
    def rebalance_when_out_of_the_market(self):
        # Swap to 'out' assets if applicable
        if not self.be_in:
            self.wt[self.STKS] = 0
            self.wt[self.TLT] = 1
            # self.wt[self.IEF] = .5
            if len(self.signals) > 1 and self.Portfolio[self.TLT].Quantity == 0:
                self.SetHoldings([PortfolioTarget(self.STKS, 0), PortfolioTarget(self.TLT, 1)])
            # for sec, weight in self.wt.items():
            #     closePosition = (self.Portfolio[sec].Quantity > 0) and (weight == 0)
            #     if closePosition:
            #         self.SetHoldings(sec, weight)
            # #second open position
            # for sec, weight in self.wt.items():
            #     openPosisition = (self.Portfolio[sec].Quantity == 0) and (weight > 0)
            #     if openPosisition:
            #         self.SetHoldings(sec, weight)

    def rebalance_when_in_the_market(self):
        # Swap to 'in' assets if applicable
        if self.be_in:
            self.wt[self.STKS] = 1
            self.wt[self.TLT] = 0
            if len(self.signals) > 1 and self.Portfolio[self.STKS].Quantity == 0:
                self.SetHoldings([PortfolioTarget(self.TLT, 0), PortfolioTarget(self.STKS, 1)])
            # self.wt[self.IEF] = 0
            #first close position
            # for sec, weight in self.wt.items():
            #     closePosition = (self.Portfolio[sec].Quantity > 0) and (weight == 0)
            #     if closePosition:
            #         self.SetHoldings(sec, weight)
            # #second open position
            # for sec, weight in self.wt.items():
            #     openPosisition = (self.Portfolio[sec].Quantity == 0) and (weight > 0)
            #     if openPosisition:
            #         self.SetHoldings(sec, weight)