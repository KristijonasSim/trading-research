from datetime import datetime
import numpy as np
import pandas as pd


class BetaAlgorithm(QCAlgorithm):


    def __init__(self):
        self.tickers = ["MMM", "AXP", "AAPL", "BA", "CAT", "CVX", "CSCO","KO",
                        "DIS","DD","XOM","GE","GS","HD","IBM","INTC","JPM","MCD",
                        "MRK","MSFT","NKE","PFE","PG","TRV","UTX","UNH","VZ","V","WMT"]   # symbols of Dow 30 companies.
        self.symbols = []     # we use a list to place symbols because symbol is an object inheriting QCAlgorithm, not a string
        self.benchmark = "SPY"  # we use SPY as benchmark
        self.regression_dates = 21   # set number days to trace back



    def Initialize(self):
        self.SetStartDate(2016, 1, 1)   # Set Start Date
        self.SetEndDate(2017, 1, 1)     # Set End Date
        self.SetCash(10000)             # Set Strategy Cash

        for i in self.tickers:                                  # Extract Symbol objects in the list
            equity = self.AddEquity(i, Resolution.Daily)
            self.symbols.append(equity.Symbol)


        self.benchmark = self.AddEquity(self.benchmark, Resolution.Daily).Symbol    #Extract benchmark symbol

        self.Schedule.On(self.DateRules.MonthStart(self.benchmark), self.TimeRules.AfterMarketOpen(self.benchmark),
                            Action(self.rebalance))

        # schedule event, trigger the event at the begining of each month.
        # for more instruction about schduled event, please refer to Lean/Algorithm.Python/ScheduledEventsAlgorithm.py   on github



    def OnData(self,data):

        pass



    def regression(self,x,y):       # This function conducts linear regression and return intercept and slope in a tuple
        x = np.array(x)
        x = np.diff(x)/x[:-1]
        y = np.array(y)
        y = np.diff(y)/y[:-1]
        A = np.vstack([x, np.ones(len(x))]).T
        result = np.linalg.lstsq(A, y)[0]   # simple linear regression function in Numpy
        beta = result[0]
        alpha = result[1]

        return(alpha,beta)



    def get_regression_data(self,symbol,history):
        symbol_price = []
        benchmark_price = []
        for i in history:
            bar = i[symbol]
            benchmark = i[self.benchmark]
            symbol_price.append(bar.Close)
            benchmark_price.append(benchmark.Close)


        result = self.regression(symbol_price,benchmark_price)
        return result



    def rebalance(self):
        history = self.History(self.regression_dates, Nullable[Resolution](Resolution.Daily))
        filter = []
        for i in self.symbols:
            filter.append((i,self.get_regression_data(i, history)[0]))  # put tuples that contain symbols and their alpha into list, named filter


        filter.sort(key = lambda x : x[1],reverse = True)   # sort the filter by alpha
        sorted_symbols = []
        for i in range(2):
            sorted_symbols.append(filter[i][0])   # put the symbols of first 2 stock in a list, named sorted_symbols


        holding_list = []
        for i in self.Portfolio:
            if i.Value.Invested:
                holding_list.append(i.Value.Symbol)


        if holding_list:
            for i in holding_list:
                if i not in sorted_symbols:
                    self.Liquidate(i)

        for i in sorted_symbols:
            self.SetHoldings(i,1)