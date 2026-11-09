"""Yahoo daily OHLCV (dividend/split adjusted) 2019-01-01..2026-11-09 -> raw/daily/<T>.csv"""
import sys, pathlib, yfinance as yf
out = pathlib.Path(sys.argv[2]); ok, bad = [], []
for t in open(sys.argv[1]).read().split():
    df = yf.download(t, start="2019-01-01", end="2026-11-10", interval="1d", auto_adjust=True, progress=False, multi_level_index=False)
    if df is None or len(df) < 50: bad.append(t); continue
    raw = yf.download(t, start="2019-01-01", end="2026-11-10", interval="1d", auto_adjust=False, progress=False, multi_level_index=False)
    df["raw_close"] = raw["Close"]
    df.to_csv(out / f"{t}.csv"); ok.append(t)
print("OK", len(ok), " ".join(ok)); print("MISSING", len(bad), " ".join(bad))
