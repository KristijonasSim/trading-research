class EtfSmaAlphaModel(AlphaModel):
    def __init__(self, main_symbol, alt_symbol):
        self.main_symbol = main_symbol
        self.alt_symbol = alt_symbol
        self.day = -1
    
    def Update(self, algorithm, data):
        if self.day == algorithm.Time.day or not algorithm.IsMarketOpen(self.main_symbol):
            return []
            
        insights = []
        
        if data.ContainsKey(self.main_symbol):
            period = timedelta(1)
            if data[self.main_symbol].Close > self.sma.Current.Value:
                insights.append(Insight.Price(self.main_symbol, period, InsightDirection.Up))
                insights.append(Insight.Price(self.alt_symbol, period, InsightDirection.Flat))
            else:
                insights.append(Insight.Price(self.alt_symbol, period, InsightDirection.Up))
                insights.append(Insight.Price(self.main_symbol, period, InsightDirection.Flat))
        
        if insights:
            self.day = algorithm.Time.day
            
        return insights
        
    def OnSecuritiesChanged(self, algorithm, changed):
        if self.main_symbol in [added.Symbol for added in changed.AddedSecurities]:
            self.sma = algorithm.SMA(self.main_symbol, 200, Resolution.Hour)