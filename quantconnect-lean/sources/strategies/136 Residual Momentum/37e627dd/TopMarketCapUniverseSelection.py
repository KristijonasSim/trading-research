from Selection.FundamentalUniverseSelectionModel import FundamentalUniverseSelectionModel

class TopMarketCapUniverseSelection(FundamentalUniverseSelectionModel):
    """
    This universe selection model refreshes monthly to contain the securities which
    have the largest market capitalizations.
    """
    def __init__(self, coarse_size = 400, fine_pct = 10):
        """
        Inputs:
         - coarse_size
            Number of securities to return from coarse selection
         - fine_pct
            Percentage of securities to return from fine selection. In decreasing order by 
            market cap
        """
        self.month = 0
        self.coarse_size = coarse_size
        self.fine_pct = fine_pct
        super().__init__(True)

    def SelectCoarse(self, algorithm, coarse):
        """
        Coarse universe selection is called each day at midnight.
        
        Inputs:
         - algorithm
            Algorithm instance running the backtest
         - coarse
            List of CoarseFundamental objects
            
        Returns the first `coarse_size` symbols that have fundamental data.
        """
        if self.month == algorithm.Time.month:
            return Universe.Unchanged
        return [ x.Symbol for x in coarse if x.HasFundamentalData ][:self.coarse_size]
        
    def FineSelectionFunction(self, algorithm, fine):
        """
        Fine universe selection is performed each day at midnight after `SelectCoarse`.
        
        Inputs:
         - algorithm
            Algorithm instance running the backtest
         - fine
            List of FineFundamental objects that result from `SelectCoarse` processing
        
        Returns a list of symbols for the `fine_pct`% of securities with the largest
        market capitalization.
        """
        self.month = algorithm.Time.month

        # Select the top `self.fine_pct`%, based on market cap
        sorted_mkt_cap = sorted(fine, key=lambda x: x.MarketCap, reverse=True)
        universe_size = int(len(sorted_mkt_cap) * (1 / self.fine_pct))
        return [ x.Symbol for x in sorted_mkt_cap[:universe_size] ]