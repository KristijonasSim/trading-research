import numpy as np
from scipy import stats
from statsmodels.distributions.empirical_distribution import ECDF
from scipy.stats import kendalltau, pearsonr, spearmanr
from scipy.optimize import minimize
from scipy.integrate import quad
import sys

class CopulaPairsTradingAlgorithm(QCAlgorithm):
    
    def Initialize(self):
        
        ## Initialise the data and resolution required, as well as the cash and start-end dates for your algorithm. All algorithms must initialized.
        
        self.SetStartDate(2010,1,1)
        self.SetEndDate(2018,11,11)
        self.SetCash(100000)
        self.numdays = 1000  # set the length of formation period which determine the copula we use
        self.lookbackdays = 250 # set the length of history data in trading period
        self.cap_CL = 0.95  # set the cap confidence level
        self.floor_CL = 0.05 # set the floor confidence level
        
        self.ticker = self._pair_selection()
        
        ## Pull history daily close data of past one year
        self.syl = []
        for i in self.ticker:
            equity = self.AddSecurity(SecurityType.Equity, i, Resolution.Daily)
            self.syl.append(equity.Symbol.Value)
    
        self.price_list = {}
        self.price_list[self.syl[0]] = []
        self.price_list[self.syl[1]] = []
        
        history = self.History(self.syl, self.numdays,Resolution.Daily)
        close = history['close'].unstack(level=0) 
        logreturn = (np.log(close) - np.log(close.shift(1))).dropna()
        x, y = logreturn[self.ticker[0]], logreturn[self.ticker[1]]        
        logreturn={} # A dictionary to store the history log return series of paired stocks 
        
        ''' Convert the two returns series to two uniform values u and v using the empirical distribution functions '''

        ecdf_x, ecdf_y  = ECDF(x), ECDF(y)
        u, v = [ecdf_x(a) for a in x], [ecdf_y(a) for a in y]

        # compute the Akaike Information Criterion (AIC) for different copulas and choose copula with minimum AIC
        
        self.family = ['clayton', 'frank', 'gumbel']
        tau = kendalltau(x, y)[0]  # estimate Kendall'rank correlation
        AIC ={}  # generate a dict with key being the copula family, value = [theta, AIC]
        for i in self.family:
            lpdf = [self._lpdf_copula(i, float(self._parameter(i,tau)), x, y) for (x, y) in zip(u, v)]
            # Replace nan with zero and inf with finite numbers in lpdf list 
            lpdf = np.nan_to_num(lpdf) 
            loglikelihood = sum(lpdf)
            AIC[i] = [self._parameter(i,tau), -2*loglikelihood + 2]
        # choose the copula with the minimum AIC  
        self.copula = min(AIC.items(), key = lambda x: x[1][1])[0]  
        self.Log(str(self.copula))
        self.Log(str(AIC))
        
        # schedule an event to fire on first day each month for a security 
        # the action compute the mispricing indices to generate the trading signals 
        self.Schedule.On(self.DateRules.MonthStart(self.syl[0]), self.TimeRules.AfterMarketOpen(self.syl[0]), Action(self._set_signal))

    def OnData(self,data):
        for i in self.syl:
            if data.Bars.ContainsKey(i):
                self.price_list[i].append(self.Portfolio[i].Price)
        
        # compute today's log return of 2 stocks
        if len(self.price_list[self.syl[0]]) < 2 or len(self.price_list[self.syl[1]]) < 2: return
        else: 
            return_x = np.log(float(self.price_list[self.syl[0]][-1]/self.price_list[self.syl[0]][-2]))
            return_y = np.log(float(self.price_list[self.syl[1]][-1]/self.price_list[self.syl[1]][-2]))
        
        # Convert the two returns to uniform values u and v using the empirical distribution functions
        u_value = self.ecdf_x(return_x)
        v_value = self.ecdf_y(return_y)
        
        # Compute the mispricing indices for u and v by using estimated copula
        self._misprice_index(self.copula, self.theta, u_value, v_value)
        quantity = float(self.CalculateOrderQuantity(self.syl[1],0.4))
        if self.MI_u_v < self.floor_CL and self.MI_v_u > self.cap_CL:
            if self.Portfolio[self.syl[0]].Quantity < 0 and self.Portfolio[self.syl[1]].Quantity > 0:
                self.Liquidate()
                quantity = float(self.CalculateOrderQuantity(self.syl[1],0.4))
                self.Sell(self.syl[1], 1 * quantity )
                self.Buy(self.syl[0], self.coef * quantity)
            else:
                self.Sell(self.syl[1], 1 * quantity )
                self.Buy(self.syl[0], self.coef * quantity)    
                
        elif self.MI_u_v > self.cap_CL and self.MI_v_u < self.floor_CL:
            if self.Portfolio[self.syl[0]].Quantity > 0 and self.Portfolio[self.syl[1]].Quantity < 0:
                self.Liquidate()
                quantity = float(self.CalculateOrderQuantity(self.syl[1],0.4))
                self.Buy(self.syl[1], 1 * quantity )
                self.Sell(self.syl[0], self.coef * quantity)
            else:
                self.Buy(self.syl[1], 1 * quantity )
                self.Sell(self.syl[0], self.coef * quantity)

    
    def _set_signal(self):
        
        history = self.History(self.ticker, self.lookbackdays,Resolution.Daily)
       
        # generate the log return series of paired stocks
        close = history['close'].unstack(level=0) 
        logreturn = (np.log(close) - np.log(close.shift(1))).dropna()
        x, y = logreturn[self.ticker[0]], logreturn[self.ticker[1]]
 
        # estimate Kendall'rank correlation each trading day
        tau = kendalltau(x, y)[0] 
        
        # etstimate the copula parameter: theta
        self.theta = self._parameter(self.copula, tau)
        
        # simulate the empirical distribution function for returns of two paired stocks
        self.ecdf_x, self.ecdf_y  = ECDF(x), ECDF(y) 
        
        # run linear regression over the two history return series
        self.coef = stats.linregress(x,y).slope
      
       
    def _parameter(self, family, tau):
        
        ''' 
        estimate the parameters for three kinds of Archimedean copulas
        According to association between Archimedean copulas and the Kendall rank correlation measure
        '''
        
        if  family == 'clayton':
            return 2*tau/float(1-tau)
        
        elif family == 'frank':
            
            '''
            debye = quad(integrand, sys.float_info.epsilon, theta)[0]/theta  is first order Debye function
            frank_fun is the squared difference
            Minimize the frank_fun would give the parameter theta for the frank copula 
            ''' 
            
            integrand = lambda t: t/(np.exp(t)-1)  # generate the integrand
            frank_fun = lambda theta: ((tau - 1)/4.0  - (quad(integrand, sys.float_info.epsilon, theta)[0]/theta - 1)/theta)**2
            
            return minimize(frank_fun, 4, method='BFGS', tol=1e-5).x 
        
        elif family == 'gumbel':
            return 1/float(1-tau)
            
    
    def _lpdf_copula(self, family, theta, u, v):
        
        # Estimate the log probability density function of three kinds of Archimedean copulas
        
        if  family == 'clayton':
            pdf = (theta+1) * ((u**(-theta)+v**(-theta)-1)**(-2-1/theta)) * (u**(-theta-1)*v**(-theta-1))
            
        elif family == 'frank':
            num = -theta * (np.exp(-theta)-1) * (np.exp(-theta*(u+v)))
            denom = ((np.exp(-theta*u)-1) * (np.exp(-theta*v)-1) + (np.exp(-theta)-1))**2
            pdf = num/denom
            
        elif family == 'gumbel':
            A = (-np.log(u))**theta + (-np.log(v))**theta
            c = np.exp(-A**(1/theta))
            pdf = c * (u*v)**(-1) * (A**(-2+2/theta)) * ((np.log(u)*np.log(v))**(theta-1)) * (1+(theta-1)*A**(-1/theta))
            
        return np.log(pdf)
    
    def _misprice_index(self, family, theta, u, v):
    
        '''
        Calculate mispricing index for every day in the trading period by using estimated copula
        Mispricing indices are the conditional probability P(U < u | V = v) and P(V < v | U = u)
        '''
    
        if  family == 'clayton':
            self.MI_u_v = v**(-theta-1) * (u**(-theta)+v**(-theta)-1)**(-1/theta-1) # P(U<u|V=v)
            self.MI_v_u = u**(-theta-1) * (u**(-theta)+v**(-theta)-1)**(-1/theta-1) # P(V<v|U=u)
    
        elif family == 'frank':
            A = (np.exp(-theta*u)-1) * (np.exp(-theta*v)-1) + (np.exp(-theta*v)-1)
            B = (np.exp(-theta*u)-1) * (np.exp(-theta*v)-1) + (np.exp(-theta*u)-1)
            C = (np.exp(-theta*u)-1) * (np.exp(-theta*v)-1) + (np.exp(-theta)-1)
            self.MI_u_v = B/float(C)
            self.MI_v_u = A/float(C)
        
        elif family == 'gumbel':
            A = (-np.log(u))**theta + (-np.log(v))**theta
            C_uv = np.exp(-A**(1/theta))   # C_uv is gumbel copula function C(u,v)
            self.MI_u_v = C_uv * (A**((1-theta)/theta)) * (-np.log(v))**(theta-1) * (1.0/v)
            self.MI_v_u = C_uv * (A**((1-theta)/theta)) * (-np.log(u))**(theta-1) * (1.0/u)
            
    def _pair_selection(self):
        
        tick_syl =  [["QQQ","XME","TNA","FAS","XLF","EWC","QLD"],
                     ["XLK","EWG","TLT","FAZ","XLU","EWA","QID"]]
                  
        logreturn={} 
        
        for i in range(2):
            syl = [self.AddSecurity(SecurityType.Equity, x, Resolution.Daily).Symbol.Value for x in tick_syl[i]]
            history = self.History(syl, self.lookbackdays,Resolution.Daily)
            # generate the log return series of paired stocks
            close = history['close'].unstack(level=0) 
            df_logreturn = (np.log(close) - np.log(close.shift(1))).dropna()
            for j in tick_syl[i]:
                logreturn[j] = df_logreturn[j]
        # estimate coefficients of different correlation measures 
        tau_coef,pr_coef,sr_coef= [],[],[]
        for i in range(len(tick_syl[i])):
            tik_x, tik_y= logreturn[tick_syl[0][i]], logreturn[tick_syl[1][i]]
            tau_coef.append(kendalltau(tik_x, tik_y)[0]) 
            pr_coef.append(pearsonr(tik_x, tik_y)[0]) 
            sr_coef.append(spearmanr(tik_x, tik_y)[0]) 
        index_max = tau_coef.index(max(tau_coef))    
        pair = [tick_syl[0][index_max],tick_syl[1][index_max]]
        self.Log("tau" + str(tau_coef))
        self.Log("pr" + str(pr_coef))
        self.Log("sr" + str(sr_coef))
        self.Log(str(pair))
        return pair