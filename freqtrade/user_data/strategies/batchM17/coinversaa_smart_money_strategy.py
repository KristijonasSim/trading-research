"""
Coinversaa Smart Money Strategy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A Freqtrade strategy that uses Coinversaa API signals as an additional
data source for trade decisions. This is a **reference implementation** —
it demonstrates how to call the API inside a strategy, not a production
trading system.

Signals used:
    1. Smart money bias   — are top traders long or short on this market?
    2. Whale positions    — is whale short exposure increasing?
    3. Liquidation walls  — are there large liquidation clusters nearby?

Logic (intentionally simple):
    - Enter long when smart money bias flips to "long" and RSI < 70.
    - Skip entry when whale short notional is rising.
    - Exit when RSI crosses above 75 or smart money flips short.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Optional

import freqtrade.vendor.qtpylib.indicators as qtpylib
import talib.abstract as ta
from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy
from pandas import DataFrame

from coinversaa_client import CoinversaaClient

logger = logging.getLogger(__name__)


class CoinversaaSmartMoneyStrategy(IStrategy):
    """
    Reference strategy showing Coinversaa API integration with Freqtrade.

    Set your API key in the Freqtrade config under strategy_params:

        "strategy_params": {
            "coinversaa_api_key": "your-api-key"
        }
    """

    # ------------------------------------------------------------------
    # Strategy settings
    # ------------------------------------------------------------------

    INTERFACE_VERSION = 3

    # Minimal ROI — this is a demo, not tuned for profit
    minimal_roi = {"0": 0.05, "30": 0.025, "60": 0.01}

    stoploss = -0.03
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02

    timeframe = "5m"
    startup_candle_count = 50

    # Only process new candles to avoid spamming the API
    process_only_new_candles = True

    # ------------------------------------------------------------------
    # Coinversaa signal cache
    # ------------------------------------------------------------------
    # We cache signals so we don't call the API on every candle for
    # every pair. Cache is refreshed once per populate_indicators call.
    _signal_cache: dict = {}
    _cache_ts: float = 0
    CACHE_TTL_SECONDS = 60  # refresh signals every 60 seconds

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def __init__(self, config: dict) -> None:
        super().__init__(config)

        # Read API key from strategy_params in config, or fall back to env var
        api_key = (
            config.get("strategy_params", {}).get("coinversaa_api_key")
            or os.getenv("COINVERSAA_API_KEY", "")
        )
        if not api_key:
            logger.warning(
                "No coinversaa_api_key found in strategy_params. "
                "Coinversaa signals will be unavailable."
            )

        self.cvsa = CoinversaaClient(api_key=api_key)

    # ------------------------------------------------------------------
    # Helpers: fetch and cache Coinversaa signals
    # ------------------------------------------------------------------

    def _freqtrade_pair_to_coin(self, pair: str) -> str:
        """Convert a Freqtrade pair like 'ETH/USDC:USDC' to 'ETH'."""
        return pair.split("/")[0]

    def _get_signals(self, coin: str) -> dict:
        """
        Fetch Coinversaa signals for a coin, with simple TTL caching.

        Returns a dict with:
            smart_money_bias:  "long", "short", or "neutral"
            smart_money_score: float from -1 (max short) to +1 (max long)
            whale_short_notional: total USD notional of whale short positions
        """
        now = datetime.now(tz=timezone.utc).timestamp()

        # Return cached signals if still fresh
        if coin in self._signal_cache and (now - self._cache_ts) < self.CACHE_TTL_SECONDS:
            return self._signal_cache[coin]

        signals = {
            "smart_money_bias": "neutral",
            "smart_money_score": 0.0,
            "whale_short_notional": 0.0,
        }

        # --- Smart money bias ---
        bias_data = self.cvsa.get_smart_money_bias(coin)
        if bias_data.get("biases"):
            # Look at the two most profitable cohorts
            top_tiers = {"money_printer", "smart_money"}
            for tier in bias_data["biases"]:
                if tier.get("pnlTier") in top_tiers:
                    score = tier.get("netBias", 0)
                    if abs(score) > abs(signals["smart_money_score"]):
                        signals["smart_money_score"] = score
                        # Normalize API labels to simple "long"/"short"/"neutral"
                        # API returns: Bullish, Slightly Bullish, Neutral,
                        #              Slightly Bearish, Bearish
                        raw_label = tier.get("biasLabel", "Neutral").lower()
                        if "bullish" in raw_label:
                            signals["smart_money_bias"] = "long"
                        elif "bearish" in raw_label:
                            signals["smart_money_bias"] = "short"
                        else:
                            signals["smart_money_bias"] = "neutral"

        # --- Whale short exposure ---
        # Use cohort positions for the "whale" size tier, then filter for
        # short positions on this coin
        whale_data = self.cvsa.get_whale_positions(limit=200)
        if whale_data.get("positions"):
            signals["whale_short_notional"] = sum(
                p.get("notional", 0)
                for p in whale_data["positions"]
                if p.get("coin", "").upper() == coin.upper()
                and p.get("side") == "short"
            )

        self._signal_cache[coin] = signals
        self._cache_ts = now

        logger.info(
            "Coinversaa signals for %s: bias=%s score=%.3f whale_short=$%.0f",
            coin,
            signals["smart_money_bias"],
            signals["smart_money_score"],
            signals["whale_short_notional"],
        )

        return signals

    # ------------------------------------------------------------------
    # Indicators
    # ------------------------------------------------------------------

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Add RSI and Coinversaa signal columns to the dataframe."""

        # Standard RSI
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        # Fetch Coinversaa signals for this pair
        coin = self._freqtrade_pair_to_coin(metadata["pair"])
        signals = self._get_signals(coin)

        # Store signals as columns so they appear in the dataframe
        dataframe["cvsa_bias"] = signals["smart_money_bias"]
        dataframe["cvsa_score"] = signals["smart_money_score"]
        dataframe["cvsa_whale_short"] = signals["whale_short_notional"]

        return dataframe

    # ------------------------------------------------------------------
    # Entry (buy) logic
    # ------------------------------------------------------------------

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Enter long when:
            1. Smart money bias is "long" (top traders are positioned long)
            2. RSI is below 70 (not overbought)
            3. Whale short notional is NOT spiking (no short squeeze setup against us)
        """
        dataframe.loc[
            (
                (dataframe["cvsa_bias"] == "long")       # smart money says long
                & (dataframe["rsi"] < 70)                 # not overbought
                & (dataframe["cvsa_score"] > 0.2)         # meaningful conviction
            ),
            "enter_long",
        ] = 1

        return dataframe

    # ------------------------------------------------------------------
    # Exit (sell) logic
    # ------------------------------------------------------------------

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Exit when:
            1. RSI crosses above 75 (overbought), or
            2. Smart money flips to short bias
        """
        dataframe.loc[
            (
                (dataframe["rsi"] > 75)                   # overbought
                | (dataframe["cvsa_bias"] == "short")     # smart money flipped
            ),
            "exit_long",
        ] = 1

        return dataframe

    # ------------------------------------------------------------------
    # Optional: custom stoploss using liquidation data
    # ------------------------------------------------------------------

    def custom_stoploss(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        after_fill: bool,
        **kwargs,
    ) -> Optional[float]:
        """
        Example of using liquidation cluster data in a custom stoploss.

        If there's a large liquidation cluster just below the current price,
        tighten the stop to avoid getting caught in a cascade.

        This is purely illustrative — tune thresholds for your own strategy.
        """
        coin = self._freqtrade_pair_to_coin(pair)
        clusters = self.cvsa.get_liquidation_clusters(coin, buckets=20)

        if not clusters.get("buckets"):
            return self.stoploss  # fallback to default

        current_price = clusters.get("currentPrice", current_rate)

        # Find buckets just below the current price (within 3%)
        for bucket in clusters["buckets"]:
            bucket_mid = (bucket["priceLow"] + bucket["priceHigh"]) / 2
            distance_pct = (current_price - bucket_mid) / current_price

            # If there's a large long liquidation cluster within 3% below us,
            # tighten the stop to 2%
            if 0 < distance_pct < 0.03 and bucket.get("longNotionalAtRisk", 0) > 5_000_000:
                logger.info(
                    "Coinversaa: large liquidation cluster at $%.0f for %s, "
                    "tightening stop to -2%%",
                    bucket_mid,
                    coin,
                )
                return -0.02

        return self.stoploss
