import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeClassifier
from AlgorithmImports import *

class MachineLearningAlgo(QCAlgorithm):
    
    def Initialize(self):
        
        self.SetStartDate(2016, 6, 2)  
        self.SetEndDate(2021, 7, 18)  
        self.SetCash(1000000)  
        # self.AddEquity("SPY", Resolution.Daily)  
        # self.SetBenchmark("SPY")
        self.SetBrokerageModel(BrokerageName.AlphaStreams)
        self.SetExecution(ImmediateExecutionModel())
        self.SetPortfolioConstruction(EqualWeightingPortfolioConstructionModel())

        self.lookback = 30
        
        symbol_list = ["BTCUSD","ETHUSD","LTCUSD","BALUSD","DAIUSD","KNCUSD",
                        "OXTUSD","RENUSD","UMAUSD","XRPUSD","ZRXUSD"]
        self.symbols = [self.AddCrypto(symbol, Resolution.Minute, Market.GDAX).Symbol for symbol in symbol_list]
        
        self.SetBenchmark("BTCUSD")
        
        self.SetWarmup(self.lookback)

        self.AddAlpha(MachineLearningAlphaModel(self.Time, self.lookback))
                        
class MachineLearningAlphaModel(AlphaModel):
                        
    def __init__(self, Time, lookback):
        self.dataBySymbol = {}
        self.rebalanceTime = Time
        self.lookback = lookback
            
    def GetMLModel(self):
        self.MLModel = 0
        self.MLModel = RidgeClassifier(random_state=18)   
        
    def Update(self, algorithm, data):
        insights = []
         
        if algorithm.Time < self.rebalanceTime: return []
        
        for symbol, symbolData in self.dataBySymbol.items():
            if data.Bars.ContainsKey(symbol) and not algorithm.IsWarmingUp:
                symbolData.Update(data, symbol)
                
                if symbolData.Close_rolling.IsReady:
                   
                    df1 = pd.DataFrame(symbolData.Close_rolling, columns=["Close"]).reset_index(drop=True)
                    
                    self.df = pd.concat([df1], axis=1)
                    
                    # calculate daily forward returns to be used to set Target / Signal
                    self.df['Return'] = np.log(self.df["Close"].shift(-1)/self.df["Close"]) 
                    self.df = self.df.dropna()
                    
                    # set Signal / Target
                    self.df["Signal"] = 0
                    self.df.loc[self.df["Return"] > 0, "Signal"] = 1
                    self.df.loc[self.df["Return"] < 0, "Signal"] = -1
                    
                    # set training data
                    self.X = self.df.drop(["Return", "Signal"], axis=1)
                    self.Y = self.df['Signal']
                    
                    # align feature set & signal 
                    self.Y, self.X = self.Y.align(self.X, axis=0, join='inner')
                    
                    self.X_train = self.X[:-1]
                    self.Y_train = self.Y[:-1]
                    self.X_train.replace([np.inf, -np.inf], np.nan, inplace=True)
                    self.Y_train.replace([np.inf, -np.inf], np.nan, inplace=True)
                    
                    drops = []
                    [drops.append(i) for i in range(self.X_train.shape[0]) if self.X_train.iloc[i].isnull().any()]
                    [drops.append(i) for i in range(self.Y_train.shape[0]) if self.Y_train.iloc[i] == np.nan and i not in drops]
                    self.X_train.drop(index=self.X_train.index[drops], inplace=True)
                    self.Y_train.drop(index=self.Y_train.index[drops], inplace=True)
                    if self.X_train.empty or self.Y_train.empty: return []
                    
                    # fit / train ML model
                    self.GetMLModel()
                    self.MLModel.fit(self.X_train, self.Y_train)
                    
                    # predict next day signal using today's values of feature set
                    self.X_today = self.X.iloc[-1]
                    # self.X_today is Series, so convert to numpy array
                    self.X_today = self.X_today.to_numpy()
                    # reshape self.X_today because it only has 1 day's sample
                    self.X_today = self.X_today.reshape(1,-1)
                    
                    # Y_predict will take predicted signal
                    self.Y_predict = self.Y.iloc[-1]
                    try:
                        self.Y_predict = self.MLModel.predict(self.X_today)
                    except: return []
                    
                    # set insight based on predicted signal
                    if self.Y_predict == 1:
                        insights.append(Insight(symbol, timedelta(days=30), InsightType.Price, InsightDirection.Up))
                    elif self.Y_predict == -1:
                        insights.append(Insight(symbol, timedelta(days=30), InsightType.Price, InsightDirection.Flat))
                    else:
                        insights.append(Insight(symbol, timedelta(days=30), InsightType.Price, InsightDirection.Flat))
                
        self.rebalanceTime = Expiry.EndOfDay(algorithm.Time)
                
        return insights
    
    def OnSecuritiesChanged(self, algorithm, changes):
        for change in changes.AddedSecurities:
            self.dataBySymbol[change.Symbol] = SymbolData(algorithm, change.Symbol, self.lookback)
            
        for change in changes.RemovedSecurities:
            if change.Symbol in self.dataBySymbol:
                del self.dataBySymbol[change.Symbol]
        
class SymbolData:
    def __init__(self, algorithm, symbol, lookback):
        
        self.lookback = lookback
        algorithm.Consolidate(symbol, Resolution.Daily, self.DailyBarHandler)
        
        self.Close_rolling = RollingWindow[float](self.lookback)

        # self.fast = algorithm.SMA(symbol, 5, Resolution.Daily, Field.Low)
        # self.slow = algorithm.SMA(symbol, 60, Resolution.Daily, Field.High)
        
        history = algorithm.History(symbol, self.lookback, Resolution.Daily)
        
        if not history.empty:
            # for index, tradebar in history.loc[symbol].iterrows():
            #     self.fast.Update(index, tradebar.low)
            #     self.slow.Update(index, tradebar.high)
            
            last_row = history.loc[symbol].iloc[-1]
            self.open = last_row.open
            self.close = last_row.close
            self.high = last_row.high
            self.low = last_row.low
        
    def DailyBarHandler(self, consolidated):
        self.open = consolidated.Open
        self.close = consolidated.Close
        self.high = consolidated.High
        self.low = consolidated.Low
        
    def Update(self, data, symbol):
            self.Close_rolling.Add(data[symbol].Close)
            
    # def IsReady(self):
    #     return self.fast.IsReady and self.slow.IsReady