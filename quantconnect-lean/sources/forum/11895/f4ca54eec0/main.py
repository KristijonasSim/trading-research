class PriceActionLSSPY(QCAlgorithm):
    
    def Initialize(self):
        
        self.SetStartDate(2016, 6, 1)  
        self.SetEndDate(2021, 7, 12)  
        self.SetCash(1000000)  
        self.AddEquity("SPY", Resolution.Daily)  
        self.SetBenchmark("SPY")
        self.SetBrokerageModel(BrokerageName.AlphaStreams)
        self.SetExecution(ImmediateExecutionModel())
        self.SetPortfolioConstruction(EqualWeightingPortfolioConstructionModel())
        
        symbol = [Symbol.Create("SPY", SecurityType.Equity, Market.USA)]
        self.AddUniverseSelection(ManualUniverseSelectionModel(symbol))
        
        self.AddAlpha(PriceActionLSSPYAlphaModel("SPY"))
        
        
class PriceActionLSSPYAlphaModel(AlphaModel):
    
    def __init__(self, tkr):
        self.period = timedelta(1)
        self.symbol = tkr
    
    def Update(self, algorithm,data):
        insights = []
        
        HO = 0.0
        OL = 0.0
        
        if data.ContainsKey(self.symbol):
            Open  = data[self.symbol].Open
            High  = data[self.symbol].High
            Low   = data[self.symbol].Low
            Close = data[self.symbol].Close
            Volume = data[self.symbol].Volume
            
            HO = High -  Open
            OL = abs(Open - Low)
            HC = High - Close
            CL = abs(Close - Low)
            
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
                
        return insights
        
    def OnSecuritiesChanged(self, algorithm, changes):
        self.changes =  changes
    
