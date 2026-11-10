# Import packages
import numpy as np
import pandas as pd
import scipy as sc
from scipy import stats


class InOut(QCAlgorithm):

    def Initialize(self):

        self.SetStartDate(2008, 1, 1)  # Set Start Date
        self.cap = 35000
        self.SetCash(self.cap)  # Set Strategy Cash
        res = Resolution.Minute
        
        # Holdings
        ### 'Out' holdings and weights
        self.HLD_OUT = {self.AddEquity('TLT', res).Symbol: 1} #TLT; TMF for 3xlev
        ### 'In' holdings and weights (static stock selection strategy)
        self.HLD_IN = {self.AddEquity('QQQ', res).Symbol: 1} #SPY or QQQ; TQQQ for 3xlev

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
        
        self.basket_in = ['QQQ']  
        self.basket_out = ['TLT', 'IEF', 'SPDN']  
        
        self.position = -1
        
        for ticker in self.basket_in: 
            self.AddEquity(ticker, res)
            self.Securities[ticker].FeeModel = ConstantFeeModel(0)
        for ticker in self.basket_out: 
            self.AddEquity(ticker, res)
            self.Securities[ticker].FeeModel = ConstantFeeModel(0)
            
        # Initialize constants and variables
        self.INI_WAIT_DAYS, self.lookback, self.be_in, self.dcount, self.outday, self.portf_val = [15, 252*5, [1], 0, 0, [self.cap]] 
        # [out for 3 trading weeks, set period for returns sample, 'In'/'out' indicator, count of total days since start, dcount when self.be_in=0, portfolio value]
        
        self.Schedule.On(self.DateRules.EveryDay(), self.TimeRules.AfterMarketOpen('QQQ', 120),
            self.inout_check)
        
        # Symbols for charts
        self.SPY = self.AddEquity('SPY', res).Symbol
        self.QQQ = self.MRKT
        
        # Setup daily consolidation
        symbols = list(set(self.SIGNALS + [self.MRKT] + self.FORPAIRS + list(self.HLD_OUT.keys()) + list(self.HLD_IN.keys()) + [self.SPY] + [self.QQQ]))
        for symbol in symbols:
            self.consolidator = TradeBarConsolidator(timedelta(days=1))
            self.consolidator.DataConsolidated += self.consolidation_handler
            self.SubscriptionManager.AddConsolidator(symbol, self.consolidator)
        
        # Warm up history
        self.history = self.History(symbols, self.lookback, Resolution.Daily)
        if self.history.empty or 'close' not in self.history.columns:
            return
        self.history = self.history['close'].unstack(level=0).dropna()
        self.update_history_shift()
        
        # Benchmarks for charts
        self.benchmarks = [self.history[self.SPY].iloc[-2], self.history[self.QQQ].iloc[-2]]    
        
    def consolidation_handler(self, sender, consolidated):
        self.history.loc[consolidated.EndTime, consolidated.Symbol] = consolidated.Close
        self.history = self.history.iloc[-self.lookback:]
        self.update_history_shift()
        
    def update_history_shift(self):
        self.history_shift = self.history.rolling(11, center=True).mean().shift(60)

    def inout_check(self):
        if self.history.empty: return
    
        # Load saved dcount and outday (for live interruptions):
        if (self.dcount==0) and (self.outday==0) and (self.ObjectStore.ContainsKey('OS_counts')):
            OS_counts = self.ObjectStore.ReadBytes('OS_counts')
            OS_counts = pickle.loads(bytearray(OS_counts))
            self.dcount, self.outday = [OS_counts['dcount'], OS_counts['outday']]
    
        # Returns sample to detect extreme observations
        returns_sample = (self.history / self.history_shift - 1)
        # Reverse code USDX: sort largest changes to bottom
        returns_sample[self.USDX] = returns_sample[self.USDX] * (-1)
        # For pairs, take returns differential, reverse coded
        returns_sample['G_S'] = -(returns_sample[self.GOLD] - returns_sample[self.SLVA])
        returns_sample['U_I'] = -(returns_sample[self.UTIL] - returns_sample[self.INDU])

        # Extreme observations; statistical significance = 5%
        extreme_b = returns_sample.iloc[-1] < np.nanpercentile(returns_sample, 5, axis=0)
        
        # Re-assess/disambiguate double-edged signals
        abovemedian = returns_sample.iloc[-1] > np.nanmedian(returns_sample, axis=0)
        ### Interest rate expectations (cost of debt) may increase because the economic outlook improves (showing in rising input prices) = actually not a negative signal
        extreme_b.loc[self.DEBT] = np.where((extreme_b.loc[self.DEBT].any()) & (abovemedian[[self.METL, self.NRES]].any()), False, extreme_b.loc[self.DEBT])
        
        # Determine whether 'in' or 'out' of the market
        if (extreme_b[self.SIGNALS + self.pairlist]).any():
            self.be_in.append(0)
            self.outday = self.dcount
        if self.dcount >= self.outday + self.INI_WAIT_DAYS:
            self.be_in.append(1)

        current_portfolio = self.Portfolio.Keys
        # Swap to 'out' assets if applicable
        if not self.be_in[-1]:
            if self.position == -1 or self.position == 1:
                self.Liquidate()
                dataframe = self.History(self.basket_out, 180, Resolution.Daily)
                df = dataframe['close'].unstack(level=0)
                self.adaptive_asset_allocation(df, 3, 40, 90, self.Portfolio.Cash, 1)
                self.position = 0
        if self.be_in[-1] and self.Time.weekday()==4:
            if self.position == -1 or self.position == 0:
                self.Liquidate()    
                self.SetHoldings('QQQ', 1)
                self.position = 1

        self.charts(extreme_b)
        self.dcount += 1
        
        # Save data: day counts from live trading for interruptions (note: backtest saves data at the end so that it's available for live trading).      
        if self.LiveMode: self.SaveData_Counts()
        
    def charts(self, extreme_b):
        # Market comparisons
        spy_perf = self.history[self.SPY].iloc[-1] / self.benchmarks[0] * self.cap
        qqq_perf = self.history[self.QQQ].iloc[-1] / self.benchmarks[1] * self.cap
        self.Plot('Strategy Equity', 'SPY', spy_perf)
        self.Plot('Strategy Equity', 'QQQ', qqq_perf)
        
        # Signals
        self.Plot("In Out", "in_market", self.be_in[-1])
        
        self.Plot("Signals", "PRDC", int(extreme_b[self.SIGNALS + self.pairlist][0]))
        self.Plot("Signals", "METL", int(extreme_b[self.SIGNALS + self.pairlist][1]))
        self.Plot("Signals", "NRES", int(extreme_b[self.SIGNALS + self.pairlist][2]))
        self.Plot("Signals", "USDX", int(extreme_b[self.SIGNALS + self.pairlist][3]))
        self.Plot("Signals", "DEBT", int(extreme_b[self.SIGNALS + self.pairlist][4]))
        self.Plot("Signals", "G_S", int(extreme_b[self.SIGNALS + self.pairlist][5]))
        self.Plot("Signals", "U_I", int(extreme_b[self.SIGNALS + self.pairlist][6]))
        
        # Comparison of out returns
        self.portf_val.append(self.Portfolio.TotalPortfolioValue)
        if not self.be_in[-1] and len(self.be_in)>=2:
            period = np.where(np.array(self.be_in)[:-1] != np.array(self.be_in)[1:])[0][-1] - len(self.be_in)
            mrkt_ret = self.history[self.MRKT].iloc[-1] / self.history[self.MRKT].iloc[period] - 1
            strat_ret = self.portf_val[-1] / self.portf_val[period] - 1
            strat_vs_mrkt = round(float(strat_ret - mrkt_ret), 4)
        else: strat_vs_mrkt = 0
        self.Plot('Out return', 'PF vs MRKT', strat_vs_mrkt)
            
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
                
    def SaveData_Counts(self):
        counts = {"dcount": self.dcount, "outday": self.outday}
        self.ObjectStore.SaveBytes('OS_counts', pickle.dumps(counts))
        
    def adaptive_asset_allocation(self, df, nlargest, volatility_window, return_window, portfolio_value, leverage): 
        window_returns = np.log(df.iloc[-1]) - np.log(df.iloc[0])
        nlargest = list(window_returns.nlargest(nlargest).index)
        
        returns = df[nlargest].pct_change()
        returns_cov_normalized = returns[-volatility_window:].apply(lambda x: np.log(1+x)).cov()
        returns_corr_normalized = returns[-volatility_window:].apply(lambda x: np.log(1+x)).corr()
        returns_std = returns.apply(lambda x: np.log(1+x)).std()
        
        port_returns = []
        port_volatility = []
        port_weights = []
    
        num_assets = len(returns.columns)
        num_portfolios = 100
        individual_rets = window_returns[nlargest]
        
        for port in range(num_portfolios): 
            weights = np.random.random(num_assets)
            weights = weights/np.sum(weights)
            port_weights.append(weights)
    
            rets = np.dot(weights, individual_rets)
            port_returns.append(rets)
    
            var = returns_cov_normalized.mul(weights, axis=0).mul(weights, axis=1).sum().sum()
            sd = np.sqrt(var)
            ann_sd = sd * np.sqrt(256)
            port_volatility.append(ann_sd)
            
        data = {'Returns': port_returns, 'Volatility': port_volatility}
        hover_data = []
        for counter, symbol in enumerate(nlargest): 
            data[symbol] = [w[counter] for w in port_weights]
            hover_data.append(symbol)
    
        portfolios_V1 = pd.DataFrame(data)
        
        min_var_portfolio = portfolios_V1.iloc[portfolios_V1['Volatility'].idxmin()]
        max_sharpe_portfolio = portfolios_V1.iloc[(portfolios_V1['Returns'] / portfolios_V1['Volatility']).idxmax()]
        proportions = min_var_portfolio[nlargest] 
        
        index = 0
        for proportion in proportions: 
            self.SetHoldings(nlargest[index], proportion * leverage)
            self.Debug('{}% of portfolio in {}'.format(proportion * leverage, nlargest[index]))
            index += 1