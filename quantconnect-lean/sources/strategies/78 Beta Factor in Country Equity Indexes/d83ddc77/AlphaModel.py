from datetime import timedelta, datetime
from QuantConnect.Algorithm.Framework.Alphas import AlphaModel, Insight, InsightType, InsightDirection
import numpy as np
from collections import deque
import calendar

class BetaAlphaModel(AlphaModel):

    def __init__(self):
        self.period = timedelta(hours=6)
        self.Name = 'BetaAlphaModel'
        self.assets = {}
        self.month = datetime.min
        
    def Update(self, algorithm, data):
        if data.ContainsKey("SPY"):
            self.market_price.append(float(algorithm.Securities["SPY"].Price))
        for key, value in self.assets.items():
            if data.ContainsKey(key):
                value.Price.append(float(algorithm.Securities[key].Price))

        insights = []

        if self.month != algorithm.Time.month:    
            self.month = algorithm.Time.month 
            beta_values = {} 
            market_return = np.diff(np.array(self.market_price))/np.array(self.market_price)[:-1]
            long = None
            for key, value in self.assets.items():
                if key != "SPY" and len(value.Price) == value.Price.maxlen:
                    asset_return = np.diff(np.array(value.Price))/np.array(value.Price)[:-1]
                    beta_values[key] = self.beta(asset_return, market_return)
            sorted_by_beta = sorted(beta_values, key = lambda x: beta_values[x])
            long = sorted_by_beta[:int(0.25*len(sorted_by_beta))]
            short = sorted_by_beta[-int(0.25*len(sorted_by_beta)):]
            
            # day: the weekday of first day of the month 
            # num_days: number of days in month  
            day, num_days = calendar.monthrange(algorithm.Time.year, algorithm.Time.month)
            insight_period = num_days - algorithm.Time.day - 1
            if long and short:
                invested = [x.Key for x in algorithm.Portfolio if x.Value.Invested]
                for i in invested:
                    if algorithm.Portfolio[i].IsLong and i not in long:  
                        insights.append(Insight.Price(i, timedelta(days=1), InsightDirection.Flat))
                    if algorithm.Portfolio[i].IsShort and i not in short:  
                        insights.append(Insight.Price(i, timedelta(days=1), InsightDirection.Flat))
                        
                for i in long:
                    insights.append(Insight.Price(i, timedelta(days=insight_period), InsightDirection.Up))
                for i in short:
                    insights.append(Insight.Price(i, timedelta(days=insight_period), InsightDirection.Down))
           
        return insights


    def OnSecuritiesChanged(self, algorithm, changes):
        for added in changes.AddedSecurities:
            if added.Symbol.Value == "SPY":
                self.market_price = deque(maxlen=253)
                hist_SPY = algorithm.History(["SPY"], 500, Resolution.Daily)
                for i in hist_SPY.loc["SPY"].itertuples():
                    self.market_price.append(i.close)     

            if added not in self.assets and added.Symbol.Value != "SPY":
                hist = algorithm.History([added.Symbol.Value], 500, Resolution.Daily)
                if not hist.empty:
                    self.assets[added.Symbol] = SymbolData(added)
                    for i in hist.loc[added.Symbol.Value].itertuples():
                        self.assets[added.Symbol].Price.append(i.close)                

        for removed in changes.RemovedSecurities:
            self.assets.pop(removed.Symbol)

    def beta(self, asset_return, market_return):
        asset_return = np.array(asset_return, dtype=np.float32)
        market_return = np.array(market_return, dtype=np.float32)
        return np.cov(asset_return, market_return)[0][1]/np.var(market_return)
    
class SymbolData:
    def __init__(self, symbol):
        self.Symbol = symbol
        self.Price = deque(maxlen=253)