"""
SEL(stock selection part)
Based on the 'Momentum Strategy with Market Cap and EV/EBITDA' strategy introduced by Jing Wu, 6 Feb 2018
adapted and recoded by Jack Simonson, Goldie Yalamanchi, Vladimir, Peter Guenther, Leandro Maia, Simone Pantaleoni, Mirko Vari(Strongs)
https://www.quantconnect.com/forum/discussion/3377/momentum-strategy-with-market-cap-and-ev-ebitda/p1
https://www.quantconnect.com/forum/discussion/9678/quality-companies-in-an-uptrend/p1
https://www.quantconnect.com/forum/discussion/9632/amazing-returns-superior-stock-selection-strategy-superior-in-amp-out-strategy/p1

I/O(in & out part)
The Distilled Bear in & out algo
based on Dan Whitnable's 22 Oct 2020 algo on Quantopian. 
Dan's original notes: 
"This is based on Peter Guenther great “In & Out” algo.
Included Tentor Testivis recommendation to use volatility adaptive calculation of WAIT_DAYS and RET.
Included Vladimir's ideas to eliminate fixed constants
Help from Thomas Chang"

https://www.quantopian.com/posts/new-strategy-in-and-out
https://www.quantconnect.com/forum/discussion/9597/the-in-amp-out-strategy-continued-from-quantopian/
"""


from QuantConnect.Data.UniverseSelection import *
import math
import numpy as np
import pandas as pd
import scipy as sp
from This_Universe_Module import this_universe_module
from This_Alpha_Module import this_alpha_module


class EarningsFactorWithMomentum_InOut(QCAlgorithm):

    def Initialize(self):

        self.SetStartDate(2008, 1, 1)  #Set Start Date
        #self.SetEndDate(2008, 3, 1)  #Set Start Date
        self.cap = 10000
        self.SetCash(self.cap)
        
        self.averages = {}
        res = Resolution.Hour
        
        self.param_dict={}
        
        # Holdings
        ### 'Out' holdings and weights
        self.BND1 = self.AddEquity('TLT', res).Symbol #TLT; TMF for 3xlev
        self.quantity = {self.BND1: 0}
        
        ##### In & Out parameters #####
        # Feed-in constants
        self.param_dict['INI_WAIT_DAYS'] = 15  # out for 3 trading weeks
        self.param_dict['wait_days'] = self.param_dict['INI_WAIT_DAYS']
        

        # Specific variables
        self.param_dict['DISTILLED_BEAR'] = 1#999
        self.param_dict['BE_IN'] = 1#999
        self.param_dict['BE_IN_PRIOR'] = 0
        self.param_dict['VOLA_LOOKBACK'] = 126
        self.param_dict['WAITD_CONSTANT'] = 85
        self.param_dict['DCOUNT'] = 0 # count of total days since start
        self.param_dict['OUTDAY'] = (-self.param_dict['INI_WAIT_DAYS']+1) # dcount when self.be_in=0, initial setting ensures trading right away
        
        # set a warm-up period to initialize the indicator
        # self.SetWarmUp(timedelta(350))
        # no warmup, will use History instead because some of the day_count items are counting during warmup
        
        ##### Momentum & fundamentals strategy parameters #####
        self.UniverseSettings.Resolution = res
        self.param_dict['num_coarse'] = 100#200
        self.param_dict['num_screener'] = 20#100  # changed from 15
        self.param_dict['num_stocks'] = 10 # lowered from 10
        self.param_dict['formation_days'] = 126
        self.param_dict['lowmom'] = False
        self.data = {}
        self.param_dict['setrebalancefreq'] = 60 # X days, update universe and momentum calculation
        self.param_dict['updatefinefilter'] = 0
        self.param_dict['symbols'] = None
        self.param_dict['reb_count'] = 0
        
        #self.Schedule.On(
        #    self.DateRules.EveryDay(),
        #    self.TimeRules.AfterMarketOpen('SPY', 30), # reduced time 
        #    self.rebalance_when_out_of_the_market)
        
        #self.Schedule.On(
        #    self.DateRules.EveryDay(), 
        #    self.TimeRules.BeforeMarketClose('SPY', 0), 
        #    self.record_vars)  
        
        # Benchmark = record SPY
        self.spy = []
        
        
        

        
        # Warm up history
        self.param_dict['lookback'] = 126

        
        
        
        ### do the framework magic
        self.AddUniverseSelection(this_universe_module(param_dict=self.param_dict, averages_dict=self.averages))
        self.AddAlpha(this_alpha_module(param_dict=self.param_dict, data_dict=self.data, when_trigger=30, assets_dict=None, assets_history_df=None, quantity_dict=self.quantity)) # the original schedule event now sits in the alpha_model
        self.SetPortfolioConstruction( EqualWeightingPortfolioConstructionModel())
        self.SetExecution( ImmediateExecutionModel())
        self.AddRiskManagement( NullRiskManagementModel())
        
        
        
   
