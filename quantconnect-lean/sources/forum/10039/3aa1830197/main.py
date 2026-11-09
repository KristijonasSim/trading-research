from datetime import timedelta
import numpy as np
from scipy import stats
from collections import deque
import math

from dateutil import parser
import pickle

class statusObj:
    def __init__(self):
        self.invested = False
        self.positionDay = '1820-01-01'

class OptimizedTransdimensionalCircuit(QCAlgorithm):

    def Initialize(self):

        self.SignalDataBySymbol = {}
        
        self.SetStartDate(2010, 1, 1)  # Set Start Date
        self.SetCash(50000)  # Set Strategy Cash
        #self.SetEndDate(2020, 11, 30)
    
        tickers = ["QQQ","SPY","IYC","IYK","IGV","GLD","TLH","TLT", 'XLI','XLU','FXA','FXF','SLV','GLD']
        
        for x in tickers:
            self.AddEquity(x, Resolution.Daily)
        self.SetUniverseSelection(CustomUniverseSelectionModel("CustomUniverseSelectionModel", lambda time: tickers)) 
        self.UniverseSettings.Resolution = Resolution.Daily

        self.AddAlpha(ETFs_for_UP()) # etfs for up
        self.AddAlpha(ETFs_for_DOWN()) # etfs for up
    
        self.SetExecution(ImmediateExecutionModel()) 
        self.SetPortfolioConstruction(EqualWeightingPortfolioConstructionModel(self.DateRules.Every(DayOfWeek.Tuesday)))

        # schedule an event to fire on a single day of the week
        self.Schedule.On(self.DateRules.Every(DayOfWeek.Monday), self.TimeRules.At(12, 0), self.calculate_signal)                 

        signal_universe = ['XLI','XLU','FXA','FXF','SLV','GLD']
        
        for x in signal_universe:
            ticker = self.Symbol(x)
            mom=CustomMomentum("Momentum", 252)
            self.RegisterIndicator(ticker, mom, Resolution.Daily)
            history = self.History(ticker, 252, Resolution.Daily)    
            mom.WarmUp(history)
            signaldata = SignalData(ticker, mom)
            self.SignalDataBySymbol[ticker] = signaldata


    def calculate_signal(self):
        indicator ={}
        self.status=statusObj()

        for ticker, SignalData in self.SignalDataBySymbol.items(): #For all securities in self.stocks
            indicator[ticker] = SignalData
        
        a = indicator[self.Symbol("GLD")].MOM.Value > indicator[self.Symbol("SLV")].MOM.Value
        b = indicator[self.Symbol("XLU")].MOM.Value > indicator[self.Symbol("XLI")].MOM.Value
        c = indicator[self.Symbol("FXA")].MOM.Value > indicator[self.Symbol("FXF")].MOM.Value
    
        if a and b and c:
            self.status.invested=False
        else:
            self.status.invested=True
        
        self.status.positionDay=str(self.Time.day)
        serialized=pickle.dumps(self.status)
        self.ObjectStore.SaveBytes("MyObject", serialized)
        #after save check
        #deserialized=bytes(self.ObjectStore.ReadBytes("MyObject"))
        #storedStatus=pickle.loads(deserialized)
        #self.Log('position day in stored object: '+str(storedStatus.positionDay))

        
class ETFs_for_DOWN(AlphaModel): 
    
    def __init__(self): # Initilize method in the alpha model only runs once
        
        
        self.stocks = [] # Array containing all actively traded stocks
        self.symbolDataBySymbol = {}
        
        self.num = 3
        
        self.mom_window = 200
        self.vola_window = 60
        self.num_stocks = 3
    
    
    def Update(self, algorithm, data): #Runs as fast as the data comes in. In this case it runs every hour
    
        insights = [] # sets insights array to empty
        indicator ={}
        self.status=statusObj()
        
        if algorithm.ObjectStore.ContainsKey("MyObject"):
            deserialized = bytes(algorithm.ObjectStore.ReadBytes("MyObject"))
            storedStatus = (pickle.loads(deserialized))
            up_down_signal=storedStatus.invested        
        
        
        for ticker, symbolData in self.symbolDataBySymbol.items(): #For all securities in self.stocks
            indicator[ticker] = symbolData
          
        # get the top momentum a=np.array([1,2,3,4]), sorted(a, reverse=True)[:2]
        top_mom = sorted(self.symbolDataBySymbol.items(), key=lambda x:  indicator[x[0]].MOM.Value, reverse=True)[:self.num_stocks]
        
        for ticker, symbolData in self.symbolDataBySymbol.items(): #For all securities in self.stocks
        
            if not data.ContainsKey(ticker):
                continue
        
            if algorithm.Portfolio[ticker].IsLong:
                continue
            '''self.SetHoldings(symbol, position, True)'''
            if up_down_signal == False:
                insights.append(Insight.Price(ticker, timedelta(days = 7), InsightDirection.Up)) #Long position that lasts 30 days. After 30 days liquidate

            
            #algorithm.Debug("Stock: " + str(x) + ". SMA: " + str(sma))
            
        return insights #Must return insights

    
    
    def OnSecuritiesChanged(self, algorithm, changes): #OnSecuritiesChanged is triggered every time Universe Selection returns a new stock
        
        sub_universe = ["GLD","TLH","TLT"]
        
        for x in changes.AddedSecurities:
            ticker = x.Symbol
            if str(ticker) in sub_universe: 
        
                self.stocks.append(ticker)
                
                if ticker not in self.symbolDataBySymbol:
                    mom=CustomMomentum("Momentum", self.mom_window)
                    vol=CustomVolatility("Volatility", self.vola_window)
    
                    algorithm.RegisterIndicator(ticker, mom, Resolution.Daily)
                    algorithm.RegisterIndicator(ticker, vol, Resolution.Daily)
                    
                    history = algorithm.History(ticker, max(self.mom_window, self.vola_window), Resolution.Daily)    
                    mom.WarmUp(history)
                    vol.WarmUp(history)
                    
                    symbolData = SymbolData(ticker, mom, vol)
                    self.symbolDataBySymbol[ticker] = symbolData
        
        symbolsRemoved = [ x.Symbol for x in changes.RemovedSecurities ]
        for ticker in symbolsRemoved:
            if ticker in self.stocks:
                self.stocks.remove(ticker)
            self.symbolDataBySymbol.pop(ticker, None)
        
        
        
        
class ETFs_for_UP(AlphaModel): 
    
    def __init__(self): # Initilize method in the alpha model only runs once
    
    
        self.stocks = [] # Array containing all actively traded stocks
        self.symbolDataBySymbol = {}
        
        self.num = 3
        
        self.mom_window = 200
        self.vola_window = 60
        self.num_stocks = 3
    
    
    def Update(self, algorithm, data): #Runs as fast as the data comes in. In this case it runs every hour
    
        insights = [] # sets insights array to empty
        indicator ={}
        self.status=statusObj()
        
        if algorithm.ObjectStore.ContainsKey("MyObject"):
            deserialized = bytes(algorithm.ObjectStore.ReadBytes("MyObject"))
            storedStatus = (pickle.loads(deserialized))
            up_down_signal=storedStatus.invested
     
        
        for ticker, symbolData in self.symbolDataBySymbol.items(): #For all securities in self.stocks
            indicator[ticker] = symbolData
          
        # get the top momentum a=np.array([1,2,3,4]), sorted(a, reverse=True)[:2]
        top_mom = sorted(self.symbolDataBySymbol.items(), key=lambda x:  indicator[x[0]].MOM.Value, reverse=True)[:self.num_stocks]
        
        for ticker, symbolData in self.symbolDataBySymbol.items(): #For all securities in self.stocks
        
            if not data.ContainsKey(ticker):
                continue
        
            if algorithm.Portfolio[ticker].IsLong:
                continue
            '''self.SetHoldings(symbol, position, True)'''
            if up_down_signal == True:
                insights.append(Insight.Price(ticker, timedelta(days = 7), InsightDirection.Up)) #Long position that lasts 30 days. After 30 days liquidate

            
            #algorithm.Debug("Stock: " + str(x) + ". SMA: " + str(sma))
            
        return insights #Must return insights

    
    
    def OnSecuritiesChanged(self, algorithm, changes): #OnSecuritiesChanged is triggered every time Universe Selection returns a new stock
        
        sub_universe = ["QQQ","SPY","IYC","IYK","IGV"]
        
        for x in changes.AddedSecurities:
            ticker = x.Symbol
            if str(ticker) in sub_universe: 
        
                self.stocks.append(ticker)
                
                if ticker not in self.symbolDataBySymbol:
                    mom=CustomMomentum("Momentum", self.mom_window)
                    vol=CustomVolatility("Volatility", self.vola_window)
    
                    algorithm.RegisterIndicator(ticker, mom, Resolution.Daily)
                    algorithm.RegisterIndicator(ticker, vol, Resolution.Daily)
                    
                    history = algorithm.History(ticker, max(self.mom_window, self.vola_window), Resolution.Daily)    
                    mom.WarmUp(history)
                    vol.WarmUp(history)
                    
                    symbolData = SymbolData(ticker, mom, vol)
                    self.symbolDataBySymbol[ticker] = symbolData
        
        symbolsRemoved = [ x.Symbol for x in changes.RemovedSecurities ]
        for ticker in symbolsRemoved:
            if ticker in self.stocks:
                self.stocks.remove(ticker)
            self.symbolDataBySymbol.pop(ticker, None)
            
            
            
class SymbolData:
    '''Contains data specific to a symbol required by this model'''
    def __init__(self, symbol, mom, vol):
        self.Symbol = symbol
        self.MOM = mom
        self.VOL = vol
        
class SignalData:
    '''Contains data specific to a symbol required by this model'''
    def __init__(self, symbol, mom):
        self.Symbol = symbol
        self.MOM = mom
        
             
        
class CustomMomentum:
    def __init__(self, name, period):
        self.Name = name
        self.Time = datetime.min
        self.IsReady = False
        self.Value = 0
        self.queue = deque(maxlen=period)

    def __repr__(self):
        return "{0} -> IsReady: {1}. Time: {2}. Value: {3}".format(self.Name, self.IsReady, self.Time, self.Value)
        
    # Update method is mandatory
    def Update(self, input):
        return self.Update_Main(input.Time, input.Close)
        
    def Update_warmup(self, input):
        return self.Update_Main(input.Index, input.close)
   
    def Update_Main(self, time, value):
        self.queue.appendleft(value) # neutral
        count = len(self.queue)
        self.Time = time # neutral

        self.IsReady = count == self.queue.maxlen
        
        #### start indicator calulation
        if self.IsReady:
            close = np.array(self.queue)
            self.Value = close[-1]/close[0]
        #### finish indicator calulation    
        return self.IsReady
        
    def WarmUp(self,history):
        for tuple in history.itertuples():
            self.Update_warmup(tuple)        
        
        
        
        
class CustomVolatility:
    def __init__(self, name, period):
        self.Name = name
        self.Time = datetime.min
        self.IsReady = False
        self.Value = 0
        self.queue = deque(maxlen=period)

    def __repr__(self):
        return "{0} -> IsReady: {1}. Time: {2}. Value: {3}".format(self.Name, self.IsReady, self.Time, self.Value)
        
    # Update method is mandatory
    def Update(self, input):
        return self.Update_Main(input.Time, input.Close)
        
    def Update_warmup(self, input):
        return self.Update_Main(input.Index, input.close)
   
    def Update_Main(self, time, value):
        self.queue.appendleft(value) # neutral
        count = len(self.queue)
        self.Time = time # neutral

        self.IsReady = count == self.queue.maxlen
        
        #### start here the indicator calulation
        if self.IsReady:
            # [0:-1] is needed to remove last close since diff is one element shorter 
            close = np.array(self.queue)
            log_close = np.log(close)
            diffs = np.diff(log_close)
            self.Value = diffs.std() * math.sqrt(252) * 100

        return self.IsReady
        
    def WarmUp(self,history):
        for tuple in history.itertuples():
            self.Update_warmup(tuple)