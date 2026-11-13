"""#15 analizė: ar long-short pelnas – tik naujų monetų (listingų) kritimas? Monetos amžiaus riba 60/180/365 d."""
import sys, os, inspect
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import xsec
src = inspect.getsource(xsec.run).replace("def run(P, V, signal, step, topn=50, q=0.2, side=\"long\", hold=None):", "def run2(P, V, signal, step, topn=50, q=0.2, side=\"long\", hold=None, minage=60):").replace("age.iloc[i] >= 60", "age.iloc[i] >= minage")
ns = dict(vars(xsec)); exec(src, ns); run2 = ns["run2"]
P, V = xsec.load()
vol = lambda p: -p.pct_change(fill_method=None).rolling(30, min_periods=20).std()
for a in [60, 180, 365, 730]:
    for side in ["ls", "long"]:
        e = run2(P, V, vol, 7, side=side, minage=a)
        x = xsec.stats(e, "2018-03-01", "2022-01-01"); y = xsec.stats(e, "2022-01-01", "2026-12-01")
        print(f"amžius ≥{a} d. {side}: 2018–21 {x['cagr']:+.1f} ({x['dd']:.0f}) | 2022–26 {y['cagr']:+.1f} ({y['dd']:.0f}) {y['yearly']}", flush=True)
