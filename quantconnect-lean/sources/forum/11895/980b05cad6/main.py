class StatArbAlgo(QCAlgorithm):
    
    def Initialize(self):
        
        self.SetStartDate(2016, 5, 2)  
        self.SetEndDate(2021, 7, 14)  
        self.SetCash(1000000)  
        self.AddEquity("SPY", Resolution.Minute)  
        self.SetBenchmark("SPY")
        self.SetBrokerageModel(BrokerageName.AlphaStreams)
        self.SetExecution(ImmediateExecutionModel())
        self.SetPortfolioConstruction(EqualWeightingPortfolioConstructionModel())
        
        symbols = [self.AddCrypto(symbol, Resolution.Minute).Symbol for symbol in ["BTCUSD","ETHUSD","LTCUSD"]]
        
        self.AddAlpha(StatArbAlphaModel(self.Time))
                        
class StatArbAlphaModel(AlphaModel):
                        
    def __init__(self, Time):
        self.dataBySymbol = {}
        self.rebalanceTime = Time
        
    def Update(self, algorithm, data):
        insights = []
        
        if algorithm.Time < self.rebalanceTime: return []
        
        for symbol, symbolData in self.dataBySymbol.items():
            if data.Bars.ContainsKey(symbol) and symbolData.IsReady():
                    
                if symbolData.slow.Current.Value < symbolData.fast.Current.Value:
                    insights.append(Insight(symbol, timedelta(days=30), InsightType.Price, InsightDirection.Up))
                else:
                    insights.append(Insight(symbol, timedelta(days=30), InsightType.Price, InsightDirection.Flat))
                    
        self.rebalanceTime = Expiry.EndOfDay(algorithm.Time)
                
        return insights
    
    def OnSecuritiesChanged(self, algorithm, changes):
        for change in changes.AddedSecurities:
            self.dataBySymbol[change.Symbol] = SymbolData(algorithm, change.Symbol)
            
        for change in changes.RemovedSecurities:
            if change.Symbol in self.dataBySymbol:
                del self.dataBySymbol[change.Symbol]
                
        
class SymbolData:
    def __init__(self, algorithm, symbol):
        
        algorithm.Consolidate(symbol, Resolution.Daily, self.DailyBarHandler)
        
        self.fast = algorithm.SMA(symbol, 5, Resolution.Daily, Field.Low)
        self.slow = algorithm.SMA(symbol, 60, Resolution.Daily, Field.Low)
        
        history = algorithm.History(symbol, 60, Resolution.Daily)
        
        if not history.empty:
            for index, tradebar in history.loc[symbol].iterrows():
                self.fast.Update(index, tradebar.low)
                self.slow.Update(index, tradebar.low)
            
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
            
    def IsReady(self):
        return self.fast.IsReady and self.slow.IsReady