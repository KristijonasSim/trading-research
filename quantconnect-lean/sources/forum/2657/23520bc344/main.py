#
#   QuantConnect Basic Template:
#    Fundamentals to using a QuantConnect algorithm.
#
#    You can view the QCAlgorithm base class on Github: 
#    https://github.com/QuantConnect/Lean/tree/master/Algorithm
#
from clr import AddReference # .NET Common Language Runtime (CLR) <- http://pythonnet.github.io/
AddReference("System")
AddReference("QuantConnect.Algorithm") # to load an assembly use AddReference
AddReference("QuantConnect.Common")

from System import * # CLR namespaces to be treatedas Python packages
from QuantConnect import *
from QuantConnect.Algorithm import *
from QuantConnect.Python import PythonQuandl # quandl data not CLOSE

from QuantConnect.Python import PythonData # custom data

import pandas as pd; import numpy as np
from collections import deque # double queue container

from my_custom_data import *  # QuandlFuture, CboeVix, CboeVxV


class VIXStrategyByRatio(QCAlgorithm):
    
    def Initialize(self):
        self.SetStartDate(2017, 9, 15)
        self.SetEndDate(datetime.now().date() - timedelta(1))
        self.SetCash(10000)
            
        # Define symbol and "type" of custom data: used for signal ratio
        self.AddData(CboeVix, "VIX")

        self.SPY = self.AddEquity("SPY", Resolution.Daily).Symbol

        # Define the Schedules
        self.Schedule.On(self.DateRules.EveryDay(), self.TimeRules.AfterMarketOpen(self.SPY, -45),        
            Action(self.EveryDayBeforeMarketOpen))
        self.Schedule.On(self.DateRules.EveryDay(), self.TimeRules.AfterMarketOpen(self.SPY, 90),        
            Action(self.Balance))
        
    def OnData(self, data):
        if "VIX" not in data: 
            self.Debug("VIX not in Data")    
            return
    

    def EveryDayBeforeMarketOpen(self):
        self.Debug(str(self.Time)  + " EveryDayBeforeMarketOpen")
        #ratio_d = self.data["VIX"].Open 
        #self.Debug("VIX_Data:%s" %self.data["VIX"].Open)

    def Balance(self):
        self.Debug(str(self.Time)  + " Balance")