class ShortTimeReversal(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2020, 3, 23)
        self.SetEndDate(2020, 6, 8)
        self.SetCash(1000000)
        
        self.UniverseSettings.Resolution = Resolution.Daily
        self.AddUniverse(self.SelectCoarse)
        
        self.dollar_volume_selection_size = 100
        self.roc_selection_size = int(0.1 * self.dollar_volume_selection_size)
        
        self.lookback = 22
        self.roc_by_symbol = {}
        self.week = 0

    def SelectCoarse(self, coarse):
        
        # We should keep a dictionary for all securities that have been selected
        for cf in coarse:
            symbol = cf.Symbol
            if symbol in self.roc_by_symbol:
                self.roc_by_symbol[symbol].Update(cf.EndTime, cf.AdjustedPrice)

        # Refresh universe each week
        week_number = self.Time.date().isocalendar()[1]
        if week_number == self.week:
            return Universe.Unchanged
        self.week = week_number

        # sort and select by dollar volume
        sortedByDollarVolume = sorted(coarse, key=lambda x: x.DollarVolume, reverse=True)
        selected = {cf.Symbol: cf for cf in sortedByDollarVolume[:self.dollar_volume_selection_size]} 
        
        # New selections need a history request to warm up the indicator
        symbols = [k for k in selected.keys()
            if k not in self.roc_by_symbol or not self.roc_by_symbol[k].IsReady]

        if symbols:
            history = self.History(symbols, self.lookback, Resolution.Daily)
            if history.empty:
                self.Log(f'No history for {", ".join([x.Value for x in symbols])}')
            history = history.close.unstack(0)

            for symbol in symbols:

                if symbol not in history:
                    continue

                # Create and warm-up the RateOfChange indicator
                roc = RateOfChange(self.lookback)
                for time, price in history[symbol].dropna().iteritems():
                    roc.Update(time, price)
                
                if roc.IsReady:
                    self.roc_by_symbol[symbol] = roc
        
        # Sort the symbols by their ROC values
        selectedRateOfChange = {}
        for symbol in selected.keys():
            if symbol in self.roc_by_symbol:
                selectedRateOfChange[symbol] = self.roc_by_symbol[symbol]
        sortedByRateOfChange = sorted(selectedRateOfChange.items(), key=lambda kv: kv[1], reverse=True)
        
        # Define the top and the bottom to buy and sell
        self.rocTop = [x[0] for x in sortedByRateOfChange[:self.roc_selection_size]]
        self.rocBottom = [x[0] for x in sortedByRateOfChange[-self.roc_selection_size:]]
        
        return self.rocTop + self.rocBottom


    def OnData(self, data):
        # Rebalance
        for symbol in self.rocTop:
            self.SetHoldings(symbol, -0.5/len(self.rocTop))
        for symbol in self.rocBottom:
            self.SetHoldings(symbol, 0.5/len(self.rocBottom))
        
        # Clear the list of securities we have placed orders for
        # to avoid new trades before the next universe selection
        self.rocTop.clear() 
        self.rocBottom.clear()

    def OnSecuritiesChanged(self, changes):
        for security in changes.RemovedSecurities:
            self.Liquidate(security.Symbol, 'Removed from Universe')