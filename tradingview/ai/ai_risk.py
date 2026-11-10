import pandas as pd,numpy as np
exec(open('ai_test.py').read().split('def run')[0])
def auc(y,s):
    y=np.asarray(y,bool);s=np.asarray(s);r=pd.Series(s).rank().values;n1=y.sum();n0=len(y)-n1
    return (r[y].sum()-n1*(n1+1)/2)/(n1*n0) if n1 and n0 else np.nan
def run_risk(d,H,K,lr,l2=1e-3):
    X=feats(d).values;c=d.Close.values;l=d.Low.values;n=len(c);w=np.zeros(X.shape[1]+1);p=np.full(n,0.2)
    a=(pd.concat([d.High-d.Low,(d.High-d.Close.shift()).abs(),(d.Low-d.Close.shift()).abs()],axis=1).max(axis=1)).ewm(alpha=1/14,adjust=False).mean().values
    y=np.zeros(n)
    for t in range(n-H): y[t]=1.0 if l[t+1:t+H+1].min()<c[t]*(1-K*a[t]/c[t]*np.sqrt(H)/np.sqrt(H)) - 0 and (c[t]-l[t+1:t+H+1].min())/c[t] > K*np.median(a[max(0,t-250):t+1]/c[max(0,t-250):t+1]) else 0.0
    for t in range(n):
        if t-H>=0:
            x=np.append(X[t-H],1);pr=1/(1+np.exp(-x@w));w+=lr*((y[t-H]-pr)*x-l2*w)
        p[t]=1/(1+np.exp(-np.append(X[t],1)@w))
    return pd.Series(p,d.index),pd.Series(y,d.index)
for H,K,lr in [(20,3,0.02),(20,4,0.02),(10,3,0.02)]:
  for per in [('2008','2015'),('2015','2027')]:
    A=[];S=[];B=[]
    for t in P.columns.get_level_values(0).unique():
        d=P[t].dropna()
        if len(d)<800: continue
        p,y=run_risk(d,H,K,lr);m=(d.index>=per[0])&(d.index<per[1]);d2=d[m]
        if len(d2)<400: continue
        A.append(auc(y[m].values[:-H],p[m].values[:-H]))
        th=p[d.index<per[0]].quantile(0.7) if (d.index<per[0]).sum()>300 else p[m].expanding().quantile(0.7).shift().fillna(1).values
        # exposure: out when risk prob above its own 70th pct over past 2y (rolling, no future)
        thr=p.rolling(500,min_periods=250).quantile(0.75).shift()
        pos=(p<=thr)|thr.isna()
        o=d2.Open;ps=pos[m].shift().fillna(True).astype(bool);r=o.pct_change().shift(-1).fillna(0);ch=ps.astype(int).diff().abs().fillna(0)
        eq=(1+r*ps-ch*0.001).cumprod();yrs=(eq.index[-1]-eq.index[0]).days/365.25
        S.append(((eq.iloc[-1]**(1/yrs)-1)*100,(eq/eq.cummax()-1).min()*100,ps.mean()))
        b=d2.Close;B.append((((b.iloc[-1]/b.iloc[0])**(1/yrs)-1)*100,(b/b.cummax()-1).min()*100))
    S=np.array(S);B=np.array(B)
    print(f"H={H} K={K} {per}: AUC {np.nanmedian(A):.3f} | strateg {np.median(S[:,0]):5.1f}%/m dd {np.median(S[:,1]):6.1f} rinkoje {np.median(S[:,2])*100:3.0f}% | laikant {np.median(B[:,0]):5.1f} dd {np.median(B[:,1]):6.1f} | MAR {np.median(S[:,0]/-S[:,1]):.2f} vs {np.median(B[:,0]/-B[:,1]):.2f}")
