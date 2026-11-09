import pandas as pd
from sklearn.naive_bayes import GaussianNB
from dateutil.relativedelta import relativedelta

from symbol_data import SymbolData

class GaussianNaiveBayesAlphaModel(AlphaModel):
    """
    Emits insights in the direction of the prediction made by the SymbolData objects.
    """
    symbol_data_by_symbol = {}
    new_securities = False

    def Update(self, algorithm, data):
        """
        Called each time the alpha model receives a new data slice.
        
        Input:
         - algorithm
            Algorithm instance running the backtest
         - data
            A data structure for all of an algorithm's data at a single time step
        
        Returns a list of Insights to the portfolio construction model.
        """
        if self.new_securities:
            self.train()
            self.new_securities = False
        
        tradable_symbols = {}
        features = [[]]
        
        for symbol, symbol_data in self.symbol_data_by_symbol.items():
            if data.ContainsKey(symbol) and data[symbol] is not None and symbol_data.IsReady:
                tradable_symbols[symbol] = symbol_data
                features[0].extend(symbol_data.features_by_day.iloc[-1].values)

        insights = []
        if len(tradable_symbols) == 0:
            return []
            
        weight = 1 / len(tradable_symbols)
        for symbol, symbol_data in tradable_symbols.items():
            direction = symbol_data.model.predict(features)
            if direction:
                insights.append(Insight.Price(symbol, data.Time + timedelta(days=1, seconds=-1), 
                                              direction, None, None, None, weight))

        return insights
        
        
    def OnSecuritiesChanged(self, algorithm, changes):
        """
        Called each time the universe has changed.
        
        Input:
         - algorithm
            Algorithm instance running the backtest
         - changes
            The additions and removals of the algorithm's security subscriptions
        """
        for security in changes.AddedSecurities:
            self.symbol_data_by_symbol[security.Symbol] = SymbolData(security, algorithm)
            
            
        for security in changes.RemovedSecurities:
            symbol_data = self.symbol_data_by_symbol.pop(security.Symbol, None)
            if symbol_data:
                symbol_data.dispose()
        
        self.new_securities = True
    
    
    def train(self):
        """
        Trains the Gaussian Naive Bayes classifier model.
        """
        features = pd.DataFrame()
        labels_by_symbol = {}
        
        for symbol, symbol_data in self.symbol_data_by_symbol.items():
            if symbol_data.IsReady:
                features = pd.concat([features, symbol_data.features_by_day], axis=1)
                labels_by_symbol[symbol] = symbol_data.labels_by_day
        
        for symbol, symbol_data in self.symbol_data_by_symbol.items():
            if symbol_data.IsReady:
                symbol_data.model = GaussianNB().fit(features.iloc[:-2], labels_by_symbol[symbol])