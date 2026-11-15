"""104: Trendo ansamblis (Hurst, Ooi, Pedersen 2017): signalas = 1/3/12 mėn. grąžų ženklų vidurkis (tik long),
pozicija = signalas * (tikslinis vol / 60 d. vol), kiekvienai monetai 1/N kapitalo, max 1x. Dieninis, mokestis 0,1 % nuo apyvartos.
Signalas pagal vakarykštę uždarymo kainą (be ateities duomenų)."""
import pandas as pd, numpy as np, os
D = os.path.expanduser("~/Desktop/trading-research/freqtrade/user_data/data/binance")
U = {"alts10 (2021-11–2026)": (["XRP","BNB","SOL","DOGE","ADA","TRX","LINK","AVAX","LTC","DOT"], "2021-11-08", "2026-11-08"),
     "BTC+ETH (2021-11–2026)": (["BTC","ETH"], "2021-11-08", "2026-11-08"),
     "2021-11 top 20 su LUNA/FTT": (["BNB","SOL","ADA","XRP","DOT","DOGE","SHIB","LUNA","AVAX","LTC","LINK","UNI","ALGO","BCH","TRX","MANA","AXS","ATOM","FTT","ICP"], "2021-11-08", "2026-11-08"),
     "BTC+ETH (2018–2021-11, nematytas)": (["BTC","ETH"], "2018-01-01", "2021-11-08"),
     "2018 top 9 (2018–2021-11, nematytas)": (["XRP","LTC","XLM","ADA","TRX","NEO","IOTA","BNB","ETC"], "2018-01-01", "2021-11-08")}
FEE = 0.001
def load(c):
    f = f"{D}/{c}_USDT-1d.feather"
    if not os.path.exists(f): return None
    d = pd.read_feather(f)[["date","close"]].set_index("date")["close"]; d.index = d.index.tz_localize(None); return d
def run(coins, a, b, tv, lbs=(21,63,252)):
    px = pd.concat({c: load(c) for c in coins if load(c) is not None}, axis=1).sort_index()
    r = px.pct_change()
    sig = sum(np.sign(px / px.shift(l) - 1).clip(lower=0) for l in lbs) / len(lbs)
    vol = r.rolling(60).std() * np.sqrt(365)
    w = (sig * (tv / vol)).clip(upper=1.0) if tv else sig
    w = w.div(len(coins))  # 1/N kiekvienai
    w = w.shift(1)  # vakarykštis signalas
    w = w[(w.index >= a) & (w.index < b)].fillna(0); rr = r.loc[w.index].fillna(0)
    pr = (w * rr).sum(axis=1) - w.diff().abs().sum(axis=1).fillna(0) * FEE
    eq = (1 + pr).cumprod(); yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = (eq.iloc[-1] ** (1 / yrs) - 1) * 100; dd = ((eq / eq.cummax()) - 1).min() * 100
    yr = (1 + pr).groupby(pr.index.year).prod().sub(1).mul(100).round(0).astype(int).to_dict()
    bh = (1 + rr.mean(axis=1)).cumprod(); bhc = (bh.iloc[-1] ** (1 / yrs) - 1) * 100
    return cagr, dd, yr, bhc, w.sum(axis=1).mean()
out = ["# 104 Trendo ansamblis – rezultatai\n", "| Rinkinys | Variantas | %/m. | Max kritimas | Vid. ekspozicija | Metai | Laikymas %/m. |", "|---|---|---|---|---|---|---|"]
for name, (coins, a, b) in U.items():
    for tv, lab in [(None, "be vol taikymo"), (0.4, "vol 40 %"), (0.6, "vol 60 %")]:
        c, dd, yr, bh, ex = run(coins, a, b, tv)
        out.append(f"| {name} | {lab} | {c:+.1f} | {dd:.0f} % | {ex:.2f} | {yr} | {bh:+.1f} |")
open("rezultatai_raw.md", "w").write("\n".join(out) + "\n"); print("\n".join(out))
