"""Loaded automatically by Python inside the offline Docker container.
Binance market list comes from a saved file instead of the internet (container has no network)."""
import json
_M = None


def _markets():
    global _M
    if _M is None:
        _M = json.load(open("/offline/binance_markets.json"))
    return _M


try:
    import ccxt, ccxt.async_support as accxt

    def _sync(self, params={}):
        return _markets()

    async def _async(self, params={}):
        return _markets()

    async def _acur(self, params={}):
        return {}

    ccxt.binance.fetch_markets = _sync
    ccxt.binance.fetch_currencies = lambda self, params={}: {}
    accxt.binance.fetch_markets = _async
    accxt.binance.fetch_currencies = _acur
except Exception:
    pass

# numpy 2 removed np.NaN; old strategies still use it (same value as np.nan)
try:
    import numpy as _np
    if not hasattr(_np, "NaN"):
        _np.NaN = _np.nan
except Exception:
    pass
