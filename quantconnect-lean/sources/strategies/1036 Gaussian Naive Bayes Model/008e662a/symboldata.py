import numpy as np
import pandas as pd

class SymbolData:
    """
    This class stores data unique to each security in the universe.
    """

    def __init__(self, security, algorithm, num_days_per_sample=4, num_samples=100):
        """
        Input:
         - security
            Security object for the security
         - algorithm
            The algorithm instance running the backtest
         - num_days_per_sample
            The number of open-close intraday returns for each sample
         - num_samples
            The number of samples to train the model
        """
        self.exchange = security.Exchange
        self.symbol = security.Symbol
        self.algorithm = algorithm
        self.num_days_per_sample = num_days_per_sample
        self.num_samples = num_samples 
        self.previous_open = 0
        self.model = None
        
        # Setup consolidators
        self.consolidator = TradeBarConsolidator(timedelta(days=1))
        self.consolidator.DataConsolidated += self.CustomDailyHandler
        algorithm.SubscriptionManager.AddConsolidator(self.symbol, self.consolidator)
        
        # Warm up training set
        self.roc_window = np.array([])
        self.labels_by_day = pd.Series()
        
        data = {f'{self.symbol.ID}_(t-{i})' : [] for i in range(1, num_days_per_sample + 1)}
        self.features_by_day = pd.DataFrame(data)
        
        lookback = num_days_per_sample + num_samples + 1 
        history = algorithm.History(self.symbol, lookback, Resolution.Daily)
        if history.empty or 'close' not in history:
            algorithm.Log(f"Not enough history for {self.symbol} yet")    
            return
        
        history = history.loc[self.symbol]
        history['open_close_return'] = (history.close - history.open) / history.open
        
        start = history.shift(-1).open
        end = history.shift(-2).open
        history['future_return'] = (end - start) / start
        
        for day, row in history.iterrows():
            self.previous_open = row.open
            if self.update_features(day, row.open_close_return) and not pd.isnull(row.future_return):
                row = pd.Series([np.sign(row.future_return)], index=[day])
                self.labels_by_day = self.labels_by_day.append(row)[-self.num_samples:]
    
    
    def update_features(self, day, open_close_return):
        """
        Updates the training data features.
        
        Inputs
         - day
            Timestamp of when we're aware of the open_close_return
         - open_close_return
            Open to close intraday return
            
        Returns T/F, showing if the features are in place to start updating the training labels.
        """
        self.roc_window = np.append(open_close_return, self.roc_window)[:self.num_days_per_sample]
        
        if len(self.roc_window) < self.num_days_per_sample: 
            return False
            
        self.features_by_day.loc[day] = self.roc_window
        self.features_by_day = self.features_by_day[-(self.num_samples+2):]
        return True
        
        
    def CustomDailyHandler(self, sender, consolidated):
        """
        Updates the rolling lookback of training data.
        
        Inputs
         - sender
            Function calling the consolidator
         - consolidated
            Tradebar representing the latest completed trading day
        """
        time = consolidated.EndTime
        if time in self.features_by_day.index:
            return
        
        _open = consolidated.Open
        close = consolidated.Close
        
        open_close_return = (close - _open) / _open
        if self.update_features(time, open_close_return) and self.previous_open:
            day = self.features_by_day.index[-3]
            open_open_return = (_open - self.previous_open) / self.previous_open
            self.labels_by_day[day] = np.sign(open_open_return)
            self.labels_by_day = self.labels_by_day[-self.num_samples:]
            
        self.previous_open = _open


    def dispose(self):
        """
        Removes the consolidator subscription.
        """
        self.algorithm.SubscriptionManager.RemoveConsolidator(self.symbol, self.consolidator)
        
    
    @property
    def IsReady(self):
        return self.features_by_day.shape[0] == self.num_samples + 2