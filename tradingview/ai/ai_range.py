# Online-learned range forecast + self-calibration (conformal): band where price will be in H bars with 80% chance
import pandas as pd,numpy as np
exec(open('ai_test.py').read().split('def run')[0])
H=10;TARGET=0.8
def run(d,lr=0.02,cal_lr=0.01):
    c=d.Close.values;F=feats(d).values;n=len(c)
    a=(pd.concat([d.High-d.Low,(d.High-d.Close.shift()).abs(),(d.Low-d.Close.shift()).abs()],axis=1).max(axis=1)).ewm(alpha=1/14,adjust=False).mean().values
    lr_ret=np.log(d.Close).diff().values
    rv=pd.Series(lr_ret).rolling(20).std().bfill().values
    w=np.zeros(F.shape[1]+1); # predicts log( |move H| / (ATR*sqrtH) ) scale factor
    s=np.ones(n);m=np.zeros(n);k_up=1.28;k_dn=1.28;res=[]
    for t in range(n):
        if t>=H:
            j=t-H;x=np.append(F[j],1);mv=np.log(c[t]/c[j]);base=a[j]/c[j]*np.sqrt(H)
            y=np.log(abs(mv)/base+1e-3); pred=x@w; w+=lr*((y-pred)*x-1e-3*w)
            # self-calibration: widen if outside, shrink if inside (online quantile / conformal)
            up=s[j]*k_up;dn=s[j]*k_dn;z=mv/base
            k_up+=cal_lr*((z>up)-(1-TARGET)/2)*1.0;k_dn+=cal_lr*((z<-dn)-(1-TARGET)/2)*1.0
            if t>=1000: res.append((d.index[t].year,z,up,-dn,s[j],np.std(lr_ret[max(0,j-20):j+1])*np.sqrt(H)/base))
        s[t]=np.exp(np.append(F[t],1)@w)/np.exp(w[-1]) if t>300 else 1.0
    return res
rows=[]
for t in P.columns.get_level_values(0).unique():
    d=P[t].dropna()
    if len(d)<1500: continue
    for r in run(d): rows.append((t,)+r)
R=pd.DataFrame(rows,columns=['t','y','z','up','dn','s','rv'])
for nm,g in [('2008-14',R[R.y<2015]),('2015-26',R[R.y>=2015])]:
    cov=((g.z<g.up)&(g.z>g.dn)).mean(); width=(g.up-g.dn).median()
    # naive: fixed ±1.28 ATR*sqrtH
    covN=((g.z.abs()<1.28)).mean()
    # does AI scale track real move size? corr of predicted width with |z|
    cr=np.corrcoef(g.up-g.dn,g.z.abs())[0,1]
    print(f"{nm}: AI juosta pataiko {cov*100:.0f}% (tikslas 80%), plotis {width:.2f} | paprasta ATR juosta {covN*100:.0f}% | AI pločio ryšys su tikru judesiu {cr:.2f}")
    print('   pagal rinką:',g.groupby('t').apply(lambda x:((x.z<x.up)&(x.z>x.dn)).mean()*100).round(0).astype(int).to_dict())
