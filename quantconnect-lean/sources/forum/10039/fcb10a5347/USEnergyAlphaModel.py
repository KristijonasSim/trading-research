from QuantConnect.Data.Custom.USEnergy import *
class USEnergyAlphaModel:
    
    def __init__(self, algorithm):
        self.energy = algorithm.AddData(USEnergy, USEnergy.Petroleum.UnitedStates.WeeklyGrossInputsIntoRefineries).Symbol
    
    def Update(self, algorithm, data):
        insights = []
        
        if not data.ContainsKey(self.energy):
            return insights

        energy_data = data.Get(USEnergy, self.energy)
            
        ## The U.S. Energy Information Administration (EIA) is a principal agency of the U.S. Federal Statistical System
        ## responsible for collecting, analyzing, and disseminating energy information to promote sound policymaking,
        ## efficient markets, and public understanding of energy and its interaction with the economy and the environment.
        ## EIA programs cover data on coal, petroleum, natural gas, electric, renewable and nuclear energy. EIA is part of the U.S. Department of Energy.
        
        ## Find more categories here: https://github.com/QuantConnect/Lean/blob/master/Common/Data/Custom/USEnergy/USEnergy.Category.cs
        
        return insights

    def OnSecuritiesChanged(self, algorithm, changes):
        # For instruction on how to use this method, please visit
        # https://www.quantconnect.com/docs/algorithm-framework/alpha-creation#Alpha-Creation-Good-Design-Patterns
        pass