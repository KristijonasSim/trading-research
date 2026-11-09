import pandas as pd
import numpy as np
from dateutil.relativedelta import relativedelta

from FamaFrench import FF
from ResidualMomentum import ResidualMomentum

class ResidualMomentumAlphaModel(AlphaModel):
    """
    This class houses the Fama French data and a dictionary of ResidualMomentum indicators for 
    symbols. Each month, we rank the symbols by the ResidualMomentum indicator scores, then
    emit insights to generate a long-short portfolio with the symbols having the highest and lowest 
    scores.
    """
    symbol_data = {}
    fama_french_factors = pd.DataFrame()
    month = -1

    def __init__(self, algorithm, num_train_months=36, num_test_months=12, long_short_pct=10, min_price=1):
        """
        Inputs:
         - algorithm
            Algorithm instance running the backtest
         - num_train_months
            Number of months to train the regression model (> 2)
         - num_test_months
            Number of months to test the regression model (1 < num_test_months < num_train_months)
         - long_short_pct
            The percentage of the universe we go long and short (0 < long_short_pct <= 50)
         - min_price
            Minimum price a security needs to be considered in the rebalance (>= 0)
        """
        self.num_train_months = num_train_months
        self.num_test_months = num_test_months
        self.long_short_pct = long_short_pct
        self.min_price = min_price
        
        self.ff = algorithm.AddData(FF, "FF", Resolution.Daily).Symbol
        
        # Warmup FF history
        end = algorithm.StartDate - timedelta(1)
        start = end - relativedelta(months=self.num_train_months)
        self.fama_french_factors = algorithm.History(self.ff, start, end).loc[self.ff]

    def Update(self, algorithm, slice):
        """
        Called each time our alpha model receives a new data slice.
        
        Inputs:
         - algorithm
            Algorithm instance running the backtest
         - slice
            A data structure for all of an algorithm's data at a single time step
        
        Returns an empty list or an Insight group to the portfolio construction model
        """
        # If we have a new month of fama french data, update our df
        if slice.ContainsKey(self.ff):
            self.update_ff(slice[self.ff])
        
        if algorithm.IsWarmingUp:
            return []
            
        # Only update insights at the start of every month
        if algorithm.Time.month == self.month:
            return []
        self.month = algorithm.Time.month
        
        # Sort self.symbol_data values by their residual momentum score
        has_score = [s for s in self.symbol_data.values() if s.score is not None]
        sorted_by_score = sorted(has_score, key=lambda x: x.score, reverse=True)
        
        # If the universe is too small to grab `long_short_pct`% on both sides, do nothing.
        num_passed = int(len(sorted_by_score) * (1 / self.long_short_pct))
        if num_passed == 0:
            return []
            
        # Create insights
        insights = []
        # Long the top `long_short_pct`% of symbols, based on score
        for s in sorted_by_score[:num_passed]:
            if s.Symbol in slice.Bars:
                insights.append(Insight(s.Symbol, timedelta(days=30), InsightType.Price, InsightDirection.Up))
        
        # Short the bottom `long_short_pct`% 
        for s in sorted_by_score[-num_passed:]:
            if s.Symbol in slice.Bars:
                insights.append(Insight(s.Symbol, timedelta(days=30), InsightType.Price, InsightDirection.Down))
        
        return Insight.Group(insights)

    def OnSecuritiesChanged(self, algorithm, changes):
        """
        Called each time our universe has changed.
        
        Inputs:
         - algorithm
            Algorithm instance running the backtest
         - changes
            The additions and subtractions to the algorithm's security subscriptions
        """
        if len(changes.AddedSecurities) > 0:
            # Get lookback dates
            end_lookback = Expiry.EndOfMonth(algorithm.Time) - relativedelta(months=1)
            start_lookback = end_lookback - relativedelta(months=self.num_train_months)
            
            # Get history of symbols over lookback window
            added_symbols = [x.Symbol for x in changes.AddedSecurities]
            history = algorithm.History(added_symbols, start_lookback, end_lookback, Resolution.Daily)
            
            # Filter for sufficient history
            if history.shape[0] > 0 and \
                (history.index.levels[1][-1] - history.index.levels[1][0]).days / 30 >= self.num_train_months:
                
                # Get monthly returns of symbols with sufficient history
                monthly_returns, closes = self.calc_performance(changes.AddedSecurities, history)
                
                for added in monthly_returns.columns:
                    # Create residual momentum indicator for this symbol
                    ret = monthly_returns[[added]].iloc[-self.num_train_months:]
                    self.symbol_data[added] = ResidualMomentum(added, ret, algorithm, self, closes[added], 
                                                                self.num_train_months, self.num_test_months, self.min_price)
            
        for removed in changes.RemovedSecurities:
            # Remove symbol from our symbol_data dictionary
            resid_mom = self.symbol_data.pop(removed.Symbol, None)
            if resid_mom:
                # Remove consolidator
                resid_mom.dispose(algorithm)
        
    def calc_performance(self, securities, history):
        """
        Calculates the monthly returns for securites over a historical period.
        Securities with insufficient history are omitted.
        
        Inputs:
        # - securities
        #    List of security objects to calculate the monthly returns for
         - history
            DataFrame containing the historical prices of securities
            
        Returns a DataFrame containing the monthly returns and the latest month's closing 
        price for securities with sufficient history.
        """
        symbols = [x.Symbol for x in securities]
        
        # Must not have null history
        duration_filter = ~history['close'].unstack(level=0).isnull().any()
        duration_filter = duration_filter[duration_filter].index
        history = history.loc[duration_filter].copy()
        
        # Roll back the timestamp of our history DataFrame by one day
        history = history.unstack(level=0)
        history = history.set_index(history.index.map(lambda x: x - timedelta(days=1))).stack().swaplevel()
        
        # Calculate monthly returns
        returns = {sym : [] for sym in symbols if sym in history.index}
        indicies = []
        for i, sym in enumerate(returns):
            for idx, g in history.loc[sym].groupby(pd.Grouper(freq='M')):
                monthly_ret = (g.iloc[-1].close - g.iloc[0].open) / g.iloc[0].open
                returns[sym].append(monthly_ret)
                if i == 0:
                    indicies.append(idx)
        monthly_returns = pd.DataFrame(returns, index=indicies)
        
        # Save latest closing price for each symbol
        closes = {sym : history.loc[sym].iloc[-1].close for sym in returns}
        
        return monthly_returns, closes
        
        return None, None
        
        
    def update_ff(self, data):
        """
        Updates the fama and french DataFrame with the latest data
        
        Inputs:
         - data
            PythonData object containing the ff data
        """
        row = pd.DataFrame({"hml" : [data.GetProperty('hml')],
                            "mkt" : [data.GetProperty('mkt')],
                            "rf"  : [data.GetProperty('rf')],
                            "smb" : [data.GetProperty('smb')]},
                            index=[data.Time])
        self.fama_french_factors = self.fama_french_factors.append(row).iloc[-self.num_train_months:]