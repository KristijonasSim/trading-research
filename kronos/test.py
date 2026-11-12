"""Kronos (Instagram jesserurka, „$24k Bloomberg vs nemokamas modelis“): ar prognozė padeda prekiauti?
Kas 4 val. modelis mato 400 val. žvakių ir prognozuoja 4 val. į priekį. Jei prognozė aukščiau dabartinės kainos -> long, žemiau -> short.
Laikotarpis 2025-07..2026-11 (po modelio paskelbimo, kad nebūtų matytas mokantis)."""
import sys, time
from pathlib import Path
import numpy as np, pandas as pd, torch
sys.path.insert(0, str(Path(__file__).parent / "src"))
from model import Kronos, KronosTokenizer, KronosPredictor

torch.set_num_threads(24); torch.manual_seed(0)
R = Path(__file__).resolve().parents[1]
name, model_name = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "NeoQuasar/Kronos-small"
if name == "BTC":
    df = pd.read_feather(R / "freqtrade/user_data/data/binance/BTC_USDT-1h.feather").set_index("date")
    COST = 0.001  # 0,05 % į kiekvieną pusę
else:
    fs = sorted((R / "tradingview/ovn_box/data").glob("NAS100_*.csv"))
    df = pd.concat(pd.read_csv(f, index_col=0, parse_dates=True) for f in fs)
    df = df[~df.index.duplicated()].sort_index().resample("1h").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
    COST = 0.0002  # ~2 t. iš 20000
df = df[["open", "high", "low", "close", "volume"]].astype(float)
df["amount"] = df.volume * df.close
LB, H, STEP, BATCH = 400, 4, 4, 32
tok = KronosTokenizer.from_pretrained("NeoQuasar/Kronos-Tokenizer-base")
pred = KronosPredictor(Kronos.from_pretrained(model_name), tok, device="cpu", max_context=512)

idx = np.where(df.index >= pd.Timestamp("2025-07-01", tz=df.index.tz))[0]
idx = idx[(idx >= LB) & (idx + H < len(df))][::STEP]
ts = pd.Series(df.index)
out, t0 = [], time.time()
for b in range(0, len(idx), BATCH):
    chunk = idx[b:b + BATCH]
    xs = [df.iloc[i - LB:i].reset_index(drop=True) for i in chunk]
    xt = [ts.iloc[i - LB:i].reset_index(drop=True) for i in chunk]
    yt = [ts.iloc[i:i + H].reset_index(drop=True) for i in chunk]
    ps = pred.predict_batch(xs, xt, yt, pred_len=H, T=1.0, top_p=0.9, sample_count=5, verbose=False)
    for i, p in zip(chunk, ps):
        last = df.close.iloc[i - 1]
        out.append(dict(t=df.index[i], pred=p.close.iloc[-1] / last - 1, real=df.close.iloc[i + H - 1] / last - 1))
    print(f"{b + len(chunk)}/{len(idx)} {time.time() - t0:.0f}s", flush=True)

r = pd.DataFrame(out).set_index("t")
r.to_csv(Path(__file__).parent / f"pred_{name}.csv")
sig = np.sign(r.pred)
pnl = sig * r.real - COST
hit = (sig == np.sign(r.real)).mean()
eq = (1 + pnl).prod()
bh = df.close.iloc[idx[-1] + H - 1] / df.close.iloc[idx[0] - 1]
lines = [f"{name} {model_name}: {len(r)} prognozių 2025-07..2026-11",
         f"Krypties atspėjimas: {100 * hit:.1f} % (aklas spėjimas ~50 %)",
         f"Visada long atspėtų: {100 * (r.real > 0).mean():.1f} %",
         f"Koreliacija prognozė/realybė: {r.pred.corr(r.real):.3f}",
         f"Prekyba (long/short kas 4 val., su kaštais): x{eq:.2f}; be kaštų x{(1 + sig * r.real).prod():.2f}",
         f"Pirkti ir laikyti: x{bh:.2f}"]
print("\n".join(lines))
(Path(__file__).parent / f"REZ_{name}.txt").write_text("\n".join(lines))
