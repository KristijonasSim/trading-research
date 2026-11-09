"""
DUAL MOMENTUM-IN OUT v2 by Vladimir
https://www.quantconnect.com/forum/discussion/9597/the-in-amp-out-strategy-continued-from-quantopian/p3/comment-28146

inspired by Peter Guenther, Tentor Testivis, Dan Whitnable, Thomas Chang and T Smith.

"""
import numpy as np
import pandas as pd

class DualMomentumInOut(QCAlgorithm):

    def Initialize(self):

        self.SetBrokerageModel(BrokerageName.InteractiveBrokersBrokerage, AccountType.Margin)
        self.SetStartDate(2008, 1, 1)
        self.cap = self.Portfolio.Cash
        self.SetCash(self.cap)

        self.MKT = self.AddEquity('SPY', Resolution.Hour).Symbol  
        self.XLI = self.AddEquity('XLI', Resolution.Hour).Symbol 
        self.XLU = self.AddEquity('XLU', Resolution.Hour).Symbol 
        self.SLV = self.AddEquity('SLV', Resolution.Hour).Symbol 
        self.GLD = self.AddEquity('GLD', Resolution.Hour).Symbol 
        self.FXA = self.AddEquity('FXA', Resolution.Hour).Symbol
        self.FXF = self.AddEquity('FXF', Resolution.Hour).Symbol
        self.DBB = self.AddEquity('DBB', Resolution.Hour).Symbol
        self.UUP = self.AddEquity('UUP', Resolution.Hour).Symbol          
        self.IGE = self.AddEquity('IGE', Resolution.Hour).Symbol
        self.SHY = self.AddEquity('SHY', Resolution.Hour).Symbol
        self.AddEquity("TLT", Resolution.Minute)

        self.FORPAIRS = [self.XLI, self.XLU, self.SLV, self.GLD, self.FXA, self.FXF]
        self.SIGNALS  = [self.XLI, self.DBB, self.IGE, self.SHY, self.UUP]
        self.PAIR_LIST = ['S_G', 'I_U', 'A_F']
        
        self.no_signals = 0
        self.INI_WAIT_DAYS = 15
        self.SHIFT = 55
        self.MEAN = 11
        self.init = 0
        
        self.bull = 1 
        self.count = 0 
        self.outday = 0
        self.in_stock = 0
        self.spy = []
        self.wait_days = self.INI_WAIT_DAYS
        self.wt = {}
        self.real_wt = {}
        
        self.UniverseSettings.Resolution = Resolution.Minute
        self.AddUniverse(self.MomentumSelectionFunction, self.FundamentalSelectionFunction)
        self.num_screener = 100
        self.num_stocks = 15
        self.formation_days = 70
        self.lowmom = False
        
        # rebalance the universe selection once a month
        self.rebalence_flag = 0
        # make sure to run the universe selection at the start of the algorithm even it's not the manth start
        self.flip_flag = 0
        self.first_month_trade_flag = 1
        self.trade_flag = 0 
        self.symbols = None
        
        self.SetWarmUp(timedelta(126))
        

        self.Schedule.On(self.DateRules.EveryDay(), self.TimeRules.AfterMarketOpen('SPY', 120),
            self.calculate_signal)

        #self.Schedule.On(
        #    self.DateRules.EveryDay(),
        #    self.TimeRules.AfterMarketOpen('SPY', 120),
        #    self.rebalance_when_out_of_the_market
        #)

        self.Schedule.On(
            self.DateRules.MonthStart("SPY"), 
            self.TimeRules.AfterMarketOpen('SPY', 150),
            Action(self.monthly_rebalance))
            
        symbols = self.SIGNALS + [self.MKT] + self.FORPAIRS
        for symbol in symbols:
            self.consolidator = TradeBarConsolidator(timedelta(days = 1))
            self.consolidator.DataConsolidated += self.consolidation_handler
            self.SubscriptionManager.AddConsolidator(symbol, self.consolidator)
            
        self.lookback = 252
        self.history = self.History(symbols, self.lookback, Resolution.Daily)
        if self.history.empty or 'close' not in self.history.columns:
            return
        self.history = self.history['close'].unstack(level=0).dropna()
        self.update_history_shift() 

    def monthly_rebalance(self):
        if self.bull:
            self.Log("REBALANCE: Monthly trigger")
            self.rebalance()
        
    def consolidation_handler(self, sender, consolidated):
        self.history.loc[consolidated.EndTime, consolidated.Symbol] = consolidated.Close
        self.history = self.history.iloc[-self.lookback:]
        self.update_history_shift()
        
        
    def update_history_shift(self):
        self.history_shift_mean = self.history.shift(self.SHIFT).rolling(self.MEAN).mean()    
            
   
    def returns(self, symbol, period, excl):
        prices = self.History(symbol, TimeSpan.FromDays(period + excl), Resolution.Daily).close
        return prices[-excl] / prices[0]
        
        
    def calculate_signal(self):
        mom = (self.history / self.history_shift_mean - 1)

        mom[self.UUP] = mom[self.UUP] * (-1)
        mom['S_G'] = mom[self.SLV] - mom[self.GLD]
        mom['I_U'] = mom[self.XLI] - mom[self.XLU]
        mom['A_F'] = mom[self.FXA] - mom[self.FXF]   

        pctl = np.nanpercentile(mom, 5, axis=0)
        extreme = mom.iloc[-1] < pctl

        self.wait_days = int(
            max(0.50 * self.wait_days,
                self.INI_WAIT_DAYS * max(1,
                     np.where((mom[self.GLD].iloc[-1]>0) & (mom[self.SLV].iloc[-1]<0) & (mom[self.SLV].iloc[-2]>0), self.INI_WAIT_DAYS, 1),
                     np.where((mom[self.XLU].iloc[-1]>0) & (mom[self.XLI].iloc[-1]<0) & (mom[self.XLI].iloc[-2]>0), self.INI_WAIT_DAYS, 1),
                     np.where((mom[self.FXF].iloc[-1]>0) & (mom[self.FXA].iloc[-1]<0) & (mom[self.FXA].iloc[-2]>0), self.INI_WAIT_DAYS, 1)
                     )))
                     
        adjwaitdays = min(60, self.wait_days)

        # self.Debug('{}'.format(self.wait_days))

        for signal in self.SIGNALS:
            if extreme[self.SIGNALS].any():
                self.no_signals += 1
        for fx in self.PAIR_LIST:
            if extreme[self.PAIR_LIST].any():
                self.no_signals += 1
                
        if self.no_signals > 5:
            self.bull = False
            self.SetHoldings("TLT", 1, True)
            self.outday = self.count
            self.no_signals = 0
        
        else:
            self.no_signals = 0
            
        if self.count >= self.outday + adjwaitdays:
            if not self.bull:
                self.flip_flag = 1
                self.Log("REBALANCE: IN trigger")
                self.rebalance()
                self.flip_flag = 0
            self.bull = True
            
        self.count += 1
        
        self.Log(f"TotalPortfolioValue: {self.Portfolio.TotalPortfolioValue}, TotalMarginUsed: {self.Portfolio.TotalMarginUsed}, MarginRemaining: {self.Portfolio.MarginRemaining}, Cash:  {self.Portfolio.Cash}")
        #self.Log("TotalHoldingsValue: " + str(self.Portfolio.TotalHoldingsValue))
    
        for key in sorted(self.Portfolio.keys()):
            if self.Portfolio[key].Quantity > 0.0:
                self.Log(f"Symbol/Qty: {key} / {self.Portfolio[key].Quantity}, Avg: {self.Portfolio[key].AveragePrice}, Curr: { self.Portfolio[key].Price}, Profit($): {self.Portfolio[key].UnrealizedProfit}");


    def MomentumSelectionFunction(self, momentum):
        if (self.rebalence_flag or self.first_month_trade_flag) and (self.bull or self.flip_flag):
            # drop stocks which have no fundamental data or have too low prices
            selected = [x for x in momentum if (x.HasFundamentalData) and (float(x.Price) > 5)]
            # rank the stocks by dollar volume 
            filtered = sorted(selected, key=lambda x: x.DollarVolume, reverse=True)
            return [ x.Symbol for x in filtered[:200]]
        else:
            return self.symbols


    def FundamentalSelectionFunction(self, fundamental):
        if (self.rebalence_flag or self.first_month_trade_flag) and (self.bull or self.flip_flag):
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