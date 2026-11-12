"""Instagram teiginys (rithvikrishna64): nakties dėžė (18:00-9:30 ET) dalinama pusiau.
Atidarymas 9:30 viršutinėje pusėje -> nakties max pasiekiamas 80.8 %, apatinėje -> min 75.7 %.
Tikriname: 1) ar tikslumas atsikartoja, 2) ar galima uždirbti (pirkti/parduoti atidaryme, tikslas = artimesnis kraštas)."""
import sys
from pathlib import Path
import numpy as np, pandas as pd

D = Path(sys.argv[1])
df = pd.concat(pd.read_csv(f, index_col=0, parse_dates=True) for f in sorted(D.glob("NAS100_*.csv")))
df = df[~df.index.duplicated()].sort_index()
df.index = df.index.tz_convert("America/New_York")
COST = 2.0  # taškai už sandorį (spread + slydimas)

t = df.index.hour * 60 + df.index.minute
rth = (t >= 570) & (t < 960)
day = pd.Series(df.index.date, index=df.index)
import datetime as _dt
# nakties sesija priskiriama kitai dienai: 18:00+ -> rytojus
on_day = np.where(t >= 1080, (day + _dt.timedelta(days=1)).values, day.values)
on_mask = (t >= 1080) | (t < 570)

on = df[on_mask].groupby(on_day[on_mask]).agg(oh=("high", "max"), ol=("low", "min"))
rows = []
for d, g in df[rth].groupby(day[rth].values):
    k = d
    if k not in on.index or len(g) < 70 or g.index[0].strftime("%H:%M") != "09:30":
        continue
    oh, ol = on.loc[k, "oh"], on.loc[k, "ol"]
    o = g.open.iloc[0]
    if not (ol < o < oh):
        rows.append(dict(date=d, zone="outside")); continue
    upper = o >= (oh + ol) / 2
    near, far = (oh, ol) if upper else (ol, oh)
    hi, lo = g.high.values, g.low.values
    hit_near = (hi.max() >= oh) if upper else (lo.min() <= ol)
    hit_far = (lo.min() <= ol) if upper else (hi.max() >= oh)
    dist = abs(near - o)
    res = dict(date=d, zone="upper" if upper else "lower", hit_near=hit_near, hit_far=hit_far,
               dist=dist, width=oh - ol)
    # prekyba: kryptis į artimesnį kraštą, tikslas = kraštas, stop = tas pats atstumas (1:1) arba tolimas kraštas
    sgn = 1 if upper else -1
    for name, stop in (("rr1", o - sgn * dist), ("far", far)):
        pnl = None
        for h, l in zip(hi, lo):
            tp_hit = h >= near if upper else l <= near
            sl_hit = l <= stop if upper else h >= stop
            if sl_hit:  # jei abu toje pačioje žvakėje, skaičiuojam nuostolį
                pnl = -abs(o - stop); break
            if tp_hit:
                pnl = dist; break
        if pnl is None:
            pnl = sgn * (g.close.iloc[-1] - o)
        res[name] = pnl - COST
    rows.append(res)

r = pd.DataFrame(rows).set_index("date")
inside = r[r.zone != "outside"]
out = []
p = lambda s: f"{100 * s.mean():.1f} %"
out.append(f"Dienų: {len(r)}, atidarymas dėžės viduje: {len(inside)}, už dėžės ribų: {(r.zone == 'outside').sum()}")
for z in ("upper", "lower"):
    s = inside[inside.zone == z]
    out.append(f"{z}: {len(s)} d., artimas kraštas pasiektas {p(s.hit_near)} (Instagram: {'80.8' if z == 'upper' else '75.7'} %), "
               f"tolimas {p(s.hit_far)}, vid. atstumas iki artimo {s.dist.mean():.0f} t., dėžės plotis {s.width.mean():.0f} t.")
out.append("\nPrekyba (taškais NAS100, po 2 t. kaštų), pagal metus:")
inside = inside.assign(y=[x.year for x in inside.index])
tab = inside.groupby("y").agg(n=("rr1", "size"), hit=("hit_near", "mean"), rr1=("rr1", "sum"), far=("far", "sum"),
                              rr1_win=("rr1", lambda x: (x > 0).mean()), far_win=("far", lambda x: (x > 0).mean()))
tab.loc["VISO"] = [len(inside), inside.hit_near.mean(), inside.rr1.sum(), inside.far.sum(),
                   (inside.rr1 > 0).mean(), (inside.far > 0).mean()]
out.append(tab.round(2).to_string())
out.append(f"\nVidutinis sandoris: 1:1 stop {inside.rr1.mean():.1f} t., stop už tolimo krašto {inside.far.mean():.1f} t.")
print("\n".join(out))
Path(sys.argv[2]).write_text("\n".join(out))
