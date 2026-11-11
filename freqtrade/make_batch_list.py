"""Batches of 50 from sources_more/new_strategies.txt (name<TAB>path), skipping names already
tested in batch50*/batchM*. Usage: .venv/bin/python make_batch_list.py  -> batchM1, batchM2, ..."""
import json, re, shutil
from pathlib import Path

ROOT = Path(__file__).parent
S = ROOT / "user_data/strategies"
done = set()
for b in list(S.glob("batch50*/_list.json")) + list(S.glob("batchM*/_list.json")):
    done |= {s for s, _, _ in json.loads(b.read_text())}
todo = []
for line in (ROOT / "sources_more/new_strategies.txt").read_text().splitlines():
    name, path = line.split("\t")
    if name in done: continue
    src = (ROOT / path).read_text(errors="replace")
    m = re.search(rf"class\s+{name}\b.*?^\s*(?:timeframe|ticker_interval)\s*=\s*['\"](\w+)['\"]", src, re.M | re.S) \
        or re.search(r"^\s*(?:timeframe|ticker_interval)\s*=\s*['\"](\w+)['\"]", src, re.M)
    todo.append((name, ROOT / path, m.group(1) if m else "5m"))
k = 1
while (S / f"batchM{k}").exists(): k += 1
for i in range(0, len(todo), 50):
    d = S / f"batchM{k}"; d.mkdir()
    lst = []
    for name, p, tf in todo[i:i + 50]:
        fn = f"{name}__{p.name}" if (d / p.name).exists() else p.name
        shutil.copy(p, d / fn); lst.append([name, fn, tf])
        if tf == "1m":  # does not fit in RAM for 10 alts x 5 years
            r = ROOT / "results" / f"batchM{k}" / f"alts10__{name}"; r.mkdir(parents=True, exist_ok=True)
            (r / "error.txt").write_text("out of memory: 1m data, 10 pairs, 5 years needs > 10 GB (skipped)")
    (d / "_list.json").write_text(json.dumps(lst))
    print(f"batchM{k}", len(lst), sorted({x[2] for x in lst})); k += 1
