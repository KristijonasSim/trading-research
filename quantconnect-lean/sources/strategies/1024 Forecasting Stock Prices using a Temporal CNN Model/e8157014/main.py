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

from MyTemporalCNN import MyTemporalCNN, Direction, input_vars
import pandas as pd
import math
from random import randint
from CloseOnCloseExecutionModel import CloseOnCloseExecutionModel

class TransdimensionalUncoupledComputer(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2015, 8, 15)  
        self.SetEndDate(2020, 8, 15)
        self.SetCash(100000) 
        
        self.SetBrokerageModel(AlphaStreamsBrokerageModel())
        self.SetExecution(CloseOnCloseExecutionModel())
        self.SetPortfolioConstruction(InsightWeightingPortfolioConstructionModel())
        
        tickers = ['AAPL', 'FB', 'MSFT']
        
        # subscribe to minute data for our tickers
        for ticker in tickers:
            self.AddEquity(ticker, Resolution.Daily)
            
        self.models = {}  # store our Temporal CNN Models for each symbol
        
        self.window = RollingWindow[Slice](500)
        
        self.SetWarmup(500)
        
        # retrain our model periodically
        self.Train(self.DateRules.MonthStart('MSFT'), self.TimeRules.Midnight, self.TrainModel)
        self.months = self.Time.month
        
        self.training_complete = False
    
    
    def OnData(self, data):
        self.window.Add(data)
        
        if self.IsWarmingUp:
            return
        
        # this helps limit the number of trades
        if self.Time.day % 5 == 0:
            self.Trade()
       
    def TrainModel(self):
        '''Feed in past data to train our models'''
        
        self.months += 1
        
        # retrain every six months
        if self.months % 3 != 1:
            return
        
        self.Debug('Training in progress')
        
        try:
            # since RollingWindow is recent at top, we need to reverse it
            data = self.PandasConverter.GetDataFrame(self.window).iloc[::-1]
        except:
            return
        
        # iterate over our symbols and train each model
        for symbol in self.Securities.Keys:
            # if model doesn't exist, create one
            if symbol not in self.models:
                self.models[symbol] = MyTemporalCNN()
            # train our model
            self.models[symbol].Train(data.loc[symbol])
            
        self.training_complete = True
        
        self.Debug('Training completed')
    
    def Trade(self):
        '''Emit insights using predictions from models on future prices'''
        
        if not self.training_complete:
            return
        
        insights = []
        
        try:
            # since RollingWindow has the recent data at top and oldest data at the bottom, 
            #   we need to reverse it before getting the latest values
            df = self.PandasConverter.GetDataFrame(self.window).iloc[::-1][input_vars]  
        except:
            return
        
        # use recent data to forecast future price movements, 
        #   then emit insights based on predictions
        for symbol in self.Securities.Keys:
            
            symbol_df = df.loc[symbol].tail(15)
            prediction, confidence = self.models[symbol].Predict(symbol_df)
            
            # sometimes we get NaN values in our model prediction,
            #   which means the model is faulty so we don't want to make predictions.
            if not math.isnan(confidence) and confidence > .55:
                
                # since we are prediction the average price of the next five timesteps, choosing a 
                # random value of the future five time steps, over time, pseudo simulates average
                if prediction == Direction.UP:
                    insights.append(Insight.Price(symbol, timedelta(randint(1,5)), InsightDirection.Up, None, None, None, confidence))
                elif prediction == Direction.DOWN:
                    insights.append(Insight.Price(symbol, timedelta(randint(1,5)), InsightDirection.Down, None, None, None, confidence))
        
        # only emit insights if insights isn't empty
        if insights:
            self.EmitInsights(insights)