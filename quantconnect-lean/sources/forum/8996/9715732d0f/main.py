#take the paper "Leverage For The Long Run", use a 200 SMA on SPY to generate weekly buy/sell signals to either go long SPX futures or cash.

class LeverageForTheLongRunDiversifiedWeekly(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2020,1, 1)  #Set Start Date
        self.SetEndDate(2020,6,20)    #Set End Date
        self.SetCash(100000)           #Set Strategy Cash
        
        self.shy = self.AddEquity("SHY", Resolution.Minute).Symbol
        self.spy = self.AddEquity("SPY", Resolution.Minute).Symbol
        
        self.futureSP500  = self.AddFuture(Futures.Metals.Gold) 
        self.futureSP500 .SetFilter(10, 120)    # Get contracts from 10 days to 120 days out
        
        self.sma = self.SMA("SPY", 200, Resolution.Daily)
        self.SetWarmUp(200, Resolution.Daily)      # warm up the indicator
        self.Settings.FreePortfolioValuePercentage = 0.05
        
        self.rebalance = True                            # Flag to initate trades
        
        # Increment rebalance timer at every week start
        self.Schedule.On(self.DateRules.WeekStart("SPY"), self.TimeRules.AfterMarketOpen("SPY", 30), self.Rebalance)
        
        self.contract = None

    def OnData(self, data):
        if not (self.sma.IsReady and \
                data.ContainsKey(self.shy) and data[self.shy] is not None and \
                data.ContainsKey(self.spy) and data[self.spy] is not None and \
                self.rebalance):
            return
        
        if data[self.spy].Close > self.sma.Current.Value:
            for contracts in data.FutureChains.Values:
                sorted_contracts = sorted(contracts, key=lambda c: c.Expiry, reverse = True)
                if len(sorted_contracts) == 0 or \
                   (self.contract is not None and sorted_contracts[0].Symbol == self.contract.Symbol):
                    continue
                
                self.contract = sorted_contracts[0]
                self.MarketOrder(sorted_contracts[0].Symbol, 1)
        else:
            self.SetHoldings("SHY", 1, True)
            self.contract = None
            
        self.rebalance = False     # Reset rebalance timer
        
    def Rebalance(self):
        self.rebalance = True