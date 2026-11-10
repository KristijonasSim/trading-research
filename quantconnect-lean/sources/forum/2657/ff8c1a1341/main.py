from System import *
from QuantConnect import *
from QuantConnect.Algorithm import *
from QuantConnect.Data.Custom.CBOE import *
from QuantConnect.Python import PythonQuandl # quandl data not CLOSE
from QuantConnect.Data import SubscriptionDataSource
from QuantConnect.Python import PythonData
import pandas as pd
from my_custom_data import *  # QuandlFuture, CboeVix, CboeVxV
from QuantConnect.Python import PythonData # custom data

from datetime import date, timedelta, datetime
from decimal import Decimal
import numpy as np
from math import floor
import json

class QuandlFutures(PythonQuandl):
        def __init__(self):
            self.ValueColumnName = "open"

class VentralTachyonAtmosphericScrubbers(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2011, 10, 1)  # Set Start Date
        #self.SetStartDate(2018, 3, 20)
        self.SetEndDate(2020, 1, 1)
        self.SetCash(100000)  # Set Strategy Cash
        
        self.perc_qnty = 1
        self.selectedResolution = Resolution.Daily
        
        self.uvxy = self.AddEquity("UVXY", self.selectedResolution).Symbol
        self.svxy = self.AddEquity("SVXY", self.selectedResolution).Symbol
        
        self.spy = self.AddEquity("SPY", self.selectedResolution).Symbol
        self.tqqq = self.AddEquity("TQQQ", self.selectedResolution).Symbol
        self.spySma = self.SMA(self.spy, 25, self.selectedResolution, Field.Open)
        
        self.vixStr = "VIX"
        self.vxvStr = "VXV"
        self.vixsmStr = "VIX9D"
        self.AddData(CboeVix, "VIX")
        self.AddData(CboeVxv, "VXV")
        self.AddData(CboeVixsm, "VIX9D")
        
        self.macd = self.MACD("SPY", 12, 26, 6, MovingAverageType.Exponential, self.selectedResolution, Field.Open)
        
        self.yvixRatio = 0
        self.yvixCrossUp = False
        self.yspy = 0
        self.yspySma = 0

    def OnData(self, data):
        if self.vixStr not in data or self.vxvStr not in data: return
        
        vixPrice = data[self.vixStr].Open
        vxvPrice = data[self.vxvStr].Open
        vixsmPrice = None
        if self.vixsmStr in data:
            vixsmPrice = data[self.vixsmStr].Open
        
        uvxy_qnty = self.Portfolio[self.uvxy].Quantity
        svxy_qnty = self.Portfolio[self.svxy].Quantity
        tqqq_qnty = self.Portfolio[self.tqqq].Quantity
        
        vixRatio = vixPrice/vxvPrice
        #self.Plot("Vix/Vix3M", "Vix/Vix3M", vixRatio)
        #self.Plot("SVXY", "SVXY", self.Securities["SVXY"].Price)
        #self.Plot("SPY", "SPY", self.Securities["SPY"].Open)
        #self.Plot("MACD", "Source", self.macd.Current.Value)
        #self.Plot("MACD", "Signal", self.macd.Signal.Current.Value)
        
        vixCrossUp = False
        if vixsmPrice:
            vixCrossUp = vixsmPrice > vixPrice
            
        macdLong = self.macd.Current.Value < self.macd.Signal.Current.Value
        
        inLong = uvxy_qnty != 0
        inShort = svxy_qnty != 0
        inRest = tqqq_qnty != 0 
        
        shortEntry = (vixRatio < 0.95) and not vixCrossUp and not (self.Securities["SPY"].Open <= self.spySma.Current.Value and self.yspy > self.yspySma)
        shortExit = inShort and (not shortEntry)
        
        longEntry = vixRatio > 1.05 and vixCrossUp and macdLong
        longExit = inLong and (not longEntry)
        
        if shortExit or longExit:
            self.Liquidate()
            if not inRest and longExit:
                self.SetHoldings(self.tqqq, self.perc_qnty)
            return
        
        if (shortEntry):
            if inLong:
                self.Liquidate(self.uvxy)
            if inRest:
                self.Liquidate(self.tqqq)
            if not inShort:
                self.SetHoldings(self.svxy, self.perc_qnty)
        
        if (longEntry):
            if inShort:
                self.Liquidate(self.svxy)
            if inRest:
                self.Liquidate(self.tqqq)
            if not inLong:
                self.SetHoldings(self.uvxy, self.perc_qnty)
        
        self.yvixRatio = vixRatio
        self.yvixCrossUp = vixCrossUp
        self.yspy = self.Securities["SPY"].Open
        self.yspySma = self.spySma.Current.Value