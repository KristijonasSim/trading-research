# Online logistic regression (learns while it goes, never sees the future): P(close in H bars > close now)
import pandas as pd,numpy as np,sys
P=pd.read_pickle('../swing/px.pkl')
ema=lambda x,n:x.ewm(span=n,adjust=False).mean()
def rsi(x,n):
    g=x.diff();u=g.clip(lower=0).ewm(alpha=1/n,adjust=False).mean();dn=(-g.clip(upper=0)).ewm(alpha=1/n,adjust=False).mean();return 100-100/(1+u/dn)
def feats(d):
    c=d.Close;a=(pd.concat([d.High-d.Low,(d.High-c.shift()).abs(),(d.Low-c.shift()).abs()],axis=1).max(axis=1)).ewm(alpha=1/14,adjust=False).mean()
    v=np.log(d.Volume.replace(0,np.nan)).ffill()
    F=pd.DataFrame({'r5':(c-c.shift(5))/a/5,'r20':(c-c.shift(20))/a/10,'rsi':(rsi(c,14)-50)/25,'d50':(c-ema(c,50))/a/5,
       'd200':(c-ema(c,200))/a/10,'tr':(ema(c,20)-ema(c,50))/a/2,'vol':((a/c)/(a/c).rolling(100).mean()-1),'vz':((v-v.rolling(50).mean())/v.rolling(50).std()).fillna(0)/2})
    return F.clip(-3,3).fillna(0)
def run(d,H,lr,l2=1e-3):
    X=feats(d).values;c=d.Close.values;n=len(c);k=X.shape[1];w=np.zeros(k+1);p=np.full(n,0.5)
    for t in range(n):
        if t-H>=0:  # label for features at t-H is known now
            x=np.append(X[t-H],1);y=1.0 if c[t]>c[t-H] else 0.0
            pr=1/(1+np.exp(-x@w));w+=lr*((y-pr)*x-l2*w)
        p[t]=1/(1+np.exp(-np.append(X[t],1)@w))
    return pd.Series(p,d.index)
def bt(d,p,th,fee=0.001,start='2008-01-01'):
    m=d.index>=start;o=d.Open[m];pos=(p[m]>th).shift().fillna(False).astype(bool)
    r=o.pct_change().shift(-1).fillna(0);ch=pos.astype(int).diff().abs().fillna(0);eq=(1+r*pos-ch*fee).cumprod()
    y=(eq.index[-1]-eq.index[0]).days/365.25
    return (eq.iloc[-1]**(1/y)-1)*100,(eq/eq.cummax()-1).min()*100,pos.mean()
for H,lr in [(5,0.01),(10,0.01),(10,0.03),(20,0.01)]:
  for per in [('2008','2015'),('2015','2027')]:
    acc=[];res=[];bh=[]
    for t in P.columns.get_level_values(0).unique():
        d=P[t].dropna()
        if len(d)<800: continue
        p=run(d,H,lr); d2=d[(d.index>=per[0])&(d.index<per[1])];p2=p.loc[d2.index]
        if len(d2)<400: continue
        fut=(d2.Close.shift(-H)>d2.Close)
        sel=p2>0.6; base=fut[:-H].mean(); hit=fut[sel][:-H].mean() if sel.sum()>20 else np.nan
        acc.append(hit-base)
        c,dd,tim=bt(d2,p2,0.55,start=per[0]); res.append((c,dd,tim))
        b=d2.Close;y=(b.index[-1]-b.index[0]).days/365.25;bh.append(((b.iloc[-1]/b.iloc[0])**(1/y)-1)*100)
    R=np.array(res)
    print(f"H={H} lr={lr} {per}: kai P>60% kyla dažniau +{np.nanmedian(acc)*100:4.1f} p.p. | strateg {np.median(R[:,0]):5.1f}%/m dd {np.median(R[:,1]):5.1f} rinkoje {np.median(R[:,2])*100:3.0f}% | laikant {np.median(bh):5.1f}")
