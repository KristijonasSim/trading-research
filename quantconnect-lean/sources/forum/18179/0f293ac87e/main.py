from AlgorithmImports import *

class BasicTemplateAlgorithm(QCAlgorithm):
    '''Basic template algorithm simply initializes the date range and cash'''

    def GetRsi(self, symbol, days):
        trades = self.history[TradeBar](symbol, days, Resolution.DAILY, data_normalization_mode=DataNormalizationMode.SPLIT_ADJUSTED)
        rsi = RelativeStrengthIndex(symbol, days, MovingAverageType.WILDERS)
        self.Debug("calculating rsi for {}".format(symbol))
        for trade in trades:
            self.Debug("{}:{}".format(trade.time.strftime("%Y-%m-%d %H:%M:%S %Z%z"), trade.close)) 
            rsi.update(trade.time, trade.close)
        rsi.update(self.Time, self.securities[symbol].price)
        self.Debug("{}:{}".format(self.Time.strftime("%Y-%m-%d %H:%M:%S %Z%z"), self.securities[symbol].price)) 
        return rsi.current.value

    def TradeBeforeMarketClose(self):
        if self.IsWarmingUp:
           return
        rsi = self.GetRsi("TQQQ", 10)
        self.plot("RelativeStrengthIndex", "rsi", rsi)
        if rsi > 79:
            self.SetHoldings("UVXY", 1, True)
        else:
            self.SetHoldings("TQQQ", 1, True)

    def Initialize(self):
        '''Initialise the data and resolution required, as well as the cash and start-end dates for your algorithm. All algorithms must initialized.'''

        self.SetStartDate(2023, 1, 3)  #Set Start Date
        self.SetEndDate(2024, 1, 2)    #Set End Date
        self.SetCash(10000)           #Set Strategy Cash
        self.set_time_zone(TimeZones.NEW_YORK)
        self.add_equity("UVXY", Resolution.MINUTE, data_normalization_mode=DataNormalizationMode.RAW)
        self.add_equity("TQQQ", Resolution.MINUTE, data_normalization_mode=DataNormalizationMode.RAW)
        self.Debug("Initilize is complete")
        self.Schedule.On(
            self.DateRules.EveryDay("TQQQ"),
            self.TimeRules.BeforeMarketClose("TQQQ", 5),
            self.TradeBeforeMarketClose)

    def OnData(self, data):
        return
