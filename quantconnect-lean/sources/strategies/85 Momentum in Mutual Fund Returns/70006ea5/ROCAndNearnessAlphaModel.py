import pandas as pd
from dateutil.relativedelta import relativedelta

from ROCAndNearness import ROCAndNearness

class ROCAndNearnessAlphaModel(AlphaModel):
    """
    This class ranks securities in the universe by their historical rate of change and nearness to trailing highs.
    """
    symbol_data_by_symbol = {}
    month = -1
    
    def __init__(self, roc_lookback_months=6, nearness_lookback_months=12, holding_months=6, pct_long_short=25):
        """
        Input:
         - roc_lookback_months
            Number of trailing months to calculate the rate of change over (> 0)
         - nearness_lookback_months
            Number of trailing months to calculate the nearness factor over (> 0)
         - holding_months
            Number of months to hold positions (> 0)
         - pct_long_short
            The percentage of the universe we go long and short (0 < pct_long_short <= 50)
        """
        if roc_lookback_months <= 0 or nearness_lookback_months <= 0 or holding_months <= 0:
            algorithm.Quit(f"Requirement violated:  roc_lookback_months > 0 and nearness_lookback_months > 0 and holding_months > 0")
        
        if pct_long_short <= 0 or pct_long_short > 50:
            algorithm.Quit(f"Requirement violated: 0 < pct_long_short <= 50")
        
        self.roc_lookback_months = roc_lookback_months
        self.nearness_lookback_months = nearness_lookback_months
        self.holding_months = holding_months
        self.pct_long_short = pct_long_short
    
    def Update(self, algorithm, data):
        """
        Called each time our alpha model receives a new data slice.
        
        Input:
         - algorithm
            Algorithm instance running the backtest
         - data
            A data structure for all of an algorithm's data at a single time step
        
        Returns a list of Insights to the portfolio construction model
        """
        # Emit insights on a monthly basis
        time = algorithm.Time
        if self.month == time.month:
            return []
        self.month = time.month
        
        
        # Rank symbols. A higher rank (or index in the list) is associated with relatively greater rate of change
        # over the roc lookback window and a closer closing price to the max price in the nearness lookback window
        ranking_df = pd.DataFrame()
        for symbol, symbol_data in self.symbol_data_by_symbol.items():
            if data.ContainsKey(symbol) and symbol_data.IsReady:
                row = pd.DataFrame({'ROC': symbol_data.roc, 'Nearness': symbol_data.nearness}, index=[symbol])
                ranking_df = ranking_df.append(row)
        ranked_symbols =  ranking_df.rank().sum(axis=1).sort_values().index
        
        # Generate insights to form a balanced long-short portfolio
        insights = []
        num_long_short = int(len(ranked_symbols) * (self.pct_long_short / 100))
        if num_long_short > 0:
            hold_duration = Expiry.EndOfMonth(time) + relativedelta(months=self.holding_months-1, seconds=-1)
            for symbol in ranked_symbols[-num_long_short:]:
                insights.append(Insight.Price(symbol, hold_duration, InsightDirection.Up))
            for symbol in ranked_symbols[:num_long_short]:
                insights.append(Insight.Price(symbol, hold_duration, InsightDirection.Down))
        return insights
    
    
    def OnSecuritiesChanged(self, algorithm, changes):
        """
        Called each time our universe has changed.
        
        Input:
         - algorithm
            Algorithm instance running the backtest
         - changes
            The additions and subtractions to the algorithm's security subscriptions
        """
        for added in changes.AddedSecurities:
            roc_and_nearness = ROCAndNearness(added.Symbol, algorithm, self.roc_lookback_months, self.nearness_lookback_months)
            self.symbol_data_by_symbol[added.Symbol] = roc_and_nearness

        for removed in changes.RemovedSecurities:
            symbol_data = self.symbol_data_by_symbol.pop(removed.Symbol, None)
            if symbol_data:
                symbol_data.dispose()