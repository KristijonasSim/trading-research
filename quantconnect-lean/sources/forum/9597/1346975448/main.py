#region imports
from AlgorithmImports import *
#endregion
import decimal as d
from datetime import datetime, timedelta
from decimal import Decimal
import calendar

"""

class MyAlgo(QCAlgorithm):
def Initialize(self):
AddEquity("SPY")

self.Schedule.On(self.DateRules.Every(DayOfWeek.Monday, DayOfWeek.Monday), \
self.TimeRules.AfterMarketOpen(self.spy), \
Action(self.open_positions))

self.Schedule.On(self.DateRules.Every(DayOfWeek.Friday, DayOfWeek.Friday), \
self.TimeRules.BeforeMarketClose(self.spy, 30), \
Action(self.close_positions))

def open_positions(self):
self.SetHoldings("SPY", 0.10)

def close_positions(self):
self.Liquidate("SPY")
"""

class VigilantAssetAllocationAlgorithm(QCAlgorithm):

    def Initialize(self):
        
        #self.SetBrokerageModel(BrokerageName.QuantConnectBrokerage, AccountType.Margin)
        self.SetCash(100000)
        self.SetStartDate(2008, 1, 1)
        self.LastRotationTime = datetime.min
        self.RotationInterval = timedelta(days=1)
        self.first = True
        #self.AddRiskManagement(MaximumDrawdownPercentPerSecurity(0.025))
        #self.AddRiskManagement(TrailingStopRiskManagementModel(0.025))
        self.spy = self.AddEquity("SPY", Resolution.Daily).Symbol  
        self.sma = self.SMA(self.spy, 50, Resolution.Daily) 

        #These are the growth symbols we'll rotate through
        GrowthSymbols = ["EFA","SPY","EEM","QQQ", "AAG"]
                        
        # these are the safety symbols we go to when things are looking bad for growth
        SafetySymbols = ["LQD", 
                         "IEF", 
                         "BIL"]
                         
        # I split the indicators into two different sets to make it easier for illustrative purposes below.
        # Storing all risky asset data into SymbolData object
        self.SymbolData = []
        for symbol in list(GrowthSymbols):
            self.AddSecurity(SecurityType.Equity, symbol, Resolution.Minute).SetLeverage(10)
            self.oneMonthPerformance = self.MOMP(symbol, 21, Resolution.Daily)
            self.threeMonthPerformance = self.MOMP(symbol, 63, Resolution.Daily)
            self.sixMonthPerformance = self.MOMP(symbol, 126, Resolution.Daily)
            self.twelveMonthPerformance = self.MOMP(symbol, 252, Resolution.Daily)
            self.SymbolData.append([symbol, self.oneMonthPerformance, self.threeMonthPerformance, self.sixMonthPerformance, self.twelveMonthPerformance])  
        # Storing all risk-free data into SafetyData object
        self.SafetyData = []
        for symbol in list(SafetySymbols):
            self.AddSecurity(SecurityType.Equity, symbol, Resolution.Minute).SetLeverage(10)
            self.oneMonthPerformance = self.MOMP(symbol, 21, Resolution.Daily)
            self.threeMonthPerformance = self.MOMP(symbol, 63, Resolution.Daily)
            self.sixMonthPerformance = self.MOMP(symbol, 126, Resolution.Daily)
            self.twelveMonthPerformance = self.MOMP(symbol, 252, Resolution.Daily)
            #self.SymbolData.append([symbol, self.oneMonthPerformance, self.threeMonthPerformance, self.sixMonthPerformance, self.twelveMonthPerformance])
            self.SafetyData.append([symbol, self.oneMonthPerformance, self.threeMonthPerformance, self.sixMonthPerformance, self.twelveMonthPerformance])

        self.Schedule.On(self.DateRules.MonthEnd('BIL'), self.TimeRules.AfterMarketOpen("BIL", 0), self.Rebalance)
        self.rebalance = True 
        
    def OnData(self, data):
        
        if self.first:
            self.first = False
            #self.LastRotationTime = self.Time
            return
        #delta = self.Time - self.LastRotationTime
        #if delta > self.RotationInterval:
        if self.rebalance == True:
            #self.LastRotationTime = self.Time
            
            ##Using the Score class at the bottom, compute the score for each risky asset.
            ##This approach overweights the front month momentum value and progressively underweights older momentum values
            
            #currentHoldings = all_symbols = [ x for x in self.Portfolio.Keys ]
            
            orderedObjScores = sorted(self.SymbolData, key=lambda x: Score(x[1].Current.Value,x[2].Current.Value,x[3].Current.Value,x[4].Current.Value).ObjectiveScore(), reverse=True)
            
            ##Using the Score class at the bottom, compute the score for each risk-free asset.
            orderedSafeScores = sorted(self.SafetyData, key=lambda x: Score(x[1].Current.Value,x[2].Current.Value,x[3].Current.Value,x[4].Current.Value).ObjectiveScore(), reverse=True)
            
            ##Count the number of risky assets with negative momentum scores and store in N. If all four of the offensive assets exhibit positive momentum scores, 
            ##select the offensive asset with the highest score and allocate 100% of the portfolio to that asset at the close
            N = 0
            for x in orderedObjScores:
                self.Log(">>SCORE>>" + x[0] + ">>" + str(Score(x[1].Current.Value,x[2].Current.Value,x[3].Current.Value,x[4].Current.Value).ObjectiveScore()))
                if Score(x[1].Current.Value,x[2].Current.Value,x[3].Current.Value,x[4].Current.Value).ObjectiveScore() < 0:
                    N += 1
                   
            # pick which one is best from risky and risk-free symbols and store for use below
            bestGrowth = orderedObjScores[0]
            secondGrowth = orderedObjScores[1]
            bestSafe = orderedSafeScores[0]
            #secondSafe = orderedSafeScores[1]
            
            ## If any of the four risky assets exhibit negative momentum scores, select the risk-free asset (LQD, IEF or SHY) with the highest score 
            ## (regardless of whether the score is > 0) and allocate 100% of the portfolio to that asset at the close. 
            if N > 0:
                self.Log("PREBUY>>LIQUIDATE>>")
                self.Liquidate()
            #    self.Log(">>BUY>>" + str(bestSafe[0]) + "@" + str(Decimal(100) * bestSafe[1].Current.Value))
                self.SetHoldings(bestSafe[0], 1) 
                #self.SetHoldings(currentHoldings[0], .75) 
                #self.SetHoldings(secondSafe[0], .5) 
                self.rebalance = False
            else:                
                self.Log("PREBUY>>LIQUIDATE>>")
                self.Liquidate()
            #    self.Log(">>BUY>>" + str(bestGrowth[0]) + "@" + str(Decimal(100) * bestGrowth[1].Current.Value))
                self.SetHoldings(bestGrowth[0], 1) 
                #self.SetHoldings(currentHoldings, .75) 
                #self.SetHoldings(secondGrowth[0], .5) 
                self.rebalance = False

    def Rebalance(self):
        self.rebalance = True
        self.Debug("Rebalance") 
     

class Score(object):
    
    def __init__(self,oneMonthPerformanceValue,threeMonthPerformanceValue,sixMonthPerformanceValue,twelveMonthPerformanceValue):
        self.oneMonthPerformance = oneMonthPerformanceValue
        self.threeMonthPerformance = threeMonthPerformanceValue
        self.sixMonthPerformance = sixMonthPerformanceValue
        self.twelveMonthPerformance = twelveMonthPerformanceValue
        
    def ObjectiveScore(self):
        weight1 = 12
        weight2 = 4
        weight3 = 2
        return (weight1 * self.oneMonthPerformance) + (weight2 * self.threeMonthPerformance) + (weight3 * self.sixMonthPerformance) + self.twelveMonthPerformance