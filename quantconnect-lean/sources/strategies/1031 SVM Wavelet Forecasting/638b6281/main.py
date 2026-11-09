# QUANTCONNECT.COM - Democratizing Finance, Empowering Individuals.
# Lean Algorithmic Trading Engine v2.0. Copyright 2020 QuantConnect Corporation.
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

import SVMWavelet as svmw
import numpy as np

class OptimizedUncoupledRegulators(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2015, 9, 20)  # Set Start Date
        self.SetCash(1000000)  # Set Strategy Cash
        
        period = 152
        
        self.SetBrokerageModel(AlphaStreamsBrokerageModel())
        self.SetPortfolioConstruction(InsightWeightingPortfolioConstructionModel(lambda time: None))
        self.SetAlpha(SVMWaveletAlphaModel(period))
        
        # 1549 data points with FXCM, 1560 data points with Oanda
        self.AddForex('EURJPY', Resolution.Daily, Market.Oanda)
        
class SVMWaveletAlphaModel(AlphaModel):
    def __init__(self, period):
        self.period = period
        self.closes = {}
        
    def Update(self, algorithm, data):
        for symbol, closes in self.closes.items():
            if data.Bars.ContainsKey(symbol):
                closes.Add(data[symbol].Close)
       
        insights = []
        
        for symbol, closes in self.closes.items():
            recent_close = closes[0]
            forecasted_value = svmw.forecast(np.array(list(closes))[::-1])
            
            # if the sums of the weights > 1, IWPCM normalizes the sum to 1, which
            #   means we don't need to worry about normalizing them
            weight = (forecasted_value / recent_close) - 1
            
            insightDirection = InsightDirection.Flat
            
            if weight > 0.005:
                insightDirection = InsightDirection.Up
            elif weight < -0.005:
                insightDirection = InsightDirection.Down
            
            insights.append(Insight.Price(symbol, timedelta(1), insightDirection, None, None, None, abs(weight)))
        
        return insights
  
    def OnSecuritiesChanged(self, algorithm, changed):
        for security in changed.AddedSecurities:
            symbol = security.Symbol
            self.closes[symbol] = RollingWindow[float](self.period)
            
            hist_data = algorithm.History(symbol, self.period, Resolution.Daily).loc[symbol]
            for _, row in hist_data.iterrows():
                self.closes[symbol].Add(row['close'])
        
        for security in changed.RemovedSecurities:
            self.closes.pop(security.Symbol)