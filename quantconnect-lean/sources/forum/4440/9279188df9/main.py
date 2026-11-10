from clr import AddReference
AddReference("System")
AddReference("QuantConnect.Algorithm")
AddReference("QuantConnect.Indicators")
AddReference("QuantConnect.Common")

from System import *
from QuantConnect import *
from QuantConnect.Algorithm import *
from QuantConnect.Indicators import *
from QuantConnect.Python import PythonQuandl
from QuantConnect.Securities.Equity import EquityExchange
from datetime import datetime, timedelta

class BasicTemplateAlgorithm(QCAlgorithm):

    def Initialize(self):

        self.SetStartDate(2002, 1, 1)
        self.SetEndDate(2017, 12, 31)
        self.SetCash(10000)
        
        self.AddEquity('XLU', Resolution.Daily)
        self.AddEquity('VTI', Resolution.Daily)
        
        self.Securities['XLU'].FeeModel = ConstantFeeTransactionModel(1)
        self.Securities['VTI'].FeeModel = ConstantFeeTransactionModel(1)
        
        self.RS = 0
        
        self.SetWarmUp(10)
        self.Schedule.On(self.DateRules.WeekStart('XLU'), self.TimeRules.AfterMarketOpen('XLU', 1), Action(self.RelativeStrength))
        self.Schedule.On(self.DateRules.WeekStart('XLU'), self.TimeRules.AfterMarketOpen('XLU', 2), Action(self.Trade))
        
    def RelativeStrength(self):
        
        slices = self.History(['XLU', 'VTI'], 5, Resolution.Daily)
        
        if not slices.empty:
            df_xlu = slices.loc['XLU']
            xlu_open = df_xlu['open'][0]
            xlu_close = df_xlu['close'][-1]
            
            df_vti = slices.loc['VTI']
            vti_open = df_vti['open'][0]
            vti_close = df_vti['close'][-1]
            
            vtixlu_open = vti_open / xlu_open
            xluvti_close = xlu_close / vti_close
            comb = vtixlu_open * xluvti_close
            
        self.RS = comb - 1

    def Trade(self):
        
        if self.RS > 0:
            if self.Portfolio['XLU'].Quantity > 0 and self.Portfolio['VTI'].Quantity == 0:
                return
            elif self.Portfolio['XLU'].Quantity == 0 and self.Portfolio['VTI'].Quantity > 0:
                self.Liquidate('VTI')
                self.SetHoldings('XLU', 1)
            else:
                self.SetHoldings('XLU', 1)
        elif self.RS < 0:
            if self.Portfolio['XLU'].Quantity == 0 and self.Portfolio['VTI'].Quantity > 0:
                return
            elif self.Portfolio['XLU'].Quantity > 0 and self.Portfolio['VTI'].Quantity == 0:
                self.Liquidate('XLU')
                self.SetHoldings('VTI', 1)
            else:
                self.SetHoldings('VTI', 1)
        else:
            if self.Portfolio['XLU'].Quantity != 0 or self.Portfolio['VTI'].Quantity != 0:
                return
            else:
                return