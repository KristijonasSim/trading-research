from AlgorithmImports import *


class MovingAverageStrategy(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2000, 1, 1)
        self.SetCash(30000)
        self.cash=30000
        self.AddEquity("QQQ", Resolution.Daily)
        self.AddEquity("IWM", Resolution.Daily)
        self.AddEquity("SPY", Resolution.Daily)
        self.spyatr = self.ATR("SPY", 10, Resolution.Daily)
        self.qqqatr = self.ATR("QQQ", 10, Resolution.Daily)
        self.iwmatr = self.ATR("IWM", 10, Resolution.Daily)
        self.profit_target = {}
        self.profit_target["SPY"] = 0
        self.profit_target["QQQ"] = 0
        self.profit_target["IWM"] = 0
        self.entry={}
        self.avol = {}
        self.df = pd.DataFrame()
        self.entry["SPY"]=0
        self.entry["QQQ"]=0
        self.entry["IWM"]=0
        


        self.fastMA = {
            "QQQ": self.SMA("QQQ", 4),
            "IWM": self.SMA("IWM", 10),
            "SPY": self.SMA("SPY", 4)
        }

        self.slowMA = {
            "QQQ": self.SMA("QQQ", 90),
            "IWM": self.SMA("IWM", 100),
            "SPY": self.SMA("SPY", 50)
        }

        self.investment = {
            "QQQ": 10000,
            "IWM": 10000,
            "SPY": 10000
        }

        self.SetWarmUp(100)


       

    def OnData(self, data):
        if self.IsWarmingUp:
            return
        # self.Debug(f"value of portfolio: {self.Portfolio.TotalHoldingsValue}")
        # self.df = self.df.append({"PortfolioValue": self.Portfolio.TotalHoldingsValue}, ignore_index=True)
        
        # returns = self.df['PortfolioValue'].pct_change().dropna()
        # rolling_std = returns.tail(20).std()
        # self.volatility = rolling_std * np.sqrt(252)
        # self.Log(f"Portfolio value: {self.Portfolio.TotalHoldingsValue}, Volatility: {self.volatility}")
        # if not self.Portfolio.Invested:
        #         self.df = self.df.append({"PortfolioValue": self.cash}, ignore_index=True)
        # if math.isnan(self.volatility) == False and self.volatility > 0.5:
        #     self.Liquidate()
        
        for symbol in ["QQQ", "IWM", "SPY"]:
          
         history = self.History([symbol], timedelta(days=20), Resolution.Daily)
         if not history.empty:
                # Calculate daily returns
                returns = history['close'].pct_change()[1:]
          

            # Calculate annualized volatility
         volatility = np.std(returns) * np.sqrt(252)
         self.avol[symbol] = round(volatility,2)


        for symbol in ["QQQ", "IWM", "SPY"]:
            if not self.Portfolio[symbol].Invested:
                if (self.fastMA[symbol].Current.Value > self.Securities[symbol].Close and self.Securities[symbol].Close < self.fastMA[symbol].Current.Value and  self.avol[symbol] < 0.5):
                    investment_size = self.investment[symbol] / self.Securities[symbol].Close
                    if (self.avol[symbol] > 0.10 and self.avol[symbol] < 0.45):
                     self.SetHoldings(symbol, 1 / 3)
                     self.entry[symbol]=  self.Securities[symbol].Price
                     self.Log("avol of symbol"+str(symbol)+": "+str(self.avol[symbol]))

        if self.spyatr.IsReady:
            self.Debug("inside spyatr")
            symbol = "SPY"
            entry_price = self.Portfolio[symbol].AveragePrice
            self.profit_target[symbol] =  self.entry[symbol] + 3.5 * self.spyatr.Current.Value

            self.Debug('profit target is ' + str(self.profit_target[symbol]))
            if self.Portfolio[symbol].Invested:
                if self.Securities[symbol].High >= self.profit_target[symbol]:
                
                  #  self.Liquidate(symbol, "profit")
                    self.Debug("liquidated")
                    
                else:
                    if self.Securities[symbol].Close < self.slowMA[symbol].Current.Value and self.slowMA[symbol].Current.Value > self.fastMA[symbol].Current.Value:
                    
                        self.Liquidate(symbol)

            
        if self.qqqatr.IsReady:
            self.Debug("inside qqqatr")
            symbol = "QQQ"
            entry_price = self.Portfolio[symbol].AveragePrice
            self.profit_target[symbol] =  self.entry[symbol] + 3.5 * self.qqqatr.Current.Value
            self.Debug('profit target is ' + str(self.profit_target[symbol]))
            if self.Portfolio[symbol].Invested:
                if self.Securities[symbol].High >= self.profit_target[symbol]:
                
                   # self.Liquidate(symbol, "profit")
                    self.Debug("liquidated")
                else:
                    if self.Securities[symbol].Close < self.slowMA[symbol].Current.Value and self.slowMA[symbol].Current.Value > self.fastMA[symbol].Current.Value:
                    
                        self.Liquidate(symbol)

           

        if self.iwmatr.IsReady:
            self.Debug("inside iwmatr")
            symbol = "IWM"
            entry_price = self.Portfolio[symbol].AveragePrice
            self.profit_target[symbol] =  self.entry[symbol] + 3.5 * self.iwmatr.Current.Value

            self.Debug('profit target is ' + str(self.profit_target[symbol]))
            if self.Portfolio[symbol].Invested:
                if self.Securities[symbol].High >= self.profit_target[symbol]:
                
                  #  self.Liquidate(symbol, "profit")
                    self.Debug("liquidated")
                else:
                    if self.Securities[symbol].Close < self.slowMA[symbol].Current.Value and self.slowMA[symbol].Current.Value > self.fastMA[symbol].Current.Value:
                  
                        self.Liquidate(symbol)
    def OnOrderEvent(self, OrderEvent):
        if OrderEvent.FillQuantity == 0:
            return
       
      #  self.entry[OrderEvent.Symbol] = round(OrderEvent.FillPrice*1, 2);
        