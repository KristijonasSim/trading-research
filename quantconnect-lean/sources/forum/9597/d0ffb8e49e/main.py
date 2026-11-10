#region imports
from AlgorithmImports import *
#endregion
"""
Based on 'In & Out' strategy by Peter Guenther 4 Oct 2020
expanded/inspired by Tentor Testivis, Dan Whitnable (Quantopian), Vladimir, Thomas Chang, 
Derek Melchin (QuantConnect), Nathan Swenson, and Goldie Yalamanchi.

https://www.quantopian.com/posts/new-strategy-in-and-out
https://www.quantconnect.com/forum/discussion/9597/the-in-amp-out-strategy-continued-from-quantopian/p1
Starting with v8:  https://www.quantconnect.com/forum/discussion/9597/the-in-amp-out-strategy-continued-from-quantopian/p4/comment-36820
Add relative momentum for in (offensive) and out (defensive) assets, similar to Bold Asset Allocation (https://www.quantconnect.com/forum/discussion/14190/bold-asset-allocation-baa-keller/p1)
Major changes are:
    - Add relative momentum logic in trade_wts() function
    - Include cash (BIL) as a safeguard for both offensive and defensive assets
    - Include consumer staples (XLP) as a risk-on alternative to QQQ (well diversifed against QQQ)
    - relative momentum is faster for offensive (6 months) than defensive (12 months) to capture higher volatility of equities
    - The relative momentum approach is likely sub-optimal in this initial version
    - Explicitely define the signal assets for In/Out to maintain that logic (self.signal_eq)
"""

# Import packages
import numpy as np
import pandas as pd
from collections import deque
import pickle


class InOut(QCAlgorithm):

    def Initialize(self):

        self.SetStartDate(2008, 1, 1)  # Set Start Date
        self.cap = 100000
        self.SetCash(self.cap)  # Set Strategy Cash
        res = Resolution.Minute
        
        # parameters for relative momentum
        self.LO, self.LD, self.LP, self.B, self.TO, self.TD = [6,12,0,1,1,1]

        # Holdings
        self.offensive = ['BIL','XLP','QQQ']
        self.defensive = ['BIL','TLT']
        self.safe = 'BIL'
        # repeat safe asset so it can be selected multiple times
        self.alldefensive = self.defensive + [self.safe] * max(0,self.TD - sum([1*(e==self.safe) for e in self.defensive]))
        self.trade_eq = list(set(self.offensive + self.alldefensive))
        for eq in self.trade_eq:
            self.AddEquity(eq, res)

        # Market and list of signals based on ETFs
        self.MRKT = self.AddEquity('QQQ', res).Symbol  # market
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

        # Initialize parameters and tracking variables
        self.lookback, self.shift_vars, self.stat_alpha, self.ema_f = [252*5, [11, 60, 45], 5, 2/(1+50)]
        self.be_in, self.portf_val, self.signal_dens, self.reg_slope = [[1], [self.cap], deque([0, 0, 0, 0, 0], maxlen = 100), deque([0, 0, 0, 0, 0], maxlen = 100)]
        
        self.Schedule.On(self.DateRules.EveryDay(), self.TimeRules.AfterMarketOpen('QQQ', 120),
            self.inout_check)
        
        # Symbols for charts
        self.SPY = self.AddEquity('SPY', res).Symbol
        self.QQQ = self.AddEquity('QQQ', res).Symbol
        self.signal_eq = list(set(self.SIGNALS + self.FORPAIRS + [self.QQQ]))

        # Setup daily consolidation
        symbols = list(set(self.signal_eq  + self.trade_eq + [self.SPY]))
        for symbol in symbols:
            self.consolidator = TradeBarConsolidator(timedelta(days=1))
            self.consolidator.DataConsolidated += self.consolidation_handler
            self.SubscriptionManager.AddConsolidator(symbol, self.consolidator)
        
        # Warm up history
        self.history = self.History(symbols, self.lookback, Resolution.Daily)
        if self.history.empty or 'close' not in self.history.columns:
            return
        self.history = self.history['close'].unstack(level=0)
        self.update_history_shift()
        
        # Benchmarks for charts
        self.benchmarks = [self.history[eq].iloc[-2] for eq in [self.SPY,self.QQQ]]
        
    def consolidation_handler(self, sender, consolidated):
        self.history.loc[consolidated.EndTime, consolidated.Symbol] = consolidated.Close
        self.history = self.history.iloc[-self.lookback:]
        self.update_history_shift()
        
    def update_history_shift(self):
        self.history_shift = self.history.rolling(self.shift_vars[0], center=True).mean().shift(self.shift_vars[1])

    def replace_tqqq(self):
        if self.Time.date() <= datetime.strptime('2010-02-09', '%Y-%m-%d').date():
            self.HLD_IN[list(self.HLD_IN.keys())[0]] = 0; self.HLD_IN[list(self.HLD_IN.keys())[1]] = 1
        else: self.HLD_IN[list(self.HLD_IN.keys())[0]] = 1; self.HLD_IN[list(self.HLD_IN.keys())[1]] = 0

    def inout_check(self):
        if self.history.empty: return
    
        if Symbol.Create('TQQQ', SecurityType.Equity, Market.USA) in self.trade_eq: self.replace_tqqq()
    
        # Load saved signal density (for live interruptions):
        if self.LiveMode and sum(list(self.signal_dens))==0 and self.ObjectStore.ContainsKey('OS_signal_dens'):
            OS = self.ObjectStore.ReadBytes('OS_signal_dens')
            OS = pickle.loads(bytearray(OS))
            self.signal_dens = deque(OS, maxlen = 100)
    
        # Returns sample to detect extreme observations
        sig_hist, sig_hist_shift = [self.history.loc[:,self.signal_eq],self.history_shift.loc[:,self.signal_eq]]
        returns_sample = (sig_hist / sig_hist_shift - 1).dropna()
        # Reverse code USDX: sort largest changes to bottom
        returns_sample[self.USDX] = returns_sample[self.USDX] * (-1)
        # For pairs, take returns differential, reverse coded
        returns_sample['G_S'] = -(returns_sample[self.GOLD] - returns_sample[self.SLVA])
        returns_sample['U_I'] = -(returns_sample[self.UTIL] - returns_sample[self.INDU])

        # Extreme observations; statistical significance = X% (stat_alpha)
        extreme_b = returns_sample.iloc[-1] < np.nanpercentile(returns_sample, self.stat_alpha, axis=0)
        
        # Re-assess/disambiguate double-edged signals
        abovemedian = returns_sample.iloc[-1] > np.nanmedian(returns_sample, axis=0)
        ### Interest rate expectations (cost of debt) may increase because the economic outlook improves (showing in rising input prices) = actually not a negative signal
        extreme_b.loc[self.DEBT] = np.where((extreme_b.loc[self.DEBT].any()) & (abovemedian[[self.METL, self.NRES]].any()), False, extreme_b.loc[self.DEBT])
        
        cur_signal_dens = extreme_b[self.SIGNALS + self.pairlist].sum() / len(self.SIGNALS + self.pairlist)
        add_dens = np.array((1-self.ema_f) * self.signal_dens[-1] + self.ema_f * cur_signal_dens)
        self.signal_dens.append(add_dens)
        
        # Determine whether 'in' or 'out' of the market
        if self.signal_dens[-1] > self.signal_dens[-2]:
            self.be_in.append(0)
        if self.signal_dens[-1] < min(list(self.signal_dens)[-(self.shift_vars[2]):-2]):
            self.be_in.append(1)

        # Get Trade weights and trade:
        wts = self.trade_wts(self.history,self.be_in[-1])
        # trade
        self.trade(wts.to_dict())
        # chart
        self.charts(extreme_b)
        
        # Save data: signal density from live trading for interruptions (note: backtest saves data at the end so that it's available for live trading).      
        if self.LiveMode: self.SaveData()
        
    def trade(self, weight_by_sec):
        # sort: execute largest sells first, largest buys last
        hold_wt = {k: (self.Portfolio[k].Quantity*self.Portfolio[k].Price)/self.Portfolio.TotalPortfolioValue for k in self.Portfolio.Keys}
        order_wt = {k: weight_by_sec[k] - hold_wt.get(k, 0) for k in weight_by_sec}
        weight_by_sec = {k: weight_by_sec[k] for k in dict(sorted(order_wt.items(), key=lambda item: item[1]))}
        for sec, weight in weight_by_sec.items(): 
            # Check that we have data in the algorithm to process a trade
            if not self.CurrentSlice.ContainsKey(sec) or self.CurrentSlice[sec] is None:
                continue
            # Only trade if holdings fundamentally change
            cond1 = (weight==0) and self.Portfolio[sec].IsLong
            cond2 = (weight>0) and not self.Portfolio[sec].Invested
            if cond1 or cond2:
                self.SetHoldings(sec, weight)
                
    def charts(self, extreme_b):
        # Market comparisons
        spy_perf = self.history[self.SPY].iloc[-1] / self.benchmarks[0] * self.cap
        qqq_perf = self.history[self.QQQ].iloc[-1] / self.benchmarks[1] * self.cap
        self.Plot('Strategy Equity', 'SPY', spy_perf)
        self.Plot('Strategy Equity', 'QQQ', qqq_perf)
        
        # Signals
        self.Plot("In Out", "in_market", self.be_in[-1])
        self.Plot("In Out", "signal_dens", self.signal_dens[-1])
        self.Plot("In Out", "reg_slope", self.reg_slope[-1])
        
        # self.Plot("Signals", "PRDC", int(extreme_b[self.SIGNALS + self.pairlist][0]))
        # self.Plot("Signals", "METL", int(extreme_b[self.SIGNALS + self.pairlist][1]))
        # self.Plot("Signals", "NRES", int(extreme_b[self.SIGNALS + self.pairlist][2]))
        # self.Plot("Signals", "USDX", int(extreme_b[self.SIGNALS + self.pairlist][3]))
        # self.Plot("Signals", "DEBT", int(extreme_b[self.SIGNALS + self.pairlist][4]))
        # self.Plot("Signals", "MRKT", int(extreme_b[self.SIGNALS + self.pairlist][5]))
        # self.Plot("Signals", "G_S", int(extreme_b[self.SIGNALS + self.pairlist][6]))
        # self.Plot("Signals", "U_I", int(extreme_b[self.SIGNALS + self.pairlist][7]))
        
        # Comparison of out returns
        self.portf_val.append(self.Portfolio.TotalPortfolioValue)
        if not self.be_in[-1] and len(self.be_in)>=2:
            period = np.where(np.array(self.be_in)[:-1] != np.array(self.be_in)[1:])[0][-1] - len(self.be_in)
            mrkt_ret = self.history[self.MRKT].iloc[-1] / self.history[self.MRKT].iloc[period] - 1
            strat_ret = self.portf_val[-1] / self.portf_val[period] - 1
            strat_vs_mrkt = round(float(strat_ret - mrkt_ret), 4)
        else: strat_vs_mrkt = 0
        self.Plot('Out return', 'PF vs MRKT', strat_vs_mrkt)
        
        
    def SaveData(self):
        self.ObjectStore.SaveBytes('OS_signal_dens', pickle.dumps(self.signal_dens))

    def trade_wts(self,hist,pct_in):
        # only keep history of trade equities:
        hist = hist.loc[:,self.trade_eq].dropna()
        # initialize wts Series
        wts = pd.Series(0,index=hist.columns)
        # end of month values
        h_eom = (hist.loc[hist.groupby(hist.index.to_period('M')).apply(lambda x: x.index.max())]
                .iloc[:-1,:])

        # =====================================
        # get weights for offensive and defensive universes
        # =====================================
        # determine weights of offensive universe
        if pct_in > 0:
            # price / SMA
            lookback = min(h_eom.shape[0],self.LO+1)
            mom_in = h_eom.iloc[-1,:].div(h_eom.iloc[[-t for t in range(1,lookback)]].mean(axis=0),axis=0)
            mom_in = mom_in.loc[self.offensive].sort_values(ascending=False)
            # equal weightings to top relative momentum securities
            in_wts = pd.Series(pct_in/self.TO,index=mom_in.index[:self.TO])
            wts = pd.concat([wts,in_wts])
        # determine weights of defensive universe
        if pct_in < 1:
            # price / SMA
            lookback = min(h_eom.shape[0],self.LD+1)
            mom_out = h_eom.iloc[-1,:].div(h_eom.iloc[[-t for t in range(1,lookback)]].mean(axis=0),axis=0)
            mom_out = mom_out.loc[self.alldefensive].sort_values(ascending=False)
            # equal weightings to top relative momentum securities
            out_wts = pd.Series((1-pct_in)/self.TD,index=mom_out.index[:self.TD])
            wts = pd.concat([wts,out_wts])     
        
        wts = wts.groupby(wts.index).sum()

        return wts