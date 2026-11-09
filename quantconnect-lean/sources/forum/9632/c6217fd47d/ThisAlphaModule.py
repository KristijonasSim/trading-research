# QUANTCONNECT.COM - Democratizing Finance, Empowering Individuals.
# Lean Algorithmic Trading Engine v2.0. Copyright 2014 QuantConnect Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from clr import AddReference
AddReference("QuantConnect.Common")
AddReference("QuantConnect.Algorithm")
AddReference("QuantConnect.Algorithm.Framework")
AddReference("QuantConnect.Indicators")

from QuantConnect import *
from QuantConnect.Indicators import *
from QuantConnect.Algorithm import *
from QuantConnect.Algorithm.Framework import *
from QuantConnect.Algorithm.Framework.Alphas import *
import numpy as np
import pandas as pd
import math

class this_alpha_module(AlphaModel):
    '''Alpha model that uses an EMA cross to create insights'''

    def __init__(self, max_holding_period=250, resolution = Resolution.Daily, param_dict=None, data_dict=None, when_trigger=None, assets_dict=None, assets_history_df=None, quantity_dict=None):
        self.param_dict=param_dict
        self.data=data_dict
        #self.assets_dict=assets_dict
        self.history=assets_history_df
        self.quantity=quantity_dict
        self.predictionInterval = Time.Multiply(Extensions.ToTimeSpan(resolution), max_holding_period)
        self.very_first_time=True
        self.consol_counting={}
        
        resolutionString = Extensions.GetEnumString(resolution, Resolution)
        self.Name = '{}({}_{})'.format(self.__class__.__name__, resolutionString, when_trigger)
        self.latest_rebalance_date=None
        self.when_trigger=when_trigger
        self.tlt_symbol = Symbol.Create('TLT', SecurityType.Equity, Market.USA)
        
        self.assets_dict={}
        # Market and list of signals based on ETFs

        

    def Update(self, algorithm, data):
        '''Updates this alpha model with the latest data from the algorithm.
        This is called each time the algorithm receives data for subscribed securities
        Args:
            algorithm: The algorithm instance
            data: The new data available
        Returns:
            The new insights generated'''
        if algorithm.Time.date()==self.latest_rebalance_date:
            return []
            
        if algorithm.Time.hour>=10:
            self.insights=[]
            self.rebalance_when_out_of_the_market(algorithm)
            
            self.latest_rebalance_date=algorithm.Time.date()
            algorithm.Log('done rebalancing for insight, len of insight is {}'.format(len(self.insights)))
            
        return self.insights





    def OnSecuritiesChanged(self, algorithm, changes):
        '''Event fired each time the we add/remove securities from the data feed
        Args:
            algorithm: The algorithm instance that experienced the change in securities
            changes: The security additions and removals from the algorithm'''
        if self.very_first_time==True:
            self.very_first_time=False
            self.assets_dict['MRKT'] = algorithm.AddEquity('SPY', Resolution.Daily).Symbol  # market
            self.assets_dict['GOLD'] = algorithm.AddEquity('GLD', Resolution.Daily).Symbol  # gold
            self.assets_dict['SLVA'] = algorithm.AddEquity('SLV', Resolution.Daily).Symbol  # vs silver
            self.assets_dict['UTIL'] = algorithm.AddEquity('XLU', Resolution.Daily).Symbol  # utilities
            self.assets_dict['INDU'] = algorithm.AddEquity('XLI', Resolution.Daily).Symbol  # vs industrials
            self.assets_dict['METL'] = algorithm.AddEquity('DBB', Resolution.Daily).Symbol  # input prices (metals)
            self.assets_dict['USDX'] = algorithm.AddEquity('UUP', Resolution.Daily).Symbol  # safe haven (USD)
            
            self.FORPAIRS = [self.assets_dict['GOLD'], self.assets_dict['SLVA'], self.assets_dict['UTIL'], self.assets_dict['INDU'], self.assets_dict['METL'], self.assets_dict['USDX']]
            
    
            # Setup daily consolidation
            symbols = [self.assets_dict['MRKT']] + self.FORPAIRS
            for symbol in symbols:
                self.consol_counting[symbol]=0
                self.consolidator = TradeBarConsolidator(timedelta(days=1))
                self.consolidator.DataConsolidated += self.consolidation_handler
                algorithm.SubscriptionManager.AddConsolidator(symbol, self.consolidator)
            
            # Warm up history
            self.history = algorithm.History(symbols, self.param_dict['lookback'], Resolution.Daily)
            if self.history.empty or 'close' not in self.history.columns:
                return
            self.history = self.history['close'].unstack(level=0).dropna()
            #algorithm.Log('very first index and last index of history dict is {} and {}'.format(self.history.index[0],self.history.index[-1]))
            
            
        
            
            
        #algorithm.Log('securities changes, in alpha model, {} added'.format(len(changes.AddedSecurities)))
        addedSymbols = []
        for security in changes.AddedSecurities:
            addedSymbols.append(security.Symbol)
            if security.Symbol not in self.data:
                self.data[security.Symbol] = SymbolData(security.Symbol, self.param_dict['formation_days'], algorithm)
       
        if len(addedSymbols) > 0:
            history = algorithm.History(addedSymbols, 1 + self.param_dict['formation_days'], Resolution.Daily).loc[addedSymbols]
            for symbol in addedSymbols:
                try:
                    self.data[symbol].Warmup(history.loc[symbol])
                except:
                    self.Debug(str(symbol))
                    continue

                    
                    
                    
    def derive_vola_waitdays(self):
        volatility = 0.6 * np.log1p(self.history[[self.assets_dict['MRKT']]].pct_change()).std() * np.sqrt(252)
        wait_days = int(volatility * self.param_dict['WAITD_CONSTANT'])
        returns_lookback = int((1.0 - volatility) * self.param_dict['WAITD_CONSTANT'])
        return wait_days, returns_lookback
 
        
        
    def rebalance_when_out_of_the_market(self, algorithm):
        self.param_dict['wait_days'], returns_lookback = self.derive_vola_waitdays()
        ## Check for Bears
        algorithm.Log('history first index is {}'.format(self.history.index[0]))
        for key in self.consol_counting.keys():
            algorithm.Log('consol updated {} so far for {}'.format(key, self.consol_counting[key]))
        
        returns = self.history.pct_change(returns_lookback).iloc[-1]
        silver_returns = returns[self.assets_dict['SLVA']]
        gold_returns = returns[self.assets_dict['GOLD']]
        industrials_returns = returns[self.assets_dict['INDU']]
        utilities_returns = returns[self.assets_dict['UTIL']]
        metals_returns = returns[self.assets_dict['METL']]
        dollar_returns = returns[self.assets_dict['USDX']]
        
        #algorithm.Log('g last index is {}'.format(self.history.index[-1]))
        #algorithm.Log('s is {}'.format(silver_returns))
        #algorithm.Log('u is {}'.format(utilities_returns))
        #algorithm.Log('i is {}'.format(industrials_returns))
        #algorithm.Log('m is {}'.format(metals_returns))
        #algorithm.Log('d is {}'.format(dollar_returns))
        
        self.param_dict['DISTILLED_BEAR'] = (((gold_returns > silver_returns) and
                       (utilities_returns > industrials_returns)) and 
                       (metals_returns < dollar_returns)
                       )
        
        #algorithm.Log('dist is {}'.format(self.param_dict['DISTILLED_BEAR']))
        
        # Determine whether 'in' or 'out' of the market
        if self.param_dict['DISTILLED_BEAR']:
            self.param_dict['BE_IN'] = False
            self.param_dict['OUTDAY'] = self.param_dict['DCOUNT']
            
            if self.quantity[self.tlt_symbol] == 0:
                for symbol in self.quantity.copy().keys():
                    if symbol == self.tlt_symbol: 
                        continue
                    #self.Order(symbol, - self.quantity[symbol])
                    self.insights.append(Insight.Price(symbol, self.predictionInterval, InsightDirection.Flat))
                    #algorithm.Debug([str(algorithm.Time), str(symbol), str(-self.quantity[symbol])])
                    del self.quantity[symbol]
                quantity = algorithm.Portfolio.TotalPortfolioValue / algorithm.Securities[self.tlt_symbol].Close
                self.quantity[self.tlt_symbol] = math.floor(quantity)
                #self.Order(self.BND1, self.quantity[self.BND1])
                self.insights.append(Insight.Price(self.tlt_symbol, self.predictionInterval, InsightDirection.Up))
                #algorithm.Debug([str(algorithm.Time), str(self.tlt_symbol), str(self.quantity[self.tlt_symbol])])
                algorithm.Log('flipping to tlt today')
    
        if (self.param_dict['DCOUNT'] >= self.param_dict['OUTDAY'] + self.param_dict['wait_days']):
            self.param_dict['BE_IN'] = True
        
        #algorithm.Log('distilled is {}'.format(self.param_dict['DISTILLED_BEAR']))
        #algorithm.Log('be_in is {}'.format(self.param_dict['BE_IN']))
        #algorithm.Log('dcount is {}'.format(self.param_dict['DCOUNT']))
        #algorithm.Log('reb_count is {}'.format(self.param_dict['reb_count']))
        # Update stock ranking/holdings, when swithing from 'out' to 'in' plus every X days when 'in' (set rebalance frequency)
        if (self.param_dict['BE_IN'] and not self.param_dict['BE_IN_PRIOR']) or (self.param_dict['BE_IN'] and (self.param_dict['DCOUNT']==self.param_dict['reb_count'])):
            self.rebalance(algorithm)
                
        self.param_dict['BE_IN_PRIOR'] = self.param_dict['BE_IN']
        self.param_dict['DCOUNT'] += 1


    def rebalance(self, algorithm):
        algorithm.Log('triggering rebalance, ie buying stocks and selling tlt')
        if self.param_dict['symbols'] is None: return
        chosen_df = self.calc_return(self.param_dict['symbols'])
        chosen_df = chosen_df.iloc[:self.param_dict['num_stocks']]
        
        if self.quantity[self.tlt_symbol] > 0:
            #self.Order(self.BND1, - self.quantity[self.BND1])
            self.insights.append(Insight.Price(self.tlt_symbol, self.predictionInterval, InsightDirection.Flat))
            #algorithm.Debug([str(algorithm.Time), str(self.tlt_symbol), str(-self.quantity[self.tlt_symbol])])
            self.quantity[self.tlt_symbol] = 0
            
        weight = 1 / self.param_dict['num_stocks']
        for symbol in self.quantity.copy().keys():
            if symbol == self.tlt_symbol: 
                continue
            if not algorithm.CurrentSlice.ContainsKey(symbol) or algorithm.CurrentSlice[symbol] is None:
                continue
            if symbol not in chosen_df.index:
                #self.Order(symbol, - self.quantity[symbol])
                self.insights.append(Insight.Price(symbol, self.predictionInterval, InsightDirection.Flat))
                #algorithm.Debug([str(algorithm.Time), str(symbol), str(-self.quantity[symbol])])
                del self.quantity[symbol]
            else:
                quantity = algorithm.Portfolio.TotalPortfolioValue * weight / algorithm.Securities[symbol].Close
                if math.floor(quantity) != self.quantity[symbol]:
                    #self.Order(symbol, math.floor(quantity) - self.quantity[symbol])
                    self.insights.append(Insight.Price(symbol, self.predictionInterval, InsightDirection.Up))
                    #algorithm.Debug([str(algorithm.Time), str(symbol), str(math.floor(quantity) -self.quantity[symbol])])
                    self.quantity[symbol] = math.floor(quantity)
        
        algorithm.Log('chosen_df in alpha model contains {}'.format(chosen_df.index))
        for symbol in chosen_df.index:
            if not algorithm.CurrentSlice.ContainsKey(symbol) or algorithm.CurrentSlice[symbol] is None:
                continue
            if symbol not in self.quantity.keys():
                quantity = algorithm.Portfolio.TotalPortfolioValue * weight / algorithm.Securities[symbol].Close
                self.quantity[symbol] = math.floor(quantity)
                #self.Order(symbol, self.quantity[symbol])
                self.insights.append(Insight.Price(symbol, self.predictionInterval, InsightDirection.Up))
                #algorithm.Debug([str(algorithm.Time), str(symbol), str(self.quantity[symbol])])
        algorithm.Log('flipping to stocks')
        
    def calc_return(self, stocks):
        #ready = [self.data[symbol] for symbol in stocks if self.data[symbol].Roc.IsReady]
        #sorted_by_roc = sorted(ready, key=lambda x: x.Roc.Current.Value, reverse = not self.lowmom)
        #return [symbol_data.Symbol for symbol_data in sorted_by_roc[:self.num_stocks] ]

        ret = {}
        for symbol in stocks:
            try:
                ret[symbol] = self.data[symbol].Roc.Current.Value
            except:
                # self.Debug(str(symbol))
                continue
            
        df_ret = pd.DataFrame.from_dict(ret, orient='index')
        df_ret.columns = ['return']
        sort_return = df_ret.sort_values(by = ['return'], ascending = self.param_dict['lowmom'])
        
        return sort_return
                
    
    
    def consolidation_handler(self, sender, consolidated):
        self.history.loc[consolidated.EndTime, consolidated.Symbol] = consolidated.Close
        self.history = self.history.iloc[-self.param_dict['lookback']:]
        self.consol_counting[consolidated.Symbol]+=1
        
                
class SymbolData(object):
    def __init__(self, symbol, roc, algorithm):
        self.Symbol = symbol
        self.Roc = RateOfChange(roc)
        
        self.consolidator = algorithm.ResolveConsolidator(symbol, Resolution.Daily)
        algorithm.RegisterIndicator(symbol, self.Roc, self.consolidator)
        
    def Warmup(self, history):
        for index, row in history.iterrows():
            self.Roc.Update(index, row['close'])