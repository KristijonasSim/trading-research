"""
Based on the 'In & Out' strategy introduced by Peter Guenther, 4 Oct 2020
expanded/inspired by Tentor Testivis, Dan Whitnable (Quantopian), Vladimir, Thomas Chang, 
Mateusz Pulka, Derek Melchin (QuantConnect), Nathan Swenson, Goldie Yalamanchi, and Sudip Sil

https://www.quantopian.com/posts/new-strategy-in-and-out
https://www.quantconnect.com/forum/discussion/9597/the-in-amp-out-strategy-continued-from-quantopian/p1
"""

# Import packages
import numpy as np
import pandas as pd
import scipy as sc


class InOut(QCAlgorithm):

    def Initialize(self):
        # Basics
        self.SetStartDate(2008, 1, 1)  # Set Start Date
        #self.SetEndDate(2020, 12, 31) # Set End Date
        self.cap = 100000 # Set Strategy Cash
        self.SetCash(self.cap)
        res = Resolution.Minute
        
        # Feed-in constants
        self.INI_WAIT_DAYS = 15  # out for 3 trading weeks
        
        # Holdings
        ### 'Out' holdings and weights
        self.BND1 = self.AddEquity('TLT', res).Symbol #TLT; TMF for 3xlev
        self.BND2 = self.AddEquity('IEF', res).Symbol #IEF; TYD for 3xlev
        self.HLD_OUT = {self.BND1: .5, self.BND2: .5}
        ### 'In' holdings and weights (static stock selection strategy)
        self.STKS1 = self.AddEquity('QQQ', res).Symbol #SPY or QQQ; TQQQ for 3xlev
        self.HLD_IN = {self.STKS1: 1}

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

        self.FORPAIRS = [self.GOLD, self.SLVA, self.UTIL, self.SHCU, self.RICU, self.TIPS, self.INFL] #self.INFL
        self.SIGNALS = [self.PRDC, self.METL, self.NRES, self.DEBT, self.USDX]
        self.pairlist = ['G_S', 'U_I', 'C_A']

        # Initialize variables
        ## 'In'/'out' indicator
        self.be_in = -1 #initially, set to an arbitrary value different from 1 (in) and 0 (out)
        ## Day count variables
        self.dcount = 0  # count of total days since start
        self.outday = 0  # dcount when self.be_in=0
        ## Flexi wait days
        self.WDadjvar = self.INI_WAIT_DAYS
        self.adjwaitdays = self.INI_WAIT_DAYS
        ## For inflation gauge
        self.debt1st = []
        self.tips1st = []
        
        # Variables for charts
        self.act_inout = -1
        self.benchmark1st = []
        self.benchmark = []
        self.portfolio_value = [self.cap] * 60
        self.year = self.Time.year
        self.saw_alwaysin_base = []
        self.saw_portfolio_base = []
        
        
        self.Schedule.On(
            self.DateRules.EveryDay(),
            self.TimeRules.AfterMarketOpen('SPY', 120),
            self.rebalance_when_out_of_the_market
        )

        self.Schedule.On(
            self.DateRules.WeekEnd(),
            #self.DateRules.EveryDay(),
            self.TimeRules.AfterMarketOpen('SPY', 120+5), #add 5 mins to ensure that calculation of in vs out (be_in) is completed before
            self.rebalance_when_in_the_market
        )
        
        self.Schedule.On(
            self.DateRules.EveryDay(),
            self.TimeRules.AfterMarketOpen('SPY', 120+7), #add 7 mins to ensure that all calculation are completed before charting
            self.create_charts
        )
        
        
        # Setup daily consolidation
        symbols = list(dict.fromkeys(self.SIGNALS + [self.MRKT] + self.FORPAIRS + list(self.HLD_IN.keys())))
        #self.Debug("List of symbols for consolidator: " + str(symbols))
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

        # self.Debug('{}'.format(self.WDadjvar))

        # Determine whether 'in' or 'out' of the market
        if (extreme_b[self.SIGNALS + self.pairlist]).any():
            self.be_in = False
            self.outday = self.dcount
        if self.dcount >= self.outday + self.adjwaitdays:
            self.be_in = True
        self.dcount += 1

        #self.be_in = True # for testing; sets the algo to being always in

        # Swap to 'out' assets if applicable
        if not self.be_in:
            # Only trade when changing from in to out
            self.trade({**dict.fromkeys(self.HLD_IN, 0), **self.HLD_OUT})
            self.act_inout = 0

    def rebalance_when_in_the_market(self):
        # Swap to 'in' assets if applicable
        if self.be_in:
            # Only trade when changing from out to in
            self.trade({**self.HLD_IN, **dict.fromkeys(self.HLD_OUT, 0)})
            self.act_inout = 1
            
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
            
    def create_charts(self):
        # Record variables
        ### IN/Out indicator and wait days
        self.Plot("In Out", "in_market", int(self.be_in))
        self.Plot("In Out", "act in & out", int(self.act_inout))
        self.Plot("Wait Days", "waitdays", self.adjwaitdays)
        
        ### Benchmark wealth (= portfolio value if always in)
        if self.dcount==1:
            self.benchmark1st = pd.DataFrame(self.history[list(self.HLD_IN.keys())].iloc[-1]).set_axis(['date'], axis=1, inplace=False).T
        self.benchmark = pd.DataFrame(self.history[list(self.HLD_IN.keys())].iloc[-1]).set_axis(['date'], axis=1, inplace=False).T
        benchmark_perf = (((self.benchmark / self.benchmark1st) * pd.DataFrame(data=list(self.HLD_IN.values()), index=self.benchmark.columns, columns=["date"]).T)).sum(axis=1) * self.cap
        self.Plot('Strategy Equity', 'Benchmark, Always in', float(benchmark_perf))
        
        ### X-month return comparison: In & out logic (Portfolio) VS always in
        #mrkt_return = self.history[self.MRKT].iloc[-1] / self.history[self.MRKT].iloc[-60] - 1
        alwaysin_return = ((self.benchmark / pd.DataFrame(self.history[list(self.HLD_IN.keys())].iloc[-60]).set_axis(['date'], axis=1, inplace=False).T -1) * pd.DataFrame(data=list(self.HLD_IN.values()), index=self.benchmark.columns, columns=["date"]).T).sum(axis=1)
        self.portfolio_value.append(self.Portfolio.TotalPortfolioValue)
        portfolio_return = self.portfolio_value[-1] / self.portfolio_value[-60] - 1
        self.Plot('Returns: In Out VS Always In', '3-m portfolio return', round(portfolio_return, 4))
        #self.Plot('Returns', '3-m market return', round(float(mrkt_return), 4))
        self.Plot('Returns: In Out VS Always In', '3-m always in return', round(float(alwaysin_return), 4))
        
        ### Annual saw tooth return comparison: In & out logic (Portfolio) VS always in
        if (self.dcount==1) or (self.Time.year!=self.year):
            self.saw_alwaysin_base = pd.DataFrame(self.history[list(self.HLD_IN.keys())].iloc[-1]).set_axis(['date'], axis=1, inplace=False).T
            self.saw_portfolio_base = self.Portfolio.TotalPortfolioValue
        saw_alwaysin_return = ((self.benchmark / self.saw_alwaysin_base -1) * pd.DataFrame(data=list(self.HLD_IN.values()), index=self.benchmark.columns, columns=["date"]).T).sum(axis=1)
        saw_portfolio_return = self.portfolio_value[-1] / self.saw_portfolio_base - 1
        self.Plot('Annual Saw Tooth Returns: In Out VS Always In', 'Annual portfolio return', round(saw_portfolio_return, 4))
        self.Plot('Annual Saw Tooth Returns: In Out VS Always In', 'Annual always in return', round(float(saw_alwaysin_return), 4))
        self.year = self.Time.year
        
        ### Leverage
        account_leverage = self.Portfolio.TotalHoldingsValue / self.Portfolio.TotalPortfolioValue
        self.Plot('Leverage', 'leverage', round(account_leverage, 4))