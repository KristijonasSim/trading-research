import sys, os; sys.argv=["x"]
exec(open("test.py").read().split("P0 = ")[0].replace(".dayofweek", ".day_of_week"))
def analyse2(name, df, fee, a, b):
    sma = df.close.rolling(20).mean()
    W = weeks(df[(df.index >= a) & (df.index < b)])
    tue = lambda w: df.loc[(df.index > w[1].name) & (df.index < w[2].name)]
    cond = []
    for w in W:
        t = tue(w)
        if len(t) and t.high.max() < w[1].high and w[2].high < w[1].high and w[2].close < w[1].high and w[1].close > sma.get(w[1].name, np.inf): cond.append(w)
    if not cond: return f"| {name} | {a[:4]}–{b[:4]} | 0 |"
    hit = np.mean([w[3].low < w[2].low for w in cond]) * 100
    r = np.array([-(w[3].close / w[2].close - 1) - fee for w in cond])
    return f"| {name} | {a[:4]}–{b[:4]} | {len(cond)} | **{hit:.0f} %** | {r.mean()*100:+.3f} % | laimi {np.mean(r>0)*100:.0f} % |"
out = ["\n## Griežtas variantas: pirmadienis – savaitės viršūnė (antr. ir treč. aukščiausios žemiau), kylanti rinka (pirm. > SMA20)\n", "| Rinka | Laikotarpis | Atvejų | Ketv. < treč. žemiausios | Short treč.→ketv. vid. | |", "|---|---|---|---|---|---|"]
for n, s in [("Dow Jones", "DJI"), ("S&P 500", "GSPC"), ("Nasdaq-100", "NDX")]:
    df = yahoo(s)
    for a, b in [("1992-01-01", "2010-01-01"), ("2010-01-01", "2026-11-17")]: out.append(analyse2(n, df, 0.0002, a, b))
for n, s in [("BTC", "BTC"), ("ETH", "ETH")]:
    out.append(analyse2(n, binance(s), 0.001, "2018-01-01", "2026-11-17"))
open("rezultatai_raw.md", "a").write("\n".join(out) + "\n"); print("\n".join(out))
