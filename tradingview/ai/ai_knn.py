import pandas as pd,numpy as np
exec(open('ai_test.py').read().split('def run')[0])
H=10;K=40
out=[]
for t in P.columns.get_level_values(0).unique():
    d=P[t].dropna()
    if len(d)<1500: continue
    c=d.Close.values;F=feats(d).values;n=len(c)
    a=(pd.concat([d.High-d.Low,(d.High-d.Close.shift()).abs(),(d.Low-d.Close.shift()).abs()],axis=1).max(axis=1)).ewm(alpha=1/14,adjust=False).mean().values
    fr=np.full(n,np.nan);fr[:-H]=(c[H:]-c[:-H])/a[:-H]   # future move in ATRs
    for i in range(1000,n-H,3):
        past=np.arange(250,i-H)   # only analogs whose outcome is already known
        dist=np.log1p(np.abs(F[past]-F[i])).sum(1)   # Lorentzian distance
        nn=past[np.argsort(dist)[:K]]
        q=np.quantile(fr[nn],[0.1,0.5,0.9]);allq=np.quantile(fr[past],[0.1,0.5,0.9])
        out.append((t,d.index[i].year,fr[i],q[0],q[1],q[2],allq[0],allq[1],allq[2]))
R=pd.DataFrame(out,columns=['t','y','f','q1','q5','q9','a1','a5','a9'])
R.to_pickle('knn.pkl')
for nm,g in [('2008-14',R[R.y<2015]),('2015-26',R[R.y>=2015])]:
    cov=((g.f>g.q1)&(g.f<g.q9)).mean();covA=((g.f>g.a1)&(g.f<g.a9)).mean()
    w=(g.q9-g.q1).median();wA=(g.a9-g.a1).median()
    up=g.q5>g.a5; hit=(g.f>0)[up].mean()-(g.f>0).mean(); hitd=(g.f>0)[~up].mean()-(g.f>0).mean()
    strong=g.q5-g.a5; top=g[strong>strong.quantile(0.8)]; bot=g[strong<strong.quantile(0.2)]
    print(f"{nm}: 80% juosta pataiko {cov*100:.0f}% (paprasta {covA*100:.0f}%), plotis {w:.2f} vs {wA:.2f} ATR | AI teigiamas: kyla dažniau {hit*100:+.1f} p.p., neigiamas {hitd*100:+.1f} p.p. | top20% vid. judesys {top.f.mean():+.2f} ATR, bottom20% {bot.f.mean():+.2f}, visi {g.f.mean():+.2f}")
