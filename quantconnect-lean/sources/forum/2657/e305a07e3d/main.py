# ref
# Alexi Muci, A simple VIX Strategy, https://www.quantconnect.com/forum/discussion/2657/a-simple-vix-strategy
# Tony Cooper, Easy Volatility Investing, https://www.ssrn.com/abstract=2255327

from QuantConnect import *
from QuantConnect.Algorithm import *

import pandas as pd
import numpy as np

from my_custom_data import CboeVix, CboeVxV


class VIXStrategyByRatio(QCAlgorithm):
    
    def Initialize(self):
        # SVXY inception date 10/3/2011
        # VXX inception date 1/29/2009
        
        self.SetStartDate(2011, 10, 15)
        #self.SetStartDate(2019, 1, 15)
        self.SetEndDate(datetime.now().date() - timedelta(1))
        self.SetCash(10000)
            
        #self.SetBrokerageModel(BrokerageName.InteractiveBrokersBrokerage, AccountType.Margin) 
        # ^^ with a low alpha model that trades daily, you get eaten alive by brokerage fees if you close positions everyday with starting capital of 10k.
        self.SetBrokerageModel(BrokerageName.AlphaStreams)

        # add the #2 ETFs (short and long VIX futures)
        # swap xiv with svxy, since xiv is wiped out.
        self.XIV = self.AddEquity("SVXY", Resolution.Daily).Symbol # switched to svxy
        self.VXX = self.AddEquity("ZIV", Resolution.Daily).Symbol # switched to ziv
        self.SPY = self.AddEquity("SPY", Resolution.Daily).Symbol
        self.SHY = self.AddEquity("SHY", Resolution.Daily).Symbol
        
        self.SetBenchmark("SPY")
        
        # Define symbol and "type" of custom data: used for signal ratio
        self.VIX = self.AddData(CboeVix, "VIX").Symbol
        self.VXV = self.AddData(CboeVxV, "VXV").Symbol
        
        self.window_len = 252
        hist = self.History([self.VIX], self.window_len, Resolution.Daily)
        
        self.window_vix = RollingWindow[float](self.window_len)
        for close in hist.loc[self.VIX]['close']:
            self.window_vix.Add(close)
        
        self.window_vix_date = RollingWindow[str](self.window_len)
        for item in hist.index:
            self.window_vix_date.Add(item[-1].strftime('%Y-%m-%d'))
        
        hist = self.History([self.VXV], self.window_len, Resolution.Daily)
        
        self.window_vxv = RollingWindow[float](self.window_len)
        for close in hist.loc[self.VXV]['close']:
            self.window_vxv.Add(close)
            
        self.window_vxv_date = RollingWindow[str](self.window_len)
        for item in hist.index:
            self.window_vxv_date.Add(item[-1].strftime('%Y-%m-%d'))
            
        # Define the Schedules
        self.Schedule.On(
            self.DateRules.EveryDay(),
            self.TimeRules.AfterMarketOpen(self.XIV, 0),
            Action(self.Balance)
        )
        #self.Schedule.On(
        #    self.DateRules.EveryDay(),
        #    self.TimeRules.BeforeMarketClose(self.XIV, 5),
        #    Action(self.Close)
        #)
        self.SetWarmUp(timedelta(self.window_len))
        
    
    # TODO: verify data correctness.
    # TODO: is there a better way to collect data?    
    def OnData(self, data):
        
        if data.ContainsKey(self.VIX):
            self.window_vix.Add(data[self.VIX].Price)
            self.window_vix_date.Add(data.Time.strftime('%Y-%m-%d'))
            
        if data.ContainsKey(self.VXV):
            self.window_vxv.Add(data[self.VXV].Price)
            self.window_vxv_date.Add(data.Time.strftime('%Y-%m-%d'))
        
    def Close(self):
        for x in [self.SPY,self.SHY,self.XIV,self.VXX]:
            self.SetHoldings(x, 0.0)
            
    def Balance(self):

        if not self.window_vxv.IsReady: return
        if not self.window_vix.IsReady: return
        if not self.window_vxv_date.IsReady: return
        if not self.window_vix_date.IsReady: return
        
        # TODO: compute needs to be moved to ??? alpha compute method.
        # then alpha can be used to aid in construct portfolio.
        
        df = pd.DataFrame()
        # flip the data, so last item is the most current.
        vix_date_array = [i for i in self.window_vix_date][::-1]
        vxv_date_array = [i for i in self.window_vxv_date][::-1]
        vix_price = np.array([i for i in self.window_vix])[::-1]
        vxv_price = np.array([i for i in self.window_vxv])[::-1]
        
        df['vix_date'] = vix_date_array
        df['vxv_date'] = vxv_date_array
        df['VIX'] = vix_price
        df['VXV'] = vxv_price
        
        # avoid look ahead bias.
        df['VIX'] = df['VIX'].shift(1)
        df['VXV'] = df['VXV'].shift(1)
        
        df["cob"] = df["VIX"]/df["VXV"]
        
        # compute momentum of cob.
        # get z score of cob. if z score increases
        # it is likely that backwardation would happen
        df['mean'] = df['cob'].rolling(126).mean()
        df['sd'] = df['cob'].rolling(126).std()
        df['z'] = (df['cob']-df['mean'])/df['sd']
        df['dz'] = df['z'].pct_change()
        df['dzma'] = df['dz'].rolling(5).mean()
        
        df['cobma'] = df['cob'].rolling(10).median() # "Strategy 3, Vratio10 by Tony Cooper"
        cob = df["cobma"].iloc[-1]
        dzma = df['dzma'].iloc[-1]
        
        XIV_qnty = self.Portfolio[self.XIV].Quantity
        VXX_qnty = self.Portfolio[self.VXX].Quantity
        
        self.Log("{},{},{},{},{},{}".format(
            df['vix_date'].iloc[-1],
            df['vxv_date'].iloc[-1],
            df['VIX'].iloc[-1],
            df['VXV'].iloc[-1],
            cob,dzma))
        
        # cob = vix/vxv
        # cob < 1 , vix < vxv: contago
        # cob > 1 , vix > vxv: backwardation (1 mnth more expensive than 3 mnth future)
        # https://en.wikipedia.org/wiki/Contango
        # https://en.wikipedia.org/wiki/Normal_backwardation
        # 
        # np.nanpercentile(df['VIX/VXV'],[30,40,50,60,70,80,90])
        # >>> array([0.86649373, 0.88454818, 0.9025271 , 0.92344436, 0.94629521, 0.97491226, 1.01362785])
        
        #
        #     ___o .--.
        #   /___| |OO|
        #   /'   |_|  |_
        #       (_    _)
        #       | |   \
        #       | |oo_/sjw
        #
        # Don't say Tony Cooper didn't warn you about the Grim Reaper.

        # !prioritize fear
        # long volatility if trending towards backwardation at any time
        #if cob > 0.88 and dzma > 0:
        if cob > np.nanpercentile(df['cob'],[20])[0] and dzma > 0:
            situation = 'long_volatility'
            self.Log("long VOL")
            #self.Notify.Email("XXXX@gmail.com", "IB Algo Execution", "long VXX"); self.Log("long VOL")
            Insight(self.XIV, timedelta(days=1), InsightType.Price, InsightDirection.Down, confidence=1.0)
            Insight(self.VXX, timedelta(days=1), InsightType.Price, InsightDirection.Up, confidence=1.0)
            
        # short volatility if trending towards contago plus a threshold for absolute cob value.
        #elif cob < 0.97 and dzma < 0:
        elif cob < np.nanpercentile(df['cob'],[80])[0] or dzma < 0: # or gets better PSR than and... ? why?
            situation = 'short_volatility'
            self.Log("short VOL")
            #self.Notify.Email("XXXXX@gmail.com", "IB Algo Execution", "long XIV"); self.Log("short VOL")
            Insight(self.VXX, timedelta(days=1), InsightType.Price, InsightDirection.Down, confidence=1.0)
            Insight(self.XIV, timedelta(days=1), InsightType.Price, InsightDirection.Up, confidence=1.0)
        
        # flat ? - not really sure what to do - chicken mode
        else:
            situation = 'flat'
            self.Log("Flat")
            #self.Notify.Email("xxxxxxxxxx@gmail.com", "IB Algo Execution", "Flat position"); self.Log("Flat")
            Insight(self.XIV, timedelta(days=1), InsightType.Price, InsightDirection.Flat, confidence=0.3)
            Insight(self.VXX, timedelta(days=1), InsightType.Price, InsightDirection.Flat, confidence=0.3)
            
        iama_braveheart = {
            'short_volatility':{ self.SPY: 0.0, self.SHY: 0.0, self.XIV: 1.0, self.VXX: 0.0, },
            'flat':            { self.SPY: 0.3, self.SHY: 0.7, self.XIV: 0.0, self.VXX: 0.0, },
            'long_volatility': { self.SPY: 0.0, self.SHY: 0.0, self.XIV: 0.0, self.VXX: 1.0, },
        }
        ihave_babies_and_30_year_home_mortgage = { # blend in some SHY and SPY to reduce drawdowns.
            'short_volatility':{ self.SPY: 0.7, self.SHY: 0.0, self.XIV: 0.3, self.VXX: 0.0, },
            'flat':            { self.SPY: 0.5, self.SHY: 0.5, self.XIV: 0.0, self.VXX: 0.0, },
            'long_volatility': { self.SPY: 0.3, self.SHY: 0.7, self.XIV: 0.0, self.VXX: 0.0, },
        }
        
        # braveheart param:  PSR 41%, win/loss rate 59/41, max Drawdown 49%
        # alternative param: PSR 34%, win/loss rate 57/43, max Drawdown 18%
        mydict = ihave_babies_and_30_year_home_mortgage 
        for k,v in mydict[situation].items():
            self.SetHoldings(k,v)