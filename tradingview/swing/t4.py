import pandas as pd,numpy as np
exec(open('t2.py').read().split("S={")[0])
def st_dir(d,n=10,m=3.0):
    a=atr(d,n).values;h=((d.h+d.l)/2).values;c=d.c.values;N=len(d)
    up=h-m*a;dn=h+m*a;fu=up.copy();fd=dn.copy();dr=np.ones(N)
    for i in range(1,N):
        fu[i]=max(up[i],fu[i-1]) if c[i-1]>fu[i-1] else up[i]
        fd[i]=min(dn[i],fd[i-1]) if c[i-1]<fd[i-1] else dn[i]
        dr[i]=1 if c[i]>fd[i-1] else (-1 if c[i]<fu[i-1] else dr[i-1])
    return pd.Series(dr==1,d.index)
def psar(d,step=0.02,mx=0.2):
    h=d.h.values;l=d.l.values;N=len(d);up=True;sar=l[0];ep=h[0];af=step;out=np.ones(N,bool)
    for i in range(1,N):
        sar=sar+af*(ep-sar)
        if up:
            sar=min(sar,l[i-1],l[i-2] if i>1 else l[i-1])
            if l[i]<sar: up=False;sar=ep;ep=l[i];af=step
            elif h[i]>ep: ep=h[i];af=min(af+step,mx)
        else:
            sar=max(sar,h[i-1],h[i-2] if i>1 else h[i-1])
            if h[i]>sar: up=True;sar=ep;ep=h[i];af=step
            elif l[i]<ep: ep=l[i];af=min(af+step,mx)
        out[i]=up
    return pd.Series(out,d.index)
def state_sim(d,longstate,fee=0.001):
    s=longstate.shift().fillna(False).astype(bool)  # act next bar open
    r=d.o.pct_change().shift(-1).fillna(0)  # open-to-open return held from open i
    ch=s.astype(int).diff().abs().fillna(0)
    eq=(1+r*s - ch*fee).cumprod(); return eq
def mine(d):
    A=atr(d,22).values;c=d.c.values;e=(((rsi(d.c,2)<25)|(d.c>d.h.shift().rolling(20).max()))&(ema(d.c,50)>ema(d.c,200))).values
    pos=np.zeros(len(d),bool);p=False;hi=0;stop=0
    for i in range(len(d)):
        if p:
            hi=max(hi,c[i]);stop=max(stop,hi-5*A[i])
            if c[i]<stop: p=False
        elif e[i]: p=True;hi=c[i];stop=c[i]-5*A[i]
        pos[i]=p
    return pd.Series(pos,d.index)
macd=lambda d:(ema(d.c,12)-ema(d.c,26))>ema(ema(d.c,12)-ema(d.c,26),9)
C={'MANO Swing Trend Pullback':mine,'Supertrend 10/3':st_dir,'Supertrend + EMA200':lambda d:st_dir(d)&(d.c>ema(d.c,200)),
 'Golden cross 50/200':lambda d:d.c.rolling(50).mean()>d.c.rolling(200).mean(),'MACD 12/26/9':macd,
 'Parabolic SAR':psar,'Turtle 20/10':None,'EMA 9/21':lambda d:ema(d.c,9)>ema(d.c,21),'Laikyti':lambda d:pd.Series(True,d.index)}
def turtle(d):
    hi=d.h.shift().rolling(20).max();lo=d.l.shift().rolling(10).min();p=False;out=[]
    for c,a,b in zip(d.c,hi,lo):
        if not p and c>a: p=True
        elif p and c<b: p=False
        out.append(p)
    return pd.Series(out,d.index)
C['Turtle 20/10']=turtle
per=[('2005-01-01','2015-01-01'),('2015-01-01','2027-01-01')]
rows=[]
for nm,fn in C.items():
    for a,b in per:
        cs=[];ds=[]
        for t,d0 in D.items():
            ls=fn(d0);m=(d0.index>=a)&(d0.index<b);d=d0[m]
            if len(d)<500: continue
            c,dd=st(state_sim(d,ls[m]));cs.append(c);ds.append(dd)
        cs=np.array(cs);ds=np.array(ds)
        rows.append((nm,a[:4],np.median(cs),np.median(ds),np.median(cs/-ds)))
R=pd.DataFrame(rows,columns=['ind','per','cagr','dd','mar'])
P=R.pivot(index='ind',columns='per',values=['cagr','dd','mar'])
P['mar_vid']=P['mar'].mean(axis=1);P=P.sort_values('mar_vid',ascending=False)
print(P.round(2).to_string())
P.round(2).to_csv('t4_palyginimas.csv')
