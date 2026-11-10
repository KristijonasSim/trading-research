import pandas as pd, numpy as np, itertools
P=pd.read_pickle('px.pkl')
D={}
for t in P.columns.get_level_values(0).unique():
    d=P[t].rename(columns={'Open':'o','High':'h','Low':'l','Close':'c'})[['o','h','l','c']].dropna()
    D[t]=d
ema=lambda x,n:x.ewm(span=n,adjust=False).mean()
def atr(d,n):
    tr=pd.concat([d.h-d.l,(d.h-d.c.shift()).abs(),(d.l-d.c.shift()).abs()],axis=1).max(axis=1); return tr.ewm(alpha=1/n,adjust=False).mean()
def rsi(x,n):
    g=x.diff(); u=g.clip(lower=0).ewm(alpha=1/n,adjust=False).mean(); dn=(-g.clip(upper=0)).ewm(alpha=1/n,adjust=False).mean(); return 100-100/(1+u/dn)
def sim(d,ent,reg,k,fee=0.001):
    A=atr(d,22).values;c=d.c.values;o=d.o.values;e=ent.values;r=reg.values;n=len(d)
    eq=np.ones(n);cash=1.0;pos=False;px=0;hi=0;stop=-1;tr=[];bars=0
    for i in range(1,n):
        # act at open i on signal from i-1
        if not pos and e[i-1] and r[i-1]:
            pos=True;px=o[i]*(1+fee);hi=c[i-1];stop=c[i-1]-k*A[i-1]
        elif pos and (c[i-1]<stop or not r[i-1]):
            cash*=o[i]*(1-fee)/px;tr.append(o[i]*(1-fee)/px-1);pos=False
        if pos:
            bars+=1;hi=max(hi,c[i]);stop=max(stop,hi-k*A[i]);eq[i]=cash*c[i]/px
        else: eq[i]=cash
    return pd.Series(eq,d.index),tr,bars/n
def st(s):
    y=(s.index[-1]-s.index[0]).days/365.25;return (s.iloc[-1]**(1/y)-1)*100,(s/s.cummax()-1).min()*100
S={
 'A_donch20':lambda d:(d.c>d.h.shift().rolling(20).max(), d.c>ema(d.c,200)),
 'E_donch55':lambda d:(d.c>d.h.shift().rolling(55).max(), d.c>ema(d.c,200)),
 'C_pull':lambda d:(rsi(d.c,2)<10, d.c>ema(d.c,200)),
 'D_trendpull':lambda d:((d.c>ema(d.c,20))&(d.c.shift()<=ema(d.c,20).shift()), ema(d.c,50)>ema(d.c,200)),
 'F_donch20_reg50':lambda d:(d.c>d.h.shift().rolling(20).max(), ema(d.c,50)>ema(d.c,200)),
 'G_pull_or_break':lambda d:((rsi(d.c,2)<10)|(d.c>d.h.shift().rolling(20).max()), ema(d.c,50)>ema(d.c,200)),
}
per=[('2005-01-01','2015-01-01'),('2015-01-01','2027-01-01')]
rows=[]
for (nm,fn),k,(a,b) in itertools.product(S.items(),(2.5,3,4),per):
    for t,d0 in D.items():
        ent,reg=fn(d0); m=(d0.index>=a)&(d0.index<b)
        d=d0[m]
        if len(d)<500: continue
        s,tr,tim=sim(d,ent[m],reg[m],k); c,dd=st(s); bc,bdd=st(d.c/d.c.iloc[0])
        rows.append((nm,k,a[:4],t,c,dd,bc,bdd,len(tr),np.mean([x>0 for x in tr]) if tr else 0,tim))
R=pd.DataFrame(rows,columns=['sys','k','per','t','cagr','dd','bh','bhdd','n','win','time'])
R['mar']=R.cagr/-R.dd; R['bmar']=R.bh/-R.bhdd
g=R.groupby(['sys','k','per']).agg(cagr=('cagr','median'),dd=('dd','median'),bh=('bh','median'),bhdd=('bhdd','median'),mar=('mar','median'),bmar=('bmar','median'),beat=('mar',lambda x:0),win=('win','median'),time=('time','median'))
R['beatmar']=R.mar>R.bmar
g['beat%']=R.groupby(['sys','k','per']).beatmar.mean()*100
pd.set_option('display.width',200); print(g.drop(columns='beat').round(2))
R.to_csv('t2_results.csv',index=False)
