from Selection.FundamentalUniverseSelectionModel import FundamentalUniverseSelectionModel

class AssetManagementUniverseSelection(FundamentalUniverseSelectionModel):
    """
    This universe selection model refreshes monthly to contain US securities in the asset management industry.
    """
    def __init__(self):
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
        if self.month == algorithm.Time.month:
            return Universe.Unchanged
            
        return [x.Symbol for x in coarse if x.HasFundamentalData]
        
    def SelectFine(self, algorithm, fine):
        """
        Fine universe selection is performed each day at midnight after `SelectCoarse`.
        
        Input:
         - algorithm
            Algorithm instance running the backtest
         - fine
            List of FineFundamental objects that result from `SelectCoarse` processing
        
        Returns a list of symbols that are in the asset management industry.
        """
        self.month = algorithm.Time.month
        
        return [f.Symbol for f in fine if f.AssetClassification.MorningstarIndustryCode == MorningstarIndustryCode.AssetManagement]