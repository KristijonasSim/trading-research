"""
Based on 'In & Out' strategy by Peter Guenther 4 Oct 2020
expanded/inspired by Tentor Testivis, Dan Whitnable (Quantopian), Vladimir, Thomas Chang, 
Derek Melchin (QuantConnect), Nathan Swenson, and Goldie Yalamanchi.

https://www.quantopian.com/posts/new-strategy-in-and-out
https://www.quantconnect.com/forum/discussion/9597/the-in-amp-out-strategy-continued-from-quantopian/p1
"""

# Import packages
import numpy as np
import pandas as pd
from collections import deque
import pickle
from dateutil.relativedelta import relativedelta


class InOut(QCAlgorithm):

    def Initialize(self):
        if not self.LiveMode:
            yr_delta = int(self.GetParameter("m"))

            # following will  it for 1 year, you can run it in paralllel in optimizer by selectong value of m from 0 to 13
            yr, m, d, n = 2008, 1, 1, 365*1
            # following willrun it for 14 years
            # yr, m, d, n = 2008, 1, 1, 365 * 14
            # yr, m, d, n = 2008, 1, 1, 10
            
            std = date(yr + yr_delta, m, d)
            edt = std + relativedelta(days=+n)
            self.SetStartDate(std.year, std.month, std.day)
            self.SetEndDate(edt.year, edt.month, edt.day)
        self.cap = 100000
        self.SetCash(self.cap)  # Set Strategy Cash
        res = Resolution.Minute

        self.frequent_rebalance = True
        # self.frequent_rebalance = False
        self.stat_alpha = 5
        signal_history_period = 20
        self.lookback = 5 * 252
        self.exp_f = 2
        self.smoothing_factor = self.exp_f / (signal_history_period + 1)
        # Initialize parameters and tracking variables
        self.price_smoothing_period, self.momentum_period = 11, 60
        

        
        # Holdings
        ### 'Out' holdings and weights
        self.HLD_OUT = {self.AddEquity('TLT', res).Symbol: 1.5}  # TLT; TMF for 3xlev
        ### 'In' holdings and weights (static stock selection strategy)
        self.HLD_IN = {self.AddEquity('QQQ', res).Symbol: 1.5}
        # self.HLD_IN = {self.AddEquity('TQQQ', res).Symbol: 1, self.AddEquity('QLD', res).Symbol: 0} #SPY or QQQ; TQQQ for 3xlev

        # Market and list of signals based on ETFs
        self.MRKT = self.AddEquity('QQQ', res).Symbol  # market; QQQ
        self.PRDC = self.AddEquity('XLI', res).Symbol  # production (industrials)
        self.METL = self.AddEquity('DBB', res).Symbol  # input prices (metals)
        self.NRES = self.AddEquity('IGE', res).Symbol  # input prices (natural res)
        self.DEBT = self.AddEquity('SHY', res).Symbol  # cost of debt (bond yield)
        self.USDX = self.AddEquity('UUP', res).Symbol  # safe haven (USD)
        self.GOLD = self.AddEquity('GLD', res).Symbol  # gold
        self.SLVA = self.AddEquity('SLV', res).Symbol  # vs silver
        self.UTIL = self.AddEquity('XLU', res).Symbol  # utilities
        self.INDU = self.PRDC  # vs industrials

        self.SIGNALS = [self.PRDC, self.METL, self.NRES, self.USDX, self.DEBT, self.MRKT]
        self.FORPAIRS = [self.GOLD, self.SLVA, self.UTIL, self.INDU]
        self.pairlist = ['G_S', 'U_I']

        
        self.signal_dens = deque([0] * signal_history_period,maxlen=signal_history_period)
        
        
        # Symbols for charts
        self.SPY = self.AddEquity('SPY', res).Symbol
        self.QQQ = self.MRKT

        # Setup daily consolidation
        self.symbols = list(set(
            self.SIGNALS + [self.MRKT] + self.FORPAIRS + list(self.HLD_OUT.keys()) + list(self.HLD_IN.keys()) + [
                self.SPY] + [self.QQQ]))
        # for symbol in symbols:
        #     self.consolidator = TradeBarConsolidator(timedelta(days=1))
        #     self.consolidator.DataConsolidated += self.consolidation_handler
        #     self.SubscriptionManager.AddConsolidator(symbol, self.consolidator)
        for symbol in self.symbols:
            self.Securities[symbol].MarginModel = PatternDayTradingMarginModel()
        self.getFreshHistory()

        # Benchmarks for charts
        self.benchmarks = [self.history[self.SPY].iloc[-2], self.history[self.QQQ].iloc[-2]]
        self.SetWarmUp(50, Resolution.Daily)
        self.bull_signal_up = 1 
        self.Schedule.On(self.DateRules.EveryDay(), self.TimeRules.AfterMarketOpen('QQQ', 120),
                         self.trade)

    # def consolidation_handler(self, sender, consolidated):
    #     return
    #     self.history.loc[consolidated.EndTime, consolidated.Symbol] = consolidated.Close
    #     self.history = self.history.iloc[-self.lookback:]
    #     # self.update_history_shift()
    
    def OnData(self, slice):
        self.slice = slice
        if self.IsWarmingUp:
            self.inout_check()
        

    def getFreshHistory(self):
        self.history = self.History(self.symbols, self.lookback, Resolution.Daily)
        if self.history is None or self.history.empty or 'close' not in self.history.columns:
            return
        # self.history = self.history['close'].unstack(level=0).dropna()
        self.history = self.history['open'].unstack(level=0).dropna()
        self.history = self.addLatest(self.history)
        self.history_shift = self.history.rolling(self.price_smoothing_period, center=True).mean().shift(self.momentum_period)

    def addLatest(self, hist):
        hist2 = hist
        col = 0
        for s in hist.columns:
            # latest = self.Securities[s].Price
            latest = self.Securities[s].Open
            hist2.loc[self.Time, s] = latest
            col += 1
        hist2 = hist2.iloc[-self.lookback:]

        return hist2
    
    def replace_tqqq(self):
        if self.Time.date() <= datetime.strptime('2010-02-09', '%Y-%m-%d').date():
            self.HLD_IN[list(self.HLD_IN.keys())[0]] = 0;
            self.HLD_IN[list(self.HLD_IN.keys())[1]] = 1
        else:
            self.HLD_IN[list(self.HLD_IN.keys())[0]] = 1; self.HLD_IN[list(self.HLD_IN.keys())[1]] = 0

    def inout_check(self):
        self.getFreshHistory()
        if self.history is None or self.history.empty:
            return
    
        if Symbol.Create('TQQQ', SecurityType.Equity, Market.USA) in self.HLD_IN.keys(): self.replace_tqqq()
    
        # Load saved signal density (for live interruptions):
        if self.LiveMode and sum(list(self.signal_dens)) == 0 and self.ObjectStore.ContainsKey('OS_signal_dens'):
            OS = self.ObjectStore.ReadBytes('OS_signal_dens')
            OS = pickle.loads(bytearray(OS))
            self.signal_dens = deque(OS, maxlen=100)
        
        
        returns_sample = (self.history / self.history_shift - 1)
        # Reverse code USDX: sort largest changes to bottom
        returns_sample[self.USDX] = returns_sample[self.USDX] * (-1)
        # For pairs, take returns differential, reverse coded
        returns_sample['G_S'] = -(returns_sample[self.GOLD] - returns_sample[self.SLVA])
        returns_sample['U_I'] = -(returns_sample[self.UTIL] - returns_sample[self.INDU])
        returns_sample = returns_sample[self.SIGNALS + self.pairlist]
        
        # Extreme observations; statistical significance = X% (stat_alpha)
        extreme_b = returns_sample.iloc[-1] < np.nanpercentile(returns_sample, self.stat_alpha, axis=0)
    
        # Re-assess/disambiguate double-edged signals
        abovemedian = returns_sample.iloc[-1] > np.nanmedian(returns_sample, axis=0)
        ### Interest rate expectations (cost of debt) may increase because the economic outlook improves (showing in rising input prices) = actually not a negative signal
        extreme_b.loc[self.DEBT] = np.where(
            (extreme_b.loc[self.DEBT].any()) & (abovemedian[[self.METL, self.NRES]].any()), False,
            extreme_b.loc[self.DEBT])
    
        n = len(self.SIGNALS + self.pairlist)
        self.cur_signal_dens = extreme_b.sum() / n * 100 
        add_dens = (1 - self.smoothing_factor) * self.signal_dens[-1] + self.smoothing_factor * self.cur_signal_dens
        self.signal_dens.append(add_dens)
    
        # Determine whether 'in' or 'out' of the market
        if self.cur_signal_dens >= self.stat_alpha / 2 and (\
                self.signal_dens[-1] > (self.signal_dens[-2])):
            self.bull_signal_up = 0
        elif (self.signal_dens[-1] <= min(self.signal_dens)):
            self.bull_signal_up = 1
    
        
       


    def trade(self):
        self.inout_check()
        if self.IsWarmingUp: 
            return
        
        if not self.bull_signal_up:
            weight_by_sec = {**dict.fromkeys(self.HLD_IN, 0), **self.HLD_OUT}
        if self.bull_signal_up:
            weight_by_sec = {**self.HLD_IN, **dict.fromkeys(self.HLD_OUT, 0)}
            
        # sort: execute largest sells first, largest buys last
        hold_wt = {k: (self.Portfolio[k].Quantity * self.Portfolio[k].Price) / self.Portfolio.TotalPortfolioValue for k
                   in self.Portfolio.Keys}
        order_wt = {k: weight_by_sec[k] - hold_wt.get(k, 0) for k in weight_by_sec}
        weight_by_sec = {k: weight_by_sec[k] for k in dict(sorted(order_wt.items(), key=lambda item: item[1]))}
        for sec, weight in weight_by_sec.items():
            # Check that we have data in the algorithm to process a trade
            if not self.CurrentSlice.ContainsKey(sec) or self.CurrentSlice[sec] is None:
                continue
            # Only trade if holdings fundamentally change
            cond1 = (weight == 0) and self.Portfolio[sec].Invested

            # Change introduced by Manoj Agarwala for frequent rebalancing
            cond2 = (abs(weight) > 0.01) and \
                    (self.frequent_rebalance \
                     or (not self.Portfolio[sec].Invested and not self.frequent_rebalance))
            if cond1 or cond2:
                self.SetHoldings(sec, weight)
        
        self.charts()
    
        # Save data: signal density from live trading for interruptions (note: backtest saves data at the end so that it's available for live trading).
        if self.LiveMode: self.SaveData()



    def charts(self):
        # Market comparisons
        spy_perf = self.history[self.SPY].iloc[-1] / self.benchmarks[0] * self.cap
        qqq_perf = self.history[self.QQQ].iloc[-1] / self.benchmarks[1] * self.cap
        self.Plot('Strategy Equity', 'SPY', spy_perf)
        self.Plot('Strategy Equity', 'QQQ', qqq_perf)

        # Signals
        # self.Plot("In Out", "in_market", self.be_in[-1])
        # self.Plot("In Out", "signal_dens", self.signal_dens[-1])
    

        # self.Plot("Signals", "PRDC", int(extreme_b[self.SIGNALS + self.pairlist][0]))
        # self.Plot("Signals", "METL", int(extreme_b[self.SIGNALS + self.pairlist][1]))
        # self.Plot("Signals", "NRES", int(extreme_b[self.SIGNALS + self.pairlist][2]))
        # self.Plot("Signals", "USDX", int(extreme_b[self.SIGNALS + self.pairlist][3]))
        # self.Plot("Signals", "DEBT", int(extreme_b[self.SIGNALS + self.pairlist][4]))
        # self.Plot("Signals", "MRKT", int(extreme_b[self.SIGNALS + self.pairlist][5]))
        # self.Plot("Signals", "G_S", int(extreme_b[self.SIGNALS + self.pairlist][6]))
        # self.Plot("Signals", "U_I", int(extreme_b[self.SIGNALS + self.pairlist][7]))

        # Comparison of out returns
        # self.portf_val.append(self.Portfolio.TotalPortfolioValue)
        # if not self.be_in[-1] and len(self.be_in) >= 2:
        #     period = np.where(np.array(self.be_in)[:-1] != np.array(self.be_in)[1:])[0][-1] - len(self.be_in)
        #     mrkt_ret = self.history[self.MRKT].iloc[-1] / self.history[self.MRKT].iloc[period] - 1
        #     strat_ret = self.portf_val[-1] / self.portf_val[period] - 1
        #     strat_vs_mrkt = round(float(strat_ret - mrkt_ret), 4)
        # else:
        #     strat_vs_mrkt = 0
        # self.Plot('Out return', 'PF vs MRKT', strat_vs_mrkt)

    def SaveData(self):
        self.ObjectStore.SaveBytes('OS_signal_dens', pickle.dumps(self.signal_dens))

