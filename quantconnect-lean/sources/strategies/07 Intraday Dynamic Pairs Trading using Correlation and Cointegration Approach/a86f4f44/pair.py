import numpy as np
import pandas as pd
import datetime as datetime
import statsmodels.formula.api as sm
import statsmodels.tsa.stattools as ts

class pairs(object):

    def __init__(self,a,b):
        self.a = a
        self.b = b
        self.name = str(a) + ':' + str(b)
        self.df = pd.concat([a.df,b.df],axis = 1).dropna()
        self.num_bar = self.df.shape[0]
        self.cor = self.df.corr().ix[0][1]
        self.error = 0
        self.last_error = 0
        self.a_price = []
        self.a_date = []
        self.b_price = []
        self.b_date = []

    def cor_update(self):
        self.cor = self.df.corr().ix[0][1]

    def cointegration_test(self):
        self.model = sm.ols(formula = '%s ~ %s'%(str(self.a),str(self.b)), data = self.df).fit()
        self.adf = ts.adfuller(self.model.resid,autolag = 'BIC')[0]
        self.mean_error = np.mean(self.model.resid)
        self.sd = np.std(self.model.resid)

    def price_record(self,data_a,data_b):
        self.a_price.append(float(data_a.Close))
        self.a_date.append(data_a.EndTime)
        self.b_price.append(float(data_b.Close))
        self.b_date.append(data_b.EndTime)

    def df_update(self):
        new_df = pd.DataFrame({str(self.a):self.a_price,str(self.b):self.b_price},index = [self.a_date]).dropna()
        self.df = pd.concat([self.df,new_df])
        self.df = self.df.tail(self.num_bar)
        for i in [self.a_price,self.a_date,self.b_price,self.b_date]:
            i = []