from clr import AddReference
AddReference("System")
AddReference("QuantConnect.Algorithm")
AddReference("QuantConnect.Common")

from System import *
from QuantConnect import *
from QuantConnect.Algorithm import *
from QuantConnect.Indicators import *
from QuantConnect.Data.Market import TradeBar

import numpy as np
import decimal as d
from datetime import timedelta, datetime

class OptionsAlgorithm(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2018, 12, 20)
        self.SetEndDate(2020, 1, 12)
        self.SetCash(1000000)
        self.SetBrokerageModel(BrokerageName.InteractiveBrokersBrokerage)
        
        self.equitylist = ["FAS","TNA","UVXY","TQQQ","JDST","FAZ","TZA", "SVXY", "SQQQ", "JNUG", "UGAZ","DGAZ"]

        #total number of equities
        self.noe = len(self.equitylist)
        def zerolistmaker(n):
            listofzeros = [0] * n
            return listofzeros

        #generate blank list
        self.equity = zerolistmaker(self.noe)
        self.syl = zerolistmaker(self.noe)
        
        # Add assets you'd like to see
        for x in range(self.noe):
            self.equity[x] = self.AddSecurity(SecurityType.Equity, self.equitylist[x], Resolution.Minute)
            self.syl[x] = self.equity[x].Symbol
        
        self.days_counter = 100000
        
        #Set Trading and closing Times, for 1 day intra
        self.Schedule.On(self.DateRules.EveryDay(),self.TimeRules.At(10, 35),Action(self.Rebalance))
    
    def Rebalance(self): 
        
        self.days_counter+=1
        
        if self.days_counter >= 1:
            for x in range(self.noe):
                self.SetHoldings(self.syl[x], -1/(self.noe))
                self.days_counter = 0
                
                
                
#end