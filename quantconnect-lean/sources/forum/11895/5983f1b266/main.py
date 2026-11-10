import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeClassifier
from AlgorithmImports import *

class MachineLearningAlgo(QCAlgorithm):
    
    def Initialize(self):
        
        self.SetStartDate(2021, 7, 2)  
        self.SetEndDate(2021, 7, 18)  
        self.SetCash(1000000)  
        
        self.SetBrokerageModel(BrokerageName.AlphaStreams)
        self.SetExecution(ImmediateExecutionModel())
        self.SetPortfolioConstruction(EqualWeightingPortfolioConstructionModel())

        self.lookback = 30
        
        symbol_list = ["BTCUSD","ETHUSD","LTCUSD","BALUSD","DAIUSD","KNCUSD",
                        "OXTUSD","RENUSD","UMAUSD","XRPUSD","ZRXUSD"]
        self.symbols = [self.AddCrypto(symbol, Resolution.Minute, Market.GDAX).Symbol for symbol in symbol_list]
        
        self.SetBenchmark("BTCUSD")

        self.AddAlpha(MachineLearningAlphaModel(self.Time, self.lookback))
                        
class MachineLearningAlphaModel(AlphaModel):
                        
    def __init__(self, Time, lookback):
        self.dataBySymbol = {}
        self.rebalanceTime = Time
        self.lookback = lookback
            
    def GetMLModel(self):
        self.MLModel = RidgeClassifier(random_state=18)   
        
    def Update(self, algorithm, data):
        insights = []
         
        if algorithm.Time < self.rebalanceTime: return []
        
        for symbol, symbolData in self.dataBySymbol.items():
            if data.Bars.ContainsKey(symbol) and not algorithm.IsWarmingUp:
                symbolData.Update(data, symbol)
                
                if symbolData.Close_rolling.IsReady:
                   
                    self.df = pd.DataFrame(symbolData.Close_rolling, columns=["Close"])[::-1].reset_index(drop=True)
                    
                    # calculate daily forward returns to be used to set Target / Signal
                    self.df['Return'] = np.log(self.df["Close"].shift(-1)/self.df["Close"]) 
                    self.df = self.df.dropna()
                    
                    # set Signal / Target
                    self.df["Signal"] = 0
                    self.df['Signal'][self.df["Return"] > 0] = 1
                    self.df['Signal'][self.df["Return"] < 0] = -1
                    
                    # set training data
                    self.X = self.df.drop(["Return", "Signal"], axis=1)
                    self.Y = self.df['Signal']
                    
                    # align feature set & signal 
                    self.Y, self.X = self.Y.align(self.X, axis=0, join='inner')
                    
                    self.X_train = self.X[:-1]
                    self.Y_train = self.Y[:-1]
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
                    self.Y_predict = self.MLModel.predict(self.X_today)
                    
                    # set insight based on predicted signal
                    # We cannot short crypto in GDAX
                    direction = InsightDirection.Up if self.Y_predict == 1 else InsightDirection.Flat
                    insights.append(Insight(symbol, timedelta(days=30), InsightType.Price, direction))
                
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
        algorithm.Consolidate(symbol, Resolution.Daily, lambda x: None)
        
        self.Close_rolling = RollingWindow[float](self.lookback)
        
        history = algorithm.History(symbol, self.lookback, Resolution.Daily)
        if not history.empty:
            for index, bar in history.loc[symbol].iterrows():
                self.Close_rolling.Add(bar.close)
        
    def Update(self, data, symbol):
            self.Close_rolling.Add(data[symbol].Close)