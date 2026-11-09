import statsmodels.api as sm
import pandas as pd

class ResidualMomentum:
    """
    This class manages a rolling window of the previous `num_train_months` months. It gathers
    its data via a consolidator into monthly bars. Every month, a regression model is fit to the 
    residual returns over the previous `num_train_months` months (t-`num_train_months` - t-1). 
    It calculates a score based on the residual returns over the previous `num_test_months` 
    months (excluding the lastest month) (t-`num_test_months` - t-2). 
    """
    
    def __init__(self, symbol, monthly_returns, algorithm, alpha, close, num_train_months, num_test_months, min_price):
        """
        Inputs:
         - symbol
            The symbol to apply the indicator on
         - monthly_returns
            Trailing monthly returns for the symbol
         - algorithm
            Algorithm instance running the backtest
         - alpha
            Refrence to the ResidualMomentumAlphaModel.
         - close
            Closing price of the latest full month
         - num_train_months
            Number of months to train the regression model (> 2)
         - num_test_months
            Number of months to test the regression model (1 < num_test_months < num_train_months)
         - min_price
            Minimum price a security needs to be considered in the rebalance (>= 0)
        """
        self.Symbol = symbol
        self.monthly_returns = monthly_returns
        self.monthly_returns.columns = ['m_return']
        self.score = None
        self.alpha = alpha
        self.num_train_months = num_train_months
        self.num_test_months = num_test_months
        self.min_price = min_price
        
        # Setup monthly consolidation
        self.consolidator = TradeBarConsolidator(self.CustomMonthly)
        self.consolidator.DataConsolidated += self.CustomMonthlyHandler
        algorithm.SubscriptionManager.AddConsolidator(symbol, self.consolidator)
        
        # Set the initial score
        self.update_score(close)
    
    def dispose(self, algorithm):
        """
        Removes the monthly conoslidator.
        
        Inputs
         - algorithm
            The QCAlgorithm object
        """
        algorithm.SubscriptionManager.RemoveConsolidator(self.Symbol, self.consolidator)
    
    def update_score(self, close):
        """
        Updates the score for the Residual Momentum indicator.
        
        Inputs
         - close
            The closing price of the latest full month
        """
        # If current price < $`min_price`, don't bother calculating the score
        if close < self.min_price:
            self.score = None
            return
        
        # Fit regression model over the previous `num_train_months` months
        X = self.alpha.fama_french_factors
        X = sm.add_constant(X)
        y = self.monthly_returns.values
        model = sm.OLS(y, X).fit()

        # Calculate score on the previous `num_test_months` months, excluding the most recent month
        # (t-`num_test_months` - t-2)
        pred = model.predict(X.iloc[-self.num_test_months:-1])
        residual_returns = self.monthly_returns.iloc[-self.num_test_months:-1].values - pred.values
        self.score = residual_returns.sum() / residual_returns.std()

    def CustomMonthly(self, dt):
        '''Custom Monthly Func'''
        start = dt.replace(day=1).date()
        end = dt.replace(day=28) + timedelta(4)
        end = (end - timedelta(end.day-1)).date()
        return CalendarInfo(start, end - start)

    def CustomMonthlyHandler(self, sender, consolidated):
        """
        Updates the monthly returns rolling window and the score.
        
        Inputs
         - sender
            Function calling the consolidator
         - consolidated
            Tradebar representing the latest completed month
        """
        # Append to monthly returns rolling window DataFrame
        monthly_return = (consolidated.Close - consolidated.Open) / consolidated.Close
        row = pd.DataFrame({'m_return' : [monthly_return]}, index=[consolidated.Time])
        self.monthly_returns = self.monthly_returns.append(row).iloc[-self.num_train_months:]

        self.update_score(consolidated.Close)