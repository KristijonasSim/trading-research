import pandas as pd,numpy as np
exec(open('../swing/t4.py').read().split("per=[")[0].replace("exec(open('t2.py')","exec(open('../swing/t2.py')").replace("P=pd.read_pickle('px.pkl')","P=pd.read_pickle('../swing/px.pkl')"))
EX={'trend':lambda d:ema(d.c,50)>ema(d.c,200),'swing':mine,'supertrend':st_dir,'turtle':turtle,'macd':macd,'ema921':lambda d:ema(d.c,9)>ema(d.c,21),'hold':lambda d:pd.Series(True,d.index)}
def hedge(d,eta,decay):
    E=np.column_stack([EX[k](d).astype(float).values for k in EX])  # 1=long 0=cash
    r=d.o.pct_change().shift(-1).fillna(0).values  # return from open i to i+1
    n,m=E.shape; L=np.zeros(m); expo=np.zeros(n)
    for i in range(1,n):
        w=np.exp(eta*(L-L.max())); w/=w.sum()
        expo[i]=w@E[i-1]   # decided on yesterday's signals, held from today's open
        L=L*decay+np.log1p(E[i-1]*r[i])   # each expert's realized log-return, fading memory
    return pd.Series(expo,d.index)
def bt(d,expo,fee=0.001):
    r=d.o.pct_change().shift(-1).fillna(0);ch=expo.diff().abs().fillna(0);eq=(1+r*expo-ch*fee).cumprod();return st(eq)
for eta,dec in [(5,0.995),(10,0.995),(20,0.99),(10,0.998),(20,0.998)]:
  line=[]
  for a,b in [('2005-01-01','2015-01-01'),('2015-01-01','2027-01-01')]:
    cs=[];ds=[]
    for t,d0 in D.items():
        x=hedge(d0,eta,dec);m=(d0.index>=a)&(d0.index<b);d=d0[m]
        if len(d)<500: continue
        c,dd=bt(d,x[m]);cs.append(c);ds.append(dd)
    cs=np.array(cs);ds=np.array(ds);line.append(f"{a[:4]}: {np.median(cs):5.1f}%/m dd {np.median(ds):6.1f} MAR {np.median(cs/-ds):.2f}")
  print(f"eta={eta} decay={dec}: "+" | ".join(line))
