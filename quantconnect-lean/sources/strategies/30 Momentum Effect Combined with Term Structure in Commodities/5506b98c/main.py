# https://quantpedia.com/Screener/Details/23
from datetime import timedelta
from math import floor
from decimal import Decimal
import numpy as np

class CommodityMomentumCombinedWithTermStructureAlgorithm(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2016, 1, 1)
        self.SetEndDate(2017, 1, 1)
        self.SetCash(10000000)
        tickers = [
                Futures.Softs.Cocoa,
                Futures.Softs.Coffee,
                Futures.Grains.Corn,
                Futures.Softs.Cotton2,
                Futures.Grains.Oats,
                Futures.Softs.OrangeJuice,
                Futures.Grains.SoybeanMeal,
                Futures.Grains.SoybeanOil,
                Futures.Grains.Soybeans,
                Futures.Softs.Sugar11,
                Futures.Grains.Wheat,
                Futures.Meats.FeederCattle,
                Futures.Meats.LeanHogs,
                Futures.Meats.LiveCattle,
                Futures.Energies.CrudeOilWTI,
                Futures.Energies.HeatingOil,
                Futures.Energies.NaturalGas,
                Futures.Energies.Gasoline,
                Futures.Metals.Gold,
                Futures.Metals.Palladium,
                Futures.Metals.Platinum,
                Futures.Metals.Silver
            ]
        for ticker in tickers:
            future = self.AddFuture(ticker)
            future.SetFilter(timedelta(0), timedelta(days = 90))       
        self.chains = {}
        self.AddEquity("SPY", Resolution.Minute)
        self.Schedule.On(self.DateRules.MonthStart("SPY"), self.TimeRules.AfterMarketOpen("SPY", 30), self.Rebalance)
        self.rebalance = False

        
    def OnData(self,slice):
        if not self.rebalance: return
        # Saves the Futures Chains 
        for chain in slice.FutureChains:
            if chain.Value.Contracts.Count < 2: 
                continue
            if chain.Value.Symbol.Value not in self.chains:
                self.chains[chain.Value.Symbol.Value] =  [i for i in chain.Value]
                
            self.chains[chain.Value.Symbol.Value] = [i for i in chain.Value]

        self.Liquidate()
        roll_return = {}
        for symbol, chain in self.chains.items():
            contracts = sorted(chain, key = lambda x: x.Expiry)
            expiry_nearest = contracts[0].Expiry
            price_nearest = float(contracts[0].LastPrice) if contracts[0].LastPrice>0 else 0.5*float(contracts[0].AskPrice+contracts[0].BidPrice)
            for x in contracts[1:]:
                roll_return[x] = (price_nearest-float(x.LastPrice))*365 / (x.Expiry-expiry_nearest).days
        
        sorted_by_roll_return = sorted(roll_return, key = lambda x: roll_return[x], reverse =True)
        
        tertile = floor(1/3*len(sorted_by_roll_return))
        high = sorted_by_roll_return[:tertile]
        low = sorted_by_roll_return[-tertile:]
        
        mean_return_high = {}
        for i in high:
            hist = self.History(i.Symbol, timedelta(days = 21), Resolution.Minute)
            if hist.empty:
                continue
            hist_close = hist['close'][i.Expiry][i.Symbol.Value]
            mean_return_high[i] = np.mean(hist_close.pct_change())
        
        high_winners = sorted(mean_return_high, key = lambda x: mean_return_high[x], reverse=True)[:int(len(high)*0.5)]


        mean_return_low = {}
        for i in low:
            hist = self.History(i.Symbol, timedelta(days = 21), Resolution.Minute)
            if hist.empty:
                continue
            hist_close = hist['close'][i.Expiry][i.Symbol.Value]
            mean_return_low[i] = np.mean(hist_close.pct_change())
        
        low_losers = sorted(mean_return_low, key = lambda x: mean_return_low[x], reverse=True)[-int(len(low)*0.5):]


        short_weight = 0.5/len(low_losers)
        for short in low_losers:
            self.SetHoldings(short.Symbol, -short_weight)
            
        long_weight = 0.5/len(high_winners)
        for long in high_winners:
            self.SetHoldings(long.Symbol, long_weight)
            
        self.rebalance = False
    
    def Rebalance(self):
        self.rebalance = True