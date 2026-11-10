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
        #self.SetEndDate(2011,3,25)
        self.SetCash(10000)
            
        # Define symbol and "type" of custom data: used for signal ratio
        self.AddData(CboeVix, "VIX")
        self.AddData(CboeVxV, "VXV")

    def OnData(self, data):
        
        if "VIX" not in data or "VXV" not in data: 
            self.Debug("VIX & VXV not in Data")    
            return
    
        vix_data = data["VIX"].Open
        self.Log("VIX_Open:%.5f" %vix_data)