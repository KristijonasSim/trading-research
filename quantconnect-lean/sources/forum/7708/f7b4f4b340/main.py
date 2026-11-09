#   Ray Dalio's portfolio idea with futures with monthly rebalancing.

class FuturePortfolio(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2020,1,1)  #Set Start Date - earliest for futures can be (2009,6,1)
        #self.SetEndDate(2020,1,1)    #Set End Date
        self.SetCash(1000000)           # $1M used since futures can have large requirements per contract.
        self.qqq = self.AddEquity("QQQ", Resolution.Minute).Symbol
        self.futureNQ  = self.AddFuture(Futures.Indices.NASDAQ100EMini) 
        self.futureNQ .SetFilter(30, 120)    # Get contracts from 30 days to 120 days out
        self.futureZB  = self.AddFuture(Futures.Financials.Y30TreasuryBond) 
        self.futureZB .SetFilter(30, 120)
        self.futureZN  = self.AddFuture(Futures.Financials.Y10TreasuryNote)
        self.futureZN .SetFilter(30, 120)
        self.futureVX  = self.AddFuture(Futures.Indices.VIX) 
        self.futureVX .SetFilter(30, 120)
        self.rebalance = True   # Flag to initate trades
        self.Schedule.On(self.DateRules.MonthStart("QQQ"), self.TimeRules.AfterMarketOpen("QQQ", 30), self.Rebalance)
        self.contract = None
        self.SetWarmUp(200)

    def OnData(self, data):
        if not (data.ContainsKey(self.qqq) and data[self.qqq] is not None and self.rebalance):
            return
    
        self.Liquidate()    # close all contracts at the start of each month, this way we avoid having to roll as expiration nears.
        for contracts in data.FutureChains.Values:
            sorted_contracts = sorted(contracts, key=lambda c: c.Expiry, reverse = True)
            if len(sorted_contracts) == 0 or \
            (self.contract is not None and sorted_contracts[0].Symbol == self.contract.Symbol):
                continue
            self.contract = sorted_contracts[0]
            if self.contract.Symbol.ID.Symbol == Futures.Indices.NASDAQ100EMini:
                self.SetHoldings(sorted_contracts[0].Symbol, 0.35)
            if self.contract.Symbol.ID.Symbol == Futures.Financials.Y30TreasuryBond:
                self.SetHoldings(sorted_contracts[0].Symbol, 0.35)
            if self.contract.Symbol.ID.Symbol == Futures.Financials.Y10TreasuryNote:
                self.SetHoldings(sorted_contracts[0].Symbol, 0.2)
            else:
                self.SetHoldings(sorted_contracts[0].Symbol, 0.0)     # Use this for /VX
        self.rebalance = False     # Reset rebalance timer
        
    def Rebalance(self):
        self.rebalance = True