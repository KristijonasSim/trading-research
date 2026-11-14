"""Breakout Donchian de tendencia, 1 h, spot long, con JEV como veto (spec 03).

Frontera de riesgo: freqtrade envuelve los callbacks con ``strategy_safe_wrapper``
y, si uno lanza, usa un valor por defecto que **deja pasar** la operación
(``True`` en ``confirm_trade_entry``, el stake propuesto en ``custom_stake_amount``).
Por eso esos callbacks capturan sus propias excepciones y fallan cerrados.
"""

import logging
import math
import os
from datetime import datetime
from typing import Any

import talib.abstract as ta
from pandas import DataFrame

from freqtrade.exchange import timeframe_to_prev_date
from freqtrade.persistence import Order, Trade
from freqtrade.strategy import IStrategy, stoploss_from_absolute
from jev.risk import (
    ATR_MULT,
    DAILY_LOSS_LIMIT,
    HARD_STOPLOSS,
    MAX_STAKE_FRACTION,
    RISK_PER_TRADE,
    bogota_date,
    bogota_day_start,
    compute_stake,
    daily_loss_breached,
    daily_pnl,
    equity_at_day_start,
    trailing_stop_price,
)

logger = logging.getLogger(__name__)


class DonchianTrendJEV(IStrategy):
    INTERFACE_VERSION = 3

    timeframe = "1h"
    can_short = False
    startup_candle_count = 250
    process_only_new_candles = True
    use_exit_signal = True

    EMA_LEN = 200
    DON_ENTRY = 20
    DON_EXIT = 10
    ATR_LEN = 14
    ATR_MULT = ATR_MULT
    VOL_WINDOW = 2160  # 90 días de velas de 1 h
    # En vivo Bybit entrega unas 1000 velas: exigir 2160 dejaría los cuantiles en NaN
    # y jev.state rechazaría toda señal. Solo alimentan el state de JEV, no las señales.
    VOL_MIN_PERIODS = 720
    RISK_PER_TRADE = RISK_PER_TRADE
    MAX_STAKE_FRACTION = MAX_STAKE_FRACTION
    DAILY_LOSS_LIMIT = DAILY_LOSS_LIMIT

    stoploss = HARD_STOPLOSS
    use_custom_stoploss = True
    trailing_stop = False
    minimal_roi = {"0": 100}

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self._equity_start: dict[str, float] = {}
        self._daily_alert_day: str | None = None
        self._jev_log_ready = False
        self._pending_jev_ids: dict[str, int] = {}
        # freqtrade reintenta la entrada cada iteración mientras dure la vela (ADR-002 D10).
        self._jev_seen: dict[str, tuple[datetime, bool]] = {}
        self._daily_loss_seen: dict[str, datetime] = {}

    @property
    def protections(self) -> list[dict[str, Any]]:
        return [
            {"method": "CooldownPeriod", "stop_duration_candles": 2},
            {
                "method": "StoplossGuard",
                "lookback_period_candles": 24,
                "trade_limit": 3,
                "stop_duration_candles": 12,
                "only_per_pair": False,
            },
            {
                "method": "MaxDrawdown",
                "lookback_period_candles": 720,
                "trade_limit": 1,
                "stop_duration_candles": 72,
                "max_allowed_drawdown": 0.10,
            },
        ]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=self.EMA_LEN)
        # shift(1) obligatorio: el canal no puede incluir la vela que lo rompe.
        dataframe["don_high"] = dataframe["high"].rolling(self.DON_ENTRY).max().shift(1)
        dataframe["don_low"] = dataframe["low"].rolling(self.DON_EXIT).min().shift(1)
        dataframe["atr"] = ta.ATR(dataframe, timeperiod=self.ATR_LEN)
        dataframe["atr_pct"] = dataframe["atr"] / dataframe["close"]
        dataframe["ret_24h"] = dataframe["close"] / dataframe["close"].shift(24) - 1
        vol = dataframe["atr_pct"].rolling(self.VOL_WINDOW, min_periods=self.VOL_MIN_PERIODS)
        dataframe["atr_pct_q33"] = vol.quantile(0.33).shift(1)
        dataframe["atr_pct_q66"] = vol.quantile(0.66).shift(1)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        signal = (
            (dataframe["close"] > dataframe["ema200"])
            & (dataframe["close"] > dataframe["don_high"])
            & (dataframe["volume"] > 0)
        )
        dataframe.loc[signal, ["enter_long", "enter_tag"]] = (1, "donchian_breakout")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        signal = dataframe["close"] < dataframe["don_low"]
        dataframe.loc[signal, ["exit_long", "exit_tag"]] = (1, "donchian_exit")
        return dataframe

    def custom_stoploss(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        after_fill: bool,
        **kwargs,
    ) -> float | None:
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if df.empty:
            return None
        atr = float(df["atr"].iloc[-1])
        if not math.isfinite(atr) or atr <= 0:
            return None  # Sin ATR se mantiene el stop vigente.

        entry_candle = timeframe_to_prev_date(self.timeframe, trade.open_date_utc)
        closes = df.loc[df["date"] >= entry_candle, "close"]
        highest_close = max(trade.open_rate, float(closes.max())) if len(closes) else trade.open_rate

        stop_abs = trailing_stop_price(highest_close, atr, trade.open_rate, self.ATR_MULT, self.stoploss)
        return stoploss_from_absolute(stop_abs, current_rate, is_short=False)

    def custom_stake_amount(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_stake: float,
        min_stake: float | None,
        max_stake: float,
        leverage: float,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> float:
        try:
            df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            atr = float(df["atr"].iloc[-1])
            stake = compute_stake(
                self.wallets.get_total_stake_amount(),
                current_rate,
                atr,
                min_stake=min_stake,
                max_stake=max_stake,
                risk_per_trade=self.RISK_PER_TRADE,
                max_stake_fraction=self.MAX_STAKE_FRACTION,
                atr_mult=self.ATR_MULT,
                hard_stoploss=self.stoploss,
            )
        except Exception:
            logger.exception("Sizing falló para %s: no se entra", pair)
            return 0.0
        if stake <= 0:
            logger.info("Stake 0 para %s (atr=%s, min_stake=%s): no se entra", pair, atr, min_stake)
        return stake

    def confirm_trade_entry(
        self,
        pair: str,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        current_time: datetime,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> bool:
        mode = _jev_mode()
        try:
            if self._daily_limit_hit(pair, rate, current_time, mode):
                return False
        except Exception:
            logger.exception("Control de pérdida diaria falló para %s: no se entra", pair)
            return False

        if mode == "off":
            return True
        if mode not in ("shadow", "veto"):
            logger.error("JEV_MODE desconocido %r: no se entra", mode)
            return False
        return self._jev_gate(pair, rate, mode, current_time)

    def order_filled(self, pair: str, trade: Trade, order: Order, current_time: datetime, **kwargs) -> None:
        """Enlaza la fila de ``jev_log`` con el trade cuando se llena la entrada."""
        if order.ft_order_side != trade.entry_side or order.safe_filled <= 0:
            return
        log_id = self._pending_jev_ids.pop(pair, None)
        if log_id is None:
            return
        try:
            from jev import log as jev_log

            jev_log.link_trade(log_id, trade.id)
        except Exception:
            logger.exception("No se pudo enlazar jev_log %s con el trade %s", log_id, trade.id)

    def _jev_gate(self, pair: str, rate: float, mode: str, current_time: datetime) -> bool:
        """Consulta a JEV una vez por (par, vela). Falla cerrado en ``veto``; ``shadow`` nunca bloquea."""
        shadow = mode == "shadow"
        candle = timeframe_to_prev_date(self.timeframe, current_time)
        seen = self._jev_seen.get(pair)
        if seen is not None and seen[0] == candle:
            return seen[1]
        self._jev_seen[pair] = (candle, shadow)  # Un fallo tampoco se reintenta en esta vela.
        try:
            from jev import client as jev_client
            from jev import log as jev_log

            self._ensure_jev_log(jev_log)
            df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            decision = jev_client.evaluate_pair(pair, df.iloc[-1])
            executed = bool(decision.enter) or shadow
            log_id = jev_log.insert(decision, pair, rate, mode, executed=executed)
        except Exception as exc:
            logger.exception("Fallo de JEV para %s en modo %s", pair, mode)
            self._notify(f"🛑 JEV error {pair}: {type(exc).__name__}")
            return shadow

        if executed:
            self._pending_jev_ids[pair] = log_id
        if not decision.enter:
            self._notify(
                f"🛑 JEV {decision.reason} {pair} "
                f"p_long={_fmt(decision.p_long)} conf={_fmt(decision.conf_long)} "
                f"p_risk={_fmt(decision.p_riesgo)} conf={_fmt(decision.conf_riesgo)}"
            )
        allowed = shadow or bool(decision.enter)
        self._jev_seen[pair] = (candle, allowed)
        return allowed

    def _daily_limit_hit(self, pair: str, rate: float, current_time: datetime, mode: str) -> bool:
        day_start = bogota_day_start(current_time)
        realized = [
            t.close_profit_abs or 0.0 for t in Trade.get_trades_proxy(is_open=False, close_date=day_start)
        ]
        unrealized = [
            t.calc_profit(rate if t.pair == pair else self._last_close(t.pair))
            for t in Trade.get_trades_proxy(is_open=True)
        ]
        day = bogota_date(current_time).isoformat()
        equity_start = self._day_equity(day, realized, mode)
        pnl = daily_pnl(realized, unrealized)
        if not daily_loss_breached(pnl, equity_start, self.DAILY_LOSS_LIMIT):
            return False

        logger.warning("veto_daily_loss %s: pnl=%.2f equity_inicio=%.2f", pair, pnl, equity_start)
        candle = timeframe_to_prev_date(self.timeframe, current_time)
        if self._daily_loss_seen.get(pair) != candle:
            self._daily_loss_seen[pair] = candle
            self._record_daily_loss(pair, rate, mode)
        if self._daily_alert_day != day:
            self._daily_alert_day = day
            self._notify(f"🛑 Pérdida diaria alcanzada ({pnl:.2f}): sin entradas hasta las 00:00 de Bogotá")
        return True

    def _day_equity(self, day: str, realized: list[float], mode: str) -> float:
        """Equity al inicio del día: memoria, luego SQLite, luego reconstrucción."""
        cached = self._equity_start.get(day)
        if cached is not None:
            return cached

        stored = None
        jev_log = None
        if mode != "off":
            try:
                from jev import log as jev_log

                self._ensure_jev_log(jev_log)
                stored = jev_log.get_equity_start(day)
            except Exception:
                jev_log = None
                logger.exception("No se pudo leer daily_equity; se reconstruye")

        equity = stored
        if equity is None:
            equity = equity_at_day_start(self.wallets.get_total_stake_amount(), realized)
            if jev_log is not None:
                try:
                    jev_log.set_equity_start(day, equity)
                except Exception:
                    logger.exception("No se pudo guardar daily_equity")
        self._equity_start[day] = equity
        return equity

    def _record_daily_loss(self, pair: str, rate: float, mode: str) -> None:
        if mode == "off":
            return
        try:
            from jev import log as jev_log

            self._ensure_jev_log(jev_log)
            jev_log.insert(None, pair, rate, mode, executed=False, decision_override="veto_daily_loss")
        except Exception:
            logger.exception("No se pudo registrar veto_daily_loss para %s", pair)

    def _ensure_jev_log(self, jev_log: Any) -> None:
        if not self._jev_log_ready:
            jev_log.init()
            self._jev_log_ready = True

    def _last_close(self, pair: str) -> float:
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        return float(df["close"].iloc[-1])

    def _notify(self, message: str) -> None:
        try:
            self.dp.send_msg(message)
        except Exception:
            logger.exception("No se pudo enviar el aviso de Telegram")


def _jev_mode() -> str:
    """Modo de JEV. Sin variable se asume ``veto``: nunca se opera sin filtro por omisión."""
    return os.environ.get("JEV_MODE", "veto").strip().lower()


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}"
