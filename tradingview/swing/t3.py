import pandas as pd,numpy as np,itertools
exec(open('t2.py').read().split("S={")[0])
def sim2(d,ent,reg,k,regexit,fee=0.001):
    A=atr(d,22).values;c=d.c.values;o=d.o.values;e=ent.values;r=reg.values;n=len(d)
    eq=np.ones(n);cash=1.0;pos=False;px=0;hi=0;stop=-1;tr=0
    for i in range(1,n):
        if not pos and e[i-1] and r[i-1]: pos=True;px=o[i]*(1+fee);hi=c[i-1];stop=c[i-1]-k*A[i-1]
        elif pos and (c[i-1]<stop or (regexit and not r[i-1])): cash*=o[i]*(1-fee)/px;pos=False;tr+=1
        if pos: hi=max(hi,c[i]);stop=max(stop,hi-k*A[i]);eq[i]=cash*c[i]/px
        else: eq[i]=cash
    return pd.Series(eq,d.index)
V={
 'G':lambda d:((rsi(d.c,2)<10)|(d.c>d.h.shift().rolling(20).max()), ema(d.c,50)>ema(d.c,200)),
 'G_c200':lambda d:((rsi(d.c,2)<10)|(d.c>d.h.shift().rolling(20).max()), d.c>ema(d.c,200)),
 'G_rsi25':lambda d:((rsi(d.c,2)<25)|(d.c>d.h.shift().rolling(20).max()), ema(d.c,50)>ema(d.c,200)),
 'G_any':lambda d:((rsi(d.c,2)<25)|(d.c>d.h.shift().rolling(10).max()), ema(d.c,50)>ema(d.c,200)),
}
per=[('2005-01-01','2015-01-01'),('2015-01-01','2027-01-01')]
for (nm,fn),k,rx in itertools.product(V.items(),(4,5,6),(True,False)):
  out=[]
  for a,b in per:
    cs=[];ds=[];bs=[];bd=[]
    for t,d0 in D.items():
        ent,reg=fn(d0);m=(d0.index>=a)&(d0.index<b);d=d0[m]
        if len(d)<500: continue
        c,dd=st(sim2(d,ent[m],reg[m],k,rx));bc,bdd=st(d.c/d.c.iloc[0]);cs.append(c);ds.append(dd);bs.append(bc);bd.append(bdd)
    out.append(f"{a[:4]}: {np.median(cs):5.1f}%/m dd {np.median(ds):6.1f} (laik {np.median(bs):5.1f}/{np.median(bd):6.1f}) MAR {np.median(np.array(cs)/-np.array(ds)):.2f}/{np.median(np.array(bs)/-np.array(bd)):.2f}")
  print(f"{nm:8} k={k} regexit={rx!s:5}", ' | '.join(out))
