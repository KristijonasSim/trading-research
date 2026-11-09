# QUANTCONNECT.COM - Democratizing Finance, Empowering Individuals.
# Lean Algorithmic Trading Engine v2.0. Copyright 2014 QuantConnect Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from clr import AddReference
AddReference("System")
AddReference("QuantConnect.Algorithm")
AddReference("QuantConnect.Common")

from System import *
from QuantConnect import *
from QuantConnect.Algorithm import *

from IntradayMomentumAlphaModel import IntradayMomentumAlphaModel
from CloseOnCloseExecutionModel import CloseOnCloseExecutionModel

class IntradayETFMomentumAlgorithm(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2015, 1, 1)
        self.SetEndDate(2020, 8, 16)
        self.SetCash(50000)
        
        tickers = ['SPY',  # S&P 500
                   'IWM',  # Russell 2000
                   'IYR'   # Real Estate ETF
        ]
        symbols = [ Symbol.Create(ticker, SecurityType.Equity, Market.USA) for ticker in tickers ]
        self.SetUniverseSelection( ManualUniverseSelectionModel(symbols) )
        self.UniverseSettings.Resolution = Resolution.Minute
        self.SetSecurityInitializer(self.CustomSecurityInitializer)
        
        self.SetAlpha(IntradayMomentumAlphaModel(self))
        
        self.SetPortfolioConstruction(EqualWeightingPortfolioConstructionModel(lambda time: None))
        
        self.SetExecution(CloseOnCloseExecutionModel())
        
        
    def CustomSecurityInitializer(self, security):
        security.SetFeeModel(NoFeeOrderModel())
        security.SetFillModel(NoFeeFillModel())
    
    
class NoFeeOrderModel:
    def GetOrderFee(self, parameters):
        return OrderFee(CashAmount(0, 'USD'))
        
class NoFeeFillModel(FillModel):

    def MarketFill(self, asset, order):
        fill = super().MarketFill(asset, order)

        # Set fill price to last traded price
        fill.FillPrice = asset.Price
        
        return fill
        
        
    def MarketOnCloseFill(self, asset, order):
        fill = super().MarketOnCloseFill(asset, order)
    
        # Remove slippage
        slip = asset.SlippageModel.GetSlippageApproximation(asset, order)
        if order.Direction == OrderDirection.Buy:
            fill.FillPrice -= slip
        else:
            fill.FillPrice += slip
        
        return fill