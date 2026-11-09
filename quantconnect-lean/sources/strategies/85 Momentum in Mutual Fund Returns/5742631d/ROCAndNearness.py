import pandas as pd
from dateutil.relativedelta import relativedelta

class ROCAndNearness:
    """
    This class manages the historical data for a symbol and calculates the ROC and Nearness factors.
    """
    def __init__(self, symbol, algorithm, roc_lookback_months, nearness_lookback_months):
        """
        Input:
         - symbol
            Symbol to apply this indicator to
         - algorithm
            Algorithm instance running the backtest
         - roc_lookback_months
            Number of trailing months to calculate the rate of change over (> 0)
         - nearness_lookback_months
            Number of trailing months to calculate the nearness factor over (> 0)
        """
        self.symbol = symbol
        self.algorithm = algorithm
        self.roc_lookback_months = roc_lookback_months
        self.nearness_lookback_months = nearness_lookback_months
        self.lookback_months = max(roc_lookback_months, nearness_lookback_months)

        # Warm up history
        self.warm_up_history(symbol, algorithm)

        # Setup indicator consolidator
        self.consolidator = TradeBarConsolidator(timedelta(1))
        self.consolidator.DataConsolidated += self.CustomDailyHandler
        algorithm.SubscriptionManager.AddConsolidator(self.symbol, self.consolidator)
        
    def CustomDailyHandler(self, sender, consolidated):
        """
        Updates the rolling lookback window with the latest data.
        
        Inputs
         - sender
            Function calling the consolidator
         - consolidated
            Tradebar representing the latest completed trading day
        """
        # Add new data point to history
        if consolidated.Time not in self.history.index:
            row = pd.DataFrame({'open': consolidated.Open, 'high': consolidated.High, 'close': consolidated.Close},
                                index=[consolidated.Time])
            self.history = self.history.append(row)

        # Remove expired history
        start_lookback = Expiry.EndOfMonth(self.algorithm.Time) - relativedelta(months=self.lookback_months + 1)
        self.history = self.history[self.history.index >= start_lookback]
        
    def dispose(self):
        """
        Removes the monthly conoslidator.
        """
        self.algorithm.SubscriptionManager.RemoveConsolidator(self.symbol, self.consolidator)
        
    def warm_up_history(self, symbol, algorithm):
        """
        Warms up the `historical_prices_by_symbol` dictionary with historical data as far back as the 
        earliest lookback window.
        
        Input:
         - symbol
            Symbol that needs history warm up
         - algorithm
            Algorithm instance running the backtest
        """
        # Get the historical data
        start_lookback = Expiry.EndOfMonth(algorithm.Time) - relativedelta(months=self.lookback_months + 1)
        history = algorithm.History([symbol], start_lookback, algorithm.Time, Resolution.Daily)
        
        # Rollback history timestamp by 1 day to ensure accurate monthly ROC values
        if history.shape[0] > 0:
            history = history.unstack(level=0)
            history = history.set_index(history.index.map(lambda x: x - timedelta(days=1))).stack().swaplevel()
        
        self.history = history.loc[symbol, ['open', 'high', 'close']] if symbol in history.index else pd.DataFrame()
    
    @property
    def IsReady(self):
        """
        Boolean to signal if the symbol has sufficient history to fill the ROC lookback window.
        """
        return self.get_lookback(self.roc_lookback_months).shape[0] > 1
    
    @property
    def roc(self):
        """
        Calculates the rate of change over the ROC lookback window.
        """
        lookback = self.get_lookback(self.roc_lookback_months)
        start_price = lookback.iloc[0].open
        end_price = lookback.iloc[-1].close
        return (end_price - start_price) / start_price 
        
    @property
    def nearness(self):
        """
        Calculates how close the closing price of the nearness lookback window was to its maximum price.
        """
        lookback = self.get_lookback(self.nearness_lookback_months)
        return lookback.iloc[-1].close / lookback.high.max()
    
    def get_lookback(self, num_months):
        """
        Slices the historical data into the trailing `num_months` months.
        
        Input:
         - num_months
            Number of trailing months in the lookback window
        
        Returns DataFrame containing data for the lookback window.
        """
        start_lookback = Expiry.EndOfMonth(self.algorithm.Time) - relativedelta(months=num_months + 1)
        end_lookback = Expiry.EndOfMonth(self.algorithm.Time) - relativedelta(months=1)
        
        return self.history[(self.history.index >= start_lookback) & (self.history.index < end_lookback)]