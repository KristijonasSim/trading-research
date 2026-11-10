"""
Based on 'In & Out' strategy by Peter Guenther 10-04-2020
expanded/inspired by Tentor Testivis, Dan Whitnable (Quantopian), Vladimir, and Thomas Chang.

https://www.quantopian.com/posts/new-strategy-in-and-out
"""

# Import packages
import numpy as np
import pandas as pd
import scipy as sc


class InOut(QCAlgorithm):

    def Initialize(self):

        self.SetStartDate(2008, 1, 1)  # Set Start Date
        self.cap = 100000
        self.SetCash(self.cap)  # Set Strategy Cash
        self.UniverseSettings.Resolution = Resolution.Minute

        # Feed-in constants
        self.INI_WAIT_DAYS = 15  # out for 3 trading weeks

        res = Resolution.Minute

        self.MRKT = self.AddEquity('SPY', res).Symbol
        self.TLT = self.AddEquity('TLT', res).Symbol
        self.IEF = self.AddEquity('IEF', res).Symbol

        # Market and list of signals based on ETFs
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
        self.HLD_IN = {self.MRKT: 1.0}
        self.HLD_OUT = {self.TLT: .5, self.IEF: .5}

        # Initialize variables
        ## 'In'/'out' indicator
        self.be_in = 1
        ## Day count variables
        self.dcount = 0  # count of total days since start
        self.outday = 0  # dcount when self.be_in=0
        ## Flexi wait days
        self.WDadjvar = self.INI_WAIT_DAYS
        self.spy = []


        self.Schedule.On(
            self.DateRules.EveryDay(),
            self.TimeRules.AfterMarketOpen('SPY', 75),
            self.rebalance_when_out_of_the_market
        )


        self.Schedule.On(
            self.DateRules.WeekEnd(),
            self.TimeRules.AfterMarketOpen('SPY', 75),
            self.rebalance_when_in_the_market
        )

    def rebalance_when_out_of_the_market(self):
        # Returns sample to detect extreme observations
        hist = self.History(
            self.SIGNALS + [self.MRKT] + self.FORPAIRS, 252, Resolution.Daily)['close'].unstack(level=0).dropna()

        hist_shift = hist.rolling(66).apply(lambda x: x[:11].mean())

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
                                         returns_sample[self.GOLD].iloc[-1] / returns_sample[self.SLVA].iloc[-1],
                                         returns_sample[self.UTIL].iloc[-1] / returns_sample[self.INDU].iloc[-1],
                                         returns_sample[self.SHCU].iloc[-1] / returns_sample[self.RICU].iloc[-1]
                                         ))
        )
        adjwaitdays = min(60, self.WDadjvar)


        # Determine whether 'in' or 'out' of the market
        if (extreme_b[self.SIGNALS + self.pairlist]).any():
            self.be_in = False
            self.outday = self.dcount
        if self.dcount >= self.outday + adjwaitdays:
            self.be_in = True
        self.dcount += 1

        # Swap to 'out' assets if applicable
        if not self.be_in:
            # Close 'In' holdings
            for asset, weight in self.HLD_IN.items():
                self.SetHoldings(asset, 0)

            for asset, weight in self.HLD_OUT.items():
                self.SetHoldings(asset, weight)



        self.Plot("In Out", "in_market", int(self.be_in))
        self.Plot("In Out", "num_out_signals", extreme_b[self.SIGNALS + self.pairlist].sum())
        self.Plot("Wait Days", "waitdays", adjwaitdays)

        # to plot SPY on the same chart as the performance of our algo
        self.spy.append(hist[self.MRKT].iloc[-1])
        spy_perf = self.spy[-1] / self.spy[0] * self.cap
        self.Plot("Strategy Equity", "SPY", spy_perf)


    def rebalance_when_in_the_market(self):
        # Swap to 'in' assets if applicable
        if self.be_in:
            # Close 'Out' holdings
            for asset, weight in self.HLD_OUT.items():
                self.SetHoldings(asset, 0)

            for asset, weight in self.HLD_IN.items():
                self.SetHoldings(asset, weight)