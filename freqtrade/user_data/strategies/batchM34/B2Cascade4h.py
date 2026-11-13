"""B2 cascade-reversion Candidate — forward paper trading only.

Frozen from CRYPTO-EXP-013 (A-019b): buy a severe 24-hour drawdown during
high downside dispersion and a completed-daily uptrend, but only when BTC also
fell over the same 24 hours.  This is an unleveraged long-only strategy on the
nine OKX USDT perpetuals.  It is not approved for real-money trading.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from pandas import DataFrame

from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy, informative


def append_jsonl_once(path: Path, record: dict) -> bool:
    """Append a compact JSON record unless its event_id is already persisted."""
    event_id = str(record["event_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line and json.loads(line).get("event_id") == event_id:
                return False
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, separators=(",", ":")) + "\n")
    return True


def calculate_b2_indicators(dataframe: DataFrame) -> DataFrame:
    """Calculate the exact W42/PW180/6-bar indicators used by the harness."""
    frame = dataframe.copy()
    returns = frame["close"].pct_change()
    downside = np.sqrt(np.minimum(returns, 0.0).pow(2).rolling(42).mean())
    frame["dsd_pct"] = downside.rolling(180).rank(pct=True)
    frame["mom_24h"] = frame["close"].pct_change(6)
    return frame


def calculate_daily_gate_indicators(dataframe: DataFrame) -> DataFrame:
    """Calculate and timestamp the daily gate exactly like harness gate_shift=6.

    Freqtrade normally exposes a completed 1d candle on the 4h candle opening at
    20:00 because that base candle closes simultaneously at midnight.  The frozen
    research harness instead shifts the forward-filled gate by six full 4h rows,
    making it available on the 00:00 row.  Moving the informative timestamp four
    hours forward offsets merge_informative_pair's 1d-minus-4h convention and
    preserves that deliberately conservative alignment.
    """
    frame = dataframe.copy()
    close = frame["close"]
    frame["sma200"] = close.rolling(200).mean()
    frame["ema20"] = close.ewm(span=20).mean()
    frame["ema50"] = close.ewm(span=50).mean()
    if "date" in frame:
        frame["date"] = pd.to_datetime(frame["date"], utc=True) + pd.Timedelta(hours=4)
    return frame


class B2Cascade4h(IStrategy):
    INTERFACE_VERSION = 3
    can_short = False
    timeframe = "4h"
    startup_candle_count = 250
    process_only_new_candles = True

    minimal_roi = {"0": 100.0}
    # Required by the interface; effectively disabled to preserve harness parity.
    stoploss = -0.99
    trailing_stop = False
    use_exit_signal = True
    exit_profit_only = False

    DSD_ENTRY = 0.80
    DSD_EXIT = 0.50
    MOMENTUM_ENTRY = -0.0385
    # Research HOLD=6 checks six completed post-entry candles, then fills at the
    # following open: seven 4h open-to-open intervals in the actual ledger.
    MAX_HOLD = timedelta(hours=28)
    BTC_PAIR = "BTC/USDT:USDT"
    forward_event_log = Path(__file__).resolve().parents[1] / "logs" / "b2_4h_forward_events.jsonl"

    @property
    def protections(self) -> list[dict]:
        # The frozen harness advances from exit-open k+1 to signal candle k+2.
        # Freqtrade creates the lock at the exit open and rounds its end to the
        # next candle boundary. One candle therefore skips the signal formed
        # during that exit candle and unlocks for k+2's signal.
        return [{"method": "CooldownPeriod", "stop_duration_candles": 1}]

    @informative("1d")
    def populate_indicators_1d(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return calculate_daily_gate_indicators(dataframe)

    def informative_pairs(self) -> list[tuple[str, str]]:
        return [(self.BTC_PAIR, self.timeframe)]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = calculate_b2_indicators(dataframe)
        if metadata.get("pair") == self.BTC_PAIR:
            dataframe["btc_mom_24h"] = dataframe["mom_24h"]
            return dataframe
        if not self.dp:
            dataframe["btc_mom_24h"] = np.nan
            return dataframe
        btc = self.dp.get_pair_dataframe(pair=self.BTC_PAIR, timeframe=self.timeframe)
        btc = calculate_b2_indicators(btc)[["date", "mom_24h"]].rename(
            columns={"mom_24h": "btc_mom_24h"}
        )
        return dataframe.merge(btc, on="date", how="left")

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (dataframe["dsd_pct"] >= self.DSD_ENTRY)
            & (dataframe["mom_24h"] <= self.MOMENTUM_ENTRY)
            & (dataframe["btc_mom_24h"] < 0.0)
            & (dataframe["close_1d"] > dataframe["sma200_1d"])
            & (dataframe["ema20_1d"] > dataframe["ema50_1d"])
            & (dataframe["volume"] > 0.0),
            ["enter_long", "enter_tag"],
        ] = (1, "b2_cascade")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[dataframe["dsd_pct"] < self.DSD_EXIT, ["exit_long", "exit_tag"]] = (
            1,
            "dispersion_recovered",
        )
        return dataframe

    def custom_exit(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs,
    ) -> Optional[str]:
        if current_time - trade.open_date_utc >= self.MAX_HOLD:
            return "time_stop_28h"
        return None

    def confirm_trade_entry(
        self,
        pair: str,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        current_time: datetime,
        entry_tag: Optional[str],
        side: str,
        **kwargs,
    ) -> bool:
        """Persist the decision-time quote without altering order acceptance."""
        dataframe, _ = self.dp.get_analyzed_dataframe(pair=pair, timeframe=self.timeframe)
        if dataframe is not None and not dataframe.empty:
            row = dataframe.iloc[-1]
            candle_time = pd.Timestamp(row["date"])
            if candle_time.tzinfo is None:
                candle_time = candle_time.tz_localize("UTC")
            close_time = candle_time + pd.Timedelta(hours=4)
            current = pd.Timestamp(current_time)
            if current.tzinfo is None:
                current = current.tz_localize("UTC")
            event_id = f"{pair}|{candle_time.isoformat()}|entry"
            append_jsonl_once(
                self.forward_event_log,
                {
                    "event_id": event_id,
                    "kind": "entry_decision",
                    "pair": pair,
                    "signal_candle": candle_time.isoformat(),
                    "decision_time": current.isoformat(),
                    "decision_latency_seconds": max(0.0, (current - close_time).total_seconds()),
                    "signal_close": float(row["close"]),
                    "proposed_rate": float(rate),
                    "amount": float(amount),
                    "order_type": order_type,
                    "entry_tag": entry_tag,
                    "dsd_pct": float(row["dsd_pct"]),
                    "mom_24h": float(row["mom_24h"]),
                    "btc_mom_24h": float(row["btc_mom_24h"]),
                },
            )
        return True

    def confirm_trade_exit(
        self,
        pair: str,
        trade: Trade,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        exit_reason: str,
        current_time: datetime,
        **kwargs,
    ) -> bool:
        """Persist the exit decision without altering order acceptance."""
        dataframe, _ = self.dp.get_analyzed_dataframe(pair=pair, timeframe=self.timeframe)
        if dataframe is not None and not dataframe.empty:
            row = dataframe.iloc[-1]
            candle_time = pd.Timestamp(row["date"])
            if candle_time.tzinfo is None:
                candle_time = candle_time.tz_localize("UTC")
            current = pd.Timestamp(current_time)
            if current.tzinfo is None:
                current = current.tz_localize("UTC")
            append_jsonl_once(
                self.forward_event_log,
                {
                    "event_id": f"{pair}|{trade.id}|exit",
                    "kind": "exit_decision",
                    "trade_id": int(trade.id),
                    "pair": pair,
                    "signal_candle": candle_time.isoformat(),
                    "decision_time": current.isoformat(),
                    "signal_close": float(row["close"]),
                    "proposed_rate": float(rate),
                    "amount": float(amount),
                    "order_type": order_type,
                    "exit_reason": exit_reason,
                    "dsd_pct": float(row["dsd_pct"]),
                },
            )
        return True
