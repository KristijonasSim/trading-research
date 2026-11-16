import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
exec(open("test.py").read().split("sig = lambda p: F")[0])
import xsec
out = ["\n## Atsparumas (long-short)\n", "| Variantas | 2019–21 %/m. | kritimas | 2021–26 %/m. | kritimas | Metai 2021–26 |", "|---|---|---|---|---|---|"]
def row(n, e):
    s1 = stats(e, "2019-01-01", "2021-11-08"); s2 = stats(e, "2021-11-08", "2026-11-08")
    out.append(f"| {n} | {s1['cagr']:+} | {s1['dd']} % | {s2['cagr']:+} | {s2['dd']} % | {s2['yearly']} |"); print(out[-1], flush=True)
row("bazinis", run(P, V, lambda p: F, 7, side="ls"))
row("signalas vėluoja 1 d.", run(P, V, lambda p: F.shift(1), 7, side="ls"))
xsec.FEE = 0.002; row("mokestis 0,2 %", xsec.run(P, V, lambda p: F, 7, side="ls")); xsec.FEE = 0.001
row("top 30", run(P, V, lambda p: F, 7, side="ls", topn=30))
row("top 100", run(P, V, lambda p: F, 7, side="ls", topn=100))
row("kraštas 10 %", run(P, V, lambda p: F, 7, side="ls", q=0.1))
row("kraštas 30 %", run(P, V, lambda p: F, 7, side="ls", q=0.3))
row("perbalansuoti kas 14 d.", run(P, V, lambda p: F, 14, side="ls"))
# tik short pusė ir tik long pusė (prieš lygių svorių krepšelį)
open("rezultatai_raw.md", "a").write("\n".join(out) + "\n")
