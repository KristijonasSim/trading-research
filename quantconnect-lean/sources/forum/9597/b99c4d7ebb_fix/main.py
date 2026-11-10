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

        self.SetStartDate(2008, 1, 1)  # Set Start Date
        self.SetCash(100000)  # Set Strategy Cash
        self.UniverseSettings.Resolution = Resolution.Daily
        res = Resolution.Daily
        
        
        # Feed-in constants
        self.INI_WAIT_DAYS = 15  # out for 3 trading weeks
        
        # Holdings
        ### 'Out' holdings and weights
        self.TLT = self.AddEquity('TLT', res).Symbol
        self.IEF = self.AddEquity('IEF', res).Symbol
        self.HLD_OUT = {self.TLT: .5, self.IEF: .5}
        ### 'In' holdings and weights (static stock selection strategy)
        self.STKS = self.AddEquity('SPY', res).Symbol  # tik laiko signalui
        self.HLD_IN = {self.STKS: 1}
        ### combined holdings dictionary
        self.wt = {self.AddEquity('QQQ', res).Symbol: 1, self.TLT: 0, self.IEF: 0}  # TAISYMAS: SPY nebelaikomas kartu su QQQ
        
        #New Vars
        self.ret_init = 80
        self.vola_span = 126

        # Market and list of signals based on ETFs
        self.MRKT = self.AddEquity('QQQ', res).Symbol  # market
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

    def rebalance_when_out_of_the_market(self):
        
        #das ganze hier anders aufziehen, so wie im code.txt
        vola = self.History(self.MRKT, self.vola_span, Resolution.Daily)['close'].pct_change().std() * np.sqrt(252)  
        
        WAIT_DAYS = int(vola * self.ret_init)  
        RET = int((1.0 - vola) * self.ret_init)
        
        
        # Returns sample to detect extreme observations
        hist = self.History(
            [self.SLVA] + [self.GOLD] + [self.PRDC] + [self.UTIL], RET+2, Resolution.Daily)['close'].unstack(level=0).dropna()
        
        ratio_ab = (hist[self.SLVA].iloc[-1] / hist[self.SLVA].iloc[0]) / (hist[self.GOLD].iloc[-1] / hist[self.GOLD].iloc[0])  
        ratio_cd = (hist[self.PRDC].iloc[-1] / hist[self.PRDC].iloc[0]) / (hist[self.UTIL].iloc[-1] / hist[self.UTIL].iloc[0])  
        

        # self.Debug('{}'.format(self.WDadjvar))

        # Determine whether 'in' or 'out' of the market
        if  ratio_ab < 1 and ratio_cd < 1:
            self.be_in = False
            self.outday = self.dcount
        elif self.dcount >= self.outday + WAIT_DAYS:
            self.be_in = True
        self.dcount += 1

        #self.be_in = True # for testing; sets the algo to being always in

        wt = self.wt
        # Swap to 'out' assets if applicable
        if not self.be_in:
            # Close 'In' holdings
            #for asset, weight in self.HLD_IN.items():
            #    self.SetHoldings(asset, 0)
            #for asset, weight in self.HLD_OUT.items():
            #    self.SetHoldings(asset, weight)
            wt[self.MRKT] = 0
            wt[self.TLT] = .5
            wt[self.IEF] = .5
            
        # Thomas's reducing unnecessary trades
        for sec, weight in sorted(wt.items(), key=lambda kv: kv[1]):  # TAISYMAS: pirma parduoti
            cond1 = (self.Portfolio[sec].Quantity > 0) and (weight == 0)
            cond2 = (self.Portfolio[sec].Quantity == 0) and (weight > 0)
            if cond1 or cond2:
                self.SetHoldings(sec, weight)

        self.Plot("In Out", "in_market", int(self.be_in))
        #self.Plot("In Out", "num_out_signals", extreme_b[self.SIGNALS + self.pairlist].sum())
        #self.Plot("Wait Days", "waitdays", adjwaitdays)


    def rebalance_when_in_the_market(self):
        # Swap to 'in' assets if applicable
        wt = self.wt
        if self.be_in:
            # Close 'Out' holdings
            #for asset, weight in self.HLD_OUT.items():
            #    self.SetHoldings(asset, 0)
            #for asset, weight in self.HLD_IN.items():
            #    self.SetHoldings(asset, weight)
            wt[self.MRKT] = 1
            wt[self.TLT] = 0
            wt[self.IEF] = 0
        
        # Thomas's reducing unnecessary trades
        for sec, weight in sorted(wt.items(), key=lambda kv: kv[1]):  # TAISYMAS: pirma parduoti
            cond1 = (self.Portfolio[sec].Quantity > 0) and (weight == 0)
            cond2 = (self.Portfolio[sec].Quantity == 0) and (weight > 0)
            if cond1 or cond2:
                self.SetHoldings(sec, weight)