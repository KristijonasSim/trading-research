"""Scan sources_more6 for IStrategy classes not tested yet -> sources_more6/new_strategies.txt (name<TAB>path)."""
import json, re, hashlib
from pathlib import Path
ROOT = Path(__file__).parent; S = ROOT / "user_data/strategies"
done = set(); hashes = set()
for b in list(S.glob("batch50*/_list.json")) + list(S.glob("batchM*/_list.json")):
    done |= {s.lower() for s, _, _ in json.loads(b.read_text())}
for d in ["spot", "futures", "extra"] + [p.name for p in S.glob("batch*")]:
    for p in (S / d).glob("*.py"):
        t = p.read_text(errors="replace"); hashes.add(hashlib.md5(t.encode()).hexdigest())
        done |= {m.lower() for m in re.findall(r"^class\s+(\w+)\s*\(", t, re.M)}
out = []; seen = set()
for p in sorted((ROOT / "sources_more6").rglob("*.py")):
    if not p.is_file(): continue
    if any(x in p.parts for x in ("hyperopts", "tests", "test", ".git")): continue
    t = p.read_text(errors="replace")
    if "IStrategy" not in t or hashlib.md5(t.encode()).hexdigest() in hashes: continue
    for name in re.findall(r"^class\s+(\w+)\s*\(\s*IStrategy\s*\)", t, re.M):
        if name.lower() in done or name.lower() in seen: continue
        seen.add(name.lower()); out.append(f"{name}\t{p.relative_to(ROOT)}")
(ROOT / "sources_more6/new_strategies.txt").write_text("\n".join(out) + "\n")
print(len(out))
