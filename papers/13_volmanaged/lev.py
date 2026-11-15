"""#13 papildymas (2026-11-15): tas pats Moreira-Muir tikslinis volatilumas, bet agresyvus – tikslas 30–45 %, iki 3–4x (QQQ, skolinimas T-bill + 1 %)."""
exec(open("test.py").read().split("S = {}")[0])
def yrs(r): y=(1+r["2018":]).groupby(r["2018":].index.year).prod()-1; return " ".join(f"{k%100}:{v*100:+.0f}" for k,v in y.items())
for a in ["QQQ","SPY"]:
    print(a, "laikyti", *[" ".join(st(P[a].dropna().pct_change().fillna(0),x,y)[:2]) for x,y in [("1999","2009"),("2010","2019"),("2020","2026")]])
    for tv,cap in [(0.15,2),(0.30,3),(0.40,3),(0.45,4)]:
        for daily in (False,True):
            r,w=run(a,"target",cap,tv,daily)
            print(f"{a} tikslas {tv*100:.0f}% ≤{cap}x {'kasdien' if daily else 'kas mėn'}: "+" | ".join(" ".join(st(r,x,y)[:2]) for x,y in [("1999","2009"),("2010","2019"),("2020","2026")])+f" | vid. {w['2000':].mean():.2f}x | "+yrs(r),flush=True)
print("\nSu trendo filtru (QQQ > SMA200, kitaip T-bill; signalas vakar):")
for tv,cap in [(0.20,2),(0.30,3),(0.40,3),(0.45,4)]:
    for daily in (False,True):
        a="QQQ"; p=P[a].dropna(); r0,w0=run(a,"target",cap,tv,daily)
        up=(p>p.rolling(200).mean()).shift(1).fillna(False)
        rr=p.pct_change().fillna(0); rf=(P["^IRX"].reindex(p.index).ffill()/100/252).fillna(0)
        w=w0.where(up,0); fin=np.where(w>1,rf+0.01/252,rf)
        r=w*rr+(1-w)*fin-w.diff().abs().fillna(0)*FEE
        print(f"QQQ+SMA200 tikslas {tv*100:.0f}% ≤{cap}x {'kasdien' if daily else 'kas mėn'}: "+" | ".join(" ".join(st(r,x,y)[:2]) for x,y in [("1999","2009"),("2010","2019"),("2020","2026")])+f" | rinkoje {(w>0)['2000':].mean()*100:.0f}% | "+yrs(r),flush=True)
