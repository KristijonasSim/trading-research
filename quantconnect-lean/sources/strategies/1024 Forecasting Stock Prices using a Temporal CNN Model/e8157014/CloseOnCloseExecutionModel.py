class CloseOnCloseExecutionModel(ExecutionModel):
    """
    Provides an implementation of IExecutionModel that immediately submits a market order to achieve 
    the desired portfolio targets and an associated market on close order.
    """

    def __init__(self):
        self.targetsCollection = PortfolioTargetCollection()
        self.invested_symbols = []

    def Execute(self, algorithm, targets):
        """
        Immediately submits orders for the specified portfolio targets.
        Input:
         - algorithm
            Algorithm instance running the backtest
         - targets
            The portfolio targets to be ordered
        """
        # for performance we check count value, OrderByMarginImpact and ClearFulfilled are expensive to call
        self.targetsCollection.AddRange(targets)
        if self.targetsCollection.Count > 0:
            for target in self.targetsCollection.OrderByMarginImpact(algorithm):
                # calculate remaining quantity to be ordered
                quantity = OrderSizing.GetUnorderedQuantity(algorithm, target)
                if quantity == 0:
                    continue
                
                algorithm.MarketOrder(target.Symbol, quantity)
                algorithm.MarketOnCloseOrder(target.Symbol, -quantity)
                
            self.targetsCollection.ClearFulfilled(algorithm)