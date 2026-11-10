import pandas as pd, numpy as np, zipfile, glob, sys
from pathlib import Path
R=Path('/home/kris/Desktop/trading-research')
def lean(t):
    z=zipfile.ZipFile(R/f'quantconnect-lean/data/equity/usa/daily/{t}.zip'); n=z.namelist()[0]
    d=pd.read_csv(z.open(n),header=None,names=['d','o','h','l','c','v'])
    d.index=pd.to_datetime(d.d.astype(str).str[:8]); d=d[['o','h','l','c']]/10000; return d
def ft(p):
    d=pd.read_feather(R/f'freqtrade/user_data/data/binance/{p}_USDT-1d.feather').set_index('date')
    d=d.rename(columns={'open':'o','high':'h','low':'l','close':'c'})[['o','h','l','c']]; d.index=d.index.tz_localize(None); return d
STK=['spy','qqq','iwm','gld','tlt','aapl','msft','amzn','nvda','xle','eem','efa']
CR=['BTC','ETH','SOL','XRP','BNB','ADA','LINK','DOGE']
D={t.upper():lean(t) for t in STK if (R/f'quantconnect-lean/data/equity/usa/daily/{t}.zip').exists()}
D.update({c+'-USD':ft(c) for c in CR})
def atr(d,n):
    tr=pd.concat([d.h-d.l,(d.h-d.c.shift()).abs(),(d.l-d.c.shift()).abs()],axis=1).max(axis=1); return tr.ewm(alpha=1/n,adjust=False).mean()
def ema(x,n): return x.ewm(span=n,adjust=False).mean()
def rsi(x,n):
    g=x.diff(); u=g.clip(lower=0).ewm(alpha=1/n,adjust=False).mean(); dn=(-g.clip(upper=0)).ewm(alpha=1/n,adjust=False).mean(); return 100-100/(1+u/dn)
def sim(d,entry,trail_mult,atrn=22,fee=0.001):
    # entry signal on close -> buy next open; exit when close < chandelier stop (highest close since entry - k*ATR) or regime off -> sell next open
    A=atr(d,atrn).values; c=d.c.values; o=d.o.values; e=entry.values; reg=REG.values
    pos=0; stop=np.nan; hi=0; eq=1.0; curve=[]; trades=[]; px=0; pend=0
    for i in range(len(d)):
        if pend==1: pos=1; px=o[i]*(1+fee); hi=c[i]; pend=0
        elif pend==-1: pos=0; r=o[i]*(1-fee)/px; trades.append(r-1); pend=0
        val = eq*(c[i]/px) if pos else eq
        if pos and pend==0:
            hi=max(hi,c[i]); stop=max(stop if not np.isnan(stop) else -1, hi-trail_mult*A[i])
            if c[i]<stop or not reg[i]: pend=-1; eq=eq*(o[min(i+1,len(d)-1)]*(1-fee)/px) if False else eq
        elif not pos and e[i] and reg[i]: pend=1; stop=np.nan
        curve.append(val if not pos else eq*c[i]/px)
        if pend==-1 and pos: pass
        if pos and pend==-1 and i+1<len(d): eq=eq*(o[i+1]*(1-fee)/px)
    s=pd.Series(curve,index=d.index); return s,trades
def stats(s,tr):
    y=(s.index[-1]-s.index[0]).days/365.25; cagr=s.iloc[-1]**(1/y)-1; dd=(s/s.cummax()-1).min()
    w=np.mean([t>0 for t in tr]) if tr else 0
    return cagr*100,dd*100,len(tr)/y,w*100
def run(name,fn,k,start,end):
    out=[]
    for t,d0 in D.items():
        d=d0[(d0.index>=start)&(d0.index<end)]
        if len(d)<300: continue
        global REG; ent,REG=fn(d)
        s,tr=sim(d,ent,k); c,dd,n,w=stats(s,tr)
        bh=(d.c.iloc[-1]/d.c.iloc[0])**(365.25/(d.index[-1]-d.index[0]).days)-1
        bdd=(d.c/d.c.cummax()-1).min()
        out.append((t,c,dd,n,w,bh*100,bdd*100))
    o=pd.DataFrame(out,columns=['t','cagr','dd','tr/y','win','bh','bhdd']).set_index('t')
    return o
S={}
# A Donchian 20 breakout (Turtle) + EMA200 regime
S['A_donch20']=lambda d:(d.c>d.h.shift().rolling(20).max(), d.c>ema(d.c,200))
# B EMA20>EMA50 cross + regime
S['B_ema']=lambda d:((ema(d.c,20)>ema(d.c,50))&(ema(d.c,20).shift()<=ema(d.c,50).shift()), d.c>ema(d.c,200))
# C pullback in uptrend: RSI(2)<10 above EMA200 (Connors) - with chandelier exit
S['C_pull']=lambda d:(rsi(d.c,2)<10, d.c>ema(d.c,200))
# D trend + pullback: EMA50>EMA200, close crosses back above EMA20 after dip below
S['D_trendpull']=lambda d:(((d.c>ema(d.c,20))&(d.c.shift()<=ema(d.c,20).shift()))&(ema(d.c,50)>ema(d.c,200)), ema(d.c,50)>ema(d.c,200))
# E Donchian 55
S['E_donch55']=lambda d:(d.c>d.h.shift().rolling(55).max(), d.c>ema(d.c,200))
per=[('2008-01-01','2018-01-01'),('2018-01-01','2027-01-01')]
for nm,fn in S.items():
  for k in (3,4):
    for a,b in per:
        o=run(nm,fn,k,a,b)
        print(f"{nm:12} k={k} {a[:4]}-{b[:4]} n={len(o):2} cagr {o.cagr.median():6.1f} dd {o.dd.median():6.1f} | bh {o.bh.median():6.1f} dd {o.bhdd.median():6.1f} | MAR {(o.cagr/ -o.dd).median():.2f} vs {(o.bh/-o.bhdd).median():.2f} tr/y {o['tr/y'].median():.1f} win {o.win.median():.0f}")
