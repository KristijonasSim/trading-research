"""SPY, QQQ, IWM, DIA, TLT, GLD, EFA dienos OHLC (Yahoo, auto_adjust) 2000 – dabar."""
import os, yfinance as yf
D = os.path.dirname(os.path.abspath(__file__))
for t in ("SPY", "QQQ", "IWM", "DIA", "TLT", "GLD", "EFA", "BIL"):
    d = yf.download(t, start="2000-01-01", auto_adjust=True, progress=False, multi_level_index=False)
    d.to_csv(f"{D}/data/{t}.csv"); print(t, len(d), d.index[0].date(), d.index[-1].date())
