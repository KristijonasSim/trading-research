"""Download 1h candles (2021-11-08 .. 2026-11-08) from Dukascopy for US30, NAS100, SPX500, gold."""
import sys, datetime as dt
import dukascopy_python as d, dukascopy_python.instruments as i
INS = {"US30": i.I_USA30_IDX_USD, "NAS100": i.I_USATECH_IDX_USD,
       "SPX500": i.I_USA500_IDX_USD, "XAU": i.I_XAU_USD}
out = sys.argv[1]
for name, ins in INS.items():
    df = d.to_dataframe(d.fetch_candles(ins, 1, d.TimeUnit.HOUR, d.OfferSide.BID,
                 dt.datetime(2021, 11, 1), dt.datetime(2026, 11, 9)))
    df.to_csv(f"{out}/{name}_1h.csv")
    print(name, len(df), df.index[0], df.index[-1], df.iloc[0].to_dict(), flush=True)
