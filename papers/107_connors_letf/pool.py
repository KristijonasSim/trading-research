"""#107 papildymas: viena sistema ant visų 5 3x ETF iš bendro kapitalo – iki K pozicijų po 1/K (laisvi pinigai BIL)."""
import sys; sys.argv=[""]
exec(open("test.py").read().split("P = [")[0])
P = [("2001", "2009"), ("2010", "2019"), ("2020", "2026")]
for moc in (True, False):
  for s in ["3HL","RSI25","R3","PB","MDD","RSI6","TPS"]:
    H={}; R3={}
    for base, lev in PAIRS:
        r,h = run(base,s,moc); rb=L(base).Close.pct_change(); rf=irx.reindex(rb.index).ffill().fillna(0)
        H[lev]=h; R3[lev]=3*rb-2*rf-0.0095/252
    H=pd.DataFrame(H).fillna(0); R3=pd.DataFrame(R3).fillna(0); rf=irx.reindex(H.index).ffill().fillna(0)
    for K in (1,2,3):
        # kiekvieną dieną aktyvios pozicijos (pagal laikymo svorį>0); jei daugiau nei K – pirmumas tiems, kurie atidaryti anksčiau
        act=(H>0).astype(float); w=pd.DataFrame(0.0,H.index,H.columns); cur=[]
        for i,d in enumerate(H.index):
            on=[c for c in H.columns if act.iat[i,H.columns.get_loc(c)]>0]
            cur=[c for c in cur if c in on]+[c for c in on if c not in cur]
            for c in cur[:K]: w.at[d,c]=H.at[d,c]/K
        ret=(w*R3).sum(axis=1)+(1-w.sum(axis=1))*rf-w.diff().abs().sum(axis=1).fillna(0)*0.001
        y=(1+ret["2020":]).groupby(ret["2020":].index.year).prod()-1
        print(f"{s:5s} {'MOC ' if moc else 'kitą'} K={K}: "+" | ".join(stat(ret,a,b) for a,b in P)+f" | rinkoje {w.sum(axis=1)['2010':].mean()*100:3.0f}% | "+" ".join(f"{k%100:02d}:{v*100:+.0f}" for k,v in y.items()),flush=True)
