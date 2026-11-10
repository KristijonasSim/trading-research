# 5 candles (shape + volume) -> find most similar past 5-candle patterns -> what did the 6th candle do?
import pandas as pd,numpy as np
def load_yf():
    P=pd.read_pickle('../swing/px.pkl');out={}
    for t in P.columns.get_level_values(0).unique():
        d=P[t].dropna();d.columns=[c.lower() for c in d.columns];out[t+' 1d']=d[['open','high','low','close','volume']]
    return out
def load_ft(p,tf):
    d=pd.read_feather(f'/home/kris/Desktop/trading-research/freqtrade/user_data/data/binance/{p}_USDT-{tf}.feather').set_index('date')
    return d[['open','high','low','close','volume']].iloc[-60000:]
D=load_yf()
for p in ['BTC','ETH','SOL']:
    for tf in ['1h','5m']: D[f'{p} {tf}']=load_ft(p,tf)
K=30;L=5
def feats(d):
    o,h,l,c,v=[d[x].values for x in ['open','high','low','close','volume']]
    a=pd.Series(np.maximum(h-l,1e-12)).rolling(20).mean().values
    va=pd.Series(v).rolling(20).mean().values+1e-12
    per=np.column_stack([(c-o)/a,(h-np.maximum(o,c))/a,(np.minimum(o,c)-l)/a,np.log((v+1e-12)/va)])
    F=np.column_stack([np.roll(per,i,axis=0) for i in range(L)])  # last 5 candles
    nxt=np.full(len(c),np.nan);nxt[:-1]=(c[1:]-c[:-1])/a[:-1]  # 6th candle: close-to-close in ATR
    F[:25]=np.nan;return F,nxt
rows=[]
for name,d in D.items():
    F,nx=feats(d);n=len(F);start=max(1000,n//3);step=max(1,(n-start)//1500)
    pred=[];real=[]
    for i in range(start,n-1,step):
        past=np.arange(25,i-1);X=F[past]
        dist=np.abs(X-F[i]).sum(1);nn=past[np.argpartition(dist,K)[:K]]
        pred.append(np.mean(nx[nn]>0));real.append(nx[i])
    pred=np.array(pred);real=np.array(real);up=real>0
    base=up.mean();strong=pred>=0.7;weak=pred<=0.3
    hit=(up==(pred>0.5)).mean()
    rows.append((name,len(pred),base*100,hit*100,up[strong].mean()*100 if strong.sum()>20 else np.nan,strong.mean()*100,(~up[weak]).mean()*100 if weak.sum()>20 else np.nan))
R=pd.DataFrame(rows,columns=['rinka','testu','kyla_paprastai%','atspejo_krypti%','kai_AI>=70%_kilo%','tokiu_atveju%','kai_AI<=30%_krito%'])
print(R.round(1).to_string(index=False))
print('\nVidurkis atspėjo kryptį:',round(R['atspejo_krypti%'].mean(),1),'% (atsitiktinai ~50 %)')
