from ResidualMomentumAlpha import ResidualMomentumAlphaModel
from TopMarketCapUniverseSelection import TopMarketCapUniverseSelection

class ResidualMomentumAlgorithm(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2016, 1, 1)
        self.SetCash(100000)
        
        self.SetUniverseSelection(TopMarketCapUniverseSelection(100))
        self.UniverseSettings.Resolution = Resolution.Daily
        
        self.AddAlpha(ResidualMomentumAlphaModel(self))
        
        self.SetPortfolioConstruction(EqualWeightingPortfolioConstructionModel())
        
        self.SetExecution(ImmediateExecutionModel())