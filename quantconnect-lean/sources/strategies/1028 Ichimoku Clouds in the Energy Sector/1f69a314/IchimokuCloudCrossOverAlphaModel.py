from QuantConnect.Indicators import IchimokuKinkoHyo

class IchimokuCloudCrossOverAlphaModel(AlphaModel):
    """
    This class emits insights to hold a long (short) position after the chikou line of a
    security's Ichimoku Cloud crosses over (under) the top (bottom) of the cloud.
    """
    symbol_data_by_symbol = {}
    
    def Update(self, algorithm, data):
        """
        Called each time our alpha model receives a new data slice.
        
        Input:
         - algorithm
            Algorithm instance running the backtest
         - data
            A data structure for all of an algorithm's data at a single time step
        
        Returns a list of Insights to the portfolio construction model.
        """
        insights = []

        for symbol, symbol_data in self.symbol_data_by_symbol.items():
            if not data.ContainsKey(symbol) or data[symbol] is None:
                continue
            
            # Update indicator with the latest TradeBar
            symbol_data.ichimoku.Update(data[symbol])
            
            # Determine insight direction
            current_location = symbol_data.get_location()
            if symbol_data.previous_location is not None: # Indicator is ready
                if symbol_data.previous_location != 1 and current_location == 1:
                    symbol_data.direction = InsightDirection.Up
                if symbol_data.previous_location != -1 and current_location == -1:
                    symbol_data.direction = InsightDirection.Down
            
            symbol_data.previous_location = current_location
            
            # Emit insight
            if symbol_data.direction:
                insight = Insight.Price(symbol, timedelta(days=1), symbol_data.direction)
                insights.append(insight)
        
        return insights
        
    def OnSecuritiesChanged(self, algorithm, changes):
        """
        Called each time our universe has changed.
        
        Input:
         - algorithm
            Algorithm instance running the backtest
         - changes
            The additions and subtractions to the algorithm's security subscriptions
        """
        for security in changes.AddedSecurities:
            symbol = security.Symbol
            self.symbol_data_by_symbol[symbol] = SymbolData(symbol, algorithm)
        
        for security in changes.RemovedSecurities:
            self.symbol_data_by_symbol.pop(security.Symbol, None)


class SymbolData:
    """
    This class is used to store information on each security in the universe. It is
    responsible for initializing and warming up the Ichimoku indicator and determining
    the position of the chikou line in respect to the cloud.
    """
    previous_location = None
    direction = None
    
    def __init__(self, symbol, algorithm):
        """
        Input:
         - symbol
            Symbol of the security
         - algorithm
            Algorithm instance running the backtest
        """
        # Create Ichimoku indicator
        self.ichimoku = IchimokuKinkoHyo()

        # Warm up indicator
        history = algorithm.History(symbol, self.ichimoku.WarmUpPeriod + 1, Resolution.Daily).loc[symbol]
        for idx, row in history.iterrows():
            if self.ichimoku.IsReady:
                self.previous_location = self.get_location()
            
            tradebar = TradeBar(idx, symbol, row.open, row.high, row.low, row.close, row.volume)
            self.ichimoku.Update(tradebar)
        
    def get_location(self):
        """
        Determines the location of the chikou line in respect to the cloud.
        
        Returns an integer in the interval [-1, 1], representing the location. 
        1 => Above cloud; 0 => Inside cloud; -1 => Below cloud
        """
        chikou = self.ichimoku.Chikou.Current.Value
        
        senkou_span_a = self.ichimoku.SenkouA.Current.Value
        senkou_span_b = self.ichimoku.SenkouB.Current.Value
        cloud_top = max(senkou_span_a, senkou_span_b)
        cloud_bottom = min(senkou_span_a, senkou_span_b)
        
        if chikou > cloud_top:
            return 1    # Above cloud
        if chikou < cloud_bottom:
            return -1   # Below cloud
            
        return 0        # Inside cloud