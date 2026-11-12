"""Instagram zak.elga: „absorbcija“. Stiprus agresyvių pardavėjų perviršis (delta), bet kaina nedaro naujos žemumos -> kaina kils (ir atvirkščiai).
Binance futures 5 min. (taker buy volume = agresyvūs pirkėjai), BTC ir ETH, 2021-2026.
Signalas bar t: 30 min. lango delta z <= -Z (vertinta tik pagal praeitį), lango apyvarta >= 1,5x mediana (didelės apyvartos zona),
paskutinių 3 žvakių žemuma >= pirmųjų 3 žemumos (naujos žemumos nėra). Įėjimas kitos žvakės atidarymu, laikoma 1 val. arba 4 val."""
import zipfile
from pathlib import Path
import numpy as np, pandas as pd

D = Path(__file__).parent / "data"
COLS = ["t", "open", "high", "low", "close", "volume", "ct", "qv", "n", "tbv", "tbq", "ig"]
COST = 0.001  # 0,1 % už sandorį (mokesčiai + slydimas)


def load(sym):
    parts = []
    for f in sorted(D.glob(f"{sym}-5m-*.zip")):
        with zipfile.ZipFile(f) as z:
            x = pd.read_csv(z.open(z.namelist()[0]), header=None, names=COLS)
        x = x[pd.to_numeric(x.t, errors="coerce").notna()].astype(float)
        parts.append(x)
    df = pd.concat(parts).drop_duplicates("t").sort_values("t")
    df.index = pd.to_datetime(df.t, unit="ms", utc=True)
    return df


out = ["Vid. grąža po signalo, bp (0,01 %), BE kaštų. 'visi' = vidurkis visoms žvakėms. Sandoris = su 0,1 % kaštais, be persidengimų."]
for sym in ("BTCUSDT", "ETHUSDT"):
    df = load(sym)
    o, h, l, c, v = (df[k].values for k in ("open", "high", "low", "close", "volume"))
    delta = pd.Series(2 * df.tbv.values - v, index=df.index)
    dw = delta.rolling(6).sum(); vw = df.volume.rolling(6).sum()
    z = dw / dw.rolling(8640, min_periods=2000).std().shift(1)
    heavy = (vw >= 1.5 * vw.rolling(8640, min_periods=2000).median().shift(1)).values
    low3, lowfirst = df.low.rolling(3).min().values, df.low.shift(3).rolling(3).min().values
    high3, highfirst = df.high.rolling(3).max().values, df.high.shift(3).rolling(3).max().values
    zz = z.values; n = len(df)
    fwd = {H: np.full(n, np.nan) for H in (12, 48)}
    for H in fwd:
        fwd[H][:n - H - 1] = c[H:n - 1] / o[1:n - H] - 1  # įėjimas t+1 open, išėjimas t+H close
    yr = df.index.year.values
    out.append(f"\n{sym}: {n} žvakių, visi: 1 val. {1e4 * np.nanmean(fwd[12]):+.1f} bp, 4 val. {1e4 * np.nanmean(fwd[48]):+.1f} bp")
    for Z in (1.5, 2.0, 3.0):
        groups = {
            "absorbcija long": (zz <= -Z) & heavy & (low3 >= lowfirst), "pardavėjai laimi": (zz <= -Z) & heavy & (low3 < lowfirst),
            "absorbcija short": (zz >= Z) & heavy & (high3 <= highfirst), "pirkėjai laimi": (zz >= Z) & heavy & (high3 > highfirst)}
        for name, m in groups.items():
            sgn = 1 if "long" in name or "pardavėjai" in name else -1  # kryptis, kurią siūlo įrašas (atšokimas)
            idx = np.where(m & ~np.isnan(fwd[48]))[0]
            if len(idx) < 30:
                out.append(f"  Z={Z} {name:17}: per mažai ({len(idx)})"); continue
            r1, r4 = sgn * fwd[12][idx], sgn * fwd[48][idx]
            # sandoriai be persidengimo, 1 val.
            tr, last = [], -1
            for i in idx:
                if i > last: tr.append((yr[i], sgn * fwd[12][i] - COST)); last = i + 12
            t = pd.DataFrame(tr, columns=["y", "r"])
            early, late = t[t.y <= 2023].r.mean(), t[t.y >= 2024].r.mean()
            out.append(f"  Z={Z} {name:17}: {len(idx):6} sig., 1 val. {1e4 * r1.mean():+6.1f} bp (laimi {100 * (r1 > 0).mean():.0f} %), "
                       f"4 val. {1e4 * r4.mean():+6.1f} bp | sandoriai {len(t)}: {1e4 * t.r.mean():+6.1f} bp "
                       f"(2021-23 {1e4 * early:+.1f}, 2024-26 {1e4 * late:+.1f})")
print("\n".join(out)); (Path(__file__).parent / "REZULTATAI.txt").write_text("\n".join(out))
