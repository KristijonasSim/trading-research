from QuantConnect.Data.UniverseSelection import *
import math
import numpy as np
import pandas as pd
import scipy as sp
# import statsmodels.api as sm

class InOutWithFundamentalFactorAlgorithm(QCAlgorithm):

    def Initialize(self):

        self.SetStartDate(2020, 8, 1)  #Set Start Date
        self.SetEndDate(2020, 12, 1)
        self.cap = 100000
        self.SetCash(self.cap)
        
        res = Resolution.Minute
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
        self.UTIL = self.AddEquity('XLU', res).Symbol  # utilities
        self.INDU = self.PRDC  # vs industrials
        self.SHCU = self.AddEquity('FXF', res).Symbol  # safe haven currency (CHF)
        self.RICU = self.AddEquity('FXA', res).Symbol  # vs risk currency (AUD)
        self.AddEquity("TLT", Resolution.Minute)
        
        
        self.MKT = self.AddEquity('SPY', Resolution.Minute).Symbol
        self.spy = []

        self.FORPAIRS = [self.GOLD, self.SLVA, self.UTIL, self.SHCU, self.RICU]
        self.SIGNALS = [self.PRDC, self.METL, self.NRES, self.DEBT, self.USDX]

        # Initialize variables
        ## 'In'/'out' indicator
        self.be_in = 999 #initially, set to an arbitrary value different from 1 (in) and 0 (out)
        ## Day count variables
        self.dcount = 0  # count of total days since start
        self.outday = 0  # dcount when self.be_in=0
        ## Flexi wait days
        self.WDadjvar = self.INI_WAIT_DAYS
        
        # Setup daily consolidation
        symbols = self.SIGNALS + [self.MRKT] + self.FORPAIRS
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
        
        self.UniverseSettings.Resolution = Resolution.Minute
        self.AddUniverse(self.MomentumSelectionFunction, self.FundamentalSelectionFunction)
        self.num_screener = 100
        self.num_stocks = 10
        self.formation_days = 70
        self.lowmom = False
        
        # rebalance the universe selection once a month
        self.rebalence_flag = 0
        # make sure to run the universe selection at the start of the algorithm even it's not the manth start
        self.flip_flag = 0
        self.first_month_trade_flag = 1
        self.trade_flag = 0 
        self.symbols = None
        
        self.Schedule.On(
            self.DateRules.EveryDay(),
            self.TimeRules.AfterMarketOpen('SPY', 120),
            self.rebalance_when_out_of_the_market
        )
        
        self.Schedule.On(
            self.DateRules.EveryDay(), 
            self.TimeRules.BeforeMarketClose('SPY', 0), 
            self.record_vars
        )        

    def consolidation_handler(self, sender, consolidated):
        self.history.loc[consolidated.EndTime, consolidated.Symbol] = consolidated.Close
        self.history = self.history.iloc[-self.lookback:]
        self.update_history_shift()
        
    def update_history_shift(self):
        self.history_shift = self.history.rolling(11, center=True).mean().shift(60)

    def rebalance_when_out_of_the_market(self):
        returns_sample = (self.history / self.history_shift - 1)

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
            self.SetHoldings("TLT", 1, True)
            self.Log("BE OUT to TLT")
            
            #self.Debug("Be OUT TRIGGERED: " + str(self.Time))
            
        self.Plot("Be Out", "dcount", self.dcount)
        self.Plot("Be Out", "outday", self.outday)
        self.Plot("Be Out", "adjwaitdays", adjwaitdays)
        self.Plot("Be Out", "outday + adjwaitdays", self.outday + adjwaitdays)
        
        if self.dcount >= self.outday + adjwaitdays:
            #So this logic is best put as: we are about to flip the be_in to TRUE 
            #so right before that do the rebalance otherwise everyday it be_in is true it will try to rebalance
            if not self.be_in:
                self.flip_flag = 1
                self.rebalance()
                self.flip_flag = 0
            self.be_in = True
            #self.Debug("Be IN TRIGGERED: " + str(self.Time))
        self.dcount += 1

        self.Plot("In Out", "in_market", int(self.be_in))
        self.Plot("In Out", "num_out_signals", extreme_b[self.SIGNALS + self.pairlist].sum())
        self.Plot("Wait Days", "waitdays", adjwaitdays)
        
        
 
    def MomentumSelectionFunction(self, momentum):
        #self.Debug(str(self.Time) + "MomentumSelectionFunction: be_in:" + str(self.be_in) + " flip_flag:" + str(self.flip_flag))
        if (self.rebalence_flag or self.first_month_trade_flag) and (self.be_in or self.flip_flag):
            # drop stocks which have no fundamental data or have too low prices
            selected = [x for x in momentum if (x.HasFundamentalData) and (float(x.Price) > 5)]
            # rank the stocks by dollar volume 
            filtered = sorted(selected, key=lambda x: x.DollarVolume, reverse=True)
            return [ x.Symbol for x in filtered[:200]]
        else:
            return self.symbols


    def FundamentalSelectionFunction(self, fundamental):
        #self.Debug(str(self.Time) + "FundamentalSelectionFunction: be_in:" + str(self.be_in) + " flip_flag:" + str(self.flip_flag))
        if (self.rebalence_flag or self.first_month_trade_flag) and (self.be_in or self.flip_flag):
            hist = self.History([i.Symbol for i in fundamental], 1, Resolution.Daily)
            try:
                filtered_fundamental = [x for x in fundamental if (x.ValuationRatios.EVToEBITDA > 0) 
                                                    and (x.EarningReports.BasicAverageShares.ThreeMonths > 0) 
                                                    and float(x.EarningReports.BasicAverageShares.ThreeMonths) * hist.loc[str(x.Symbol)]['close'][0] > 2e9]
            except:
                filtered_fundamental = [x for x in fundamental if (x.ValuationRatios.EVToEBITDA > 0) 
                                                and (x.EarningReports.BasicAverageShares.ThreeMonths > 0)] 

            top = sorted(filtered_fundamental, key = lambda x: x.ValuationRatios.EVToEBITDA, reverse=True)[:self.num_screener]
            self.symbols = [x.Symbol for x in top]
            self.rebalence_flag = 0
            self.first_month_trade_flag = 0
            self.trade_flag = 1
            return self.symbols
        else:
            return self.symbols


    def rebalance(self):
        self.rebalence_flag = 1
        #self.Debug(str(self.Time) + "rebalance: be_in:" + str(self.be_in) + " flip_flag:" + str(self.flip_flag))
        spy_hist = self.History([self.MRKT], 120, Resolution.Daily).loc[str(self.MRKT)]['close']
        if self.Securities[self.MRKT].Price < spy_hist.mean():
            self.SetHoldings("TLT", 1, True)
            self.Log("Rebalance to TLT")

        if self.symbols is None: return
        chosen_df = self.calc_return(self.symbols)
        chosen_df = chosen_df.iloc[:self.num_stocks]
        
        self.existing_pos = 0
        add_symbols = []
        for symbol in self.Portfolio.Keys:
            if symbol.Value == 'SPY': continue
            if (symbol.Value not in chosen_df.index):
                self.SetHoldings(symbol, 0)
            elif (symbol.Value in chosen_df.index): 
                self.existing_pos += 1
        
        weight = 0.99/len(chosen_df)
        for symbol in chosen_df.index:
            #self.AddEquity(symbol)
            
            self.SetHoldings(Symbol.Create(symbol, SecurityType.Equity, Market.USA), weight)    
    
                
    def calc_return(self, stocks):
        hist = self.History(stocks, self.formation_days, Resolution.Daily)
        current = self.History(stocks, 1, Resolution.Minute)
        
        self.price = {}
        ret = {}
     
        for symbol in stocks:
            if str(symbol) in hist.index.levels[0] and str(symbol) in current.index.levels[0]:
                self.price[symbol.Value] = list(hist.loc[str(symbol)]['close'])
                self.price[symbol.Value].append(current.loc[str(symbol)]['close'][0])
        for symbol in self.price.keys():
            ret[symbol] = (self.price[symbol][-1] - self.price[symbol][0]) / self.price[symbol][0]
        df_ret = pd.DataFrame.from_dict(ret, orient='index')
        df_ret.columns = ['return']
        sort_return = df_ret.sort_values(by = ['return'], ascending = self.lowmom)
        
        return sort_return
        
               
        
    def record_vars(self): 
    
        hist = self.History(self.MKT, 2, Resolution.Daily)['close'].unstack(level= 0).dropna() 
        self.spy.append(hist[self.MKT].iloc[-1])
        spy_perf = self.spy[-1] / self.spy[0] * self.cap
        self.Plot('Strategy Equity', 'SPY', spy_perf)
        
        account_leverage = self.Portfolio.TotalHoldingsValue / self.Portfolio.TotalPortfolioValue