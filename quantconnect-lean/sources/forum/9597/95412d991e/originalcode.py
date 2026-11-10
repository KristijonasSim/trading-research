"""
Based on 'In & Out' strategy by Peter Guenther 10-04-2020
expanded/inspired by Tentor Testivis, Dan Whitnable (Quantopian), Vladimir, and Thomas Chang.

https://www.quantopian.com/posts/new-strategy-in-and-out


# Import packages
import numpy as np
import pandas as pd
import scipy as sc

def initialize(context): 
    # Feed-in constants
    context.INI_WAIT_DAYS = 15 # out for 3 trading weeks
    
    # 'In' and 'out' holdings incl. weights
    context.HLD_IN = {symbol('SPY'): 1.0}
    context.HLD_OUT = {symbol('TLT'): .5, symbol('IEF'): .5}
    
    # Market and list of signals based on ETFs
    context.MRKT = symbol('SPY')
    context.PRDC = symbol('XLI') # production (industrials)
    context.METL = symbol('DBB') # input prices (metals)
    context.NRES = symbol('IGE') # input prices (natural res)
    context.DEBT = symbol('SHY') # cost of debt (bond yield)
    context.USDX = symbol('UUP') # safe haven (USD)
    context.SIGNALS = [context.PRDC, context.METL, context.NRES, context.DEBT, context.USDX]
    
    # Pairs for comparative returns signals
    context.GOLD = symbol('GLD') # gold
    context.SLVA = symbol('SLV') # VS silver
    context.UTIL = symbol('XLU') # utilities
    context.INDU = context.PRDC # vs industrials
    context.SHCU = symbol('FXF') # safe haven (CHF)
    context.RICU = symbol('FXA') # risk currency (AUD)
    context.FORPAIRS = [context.GOLD, context.SLVA, context.UTIL, context.SHCU, context.RICU]
    
    # Initialize variables
    ## 'In'/'out' indicator
    context.be_in = 1
    ## Day count variables
    context.dcount = 0  # count of total days since start
    context.outday = 0  # dcount when context.be_in=0
    ## Flexi wait days
    context.WDadjvar = context.INI_WAIT_DAYS
    
    # Commission
    set_commission(commission.PerShare(cost=0.0075, min_trade_cost=1.00))
    
    # Schedule functions  
    schedule_function(  
        # daily rebalance if OUT of the market
        rebalance_when_out_of_the_market,  
        date_rules.every_day(),
        time_rules.market_op en(minutes = 75)
    ) 
    schedule_function(  
        # weekly rebalance if IN the market
        rebalance_when_in_the_market,  
        date_rules.week_start(days_offset=4),
        time_rules.market_op en(minutes = 75)
    )

def rebalance_when_out_of_the_market(context, data):
    # Returns sample to detect extreme observations
    hist = data.history(context.SIGNALS+[context.MRKT]+context.FORPAIRS, 'close', 253, '1d').iloc[:-1]
    hist_shift = hist.apply(lambda x: (x.shift(65)+x.shift(64)+x.shift(63)+x.shift(62)+x.shift(61)+x.shift(60)+x.shift(59)+x.shift(58)+x.shift(57)+x.shift(56)+x.shift(55))/11)
    returns_sample = (hist/hist_shift-1)
    # Reverse code USDX: sort largest changes to bottom
    returns_sample[context.USDX] = returns_sample[context.USDX]*(-1)
    # For pairs, take returns differential, reverse coded
    returns_sample['G_S'] = -(returns_sample[context.GOLD] - returns_sample[context.SLVA])
    returns_sample['U_I'] = -(returns_sample[context.UTIL] - returns_sample[context.INDU])
    returns_sample['C_A'] = -(returns_sample[context.SHCU] - returns_sample[context.RICU])
    context.pairlist = ['G_S', 'U_I', 'C_A']
    
    # Extreme observations; statist. significance = 1%
    pctl_b = np.nanpercentile(returns_sample, 1, axis=0)
    extreme_b = returns_sample.iloc[-1] < pctl_b
 
    # Determine waitdays empirically via safe haven excess returns, 50% decay
    context.WDadjvar = int(max(0.50*context.WDadjvar, context.INI_WAIT_DAYS * max(1,returns_sample[context.GOLD].iloc[-1] / returns_sample[context.SLVA].iloc[-1],returns_sample[context.UTIL].iloc[-1] / returns_sample[context.INDU].iloc[-1],returns_sample[context.SHCU].iloc[-1] / returns_sample[context.RICU].iloc[-1])))
    adjwaitdays = min(60, context.WDadjvar)
    
    # Determine whether 'in' or 'out' of the market
    if (extreme_b[context.SIGNALS+context.pairlist]).any():
        context.be_in = False
        context.outday = context.dcount
    if context.dcount >= context.outday + adjwaitdays:
        context.be_in = True
    context.dcount += 1
    
    # Swap to 'out' assets if applicable
    if not context.be_in:
        for asset, weight in context.HLD_OUT.items(): 
            order_target_percent(asset, weight) 
        for asset in context.portfolio.positions:
            # Close 'In' holdings
            if asset not in context.HLD_OUT:
                order_target_percent(asset, 0) 
     
    # Record 
    record(in_market=context.be_in, num_out_signals=extreme_b[context.SIGNALS+context.pairlist].sum(), waitdays=adjwaitdays)
        
def rebalance_when_in_the_market(context, data):
    # Swap to 'in' assets if applicable
    if context.be_in:
        for asset, weight in context.HLD_IN.items(): 
            order_target_percent(asset, weight) 
        for asset in context.portfolio.positions:
            # Close 'Out' holdings
            if asset not in context.HLD_IN:
                order_target_percent(asset, 0)
"""