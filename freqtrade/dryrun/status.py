"""Dry-run botų suvestinė: python3 dryrun/status.py"""
import sqlite3, glob, os
for db in sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "*/tradesv3.dryrun.sqlite"))):
    c = sqlite3.connect(db); n = os.path.basename(os.path.dirname(db))
    closed = c.execute("select count(*), coalesce(sum(close_profit_abs),0) from trades where is_open=0").fetchone()
    opn = c.execute("select pair, open_rate, open_date from trades where is_open=1").fetchall()
    print(f"{n:11s} uždaryta {closed[0]:3d}, pelnas {closed[1]:+8.2f} USDT | atviri: {opn}")
