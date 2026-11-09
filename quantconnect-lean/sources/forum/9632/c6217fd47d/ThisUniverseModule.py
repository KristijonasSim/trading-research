# QUANTCONNECT.COM - Democratizing Finance, Empowering Individuals.
# Lean Algorithmic Trading Engine v2.0. Copyright 2014 QuantConnect Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from clr import AddReference
AddReference("System")
AddReference("QuantConnect.Common")
AddReference("QuantConnect.Algorithm.Framework")


from QuantConnect.Data.UniverseSelection import *
from Selection.FundamentalUniverseSelectionModel import FundamentalUniverseSelectionModel
from itertools import groupby
from math import ceil
import numpy as np


class this_universe_module(FundamentalUniverseSelectionModel):


    def __init__(self, filterFineData = True, universeSettings = None, securityInitializer = None, param_dict=None, averages_dict=None):
        '''Initializes a new default instance of the QC500UniverseSelectionModel'''
        super().__init__(filterFineData, universeSettings, securityInitializer)
        self.param_dict=param_dict
        self.averages=averages_dict


    def SelectCoarse(self, algorithm, coarse):
        # Update at the beginning (by setting self.OUTDAY = -self.INI_WAIT_DAYS), every X days (rebalance frequency), and one day before waitdays are up
        algorithm.Log('doing universe selection...current DCOUNT is {}'.format(self.param_dict['DCOUNT']))
        if not (((self.param_dict['DCOUNT']-self.param_dict['reb_count'])==self.param_dict['setrebalancefreq']) or (self.param_dict['DCOUNT'] == self.param_dict['OUTDAY'] + self.param_dict['wait_days'] - 1)):
            self.param_dict['updatefinefilter'] = 0
            return Universe.Unchanged
        
        self.param_dict['updatefinefilter'] = 1 
        
        # drop stocks which have no fundamental data or have too low prices
        selected = [x for x in coarse if (x.HasFundamentalData) and (float(x.Price) > 5)]

        # We are going to use a dictionary to refer the object that will keep the moving averages
        for cf in selected:
            symbol = cf.Symbol
            if cf.Symbol not in self.averages:
                self.averages[cf.Symbol] = SymbolDataVolume(cf.Symbol, 21, 5, 504)

            # Updates the SymbolData object with current EOD price
            avg = self.averages[cf.Symbol]
            avg.update(cf.EndTime, cf.AdjustedPrice, cf.DollarVolume)

        # Filter the values of the dict: we only want up-trending securities

        #values = list(filter(lambda sd: sd.smaw.Current.Value > 0, self.averages.values()))
        values = list(filter(lambda sd: sd.smaw.Current.Value > 0, self.averages.values()))

        values.sort(key=lambda x: (x.smaw.Current.Value), reverse=True)
        #values.sort(key=lambda x: (x.volume_ratiol), reverse=True)

        # we need to return only the symbol objects
        coarse_output=[ x.symbol for x in values[:self.param_dict['num_coarse']] ]
        algorithm.Log('coarse output len is {}'.format(len(coarse_output)))
        return coarse_output
        
        
        
        

    def SelectFine(self, algorithm, fine):
        if self.param_dict['updatefinefilter'] == 0:
            return Universe.Unchanged
             
        filtered_fundamental = [x for x in fine if  
                                 x.FinancialStatements.IncomeStatement.NetIncome.TwelveMonths and
                                 x.FinancialStatements.CashFlowStatement.CashFlowFromContinuingOperatingActivities.TwelveMonths and
                                 x.OperationRatios.ROA.ThreeMonths and x.OperationRatios.ROA.OneYear and
                                 x.FinancialStatements.BalanceSheet.ShareIssued.ThreeMonths and x.FinancialStatements.BalanceSheet.ShareIssued.TwelveMonths and
                                 x.OperationRatios.GrossMargin.ThreeMonths and x.OperationRatios.GrossMargin.OneYear and
                                 x.OperationRatios.LongTermDebtEquityRatio.ThreeMonths and x.OperationRatios.LongTermDebtEquityRatio.OneYear and 
                                 x.OperationRatios.CurrentRatio.ThreeMonths and x.OperationRatios.CurrentRatio.OneYear and 
                                 x.OperationRatios.AssetsTurnover.ThreeMonths and x.OperationRatios.AssetsTurnover.OneYear and x.ValuationRatios.NormalizedPERatio]
                                 
        sortedByfactor1 = [x for x in fine if FScore(x.FinancialStatements.IncomeStatement.NetIncome.TwelveMonths,
                            x.FinancialStatements.CashFlowStatement.CashFlowFromContinuingOperatingActivities.TwelveMonths,
                            x.OperationRatios.ROA.ThreeMonths, x.OperationRatios.ROA.OneYear,
                            x.FinancialStatements.BalanceSheet.ShareIssued.ThreeMonths, x.FinancialStatements.BalanceSheet.ShareIssued.TwelveMonths,  
                            x.OperationRatios.GrossMargin.ThreeMonths, x.OperationRatios.GrossMargin.OneYear,
                            x.OperationRatios.LongTermDebtEquityRatio.ThreeMonths, x.OperationRatios.LongTermDebtEquityRatio.OneYear,
                            x.OperationRatios.CurrentRatio.ThreeMonths, x.OperationRatios.CurrentRatio.OneYear,
                            x.OperationRatios.AssetsTurnover.ThreeMonths, x.OperationRatios.AssetsTurnover.OneYear).ObjectiveScore() > 6]                        
         
        top = sorted(sortedByfactor1, key = lambda x: x.ValuationRatios.NormalizedPERatio, reverse=False)[:self.param_dict['num_screener']]
        self.param_dict['symbols'] = [x.Symbol for x in top]
        self.param_dict['updatefinefilter'] = 0
        self.param_dict['reb_count'] = self.param_dict['DCOUNT']
        algorithm.Log('done universe selection, total {}'.format(len(self.param_dict['symbols'])))
        return self.param_dict['symbols']
        
        
        
        
class SymbolDataVolume(object):
    def __init__(self, symbol, period, periodw, periodlt):
        self.symbol = symbol
        #self.tolerance = 1.01
        self.tolerance = 0.95
        self.fast = ExponentialMovingAverage(10)
        self.slow = ExponentialMovingAverage(21)
        self.is_uptrend = False
        self.scale = 0
        self.volume = 0
        self.volume_ratio = 0
        self.volume_ratiow = 0
        self.volume_ratiol = 0
        self.sma = SimpleMovingAverage(period)
        self.smaw = SimpleMovingAverage(periodw)
        self.smalt = SimpleMovingAverage(periodlt)

    def update(self, time, value, volume):
        self.volume = volume


        if self.smaw.Update(time, volume):
            # get ratio of this volume bar vs previous 10 before it.
            if self.smaw.Current.Value != 0:
                self.volume_ratiow = volume / self.smaw.Current.Value
        if self.sma.Update(time, volume):
            # get ratio of this volume bar vs previous 10 before it.
            if self.sma.Current.Value != 0:
                self.volume_ratio = self.smaw.Current.Value / self.sma.Current.Value

        if self.smalt.Update(time, volume):
            if self.smalt.Current.Value != 0 and self.smaw.Current.Value != 0:
                self.volume_ratiol = self.smaw.Current.Value / self.smalt.Current.Value

            
        if self.fast.Update(time, value) and self.slow.Update(time, value):
            fast = self.fast.Current.Value
            slow = self.slow.Current.Value
            #self.is_uptrend = fast > slow * self.tolerance
            self.is_uptrend = (fast > (slow * self.tolerance)) and (value > (fast * self.tolerance))

        if self.is_uptrend:
            self.scale = (fast - slow) / ((fast + slow) / 2.0)
            
            
        
class FScore(object):
    def __init__(self, netincome, operating_cashflow, roa_current,
                 roa_past, issued_current, issued_past, grossm_current, grossm_past,
                 longterm_current, longterm_past, curratio_current, curratio_past,
                 assetturn_current, assetturn_past):
        self.netincome = netincome
        self.operating_cashflow = operating_cashflow
        self.roa_current = roa_current
        self.roa_past = roa_past
        self.issued_current = issued_current
        self.issued_past = issued_past
        self.grossm_current = grossm_current
        self.grossm_past = grossm_past
        self.longterm_current = longterm_current
        self.longterm_past = longterm_past
        self.curratio_current = curratio_current
        self.curratio_past = curratio_past
        self.assetturn_current = assetturn_current
        self.assetturn_past = assetturn_past

    def ObjectiveScore(self):
        fscore = 0
        fscore += np.where(self.netincome > 0, 1, 0)
        fscore += np.where(self.operating_cashflow > 0, 1, 0)
        fscore += np.where(self.roa_current > self.roa_past, 1, 0)
        fscore += np.where(self.operating_cashflow > self.roa_current, 1, 0)
        fscore += np.where(self.longterm_current <= self.longterm_past, 1, 0)
        fscore += np.where(self.curratio_current >= self.curratio_past, 1, 0)
        fscore += np.where(self.issued_current <= self.issued_past, 1, 0)
        fscore += np.where(self.grossm_current >= self.grossm_past, 1, 0)
        fscore += np.where(self.assetturn_current >= self.assetturn_past, 1, 0)
        return fscore