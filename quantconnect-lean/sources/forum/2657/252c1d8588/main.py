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
        self.SetStartDate(2011, 1, 15)
        self.SetEndDate(datetime.now().date() - timedelta(1))
        self.SetCash(10000)
            
        self.SetBrokerageModel(BrokerageName.InteractiveBrokersBrokerage, 
                                AccountType.Margin)
        self.mx_len = 3 # <--- 1 too reactive, 3 filter 1 spikes, 5 filters 2... 
        self.perc_qnty = 1.0 # 0.3 is already fun enough

        # add the #2 ETFs (short and long VIX futures)
        self.XIV = self.AddEquity("XIV", Resolution.Daily).Symbol
        self.VXX = self.AddEquity("VXX", Resolution.Daily).Symbol

        # Define symbol and "type" of custom data: used for signal ratio
        self.AddData(CboeVix, "VIX")
        self.AddData(CboeVxV, "VXV")

        # VIX futures from Quandl (rtrn'settle' of # 1st continuous VIX fut)
#       self.VIX1 = "SCF/CBOE_VX1_ON"; self.AddData(QuandlFuture, self.VIX1, Resolution.Daily)

        # median of the ratio (#5d to filter 2 spikes)
        self.med_ratio = deque(maxlen=self.mx_len)
        
        self.SetWarmUp(timedelta(self.mx_len)) # no really need for this with median


    def OnData(self, data):
        
        if "VIX" not in data or "VXV" not in data: return
    
        ratio_d = data["VIX"].Open / data["VXV"].Open    # .Close will have look-ahead bias...
        self.med_ratio.append(ratio_d) # 5d 
        ratio = np.median(self.med_ratio)

        XIV_qnty = self.Portfolio[self.XIV].Quantity
        VXX_qnty = self.Portfolio[self.VXX].Quantity
            
        # short vol (buy XIV): backwardation and declining vol
        if (ratio < 0.95): # and (mom > 0.1):
            if (VXX_qnty !=0):   self.Liquidate(self.VXX) 
            if (XIV_qnty ==0):   
                self.SetHoldings(self.XIV, self.perc_qnty)
                self.Notify.Email("XXXXX@gmail.com", "IB Algo Execution", "long XIV"); self.Log("short VOL")
        
        # long vol (buy VXX): contango and increasing vol
        elif (ratio > 1.05): # and (mom < 0.1):
            if (XIV_qnty !=0):   self.Liquidate(self.XIV)
            if (VXX_qnty ==0):
                self.SetHoldings(self.VXX, self.perc_qnty)
                self.Notify.Email("XXXX@gmail.com", "IB Algo Execution", "long VXX"); self.Log("long VOL")
            
        # flat (no position)
        else:
            if (XIV_qnty !=0) or (VXX_qnty !=0):
                self.Liquidate()
                self.Notify.Email("xxxxxxxxxx@gmail.com", "IB Algo Execution", "Flat position"); self.Log("Flat")