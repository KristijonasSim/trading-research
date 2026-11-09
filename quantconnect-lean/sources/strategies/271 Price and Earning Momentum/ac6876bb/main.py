class PriceEarningsMomentumAlgorithm(QCAlgorithm):
    '''
    A stock momentum strategy based on quarterly returns and earning growth.
    Paper: http://papers.ssrn.com/sol3/papers.cfm?abstract_id=299107
    Online copy: https://www.trendrating.com/wp-content/uploads/dlm_uploads/2019/03/momentum.pdf
    '''
    def Initialize(self):
        self.SetStartDate(2010, 1, 1)   # Set Start Date
        self.SetEndDate(2019, 9, 1)     # Set End Date
        self.SetCash(100000)            # Set Strategy Cash

        self.UniverseSettings.Resolution = Resolution.Daily          # Resolution setting of universe selection
        self.AddUniverse(self.CoarseSelection, self.FineSelection)   # Coarse and Fine Universe Selection

        self.nextRebalance = self.Time  # Initialize next balance time
        self.rebalanceDays = 90         # Rebalance quarterly

        self.numOfCoarse = 100          # Number of coarse selected universe
        self.longSymbols = []           # Symbol list of the equities we'd like to long
        self.shortSymbols = []          # Symbol list of the equities we'd like to short
        self.epsBySymbol = {}           # Contains RollingWindow objects of EPS for every stock

    def CoarseSelection(self, coarse):
        '''
        Pick the top 100 liquid equities as the coarse-selected universe
        '''
        # Before next rebalance time, just remain the current universe
        if self.Time < self.nextRebalance:
            return Universe.Unchanged

        # Sort the equities (prices > 5) by Dollar Volume descendingly
        selectedByDollarVolume = sorted([x for x in coarse if x.Price > 5 and x.HasFundamentalData], 
                                        key = lambda x: x.DollarVolume, reverse = True)

        # Pick the top 100 liquid equities as the coarse-selected universe
        return [x.Symbol for x in selectedByDollarVolume[:self.numOfCoarse]]

    def FineSelection(self, fine):
        '''
        Select securities based on their quarterly return and their earnings growth 
        '''
        symbols = [x.Symbol for x in fine]

        # Get the quarterly returns for each symbol
        history = self.History(symbols, self.rebalanceDays, Resolution.Daily)
        history = history.drop_duplicates().close.unstack(level = 0)
        rankByQuarterReturn = self.GetQuarterlyReturn(history)

        # Get the earning growth for each symbol
        rankByEarningGrowth = self.GetEarningGrowth(fine) 

        # Get the sum of rank for each symbol and pick the top ones to long and the bottom ones to short
        rankSumBySymbol = {key: rankByQuarterReturn.get(key, 0) + rankByEarningGrowth.get(key, 0) 
                                for key in set(rankByQuarterReturn) | set(rankByEarningGrowth)}

        # Get 10 symbols to long and short respectively
        sortedDict = sorted(rankSumBySymbol.items(), key = lambda x: x[1], reverse = True)
        self.longSymbols = [x[0] for x in sortedDict[:10]]
        self.shortSymbols = [x[0] for x in sortedDict[-10:]]

        return [x for x in symbols if str(x) in self.longSymbols + self.shortSymbols]

    def GetQuarterlyReturn(self, history):
        '''
        Get the rank of securities based on their quarterly return from historical close prices
        Return: dictionary
        '''
        # Get quarterly returns for all symbols
        # (The first row divided by the last row)
        returns = history.iloc[0] / history.iloc[-1]

        # Transform them to dictionary structure
        returns = returns.to_dict()

        # Get the rank of the returns (key: symbol; value: rank)
        # (The symbol with the 1st quarterly return ranks the 1st, etc.)
        ranked = sorted(returns, key = returns.get, reverse = True)
        return {symbol: rank for rank, symbol in enumerate(ranked, 1)}

    def GetEarningGrowth(self, fine):
        '''
        Get the rank of securities based on their EPS growth
        Return: dictionary
        '''

        # Earning Growth by symbol
        egBySymbol = {}
        for stock in fine:

            # Select the securities with EPS (> 0)
            if stock.EarningReports.BasicEPS.ThreeMonths == 0:
                continue

            # Add the symbol in the dict if not exist
            if not stock.Symbol in self.epsBySymbol:
                self.epsBySymbol[stock.Symbol] = RollingWindow[float](2)

            # Update the rolling window for each stock
            self.epsBySymbol[stock.Symbol].Add(stock.EarningReports.BasicEPS.ThreeMonths)

            # If the rolling window is ready
            if self.epsBySymbol[stock.Symbol].IsReady:
                rw = self.epsBySymbol[stock.Symbol]
                # Caculate the Earning Growth
                egBySymbol[stock.Symbol] = (rw[0] - rw[1]) / rw[1]

        # Get the rank of the Earning Growth
        ranked = sorted(egBySymbol, key = egBySymbol.get, reverse = True)
        return {symbol: rank for rank, symbol in enumerate(ranked, 1)}

    def OnData(self, data):
        '''
        Rebalance quarterly
        '''
        # Do nothing until next rebalance
        if self.Time < self.nextRebalance:
            return

        # Liquidate the holdings if necessary
        for holding in self.Portfolio.Values:
            symbol = holding.Symbol
            if holding.Invested and symbol.Value not in self.longSymbols + self.shortSymbols:
                self.Liquidate(symbol, "Not Selected")

        # Open positions for the symbols with equal weights
        count = len(self.longSymbols + self.shortSymbols)
        if count == 0:
            return

        # Enter long positions
        for symbol in self.longSymbols:
            self.SetHoldings(symbol, 1 / count)

        # Enter short positions
        for symbol in self.shortSymbols:
            self.SetHoldings(symbol, -1 / count)

        # Set next rebalance time
        self.nextRebalance += timedelta(self.rebalanceDays)