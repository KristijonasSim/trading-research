"""Make the next batch of 50 strategies from user_data/strategies/extra (sorted by file name,
skipping strategies already in earlier batches). Usage: .venv/bin/python make_batch.py batch50f"""
import json, re, shutil, sys
from pathlib import Path

S = Path(__file__).parent / "user_data/strategies"
name = sys.argv[1]
done = set()
for b in S.glob("batch50*/_list.json"):
    done |= {s for s, _, _ in json.loads(b.read_text())}
out = []
for f in sorted((S / "extra").glob("*.py")):
    src = f.read_text(errors="replace")
    classes = re.findall(r"^class\s+(\w+)\s*\(([^)]*)\)", src, re.M)
    cls = [c for c, base in classes if "Strategy" in base or "IStrategy" in base or c == f.stem]
    if not cls:
        continue
    c = f.stem if f.stem in cls else cls[-1]
    if c in done:
        continue
    m = re.search(r"^\s*(?:timeframe|ticker_interval)\s*=\s*['\"](\w+)['\"]", src, re.M)
    out.append([c, f.name, m.group(1) if m else "5m"])
    if len(out) == 50:
        break
d = S / name
d.mkdir(exist_ok=False)
for c, fn, tf in out:
    shutil.copy(S / "extra" / fn, d / fn)
(d / "_list.json").write_text(json.dumps(out))
print(len(out), out[0][0], "...", out[-1][0], sorted({tf for *_, tf in out}))
# 1m data for 10 alts over 5 years does not fit in 10 GB RAM: mark those tests as skipped
for c, fn, tf in out:
    if tf == "1m":
        r = S.parent.parent / "results" / name / f"alts10__{c}"
        r.mkdir(parents=True, exist_ok=True)
        (r / "error.txt").write_text("out of memory: 1m data, 10 pairs, 5 years needs > 10 GB (skipped)")
