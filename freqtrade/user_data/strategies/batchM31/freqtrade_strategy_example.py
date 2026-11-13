"""Example freqtrade strategy using QuantGistProtection.

This strategy trades the EMA crossover on the 1h timeframe and uses
``QuantGistProtection`` to automatically pause trading 10 minutes before
and 5 minutes after any high-impact macro event (NFP, CPI, FOMC, etc.).

Setup
-----
1. Install the plugin::

       pip install quantgist-freqtrade

2. Add the protection to your ``config.json`` (see PROTECTION_CONFIG_EXAMPLE
   below) or configure it directly in the ``protections`` class attribute
   (see this file).

3. Set your API key::

       export QUANTGIST_API_KEY=qg_live_...

4. Run freqtrade normally::

       freqtrade trade --strategy MacroAwareEMACross --config config.json

config.json excerpt
-------------------

    .. code-block:: json

        {
            "protections": [
                {
                    "method": "QuantGistProtection",
                    "api_key": "qg_live_...",
                    "pause_minutes_before": 10,
                    "pause_minutes_after": 5,
                    "impact": "high"
                }
            ],
            "pairlists": [
                {
                    "method": "StaticPairList"
                }
            ],
            "exchange": {
                "name": "binance",
                "pair_whitelist": ["BTC/USDT", "ETH/USDT", "EUR/USD"]
            }
        }
"""

from __future__ import annotations

import os
from datetime import datetime
from functools import reduce
from typing import Optional

# freqtrade imports — only available when running inside freqtrade
try:
    import pandas as pd
    import talib.abstract as ta
    from freqtrade.strategy import IStrategy, merge_informative_pair
    from freqtrade.strategy.interface import IStrategy as _IStratBase

    _FT_AVAILABLE = True
except ImportError:
    _FT_AVAILABLE = False
    IStrategy = object  # type: ignore[assignment, misc]

from qg_freqtrade import QuantGistProtection


# ---------------------------------------------------------------------------
# Strategy
# ---------------------------------------------------------------------------

class MacroAwareEMACross(IStrategy):  # type: ignore[misc]
    """EMA crossover strategy with QuantGist macro-event protection.

    Entry:  EMA(9) crosses above EMA(21) on 1h candles.
    Exit:   EMA(9) crosses below EMA(21), or ROI/stoploss triggers.
    Guard:  ``QuantGistProtection`` blocks all entries around high-impact events.
    """

    # -----------------------------------------------------------------------
    # Strategy metadata
    # -----------------------------------------------------------------------
    INTERFACE_VERSION = 3
    timeframe = "1h"
    can_short = False

    # ROI table
    minimal_roi = {
        "0": 0.04,   # 4 % at any time (take-profit)
        "60": 0.02,  # 2 % after 60 min
        "120": 0.01, # 1 % after 2 h
    }

    stoploss = -0.03   # 3 % stoploss
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02

    # -----------------------------------------------------------------------
    # Protection — configure via env var or hardcode for development
    # -----------------------------------------------------------------------
    @property
    def protections(self) -> list[dict]:  # type: ignore[override]
        return [
            {
                "method": "QuantGistProtection",
                # API key from env var (recommended) or inline for quick testing
                "api_key": os.environ.get("QUANTGIST_API_KEY", "qg_live_YOUR_KEY_HERE"),
                "pause_minutes_before": 10,
                "pause_minutes_after": 5,
                "impact": "high",
                # Cache event list for 5 minutes to avoid repeated API calls
                "cache_ttl_seconds": 300,
            }
        ]

    # -----------------------------------------------------------------------
    # Indicators
    # -----------------------------------------------------------------------

    def populate_indicators(self, dataframe: "pd.DataFrame", metadata: dict) -> "pd.DataFrame":  # type: ignore[name-defined]
        dataframe["ema9"] = ta.EMA(dataframe, timeperiod=9)
        dataframe["ema21"] = ta.EMA(dataframe, timeperiod=21)
        dataframe["ema50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        return dataframe

    # -----------------------------------------------------------------------
    # Entry / exit conditions
    # -----------------------------------------------------------------------

    def populate_entry_trend(self, dataframe: "pd.DataFrame", metadata: dict) -> "pd.DataFrame":  # type: ignore[name-defined]
        dataframe.loc[
            (
                # EMA 9 crosses above EMA 21
                (dataframe["ema9"] > dataframe["ema21"])
                & (dataframe["ema9"].shift(1) <= dataframe["ema21"].shift(1))
                # Price above EMA 50 (uptrend filter)
                & (dataframe["close"] > dataframe["ema50"])
                # RSI not overbought
                & (dataframe["rsi"] < 70)
                # Ensure volume is non-zero
                & (dataframe["volume"] > 0)
            ),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: "pd.DataFrame", metadata: dict) -> "pd.DataFrame":  # type: ignore[name-defined]
        dataframe.loc[
            (
                # EMA 9 crosses below EMA 21
                (dataframe["ema9"] < dataframe["ema21"])
                & (dataframe["ema9"].shift(1) >= dataframe["ema21"].shift(1))
            ),
            "exit_long",
        ] = 1
        return dataframe


# ---------------------------------------------------------------------------
# PROTECTION_CONFIG_EXAMPLE — copy-paste ready config.json snippet
# ---------------------------------------------------------------------------

PROTECTION_CONFIG_EXAMPLE = """
Add the following to your freqtrade config.json:

{
    "protections": [
        {
            "method": "QuantGistProtection",
            "api_key": "qg_live_YOUR_KEY_HERE",
            "pause_minutes_before": 10,
            "pause_minutes_after": 5,
            "impact": "high",
            "cache_ttl_seconds": 300
        }
    ]
}

Alternatively, set QUANTGIST_API_KEY as an environment variable and omit
the "api_key" field — the plugin reads it from the environment.
"""


if __name__ == "__main__":
    print("This file is a freqtrade strategy — run it with the freqtrade CLI.")
    print(PROTECTION_CONFIG_EXAMPLE)
