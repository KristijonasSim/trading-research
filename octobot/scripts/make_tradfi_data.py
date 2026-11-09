"""Turn Dukascopy CSVs into OctoBot backtest .data files (one per instrument, quoted as <X>/USDT)."""
import json, sqlite3, time, sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
RAWD = ROOT / "backtesting/raw_tradfi"
START, END = 1636329600, 1794096000
TF = {"1h": ("1h", 3600), "4h": ("4h", 14400), "1d": ("1D", 86400)}
for name in ["US30", "NAS100", "SPX500", "XAU"]:
    df = pd.read_csv(RAWD / f"{name}_1h.csv", index_col=0, parse_dates=True)
    df = df[["open", "high", "low", "close", "volume"]]
    sym = f"{name}/USDT"
    f = ROOT / f"backtesting/data/{name.lower()}.data"
    f.unlink(missing_ok=True)
    con = sqlite3.connect(f)
    con.execute("CREATE TABLE description (timestamp datetime, version text, type text, exchange text, symbols text, time_frames text, start_timestamp text, end_timestamp)")
    con.execute("CREATE TABLE ohlcv (timestamp datetime, exchange_name text, cryptocurrency text, symbol text, time_frame text, candle)")
    con.execute("CREATE INDEX index_ohlcv_timestamp ON ohlcv (timestamp)")
    for tf, (rule, secs) in TF.items():
        r = df.resample(rule, label="left", closed="left").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
        rows = []
        for ts, c in r.iterrows():
            t = int(ts.timestamp())
            if START <= t < END:
                rows.append((t + secs, "binance", name, sym, tf,
                             json.dumps([t, c.open, c.high, c.low, c.close, c.volume])))
        con.executemany("INSERT INTO ohlcv VALUES (?,?,?,?,?,?)", rows)
        print(name, tf, len(rows))
    con.execute("INSERT INTO description VALUES (?,?,?,?,?,?,?,?)",
                (time.time(), "2.0", "exchange", "binance", json.dumps([sym]),
                 json.dumps(list(TF)), str(START), str(END)))
    con.commit()
