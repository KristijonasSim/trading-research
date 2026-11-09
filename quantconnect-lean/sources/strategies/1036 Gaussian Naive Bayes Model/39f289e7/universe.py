from Selection.FundamentalUniverseSelectionModel import FundamentalUniverseSelectionModel

class BigTechUniverseSelectionModel(FundamentalUniverseSelectionModel):
    """
    This universe selection model contain the 10 largest securities in the technology sector.
    """
    
    def __init__(self, fine_size=10):
        """
        Input:
         - fine_size
            Maximum number of securities in the universe
        """
        self.fine_size = fine_size
        self.month = -1
        super().__init__(True)

    def SelectCoarse(self, algorithm, coarse):
        """
        Coarse universe selection is called each day at midnight.
        
        Input:
         - algorithm
            Algorithm instance running the backtest
         - coarse
            List of CoarseFundamental objects
            
        Returns the symbols that have fundamental data.
        """
        if algorithm.Time.month == self.month:
            return Universe.Unchanged
        return [ x.Symbol for x in coarse if x.HasFundamentalData ]
    
        
    def SelectFine(self, algorithm, fine):
        """
        Fine universe selection is performed each day at midnight after `SelectCoarse`.
        
        Input:
         - algorithm
            Algorithm instance running the backtest
         - fine
            List of FineFundamental objects that result from `SelectCoarse` processing
        
        Returns a list of symbols that are in the energy sector and have the largest market caps.
        """
        self.month = algorithm.Time.month
        
        tech_stocks = [ f for f in fine if f.AssetClassification.MorningstarSectorCode == MorningstarSectorCode.Technology ]
        sorted_by_market_cap = sorted(tech_stocks, key=lambda x: x.MarketCap, reverse=True)
        return [ x.Symbol for x in sorted_by_market_cap[:self.fine_size] ]