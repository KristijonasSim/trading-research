class IntradayMomentumAlphaModel(AlphaModel):
    """
    This class emits insights to take positions for the last `return_bar_count` minutes 
    of the day in the direction of the return for the first `return_bar_count` minutes of the day.
    """
    intraday_momentum_by_symbol = {}
    sign = lambda _, x: int(x and (1, -1)[x < 0])
    
    def __init__(self, algorithm, return_bar_count = 30):
        """
        Input:
         - return_bar_count
            Number of minutes to calculate the morning return over and the number of minutes
            to hold before the close (0 < return_bar_count < 195)
        """
        if return_bar_count <= 0 or return_bar_count >= 195:
            algorithm.Quit(f"Requirement violated:  0 < return_bar_count < 195")
        self.return_bar_count = return_bar_count
    
    
    def Update(self, algorithm, slice):
        """
        Called each time our alpha model receives a new data slice.
        
        Input:
         - algorithm
            Algorithm instance running the backtest
         - data
            A data structure for all of an algorithm's data at a single time step
        
        Returns a list of Insights to the portfolio construction model
        """
        insights = []
        
        for symbol, intraday_momentum in self.intraday_momentum_by_symbol.items():
            if slice.ContainsKey(symbol) and slice[symbol] is not None:
                intraday_momentum.bars_seen_today += 1
        
                # End of the morning return
                if intraday_momentum.bars_seen_today == self.return_bar_count:
                    intraday_momentum.morning_return = (slice[symbol].Close - intraday_momentum.yesterdays_close) / intraday_momentum.yesterdays_close
                
                ## Beginning of the close
                next_close_time = intraday_momentum.exchange.Hours.GetNextMarketClose(slice.Time, False)
                mins_to_close = int((next_close_time - slice.Time).total_seconds() / 60)
                
                if mins_to_close == self.return_bar_count + 1:
                    insight = Insight.Price(intraday_momentum.symbol, 
                                            next_close_time, 
                                            self.sign(intraday_momentum.morning_return))
                    insights.append(insight)
                    continue
                
                # End of the day
                if not intraday_momentum.exchange.DateTimeIsOpen(slice.Time):
                    intraday_momentum.yesterdays_close = slice[symbol].Close
                    intraday_momentum.bars_seen_today = 0
        
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
            self.intraday_momentum_by_symbol[security.Symbol] = IntradayMomentum(security, algorithm)
            
        for security in changes.RemovedSecurities:
            self.intraday_momentum_by_symbol.pop(security.Symbol, None)
            

class IntradayMomentum:
    """
    This class manages the data used for calculating the morning return of a security.
    """
    def __init__(self, security, algorithm):
        """
        Input:
         - security
            The security to trade
         - algorithm
            Algorithm instance running the backtest
        """
        self.symbol = security.Symbol
        self.exchange = security.Exchange
        
        self.bars_seen_today = 0
        self.yesterdays_close = algorithm.History(self.symbol, 1, Resolution.Daily).loc[self.symbol].close[0]
        self.morning_return = 0