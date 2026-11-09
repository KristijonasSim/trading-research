"""For each forum thread id: read all pages, collect comment backtest ids (JSON embedded in page),
download each embedded backtest page and extract its source files -> sources/forum/<thread>/<backtest>/."""
import re, json, sys, time, html, urllib.request
from pathlib import Path
OUT = Path(sys.argv[1]); UA = {"User-Agent": "Mozilla/5.0"}

def get(url):
    try:
        return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read().decode("utf-8", "ignore")
    except Exception:
        return ""

for tid in sys.argv[2:]:
    ids, title, empty = [], "", 0
    for p in range(1, 60):
        s = get(f"https://www.quantconnect.com/forum/discussion/{tid}/x/p{p}")
        found = re.findall(r'"backtest":"([0-9a-f]{32})"', s)
        if p == 1:
            m = re.search(r"<title>([^<]*)</title>", s); title = html.unescape(m.group(1)) if m else ""
        new = [i for i in found if i not in ids]
        empty = 0 if new else empty + 1
        if empty >= 4 or not s:
            break
        ids += new
        time.sleep(0.5)
    tdir = OUT / tid; tdir.mkdir(parents=True, exist_ok=True)
    (tdir / "title.txt").write_text(title)
    n = 0
    for bid in ids:
        s = get(f"https://www.quantconnect.com/terminal/processCache/embedded_backtest_{bid}.html")
        files = re.findall(r'id="[0-9a-f]+_source_([^"]+)"><pre class="prettyprint">(.*?)</pre>', s, re.S)
        if not files:
            continue
        d = tdir / bid[:10]; d.mkdir(exist_ok=True)
        for name, code in files:
            fname = name if "." in name else re.sub(r"(py|cs)$", r".\1", name)
            (d / fname).write_text(html.unescape(code))
        n += 1
        time.sleep(0.3)
    print(tid, title[:70], "backtests:", len(ids), "with code:", n, flush=True)
