"""Noise Breakout NAS100 (noise3.py logika, kas 60 min., long+short, 9:30-16:00 ET) -> sandoriai su datomis."""
import sys; sys.path.insert(0, "/home/kris/Desktop/trading-research/tradingview/scalp_test")
from noise3 import sess, run
from sim import load
x = sess(load("/home/kris/Desktop/trading-research/tradingview/ovn_box/data", "NAS100", "5min"), "America/New_York", 570, 960)
t = run(x, 570, 960, 60); t.to_csv("/home/kris/Desktop/trading-research/tradingview/ce50/noise_trades.csv", index=False)
print(len(t), t.day.min(), t.day.max(), t.ret.mean())
