from datetime import datetime

class MonthlyPortfolioConstructionModel(PortfolioConstructionModel):

    def __init__(self):
        self.month = datetime.min

    def CreateTargets(self, algorithm, insights):
        if self.month == algorithm.Time.month:
            return []
        
        targets = []
        self.month = algorithm.Time.month
        if len(insights) != 0:
            percent = 1 / len(insights)
            for insight in insights:
                target = PortfolioTarget.Percent(algorithm, insight.Symbol, insight.Direction * percent)
                if not target is None:
                    targets.append(target)
        return targets