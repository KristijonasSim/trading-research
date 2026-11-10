class PriceActionLSSPY(QCAlgorithm):
    
    def Initialize(self):
        
        self.SetStartDate(2016, 6, 1)  
        self.SetEndDate(2021, 7, 12)  
        self.SetCash(1000000)  
        self.AddEquity("SPY", Resolution.Minute)  
        self.SetBenchmark("SPY")
        self.SetBrokerageModel(BrokerageName.AlphaStreams)
        self.SetExecution(ImmediateExecutionModel())
        self.SetPortfolioConstruction(EqualWeightingPortfolioConstructionModel())
        
        symbol = [Symbol.Create("SPY", SecurityType.Equity, Market.USA)]
        self.AddUniverseSelection(ManualUniverseSelectionModel(symbol))
        
        self.AddAlpha(PriceActionLSSPYAlphaModel(self, "SPY"))
        
        
class PriceActionLSSPYAlphaModel(AlphaModel):
    
    def __init__(self, algorithm, tkr):
        self.period = timedelta(days=1)
        self.symbol = tkr
        self.symbolData = SymbolData(algorithm)
    
    def Update(self, algorithm, data):
        insights = []
        
        HO = 0.0
        OL = 0.0
        
        if self.symbolData.Updated:
            Open  = self.symbolData.open
            High  = self.symbolData.high
            Low   = self.symbolData.low
            Close = self.symbolData.close
            
            HO = High -  Open
            OL = Open - Low
            HC = High - Close
            CL = Close - Low
            
            if Close > Open:
                if HO > OL:
                    insights.append(Insight(self.symbol, self.period, InsightType.Price, InsightDirection.Up, 1, None))
                
            if Close < Open:
                if HO < OL:
                    insights.append(Insight(self.symbol, self.period, InsightType.Price, InsightDirection.Up, 1, None))
                if HO > OL:
                    insights.append(Insight(self.symbol, self.period, InsightType.Price, InsightDirection.Down, 1, None))
                if HO == OL:
                    insights.append(Insight(self.symbol, self.period, InsightType.Price, InsightDirection.Up, 1, None))
                    
            if Close == Open:
                if HO < OL:
                    insights.append(Insight(self.symbol, self.period, InsightType.Price, InsightDirection.Up, 1, None))
                if HO > OL:
                    insights.append(Insight(self.symbol, self.period, InsightType.Price, InsightDirection.Down, 1, None))
                if HO == OL:
                    insights.append(Insight(self.symbol, self.period, InsightType.Price, InsightDirection.Flat, 1, None))
                    
            self.symbolData.Updated = False
                
        return insights
        
    def OnSecuritiesChanged(self, algorithm, changes):
        self.changes =  changes
        
    
class SymbolData:
    
    def __init__(self, algorithm):
        algorithm.Consolidate("SPY", Resolution.Daily, self.DailyBarHandler)
        
        self.open = 0
        self.close = 0
        self.high = 0
        self.low = 0
        self.Updated = False
        
        
    def DailyBarHandler(self, consolidated):
        self.open = consolidated.Open
        self.close = consolidated.Close
        self.high = consolidated.High
        self.low = consolidated.Low
        self.Updated = True
        
