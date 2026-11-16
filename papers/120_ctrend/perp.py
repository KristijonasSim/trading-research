"""CTREND long-short tik su monetomis, turinčiomis Binance perp tą dieną, + funding mokesčiai. Dienos grąžos be dreifo."""
import sys, os, glob; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
exec(open("test.py").read().split("sig = lambda p: F")[0])
D = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/data"
fund = {}; first = {}
for f in glob.glob(f"{D}/funding/*.csv"):
    s = os.path.basename(f)[:-4]; d = pd.read_csv(f)
    if len(d) == 0: continue
    x = pd.Series(d.rate.values, pd.to_datetime(d.t, unit="ms")).resample("D").sum(); fund[s] = x; first[s] = x.index[0]
FU = pd.DataFrame(fund).reindex(P.index).fillna(0).reindex(columns=P.columns, fill_value=0)
has = pd.DataFrame({c: P.index >= first.get(c, pd.Timestamp("2100-01-01")) for c in P.columns}, index=P.index)
print("perp monetų:", len(first), "sutampa su spot:", sum(c in P.columns for c in first), flush=True)
R = P.pct_change(fill_method=None)
def bt(F, perp_only, funding, q=0.2, topn=50, fee=0.001, step=7):
    W = pd.DataFrame(0.0, index=P.index, columns=P.columns); w = pd.Series(0.0, index=P.columns)
    for i in range(230, len(P), step):
        t = P.index[i]; f = F.loc[t].dropna()
        if perp_only: f = f[has.loc[t, f.index]]
        if len(f) < 15: W.iloc[i:i + step] = w.values; continue
        f = f.sort_values(); k = max(1, int(len(f) * q)); w = pd.Series(0.0, index=P.columns)
        w[f.index[-k:]] = 0.5 / k; w[f.index[:k]] = -0.5 / k
        W.iloc[i:i + step] = w.values
    Wp = W.shift(1).fillna(0)
    r = (Wp * R.fillna(0)).sum(axis=1) - W.diff().abs().sum(axis=1).shift(1).fillna(0) * fee
    if funding: r = r - (Wp * FU).sum(axis=1)
    return (1 + r).cumprod()
out = ["\n## Tik monetos su perp + funding (dienos svoriai, be dreifo)\n", "| Variantas | 2019–21 %/m. | kritimas | 2021–26 %/m. | kritimas | Metai 2021–26 |", "|---|---|---|---|---|---|"]
for n, kw in [("visos, be funding", dict(perp_only=False, funding=False)), ("tik perp, be funding", dict(perp_only=True, funding=False)),
              ("tik perp + funding", dict(perp_only=True, funding=True)), ("tik perp + funding, mokestis 0,2 %", dict(perp_only=True, funding=True, fee=0.002)),
              ("tik perp + funding, kraštas 10 %", dict(perp_only=True, funding=True, q=0.1))]:
    e = bt(F, **kw); s1 = stats(e, "2019-01-01", "2021-11-08"); s2 = stats(e, "2021-11-08", "2026-11-08")
    out.append(f"| {n} | {s1['cagr']:+} | {s1['dd']} % | {s2['cagr']:+} | {s2['dd']} % | {s2['yearly']} |"); print(out[-1], flush=True)
open("rezultatai_raw.md", "a").write("\n".join(out) + "\n")
