from Selection.FundamentalUniverseSelectionModel import FundamentalUniverseSelectionModel

class DrugManufacturerUniverseSelection(FundamentalUniverseSelectionModel):
    """
    This universe selection model contain securities in the drug manufacturing
    industry group.
    """
    def __init__(self, coarse_size=2500, fine_size=50):
        self.coarse_size = coarse_size
        self.fine_size = fine_size
        super().__init__(True)

    def SelectCoarse(self, algorithm, coarse):
        """
        Coarse universe selection is called each day at midnight.
        
        Input:
         - algorithm
            Algorithm instance running the backtest
         - coarse
            List of CoarseFundamental objects
            
        Returns the symbols that have fundamental data and the largest dollar volume.
        """
        has_fundamentals = [c for c in coarse if c.HasFundamentalData]
        sorted_by_dollar_volume = sorted(has_fundamentals, key=lambda c: c.DollarVolume, reverse=True)
        return [ x.Symbol for x in sorted_by_dollar_volume[:self.coarse_size] ]
    
        
    def SelectFine(self, algorithm, fine):
        """
        Fine universe selection is performed each day at midnight after `SelectCoarse`.
        
        Input:
         - algorithm
            Algorithm instance running the backtest
         - fine
            List of FineFundamental objects that result from `SelectCoarse` processing
        
        Returns a list of symbols that are in the drug manufacturing industry and have
        the greatest PE ratios.
        """
        drug_manufacturers = [f for f in fine if f.AssetClassification.MorningstarIndustryGroupCode == MorningstarIndustryGroupCode.DrugManufacturers]
        sorted_by_pe = sorted(drug_manufacturers, key=lambda f: f.ValuationRatios.PERatio, reverse=True)
        return [ x.Symbol for x in sorted_by_pe[:self.fine_size] ]