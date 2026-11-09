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

# numpy 2 also removed np.NAN
try:
    if not hasattr(_np, "NAN"):
        _np.NAN = _np.nan
except Exception:
    pass

# old strategies import IntParameter/CategoricalParameter/... from freqtrade.strategy.hyper;
# newer freqtrade keeps them in freqtrade.strategy.parameters -> add them back after import
import importlib.abc, importlib.machinery, sys as _sys


class _HyperShim(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path, target=None):
        if name != "freqtrade.strategy.hyper":
            return None
        spec = importlib.machinery.PathFinder.find_spec(name, path)
        if spec is None:
            return None
        orig = spec.loader.exec_module

        def exec_module(module):
            orig(module)
            try:
                from freqtrade.strategy import parameters as _p
                for k in dir(_p):
                    if k.endswith("Parameter") and not hasattr(module, k):
                        setattr(module, k, getattr(_p, k))
            except Exception:
                pass
        spec.loader.exec_module = exec_module
        return spec


_sys.meta_path.insert(0, _HyperShim())
