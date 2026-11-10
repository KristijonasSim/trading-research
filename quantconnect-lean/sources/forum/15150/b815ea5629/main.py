import numpy as np
import pandas as pd
from datetime import datetime

from AlgorithmImports import *

class EmmausAlgorithm(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2006, 1, 1)
        self.SetCash(30000) 

        # choose 11 sector ETFs
        tickers = [ "XLY",  # Materials
                    "XLB",  # Communication Services
                    "XLE",  # Energy
                    "XLF",  # Financials
                    "XLK",  # Technology
                    "XLP",  # Staples
                    "IYR", # Real Estate
                    "XLU",  # Utilities
                    "XLV",  # Health Care
                    "XLT",
                    ]  # Discretionary 

        self.data = {}

        for ticker in tickers:
            symbol = self.AddEquity(ticker, Resolution.Daily).Symbol
            self.data[symbol] = {"roc": RateOfChangePercent(3), "dollar_return": None}
            consolidator = TradeBarConsolidator(CalendarType.Monthly)
            self.RegisterIndicator(symbol, self.data[symbol]["roc"], consolidator)

        self.SetWarmUp(30)

        # shcedule the function to fire at the month start 
        self.Schedule.On(self.DateRules.Every(DayOfWeek.Monday),  self.TimeRules.At(8, 0), self.Rebalance)


    def Rebalance(self):
        if self.IsWarmingUp:
            return
        
        # calculate dollar return for last trading year
        start_date = self.Time.replace(year=self.Time.year-1, month=1, day=1)
        end_date = self.Time.replace(year=self.Time.year-1, month=12, day=31)
        for symbol in self.data:
            history = self.History([symbol], start_date, end_date, Resolution.Daily)
            if not history.empty:
                self.data[symbol]["dollar_return"] = self.Portfolio[symbol].Price / history.iloc[0]["close"] - 1

        # calculate momentum rank based on combination of last 3 months' return and dollar return for last trading year
        momentum_rank = {symbol: 0 for symbol in self.data}
        for symbol, data in self.data.items():
            roc = data["roc"].Current.Value
            dollar_return = data["dollar_return"]
            if dollar_return is None:
                # if no dollar return data, use 0
                dollar_return = 0
            momentum_rank[symbol] = roc + dollar_return

        # select top 3 momentum ETFs
        top3 = sorted(momentum_rank.items(), key=lambda x: x[1], reverse=True)[:3]
        top3_symbols = [symbol for symbol, rank in top3]
        
        for kvp in self.Portfolio:
            symbol = kvp.Key
            if symbol in top3_symbols:
                continue
            # liquidate the security which is no longer in the top3 momentum list
            if kvp.Value.Invested:
                self.Liquidate(symbol, 'Not selected')

        for symbol in top3_symbols:
            if not self.Portfolio[symbol].Invested:
            
              self.SetHoldings(symbol, 1/3)
