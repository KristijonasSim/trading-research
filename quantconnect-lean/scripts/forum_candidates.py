"""List forum backtests that only need price data (no universes/fundamentals/options/futures/custom data)."""
import re, glob, sys, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
BAD = ["AddUniverse", "Coarse", "Fine", "Fundamental", "AddData", "AddFuture", "AddOption", "AddCrypto", "AddCfd"]
cands, tick = [], set()
for d in sorted(glob.glob(str(ROOT / "sources/forum") + "/*/*/")):
    files = glob.glob(d + "*.py")
    if not files or not any(Path(f).name == "main.py" for f in files):
        continue
    s = "".join(open(f, errors="ignore").read() for f in files)
    if any(b in s for b in BAD) or "AddForex" in s:
        continue
    t = set(re.findall(r"['\"]([A-Z]{1,5})['\"]", s))
    cands.append({"dir": d, "tickers": sorted(t)})
    tick |= t
json.dump(cands, open(ROOT / "scripts/forum_candidates.json", "w"), indent=1)
print(len(cands), "candidates;", len(tick), "tickers")
print(" ".join(sorted(tick)))
