"""
LLM 信号策略 — 调用 user_data/llm_gateway 获取 enter/exit JSON。
确定性风险帽：最大仓位、止损、冷却；LLM 不可用时不交易。
非盈利承诺；默认需在设置中启用模型 API。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from pandas import DataFrame

from freqtrade.strategy import IStrategy, DecimalParameter, IntParameter

logger = logging.getLogger(__name__)

# Allow importing sibling llm_gateway under user_data/
import sys

_UD = Path(__file__).resolve().parents[2]
if str(_UD) not in sys.path:
    sys.path.insert(0, str(_UD))


class LLMSignalStrategy(IStrategy):
    """OpenAI-compatible LLM enter/exit with hard risk caps."""

    INTERFACE_VERSION = 3
    timeframe = "15m"
    can_short = False

    minimal_roi = {"0": 0.03, "60": 0.015, "180": 0.0}
    stoploss = -0.04
    trailing_stop = False
    process_only_new_candles = True
    startup_candle_count = 30
    use_exit_signal = True

    # Hard caps (not LLM-controlled)
    max_stake_ratio = DecimalParameter(0.05, 0.5, default=0.15, decimals=2, space="buy")
    cooldown_candles = IntParameter(1, 20, default=3, space="buy")

    def bot_start(self, **kwargs) -> None:
        self._last_call: dict[str, datetime] = {}
        self._last_signal: dict[str, dict] = {}

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["sma_20"] = dataframe["close"].rolling(20).mean()
        dataframe["rsi"] = self._rsi(dataframe["close"], 14)
        return dataframe

    @staticmethod
    def _rsi(series, period: int = 14):
        delta = series.diff()
        up = delta.clip(lower=0).rolling(period).mean()
        down = (-delta.clip(upper=0)).rolling(period).mean()
        rs = up / down.replace(0, 1e-9)
        return 100 - (100 / (1 + rs))

    def _ask_llm(self, pair: str, row) -> dict:
        try:
            from llm_gateway.client import chat_json, load_llm_config

            cfg = load_llm_config()
            if not cfg.get("enabled") or not cfg.get("base_url"):
                return {"enter_long": False, "exit_long": False, "reason": "llm_disabled"}
            system = (
                "You are a conservative crypto trading assistant. "
                "Reply ONLY JSON: "
                '{"enter_long":bool,"exit_long":bool,"confidence":0-1,"reason":"short"} '
                "Prefer no-trade when unsure. Never invent prices."
            )
            def _f(key: str):
                try:
                    v = row[key]
                    if v != v:  # NaN
                        return None
                    return float(v)
                except Exception:
                    return None

            user = json.dumps(
                {
                    "pair": pair,
                    "close": _f("close"),
                    "sma_20": _f("sma_20"),
                    "rsi": _f("rsi"),
                    "volume": _f("volume"),
                },
                ensure_ascii=False,
            )
            out = chat_json(system, user, cfg=cfg, temperature=0.1)
            return {
                "enter_long": bool(out.get("enter_long")),
                "exit_long": bool(out.get("exit_long")),
                "confidence": float(out.get("confidence") or 0),
                "reason": str(out.get("reason") or "")[:120],
            }
        except Exception as exc:
            logger.warning("LLMSignalStrategy LLM call failed: %s", exc)
            return {"enter_long": False, "exit_long": False, "reason": f"error:{exc}"}

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["enter_long"] = 0
        if dataframe.empty:
            return dataframe
        pair = metadata.get("pair", "")
        # Only evaluate last closed candle to limit API cost
        idx = dataframe.index[-1]
        row = dataframe.loc[idx]
        now = datetime.now(timezone.utc)
        last = self._last_call.get(pair)
        # cooldown by wall clock ~ timeframe * cooldown_candles (approx)
        if last and (now - last).total_seconds() < int(self.cooldown_candles.value) * 60:
            sig = self._last_signal.get(pair) or {}
        else:
            sig = self._ask_llm(pair, row)
            self._last_call[pair] = now
            self._last_signal[pair] = sig
        conf = float(sig.get("confidence") or 0)
        if sig.get("enter_long") and conf >= 0.55 and row["volume"] > 0:
            dataframe.at[idx, "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0
        if dataframe.empty:
            return dataframe
        pair = metadata.get("pair", "")
        idx = dataframe.index[-1]
        sig = self._last_signal.get(pair) or {}
        if sig.get("exit_long"):
            dataframe.at[idx, "exit_long"] = 1
        return dataframe

    def custom_stake_amount(self, pair, current_time, current_rate, proposed_stake, min_stake, max_stake, leverage, entry_tag, side, **kwargs):
        # Cap stake by max_stake_ratio of max_stake
        cap = float(max_stake) * float(self.max_stake_ratio.value)
        stake = min(proposed_stake, cap)
        if min_stake and stake < min_stake:
            return None  # skip entry rather than undersize
        return stake
