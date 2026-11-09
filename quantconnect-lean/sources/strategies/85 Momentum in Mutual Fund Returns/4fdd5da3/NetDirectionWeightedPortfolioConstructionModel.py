class NetDirectionWeightedPortfolioConstructionModel(PortfolioConstructionModel):
    """
    This PCM allocates its portfolio based on the net direction of insights for all the symbols. A symbol
    that has two active insights with an up direction will have twice the allocation than a symbol with
    only one. Additionally, a symbol that has an up active insight and a down active insight will have no
    position. This PCM doesn't liquidate securities when they are removed from the universe. If it's 
    removed from the universe, it will remain invested until all the security's insights expire.
    """
    insights = []
    month = -1
    
    def CreateTargets(self, algorithm, insights):
        """
        Called each time the alpha model emits a list of insights.
        
        Input:
         - algorithm
            Algorithm instance running the backtest
         - insights
            List of insights
            
        Returns a list of portfolio targets.
        """
        for i in insights:
            self.insights.append(i)
        
        if self.month == algorithm.Time.month:
            return []
        self.month = algorithm.Time.month

        # Remove insights of delisted symbols
        self.insights = [i for i in self.insights if algorithm.Securities[i.Symbol].IsTradable]
        
        # Classify insights
        active_insights = []
        expired_insights = []
        while (len(self.insights) > 0):
            insight = self.insights.pop()
            (active_insights if insight.IsActive(algorithm.UtcTime) else expired_insights).append(insight)
        self.insights = active_insights

        # Liquidate symbols that have expired insights with no active insights
        active_symbols = set([i.Symbol for i in active_insights])
        expired_symbols = set([i.Symbol for i in expired_insights])
        liquidate_symbols = expired_symbols.difference(active_symbols)
        portfolio_targets = [PortfolioTarget.Percent(algorithm, symbol, 0) for symbol in liquidate_symbols]
        
        # Get net direction by symbol and total number of directional insights
        net_direction_by_symbol, num_directional_insights = self.get_net_direction(active_insights)
        
        # Create portfolio targets for active symbols
        for symbol, net_direction in net_direction_by_symbol.items():
            percent = 0 if num_directional_insights == 0 else net_direction / num_directional_insights
            portfolio_targets.append( PortfolioTarget.Percent(algorithm, symbol, percent) )
        
        return portfolio_targets
        
        
    def get_net_direction(self, insights):
        """
        Determines the net direction of each symbol and the number of active directional insights.
        
        Input:
         - insights
            A list of active insights
        
        Returns a dictionary showing the net direction of each symbol, and the number of directional insights.
        """
        net_direction_by_symbol = {}
        num_directional_insights = 0
        
        for insight in insights:
            symbol = insight.Symbol
            direction = insight.Direction
            if symbol in net_direction_by_symbol:
                net_direction_by_symbol[symbol] += direction
            else:
                net_direction_by_symbol[symbol] = direction
                
            num_directional_insights += abs(direction)
        
        return net_direction_by_symbol, num_directional_insights