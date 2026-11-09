#!/usr/bin/env python3
"""
Build synthetic 3x ETF 5m candles from the 1x ETF (Dukascopy, regular US hours) and write them in
Freqtrade format (feather) as fake "<ETF>/USDT" pairs, plus an offline market list for them.

3x daily-reset ETF: during day d every price = L_prev * (1 + 3 * (P / P_prevclose - 1)),
where P_prevclose is yesterday's last 1x close and L_prev yesterday's last 3x close.
At the end of each day a drag of (expense 0.95 % + financing ~2x short rate) / 252 is applied.
Gaps between days are therefore also levered 3x, like the real funds.

Usage: python build.py  -> ft/data/binance/*.feather, ft/offline/binance_markets.json
"""
import copy, json, shutil
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
FT = ROOT / "ft/data/binance"
OFF = ROOT / "ft/offline"
LEV = {"QQQ": "TQQQ", "SPY": "UPRO", "DIA": "UDOW", "IWM": "TNA", "SMH": "SOXL", "XLK": "TECL", "XLF": "FAS",
       "XLE": "ERX", "GDX": "NUGT", "GDXJ": "JNUG", "FXI": "YINN", "TLT": "TMF", "XLV": "CURE", "IYR": "DRN",
       "XLU": "UTSL", "EEM": "EDC", "KRE": "DPST", "EWZ": "BRZU"}
# yearly short rate (approx. fed funds average) for the financing drag
RATE = {2021: 0.001, 2022: 0.018, 2023: 0.051, 2024: 0.051, 2025: 0.043, 2026: 0.037}


def load(t):
    df = pd.read_csv(DATA / f"{t}_5m.csv", index_col=0, parse_dates=True)[["open", "high", "low", "close", "volume"]]
    df = df[df["volume"] > 0]
    ny = df.index.tz_convert("America/New_York")
    df = df[(ny.time >= pd.Timestamp("09:30").time()) & (ny.time < pd.Timestamp("16:00").time())]
    return df


def lever(df):
    day = df.index.tz_convert("America/New_York").date
    out, L, prev_close = [], 100.0, None
    for d, g in df.groupby(day, sort=True):
        if prev_close is None:  # first day: no reference yet
            prev_close = g["close"].iloc[-1]
            continue
        k = L / prev_close
        x = g.copy()
        for c in ("open", "high", "low", "close"):
            x[c] = L * (1 + 3 * (g[c] / prev_close - 1))
        out.append(x)
        drag = (0.0095 + 2 * RATE.get(d.year, 0.04)) / 252
        L = x["close"].iloc[-1] * (1 - drag)
        prev_close = g["close"].iloc[-1]
    return pd.concat(out)


def to_ft(df, pair, tf="5m"):
    x = df.copy()
    if tf != "5m":
        x = x.resample(tf, label="left", closed="left").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
    x = x.reset_index().rename(columns={x.index.name or "index": "date"})
    x = x.rename(columns={x.columns[0]: "date"})
    x["date"] = pd.to_datetime(x["date"], utc=True)
    x[["date", "open", "high", "low", "close", "volume"]].to_feather(FT / f"{pair.replace('/', '_')}-{tf}.feather")


def main():
    FT.mkdir(parents=True, exist_ok=True)
    OFF.mkdir(parents=True, exist_ok=True)
    pairs = []
    for base, lev in LEV.items():
        if not (DATA / f"{base}_5m.csv").exists():
            print("missing", base)
            continue
        one = load(base)
        three = lever(one)
        for tf in ("5m", "1h", "4h", "1d"):
            to_ft(three, f"{lev}/USDT", tf)
        pairs.append(f"{lev}/USDT")
        if base == "SPY":  # 1x SPY is the market filter (replaces BTC in the strategies)
            for tf in ("5m", "1h", "4h", "1d"):
                to_ft(one, "SPY/USDT", tf)
        print(lev, len(three), f"{three['close'].iloc[0]:.1f} -> {three['close'].iloc[-1]:.1f}")
    # offline market list: Binance markets + fake ETF pairs (fine price/amount precision)
    src = ROOT.parent / "freqtrade/docker_offline"
    mk = json.load(open(src / "binance_markets.json"))
    tpl = next(m for m in mk if m["symbol"] == "BTC/USDT")
    for p in pairs + ["SPY/USDT"]:
        m = copy.deepcopy(tpl)
        b = p.split("/")[0]
        m.update(symbol=p, id=f"{b}USDT", base=b, baseId=b, lowercaseId=f"{b.lower()}usdt")
        m["precision"] = {**m["precision"], "price": 1e-6, "amount": 1e-6}
        m["limits"]["amount"] = {"min": 1e-6, "max": 1e9}
        m["limits"]["cost"] = {"min": 1, "max": 1e9}
        m["limits"]["price"] = {"min": 1e-6, "max": 1e9}
        mk.append(m)
    json.dump(mk, open(OFF / "binance_markets.json", "w"), default=str)
    shutil.copy(src / "sitecustomize.py", OFF / "sitecustomize.py")
    json.dump(pairs, open(ROOT / "ft/pairs.json", "w"))
    print(len(pairs), "pairs")


if __name__ == "__main__":
    main()
