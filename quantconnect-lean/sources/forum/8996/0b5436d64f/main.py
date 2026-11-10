#take the paper "Leverage For The Long Run", use a 200 SMA on SPY to generate weekly buy/sell signals to either go long SPX futures or cash.

class LeverageForTheLongRunDiversifiedWeekly(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2010,3, 1)  #Set Start Date
        self.SetEndDate(2020,8,20)    #Set End Date
        self.SetCash(100000)           #Set Strategy Cash
        self.spy = self.AddEquity("SPY", Resolution.Daily)
        self.Securities["SPY"].SetDataNormalizationMode(DataNormalizationMode.Raw);
        self.tqqq = self.AddEquity("TQQQ", Resolution.Hour)
        self.shy = self.AddEquity("SHY", Resolution.Hour)
        self.futureSP500  = self.AddFuture(Futures.Indices.SP500EMini) 
        self.futureSP500 .SetFilter(10, 120)    # Get contracts from 10 days to 120 days out
        self.sma = self.SMA("SPY", 200, Resolution.Daily)
        self.SetWarmUp(200)      # warm up the indicator
        self.Settings.FreePortfolioValuePercentage = 0.05
        
        # Rebalancing logic
        self.rebal = 1                              # Rebalance every 1 week
        self.rebalTimer = self.rebal - 1            # Initialize to trigger first week
        self.flag1 = 0                              # Flag to initate trades
        
        # Increment rebalance timer at every week start
        self.Schedule.On(self.DateRules.WeekStart("SPY"), self.TimeRules.AfterMarketOpen("SPY", 60), self.Rebalance)

    def OnData(self, data):
        if not self.sma.IsReady: return
        if data.ContainsKey("SPY") == False: return     # make sure we have data for trading symbols
        if data.ContainsKey("TQQQ") == False: return
        if data.ContainsKey("SHY") == False: return

        if self.flag1 == 1:                     
            if data[self.spy.Symbol].Close > self.sma.Current.Value:
                for chain in data.FutureChains.Values:
                    for i in chain.Value:
                        contractSymbol = i.Symbol
                    #1. Save the notional value of the futures contract to self.notionalValue  
                    self.notionalValue = self.contractSymbol.AskPrice * self.futureSP500.SymbolProperties.ContractMultiplier
                    #2. Save the contract security object to the variable future
                    future = self.Securities[self.contractSymbol.Symbol]
                    #3. Calculate the number of contracts we can afford based on the margin required. Divide the margin remaining by the initial margin and save to self.contractsToBuy
                    self.contractsToBuy = floor(self.Portfolio.MarginRemaining / future.BuyingPowerModel.InitialOvernightMarginRequirement)
                    #4. Make a market order for the number of contracts we calculated for that symbol
                    self.MarketOrder(self.contractSymbol.Symbol, self.contractsToBuy)
                    #self.MarketOrder(self.contractSymbol, 0.1)
                    #self.SetHoldings("TQQQ", 1, True)
                    #self.Debug("long equities")
                    self.rebalTimer = 0     # Reset rebalance timer
            if data[self.spy.Symbol].Close < self.sma.Current.Value:
                self.SetHoldings("SHY", 1, True)
                self.Debug("go to cash")
                self.rebalTimer = 0     # Reset rebalance timer
        self.flag1 = 0   
        
    def Rebalance(self):
        self.rebalTimer +=1
        if self.rebalTimer == self.rebal:
            self.flag1 = 1
            
    def OnEndOfAlgorithm(self):
        # Get the margin requirements
        buyingPowerModel = self.Securities[self.contractSymbol].BuyingPowerModel
        name = type(buyingPowerModel).__name__
        if name != 'FutureMarginModel':
            raise Exception(f"Invalid buying power model. Found: {name}. Expected: FutureMarginModel")

        initialOvernight = buyingPowerModel.InitialOvernightMarginRequirement
        maintenanceOvernight = buyingPowerModel.MaintenanceOvernightMarginRequirement
        initialIntraday = buyingPowerModel.InitialIntradayMarginRequirement
        maintenanceIntraday = buyingPowerModel.MaintenanceIntradayMarginRequirement