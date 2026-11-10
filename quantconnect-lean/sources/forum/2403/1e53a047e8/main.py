import numpy as np
import pandas as pd

class BasicTemplateAlgorithm(QCAlgorithm):
	def __init__(self):
		self.symbols = ['MDY','IEV','EEM','ILF','EPP','EDV','SHY']
		self.back_period = 73

	def Initialize(self):
		self.SetCash(100000)
		self.SetStartDate(2010,1,1)
		# self.SetEndDate(2016,2,1)
		
		self.spy = self.AddEquity('SPY', Resolution.Daily).Symbol
		
		for i in range(len(self.symbols)):
			symbol = self.AddEquity(self.symbols[i], Resolution.Daily).Symbol
			self.symbols[i] = symbol
			
		self.Schedule.On(self.DateRules.MonthStart(self.spy), 
		self.TimeRules.AfterMarketOpen(self.spy,5), Action(self.rebalance))

	def OnData(self, slice):
		pass
	
# calculate historical return and volatility for each stock
	def get_history(self):
		history = self.History(self.back_period, Resolution.Daily)
		for i in self.symbols:
			bars = map(lambda x: x[i], history)
			i.prices = pd.Series([float(x.Close) for x in bars])
			vol = np.mean(pd.rolling_std(i.prices, 20)*np.sqrt(self.back_period/20.0))
			i.volatility = vol/i.prices[0]
			i.ret = (i.prices.iloc[-1] - i.prices.iloc[0])/i.prices.iloc[0]

# normalise the mesures of returns and volatilities
	def normalise(self):
		rets = [x.ret for x in self.symbols]
		vols = [x.volatility for x in self.symbols]
		self.ret_max, self.ret_min = max(rets), min(rets)
# vol_min is actually the max volatility. min means low score on this.
		self.vol_min, self.vol_max = max(vols), min(vols)
		
# select the best one with the highest score.
	def select(self):
		self.get_history()
		self.normalise()
		for i in self.symbols:
			ret = (i.ret - self.ret_min)/(self.ret_max - self.ret_min)
			vol = (i.volatility - self.vol_min)/(self.vol_max - self.vol_min)
			i.score = ret*0.7 + vol*0.3
			
		select = sorted(self.symbols, key = lambda x: x.score, reverse = True)
		return select[0]
		
	def rebalance(self):
		target = self.select()
		
		if self.Portfolio[target].Quantity != 0:
			return
		
		self.Liquidate()
		self.SetHoldings(target,1)