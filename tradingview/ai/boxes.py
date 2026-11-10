# Consolidation boxes: find quiet ranges, let them grow, trade the breakout (or fake-out). R = profit in units of risk.
import pandas as pd,numpy as np,itertools
def load_ft(p,tf):
    d=pd.read_feather(f'/home/kris/Desktop/trading-research/freqtrade/user_data/data/binance/{p}_USDT-5m.feather').set_index('date')
    d=d[['open','high','low','close','volume']]
    if tf!='5m': d=d.resample(tf).agg({'open':'first','high':'max','low':'min','close':'last','volume':'sum'}).dropna()
    return d
P=pd.read_pickle('../swing/px.pkl')
D={}
for t in ['SPY','QQQ','IWM','GLD','AAPL','MSFT','NVDA','AMZN','XLE','TLT','EEM','JPM']:
    d=P[t].dropna();d.columns=[c.lower() for c in d.columns];D[t+' 1d']=d[['open','high','low','close','volume']]
for p in ['BTC','ETH','SOL','XRP','ADA']:
    for tf in ['1h','15min']: D[f'{p} {tf}']=load_ft(p,tf)
def boxes(d,W=12,m=2.5):
    o,h,l,c,v=[d[x].values for x in ['open','high','low','close','volume']];n=len(c)
    tr=np.maximum(h-l,np.maximum(abs(h-np.roll(c,1)),abs(l-np.roll(c,1))));atr=pd.Series(tr).ewm(alpha=1/50,adjust=False).mean().values
    vavg=pd.Series(v).rolling(50).mean().values
    out=[];i=60
    while i<n-1:
        hi=h[i-W+1:i+1].max();lo=l[i-W+1:i+1].min()
        if hi-lo<m*atr[i]:
            s=i-W+1;j=i+1
            while j<n and lo<=c[j]<=hi:   # box grows: wicks widen it, a close outside ends it
                hi=max(hi,h[j]);lo=min(lo,l[j]);j+=1
            if j>=n-1: break
            # POC: price level with most volume inside the box
            seg=slice(s,j);tp=(h[seg]+l[seg]+c[seg])/3;bins=np.linspace(lo,hi,21)
            hist=np.histogram(tp,bins=bins,weights=v[seg])[0];poc=(bins[hist.argmax()]+bins[hist.argmax()+1])/2
            out.append(dict(s=s,e=j,hi=hi,lo=lo,poc=poc,pocpos=(poc-lo)/(hi-lo+1e-12),dir=1 if c[j]>hi else -1,vr=v[j]/(vavg[j]+1e-12),len=j-s))
            i=j+1
        else: i+=1
    return out
def trade(d,b,mode,tgt=2.0,stopmode='opp',fee=0.001):
    o,h,l,c=[d[x].values for x in ['open','high','low','close']];n=len(c);e=b['e'];H=b['hi']-b['lo']
    side=b['dir'] if mode=='break' else -b['dir']
    if e+1>=n: return None
    px=o[e+1]
    if mode=='break':
        stop=(b['lo'] if side==1 else b['hi']) if stopmode=='opp' else b['poc']
    else:  # fake-out: bet price returns into box, stop beyond breakout candle extreme
        stop=h[e]+0.1*H if side==-1 else l[e]-0.1*H
    risk=abs(px-stop)
    if risk<=0 or (side==1 and stop>=px) or (side==-1 and stop<=px): return None
    target=px+side*tgt*risk if mode=='break' else b['poc']
    if mode!='break' and (target-px)*side<=0: return None
    for k in range(e+1,min(n,e+1+max(3*b['len'],20))):
        if side==1:
            if l[k]<=stop: return -1-2*fee*px/risk
            if h[k]>=target: return (target-px)/risk-2*fee*px/risk
        else:
            if h[k]>=stop: return -1-2*fee*px/risk
            if l[k]<=target: return (px-target)/risk-2*fee*px/risk
    return (c[k]-px)*side/risk-2*fee*px/risk
rows=[]
for name,d in D.items():
    B=boxes(d);half=d.index[len(d)//2]
    for b in B:
        t0=d.index[b['e']]
        for mode,tgt,sm in [('break',2,'opp'),('break',1,'opp'),('break',2,'poc'),('fade',0,'')]:
            r=trade(d,b,mode,tgt,sm)
            if r is not None: rows.append((name,name.split()[1],t0>=half,mode+str(tgt)+sm,b['vr']>1.5,(b['pocpos']>0.5)==(b['dir']==1),r))
R=pd.DataFrame(rows,columns=['mkt','tf','late','rule','bigvol','poc_same_side','R'])
R['R']=R.R.clip(-3,10)
g=R.groupby(['tf','rule','late']).R.agg(['count','mean',lambda x:(x>0).mean()*100]).round(3)
g.columns=['sandoriu','vid_R','laimi%'];print(g.to_string())
print('\nFiltrai (lūžis 2R, stop kitoj pusėj):')
x=R[R.rule=='break2opp']
for f in ['bigvol','poc_same_side']:
    print(f, x.groupby(['tf',f,'late']).R.agg(['count','mean']).round(3).to_string())
R.to_pickle('boxes.pkl')
