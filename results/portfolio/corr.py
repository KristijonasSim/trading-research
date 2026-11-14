"""Atrinktų freqtrade strategijų koreliacija ir lygiais svoriais portfelis iš backtestų sandorių eksportų (results/validate50/detail_*_none_*).
Dienos grąža = per dieną uždarytų sandorių pelnas / metų pradžios balansas (1000 USDT; kiekvieni metai atskiras backtestas) – tik realizuotas pelnas (apytiksliai).
Paleisti: freqtrade/.venv/bin/python results/portfolio/corr.py"""
import glob, json, os, zipfile, re
import pandas as pd, numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); V = f"{ROOT}/freqtrade/results/validate50"
def trades(d):
    z = sorted(glob.glob(f"{d}/backtest-result-*.zip"))
    if not z: return None
    with zipfile.ZipFile(z[-1]) as f:
        name = [n for n in f.namelist() if n.endswith(".json") and "config" not in n and "meta" not in n][0]; js = json.loads(f.read(name))
    st = list(js["strategy"].values())[0]; t = pd.DataFrame(st["trades"]); return t, st.get("starting_balance", 1000)
series = {}
for d in sorted(glob.glob(f"{V}/detail_*_none_*")):
    m = re.match(r".*detail_(.+)_(alts10|btc_eth)_none_(\d{4}|full)$", d)
    if not m: continue
    s = f"{m.group(1)} ({m.group(2)})"; r = trades(d)
    if r is None: continue
    t, bal = r; t["d"] = pd.to_datetime(t.close_date).dt.tz_localize(None).dt.normalize()
    if m.group(3) == "full":
        daily = t.groupby("d").profit_abs.sum(); eq = bal + daily.cumsum(); ret = (eq / eq.shift(1).fillna(bal) - 1)
    else:
        daily = t.groupby("d").profit_abs.sum(); eq = bal + daily.cumsum(); ret = eq / eq.shift(1).fillna(bal) - 1
    series.setdefault(s, []).append(ret)
R = pd.DataFrame({k: pd.concat(v).groupby(level=0).sum() for k, v in series.items()}).sort_index()
R = R[(R.index >= "2022-01-01") & (R.index < "2026-01-01")].fillna(0)
R = R.reindex(pd.date_range("2022-01-01", "2025-12-31")).fillna(0)
def stat(x):
    e = (1 + x).cumprod(); y = len(x) / 365.25; return f"{(e.iloc[-1] ** (1 / y) - 1) * 100:+6.1f}%/m. kr {(e / e.cummax() - 1).min() * 100:5.1f}%"
print("2022–2025 (realizuotas pelnas):")
for c in R.columns: print(f"  {c:40s} {stat(R[c])}")
W = R.resample("W").sum(); C = W.corr()
print("\nsavaitinių grąžų koreliacija:"); print(C.round(2).to_string())
print(f"\nlygiais svoriais ({len(R.columns)} strategijos, kasdien perbalansuojant): {stat(R.mean(axis=1))}")
alts = [c for c in R.columns if "alts10" in c]; be = [c for c in R.columns if "btc_eth" in c]
print(f"tik alts10 ({len(alts)}): {stat(R[alts].mean(axis=1))} | tik BTC+ETH ({len(be)}): {stat(R[be].mean(axis=1))}")
