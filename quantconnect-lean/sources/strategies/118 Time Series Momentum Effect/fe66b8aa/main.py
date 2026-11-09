# https://quantpedia.com/Screener/Details/118

from QuantConnect.Python import PythonQuandl
import numpy as np

class TimeSeriesMomentumEffect(QCAlgorithm):

    def Initialize(self):

        self.SetStartDate(2014,1, 1) 
        self.SetEndDate(2019,1, 1)  
        self.SetCash(1000000)

        self.symbols = ["CHRIS/CME_LC1", # Live Cattle Futures, Continuous Contract #1 
                        "CHRIS/CME_LN1", # Lean Hog Futures, Continuous Contract #1 
                        "CHRIS/ICE_B1", # Brent Crude Futures, Continuous Contract
                        "CHRIS/ICE_G1", # Gas Oil Futures, Continuous Contract
                        "CHRIS/ICE_CT1", # Cotton No. 2 Futures, Continuous Contract
                        "CHRIS/ICE_KC1", # Coffee C Futures, Continuous Contract
                        "CHRIS/ICE_CC1", # Cocoa Futures, Continuous Contract 
                        "CHRIS/ICE_SB1", # Sugar No. 11 Futures, Continuous Contract
                        "CHRIS/CME_C1", #Corn Futures, Continuous Contract #1 (C1) (Front Month)
                        "CHRIS/CME_S1", #Soybean Futures, Continuous Contract #1 (S1) (Front Month)
                        "CHRIS/CME_SM1", #Soybean Meal Futures, Continuous Contract #1 (SM1) (Front Month)
                        "CHRIS/CME_BO1", #Soybean Oil Futures, Continuous Contract #1 (BO1) (Front Month)
                        "CHRIS/CME_W1", #Wheat Futures, Continuous Contract #1 (W1) (Front Month)
                        ]

        self.period = 252
        self.roc = {}
        for symbol in self.symbols:
            self.AddData(QuandlFutures, symbol, Resolution.Daily)
            self.roc[symbol] = self.ROC(symbol, self.period)   #Initialize ROC indicator : ROC is short for RateofChange
            
        self.SetWarmup(self.period)
        self.Schedule.On(self.DateRules.MonthStart("CHRIS/CME_S1"), self.TimeRules.AfterMarketOpen("CHRIS/CME_S1"), self.Rebalance)  # Rebalance the portfolio every month


    def Rebalance(self): 
        
        # Make a historical data Request to get the daily returns
        history = self.History(self.symbols, self.period, Resolution.Daily)
        history = history.value.unstack(level=0).pct_change().dropna()
        
        # Compute the inverse of the volatility
        # The weights are the normalized inverse of the volatility
        vol_inv = 1 / history.std(ddof=1)
        vol_sum = vol_inv.sum()
        weights = (vol_inv / vol_sum).fillna(0).to_dict()

        self.Liquidate()
        #np.sign(roc.Current.Value) tells us whether to long or short
        for symbol, roc in self.roc.items():
            percentage = np.sign(roc.Current.Value) * weights[symbol] *.5
            self.SetHoldings(symbol, percentage)


class QuandlFutures(PythonQuandl):
    def __init__(self):
        self.ValueColumnName = "Settle"  #set the column name of value to "Settle", because the column name of desired data from Quandl is "Settle".