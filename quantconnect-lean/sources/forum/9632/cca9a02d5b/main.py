# https://quantpedia.com/Screener/Details/15
import pandas as pd
from datetime import datetime

class CountryEquityIndexesMomentumAlgorithm(QCAlgorithm):

    def Initialize(self):

        self.SetStartDate(2010, 1, 1)  
        self.SetEndDate(2020,10,1)
        
        self.SetEndDate(datetime.now())  
        self.SetCash(100000) 
        # create a dictionary to store momentum indicators for all symbols 
        self.data = {}

        period = 3*21
        # choose ten sector ETFs
        self.symbols = ["GXC","EEM","SPY","EWG","EWY","IVV","ARKK","QQQ","SPXL","TMF"]# BLDRS Europe 100 ADR Index ETF
        #self.symbols = ["SPY","IEF"]
        # warm up the MOM indicator
        self.SetWarmUp(period)
        for symbol in self.symbols:
            self.AddEquity(symbol, Resolution.Daily)
            self.data[symbol] = self.MOM(symbol, period, Resolution.Daily)
        # shcedule the function to fire at the month start 
        self.Schedule.On(self.DateRules.MonthStart("SPY"), self.TimeRules.AfterMarketOpen("SPY"), self.Rebalance)
            
    def OnData(self, data):
        pass

    def Rebalance(self):
        if self.IsWarmingUp: return
        top = pd.Series(self.data).sort_values(ascending = False)[:5]
        for kvp in self.Portfolio:
            security_hold = kvp.Value
            # liquidate the security which is no longer in the top momentum list
            if security_hold.Invested and (security_hold.Symbol.Value not in top.index):
                self.Liquidate(security_hold.Symbol)
        
        added_symbols = []        
        for symbol in top.index:
            if not self.Portfolio[symbol].Invested:
                added_symbols.append(symbol)
        for added in added_symbols:
            self.SetHoldings(added, 1/len(added_symbols))