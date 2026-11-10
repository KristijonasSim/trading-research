from QuantConnect.Data.UniverseSelection import *
import math
import numpy as np
import pandas as pd
import scipy as sp
# import statsmodels.api as sm

class InOutWithFundamentalFactorAlgorithm(QCAlgorithm):

    def Initialize(self):

        self.SetStartDate(2010, 1, 1)  #Set Start Date
        self.SetEndDate(2020, 11, 27)  #Set Start Date       
        self.SetCash(100000)            #Set Strategy Cash
    
        
        self.UniverseSettings.Resolution = Resolution.Daily
        self.AddUniverse(self.CoarseSelectionFunction, self.FineSelectionFunction)
        self.spy = self.AddEquity("SPY", Resolution.Minute).Symbol 
        self.holding_months = 1
        self.num_screener = 100
        self.num_stocks = 10
        self.formation_days = 200
        self.lowmom = False
        self.month_count = self.holding_months
        #self.Schedule.On(self.DateRules.MonthEnd("SPY"), self.TimeRules.AfterMarketOpen('SPY', 120), Action(self.big_rebalance))
        #self.Schedule.On(self.DateRules.MonthEnd("SPY"), self.TimeRules.AfterMarketOpen('SPY', 120), Action(self.rebalance))
        
        
        # rebalance the universe selection once a month
        self.rebalence_flag = 0
        # make sure to run the universe selection at the start of the algorithm even it's not the manth start
        self.flip_flag = 0
        self.first_month_trade_flag = 1
        self.trade_flag = 0 
        self.symbols = None
        
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
        
        # set a warm-up period to initialize the indicator
        self.SetWarmUp(timedelta(350))
        
        self.Schedule.On(
            self.DateRules.EveryDay(),
            self.TimeRules.AfterMarketOpen('SPY', 120),
            self.rebalance_when_out_of_the_market
        )

    def rebalance_when_out_of_the_market(self):
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
            for symbol in self.Portfolio.Keys:
                if symbol.Value != "TLT":
                    self.Liquidate(symbol.Value)
            self.AddEquity("TLT")
            self.SetHoldings("TLT", 1)
            #self.Debug("Be OUT TRIGGERED: " + str(self.Time))
        if self.dcount >= self.outday + adjwaitdays:
            #So this logic is best put as: we are about to flip the be_in to TRUE 
            #so right before that do the rebalance otherwise everyday it be_in is true it will try to rebalance
            if not self.be_in:
                self.flip_flag = 1
                self.big_rebalance()
                self.rebalance()
                self.flip_flag = 0
            self.be_in = True
            #self.Debug("Be IN TRIGGERED: " + str(self.Time))
        self.dcount += 1

        self.Plot("In Out", "in_market", int(self.be_in))
        self.Plot("In Out", "num_out_signals", extreme_b[self.SIGNALS + self.pairlist].sum())
        self.Plot("Wait Days", "waitdays", adjwaitdays)
        
        
 
    def CoarseSelectionFunction(self, coarse):
        #self.Debug(str(self.Time) + "CoarseSelectionFunction: be_in:" + str(self.be_in) + " flip_flag:" + str(self.flip_flag))
        if (self.rebalence_flag or self.first_month_trade_flag) and (self.be_in or self.flip_flag):
            # drop stocks which have no fundamental data or have too low prices
            selected = [x for x in coarse if (x.HasFundamentalData) and (float(x.Price) > 5)]
            # rank the stocks by dollar volume 
            filtered = sorted(selected, key=lambda x: x.DollarVolume, reverse=True) 
    
            return [ x.Symbol for x in filtered[:200]]
        else:
            return self.symbols


    def FineSelectionFunction(self, fine):
        #self.Debug(str(self.Time) + "FineSelectionFunction: be_in:" + str(self.be_in) + " flip_flag:" + str(self.flip_flag))
        if (self.rebalence_flag or self.first_month_trade_flag) and (self.be_in or self.flip_flag):
            hist = self.History([i.Symbol for i in fine], 1, Resolution.Daily)
            try:
                filtered_fine = [x for x in fine if (x.ValuationRatios.EVToEBITDA > 0) 
                                                    and (x.EarningReports.BasicAverageShares.ThreeMonths > 0) 
                                                    and float(x.EarningReports.BasicAverageShares.ThreeMonths) * hist.loc[str(x.Symbol)]['close'][0] > 2e9]
            except:
                filtered_fine = [x for x in fine if (x.ValuationRatios.EVToEBITDA > 0) 
                                                and (x.EarningReports.BasicAverageShares.ThreeMonths > 0)] 

            top = sorted(filtered_fine, key = lambda x: x.ValuationRatios.EVToEBITDA, reverse=True)[:self.num_screener]
            self.symbols = [x.Symbol for x in top]
            
            self.rebalence_flag = 0
            self.first_month_trade_flag = 0
            self.trade_flag = 1
            return self.symbols
        else:
            return self.symbols
    
    def OnData(self, data):
        pass
    
    def big_rebalance(self):
        self.rebalence_flag = 1

    def rebalance(self):
        #self.Debug(str(self.Time) + "rebalance: be_in:" + str(self.be_in) + " flip_flag:" + str(self.flip_flag))
        spy_hist = self.History([self.spy], 120, Resolution.Daily).loc[str(self.spy)]['close']
        if self.Securities[self.spy].Price < spy_hist.mean():
            for symbol in self.Portfolio.Keys:
                if symbol.Value != "TLT":
                    self.Liquidate(symbol.Value)
            self.AddEquity("TLT")
            self.SetHoldings("TLT", 1)

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
            self.AddEquity(symbol)
            self.SetHoldings(symbol, weight)    
                
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