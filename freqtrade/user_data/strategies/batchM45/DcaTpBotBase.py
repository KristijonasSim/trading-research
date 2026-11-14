# freqtrade/user_data/strategies/DcaTpBotBase.py
import sys
import traceback
from pathlib import Path
import requests
import time as _time
import numpy as np

USER_DATA_DIR = Path(__file__).resolve().parents[1]
if str(USER_DATA_DIR) not in sys.path:
    sys.path.insert(0, str(USER_DATA_DIR))

from freqtrade.strategy.interface import IStrategy
from freqtrade.strategy import merge_informative_pair
from freqtrade.strategy import informative
from freqtrade.persistence import Trade, Order
from pandas import DataFrame, Timestamp
import pandas as pd
from typing import Any, Optional
import talib.abstract as ta
from datetime import datetime
from event_logger import record_event
import logging

RED = "\033[31m"
GREEN = "\033[32m"
BLUE = "\033[34m"
YELLOW = "\033[33m"
RESET = "\033[0m"
logger = logging.getLogger(__name__)

# 支持的 HTF 周期集合（用来做合法性校验）
_ALLOWED_HTF = {"4h", "12h", "1d"}
_direction_cache = {
    "ts": 0,
    "data": None,
}

RISK_API_URL = "http://127.0.0.1:9000/api/risk/direction"


class DcaTpBotBase(IStrategy):
    """多空共用基类：所有逻辑都在这里，用 self._is_short 判方向"""

    # DCA uses limit orders so simulated fees use the exchange maker tier.
    strategy_order_types = {
        "entry": "limit",
        "exit": "limit",
    }

    timeframe = '30m'
    # ⚠️ can_short 必须由子类覆盖，不要在这里写 True
    can_short = False

    use_exit_signal = True
    trailing_stop = False
    position_adjustment_enable = True
    use_custom_stoploss = False

    # ============================================================
    # ★ 方向判定：所有 long/short 分支的唯一入口
    # ============================================================
    @property
    def _is_short(self) -> bool:
        return bool(self.can_short)

    @property
    def _side_str(self) -> str:
        return "short" if self._is_short else "long"

    @property
    def _entry_order_side(self) -> str:
        # 开仓成交时 freqtrade 报的 side
        return "sell" if self._is_short else "buy"

    @property
    def _exit_order_side(self) -> str:
        return "buy" if self._is_short else "sell"

    # ============================================================
    # HTF 数据（4h / 12h / 1d）★ 动态：只加载 UI 选中的周期
    # ============================================================

    def _get_htf_timeframe(self) -> str:
        """
        从 runtime config 读 UI 选的 HTF 周期。
        没配置或非法值 → 兜底 '4h'
        """
        try:
            cfg = self.get_runtime_config() or {}
            htf_cfg = self._cfg(cfg, "htf_trend_filter", default={}) or {}
            tf = str(htf_cfg.get("timeframe", "4h")).lower()
            if tf in _ALLOWED_HTF:
                return tf
        except Exception as e:
            logger.warning(f"[HTF] 读取 timeframe 失败: {e}")
        return "4h"

    def _is_htf_effective(self) -> bool:
        """
        HTF 过滤是否真正生效：
          - enable = True
          - 且至少一个 protect_* 开关打开

        用于决定是否加载 / 计算 HTF 数据（性能优化）。
        """
        try:
            cfg = self.get_runtime_config() or {}
            htf_cfg = self._cfg(cfg, "htf_trend_filter", default={}) or {}

            if not bool(htf_cfg.get("enable", False)):
                return False

            return any([
                bool(htf_cfg.get("protect_entry", False)),
                bool(htf_cfg.get("protect_dca", False)),
                bool(htf_cfg.get("protect_grid", False)),
                bool(htf_cfg.get("protect_rebuy", False)),
                bool(htf_cfg.get("protect_trend", False)),
            ])
        except Exception as e:
            logger.warning(f"[HTF] _is_htf_effective 检查失败: {e}")
            return False

    def informative_pairs(self):
        """
        ★ 始终声明 HTF 周期（不再用 _is_htf_effective 做开关）。
        这样热加载时，从「关」→「开」也能生效。
        """
        pairs = self.dp.current_whitelist()
        htf_tf = self._get_htf_timeframe()
        # logger.info(f"[HTF] informative_pairs → {len(pairs)} pairs × {htf_tf}")
        return [(pair, htf_tf) for pair in pairs]

    def _calc_htf_ema(self, dataframe: DataFrame) -> DataFrame:
        """
        计算 HTF 的 EMA 列。
        ★ 注意：这里不再直接挂到主 df 上，而是返回一个独立的 DataFrame，
          由 merge_informative_pair 负责加周期后缀并合并。
        """
        cfg = self.get_runtime_config()
        ema_cfg = self._cfg(cfg, "indicator", "ema", default={}) or {}

        ema_fast = self._cfg_int(ema_cfg, "fast", 9)
        ema_mid = self._cfg_int(ema_cfg, "mid", 21)
        ema_slow = self._cfg_int(ema_cfg, "slow", 99)

        dataframe = dataframe.copy()
        dataframe['ema_fast'] = ta.EMA(dataframe['close'], timeperiod=ema_fast)
        dataframe['ema_mid'] = ta.EMA(dataframe['close'], timeperiod=ema_mid)
        dataframe['ema_slow'] = ta.EMA(dataframe['close'], timeperiod=ema_slow)
        return dataframe

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop_loss_logged = set()
        self._pair_limit_logged = set()
        self._htf_block_logged = set()
        self._pump_block_logged = set()

    # ============================================================
    # bot_start：日志统一，方向标签用 self._side_str
    # ============================================================
    def bot_start(self, **kwargs) -> None:
        ft_cfg = self.config or {}

        dry_run_wallet       = ft_cfg.get("dry_run_wallet", 0)
        stake_amount         = ft_cfg.get("stake_amount", 0)
        max_open_trades      = ft_cfg.get("max_open_trades", 0)
        tradable_balance_ratio = ft_cfg.get("tradable_balance_ratio", 0)
        leverage             = ft_cfg.get("leverage", 1)

        exchange_cfg   = ft_cfg.get("exchange", {}) or {}
        pair_whitelist = exchange_cfg.get("pair_whitelist", []) or []
        pair_blacklist = exchange_cfg.get("pair_blacklist", []) or []

        # ★ 失衡控制：按方向读不同的 key
        if self._is_short:
            imbalance_enable = ft_cfg.get("imbalance_short_enable", False)
            imbalance_count  = ft_cfg.get("imbalance_short_count", 2)
            dir_cn = "空头"
        else:
            imbalance_enable = ft_cfg.get("imbalance_long_enable", False)
            imbalance_count  = ft_cfg.get("imbalance_long_count", 2)
            dir_cn = "多头"

        logger.info(
            "\n"
            f"==================== {dir_cn}配置概览 ====================\n"
            f"初始资金          : {dry_run_wallet} USDT\n"
            f"开仓金额          : {stake_amount} USDT\n"
            f"最大持仓          : {max_open_trades}\n"
            f"资金利用率        : {tradable_balance_ratio}\n"
            f"持仓杠杆          : {leverage}x\n"
            f"K线时间周期       : {self.timeframe}\n"
            f"白名单            : {', '.join(pair_whitelist) if pair_whitelist else '(空)'}\n"
            f"黑名单            : {', '.join(pair_blacklist) if pair_blacklist else '(空)'}\n"
            f"------------------------------------------------------\n"
            f"持仓差上限        : {'开启' if imbalance_enable else '关闭'}, 上限={imbalance_count}\n"
            f"======================================================"
        )

        # 运行时策略配置详情
        try:
            cfg = self.get_runtime_config() or {}
        except Exception as e:
            logger.error(f"读取运行时策略配置失败: {e}")
            return

        amount_mode = str(cfg.get("amount_mode", "percent")).lower()

        def _fmt(v, digits=4):
            if isinstance(v, bool):
                return "开" if v else "关"
            if isinstance(v, float):
                return f"{v:.{digits}f}"
            if v is None:
                return "(空)"
            return str(v)

        def _section(title):
            logger.info(f"\n-------------------- {title} --------------------")

        _section("金额模式")
        logger.info(
            f"amount_mode       : {amount_mode} "
            f"({'百分比' if amount_mode == 'percent' else '固定金额 USDT'})"
        )

        _section("指标配置")
        ind = cfg.get("indicator", {}) or {}
        macd = ind.get("macd", {}) or {}
        kdj  = ind.get("kdj",  {}) or {}
        ema  = ind.get("ema",  {}) or {}
        rsi  = ind.get("rsi",  {}) or {}
        bb   = ind.get("bb",   {}) or {}
        logger.info(
            f"MACD              : fast={_fmt(macd.get('fast'))}, "
            f"slow={_fmt(macd.get('slow'))}, signal={_fmt(macd.get('signal'))}\n"
            f"KDJ               : fastk={_fmt(kdj.get('fastk'))}, "
            f"slowk={_fmt(kdj.get('slowk'))}, slowd={_fmt(kdj.get('slowd'))}\n"
            f"EMA               : fast={_fmt(ema.get('fast'))}, "
            f"mid={_fmt(ema.get('mid'))}, slow={_fmt(ema.get('slow'))}\n"
            f"RSI.period        : {_fmt(rsi.get('period'))}\n"
            f"BB                : period={_fmt(bb.get('period'))}, std={_fmt(bb.get('std'), 2)}"
        )

        _section("ROI止盈规则")
        tp_cfg = cfg.get("tp", {}) or {}
        roi_levels = tp_cfg.get("roi_levels", []) or []
        if roi_levels:
            for i, lv in enumerate(roi_levels, start=1):
                logger.info(
                    f"  [{i}] minutes={_fmt(lv.get('minutes'))}, "
                    f"roi={_fmt(lv.get('roi'), 2)}%"
                )
        else:
            logger.info("  (空)")

        _section("开仓信号")
        entry = cfg.get("entry", {}) or {}
        e_rsi  = entry.get("rsi", {})  or {}
        e_macd = entry.get("macd", {}) or {}
        e_bb   = entry.get("bb", {})   or {}
        e_pump = entry.get("pump_protect", {}) or {}
        logger.info(
            f"condition         : {entry.get('condition', 'and')}\n"
            f"RSI  enable={_fmt(e_rsi.get('enable'))}, value={_fmt(e_rsi.get('value'))}\n"
            f"MACD enable={_fmt(e_macd.get('enable'))}\n"
            f"BB   enable={_fmt(e_bb.get('enable'))}\n"
            f"Pump 保护 enable={_fmt(e_pump.get('enable'))}"
        )

        _section("TP止盈")
        logger.info(
            f"rebuy_enable         : {_fmt(tp_cfg.get('rebuy_enable'))}\n"
            f"reduce_amount        : {_fmt(tp_cfg.get('reduce_amount'), 2)}\n"
            f"reduce_percent       : {_fmt(tp_cfg.get('reduce_percent'))}\n"
            f"target_wallet_amount : {_fmt(tp_cfg.get('target_wallet_amount'), 2)}\n"
            f"target_wallet_percent: {_fmt(tp_cfg.get('target_wallet_percent'), 2)}"
        )

        _section("止损配置")
        sl = cfg.get("sl", {}) or {}
        ts = sl.get("time_stop", {}) or {}
        logger.info(
            f"enable            : {_fmt(sl.get('enable'))}\n"
            f"stoploss          : {_fmt(sl.get('stoploss'))}%\n"
            f"时间止损 enable   : {_fmt(ts.get('enable'))}\n"
            f"未成交时长        : {_fmt(ts.get('hours'), 1)}h\n"
            f"收益阈值模式      : {ts.get('mode', 'percent')}\n"
            f"收益阈值          : {_fmt(ts.get('profit_threshold'), 2)}"
        )

        _section("DCA配置")
        dca = cfg.get("dca", {}) or {}
        logger.info(
            f"enable            : {_fmt(dca.get('enable'))}\n"
            f"amount_mode       : {dca.get('amount_mode', 'auto')}\n"
            f"condition         : {dca.get('condition', 'or')}\n"
            f"max_count         : {_fmt(dca.get('max_count'))}\n"
            f"cooldown_minutes  : {_fmt(dca.get('cooldown_minutes'))}\n"
            f"price_offset      : {_fmt(dca.get('price_offset'), 2)}\n"
            f"price_multiplier  : {_fmt(dca.get('price_multiplier'), 2)}\n"
            f"base_amount       : {_fmt(dca.get('base_amount'), 2)}\n"
            f"base_percent      : {_fmt(dca.get('base_percent'), 2)}\n"
            f"amount_multiplier : {_fmt(dca.get('amount_multiplier'), 2)}"
        )
        dca_levels = dca.get("levels", []) or []
        if dca_levels:
            for i, lv in enumerate(dca_levels, start=1):
                logger.info(
                    f"  level[{i}] amount={_fmt(lv.get('amount'), 2)}, "
                    f"percent={_fmt(lv.get('percent'), 2)}, "
                    f"rsi_limit={_fmt(lv.get('rsi_limit'))}, "
                    f"j_limit={_fmt(lv.get('j_limit'))}"
                )
        else:
            logger.info("  levels: (空)")

        _section("DCA止盈")
        loss_tp = cfg.get("loss_tp", {}) or {}
        logger.info(
            f"enable               : {_fmt(loss_tp.get('enable'))}\n"
            f"dca_tp_profit        : {_fmt(loss_tp.get('dca_tp_profit'), 2)}%\n"
            f"is_partial(部分减仓) : {_fmt(loss_tp.get('is_partial'))} \n"
            f"target_wallet_amount : {_fmt(loss_tp.get('target_wallet_amount'), 2)}\n"
            f"target_wallet_percent: {_fmt(loss_tp.get('target_wallet_percent'), 2)}"
        )

        _section("趋势加仓")
        trend = cfg.get("trend_add", {}) or {}
        kdj_reduce = trend.get("kdj_reduce", {}) or {}
        logger.info(
            f"enable            : {_fmt(trend.get('enable'))}\n"
            f"amount_amount     : {_fmt(trend.get('amount_amount'), 2)}\n"
            f"amount_percent    : {_fmt(trend.get('amount_percent'), 2)}\n"
            f"condition         : {trend.get('condition', 'and')}\n"
            f"macd_enable       : {_fmt(trend.get('macd_enable'))}\n"
            f"kdj_enable        : {_fmt(trend.get('kdj_enable'))}\n"
            f"ema_enable        : {_fmt(trend.get('ema_enable'))}\n"
            f"KDJ减仓 enable    : {_fmt(kdj_reduce.get('enable'))}\n"
            f"KDJ减仓 reduce_amount : {_fmt(kdj_reduce.get('reduce_amount'), 2)}\n"
            f"KDJ减仓 reduce_percent: {_fmt(kdj_reduce.get('reduce_percent'))}"
        )

        _section("网格配置")
        grid = cfg.get("grid", {}) or {}
        logger.info(
            f"enable            : {_fmt(grid.get('enable'))}\n"
            f"max_count         : {_fmt(grid.get('max_count'))}\n"
            f"cooldown_minutes  : {_fmt(grid.get('cooldown_minutes'))}\n"
            f"grid_lower        : {_fmt(grid.get('grid_lower'), 2)}%\n"
            f"grid_upper        : {_fmt(grid.get('grid_upper'), 2)}%\n"
            f"buy_amount        : {_fmt(grid.get('buy_amount'), 2)}\n"
            f"buy_percent       : {_fmt(grid.get('buy_percent'), 2)}\n"
            f"sell_amount       : {_fmt(grid.get('sell_amount'), 2)}\n"
            f"sell_percent      : {_fmt(grid.get('sell_percent'), 2)}\n"
            f"order_scale       : {_fmt(grid.get('order_scale'), 2)}"
        )

        _section("单交易对持仓限制")
        pm = cfg.get("pair_max_position", {}) or {}
        logger.info(
            f"enable            : {_fmt(pm.get('enable'))}\n"
            f"percent           : {_fmt(pm.get('percent'), 2)}%"
        )

        logger.info("\n==================== 策略配置详情结束 ====================\n")

        _section("HTF 趋势过滤")
        htf = cfg.get("htf_trend_filter", {}) or {}
        ema_cfg_print = ind.get("ema", {}) or {}
        logger.info(
            f"enable            : {_fmt(htf.get('enable'))}\n"
            f"HTF 周期          : {htf.get('timeframe', '4h')}\n"
            f"EMA 参数          : {_fmt(ema_cfg_print.get('fast'))} / "
            f"{_fmt(ema_cfg_print.get('mid'))} / "
            f"{_fmt(ema_cfg_print.get('slow'))}（复用指标配置）\n"
            f"保护开仓          : {_fmt(htf.get('protect_entry'))}\n"
            f"保护 DCA          : {_fmt(htf.get('protect_dca'))}\n"
            f"保护网格          : {_fmt(htf.get('protect_grid'))}\n"
            f"保护浮盈回补      : {_fmt(htf.get('protect_rebuy'))}\n"
            f"保护趋势加仓      : {_fmt(htf.get('protect_trend'))}"
        )

    def _get_bot_id(self):
        """从 freqtrade config 读 bot_id（优先顶层，其次 custom_params）"""
        try:
            v = (self.config or {}).get("bot_id")
            if v is not None:
                return int(v)
        except Exception:
            pass
        try:
            custom = (self.config or {}).get("custom_params", {}) or {}
            v = custom.get("bot_id")
            if v is not None:
                return int(v)
        except Exception:
            pass
        return None

    # ============================================================
    # 配置读取
    # ============================================================
    def get_runtime_config(self):
        """DCA 类型读取：优先 custom_params[side]，其次 custom_params.longConfig / shortConfig"""
        custom = (self.config or {}).get("custom_params", {}) or {}
        side_key = self._side_str  # "long" / "short"

        # 1) 优先 custom_params[side]（config_service 走 inject_mode="side" 时写入）
        if side_key in custom and custom[side_key]:
            return custom[side_key]

        # 2) 兼容：custom_params.longConfig / custom_params.shortConfig
        cfg_key = f"{side_key}Config"  # "longConfig" / "shortConfig"
        if cfg_key in custom and custom[cfg_key]:
            return custom[cfg_key]

        # 3) 兜底 ConfigManager 的 side 键
        try:
            from core.config_manager import ConfigManager
            return ConfigManager.get(side_key) or {}
        except Exception:
            return {}

    def _cfg(self, cfg: dict, *keys, default=None):
        cur = cfg
        for key in keys:
            if not isinstance(cur, dict):
                return default
            if key not in cur:
                return default
            cur = cur[key]
        return default if cur is None else cur

    def _roi_target(self, cfg: dict, elapsed: float):
        levels = self._cfg(cfg, "tp", "roi_levels", default=[]) or []
        parsed = []
        for level in levels:
            if not isinstance(level, dict):
                continue
            try:
                minutes = self._cfg_int(level, "minutes", 0)
                roi = float(level.get("roi", 0))
            except Exception:
                continue
            parsed.append((minutes, roi / 100))
        parsed.sort(key=lambda x: x[0], reverse=True)
        for minutes, roi in parsed:
            if elapsed >= minutes:
                return roi, minutes
        return None, 0

    def leverage(self, pair, **kwargs):
        try:
            ft_cfg = self.config or {}
            ft_leverage = ft_cfg.get("leverage", None)
            if ft_leverage is not None:
                try:
                    return float(ft_leverage)
                except (TypeError, ValueError):
                    pass

            cfg = self.get_runtime_config()
            top_level = self._cfg(cfg, "leverage", default=None)
            if top_level is not None:
                try:
                    return float(top_level)
                except (TypeError, ValueError):
                    pass

            nested = self._cfg(cfg, "strategy", "leverage", default=None)
            if nested is not None:
                try:
                    return float(nested)
                except (TypeError, ValueError):
                    pass

            return 10.0
        except Exception:
            return 10.0

    def _available_stake(self):
        try:
            free = self.wallets.get_free("USDT")
            if free is None:
                return 0.0
            return float(free)
        except Exception:
            return 0.0

    def _get_direction_state(self, ttl: int = 5):
        now = _time.time()
        if _direction_cache["data"] and now - _direction_cache["ts"] < ttl:
            return _direction_cache["data"]
        try:
            r = requests.get(RISK_API_URL, timeout=2)
            if r.status_code == 200:
                data = r.json()
                _direction_cache["data"] = data
                _direction_cache["ts"] = now
                return data
        except Exception as e:
            logger.warning(f"获取多空失衡状态失败: {e}")
        return None

    # ============================================================
    # 时间止损：realized + unrealized 统一算法（多空通用）
    # ============================================================
    def _time_stop_triggered(self, trade, current_time, current_rate) -> bool:
        cfg = self.get_runtime_config()
        sl_cfg = self._cfg(cfg, "sl", default={}) or {}
        ts_cfg = sl_cfg.get("time_stop", {}) or {}

        if not bool(ts_cfg.get("enable", False)):
            return False

        try:
            hours = float(ts_cfg.get("hours", 24.0) or 24.0)
        except Exception:
            hours = 24.0
        if hours <= 0:
            return False

        try:
            threshold = float(ts_cfg.get("profit_threshold", -5.0) or -5.0)
        except Exception:
            threshold = -5.0

        mode = str(ts_cfg.get("mode", "percent")).lower()
        if mode not in ("percent", "amount"):
            mode = "percent"

        last_fill = self._get_int(trade, 'last_fill_time', 0)
        if last_fill <= 0:
            try:
                base_ts = int(trade.open_date_utc.timestamp())
            except Exception:
                base_ts = 0
            if base_ts <= 0:
                return False
            last_fill = base_ts

        now_ts = int(current_time.timestamp())
        elapsed_hours = (now_ts - last_fill) / 3600.0
        if elapsed_hours < hours:
            return False

        try:
            realized = float(getattr(trade, "realized_profit", 0) or 0)
        except Exception:
            realized = 0.0

        try:
            rate = float(current_rate or 0.0)
        except Exception:
            rate = 0.0

        if rate > 0:
            try:
                unrealized = float(trade.calc_profit(rate))
            except Exception:
                unrealized = 0.0
        else:
            unrealized = 0.0

        total_profit = realized + unrealized

        if mode == "percent":
            try:
                stake = float(trade.stake_amount or 0.0)
            except Exception:
                stake = 0.0
            if stake <= 0:
                return False
            profit_ratio = total_profit / stake
            triggered = profit_ratio < (threshold / 100.0)
            profit_display = f"{profit_ratio * 100:.2f}%"
            threshold_display = f"{threshold}%"
        else:
            triggered = total_profit < threshold
            profit_display = f"{total_profit:.2f} USDT"
            threshold_display = f"{threshold} USDT"

        if triggered:
            if trade.id not in self._stop_loss_logged:
                self._stop_loss_logged.add(trade.id)
                logger.info(
                    f"[STRATEGY] [SL] [{trade.pair}] {RED}触发时间止损{RESET} "
                    f"未成交时长={elapsed_hours:.2f}h (阈值={hours}h), "
                    f"累计收益={profit_display} (阈值<{threshold_display}), "
                    f"当前价={rate:.4f} {RESET}"
                )
                self._record_chart_marker(
                    event_type="time_stop",
                    pair=trade.pair,
                    trade_id=trade.id,
                    side=self._side_str,        # ★
                    price=rate,
                    amount=abs(float(trade.amount or 0)),
                    current_time=current_time,
                    message=f"时间止损 {elapsed_hours:.1f}h",
                    candle_time=self._index_candle_key(current_time)
                )
            return True
        return False

    # ============================================================
    # 图表标记
    # ============================================================
    def _record_chart_marker(self, *, event_type, pair, trade_id, side,
                             price, amount, current_time, message, candle_time=None):
        if self.config.get('runmode') == 'backtest':
            return
        if current_time is None or price is None:
            return
        try:
            price = float(price)
            amount = float(amount)
        except Exception:
            return

        record_event(
            strategy=self.__class__.__name__,
            pair=pair,
            trade_id=trade_id,
            event_type=event_type,
            side=side,
            price=price,
            amount=amount,
            message=message,
            current_time=current_time,
            candle_time=candle_time,
            bot_id=self._get_bot_id(),
        )

    # ============================================================
    # order_filled：方向相关全部走 _entry_order_side / _exit_order_side
    # ============================================================
    def order_filled(self, pair, trade, order, current_time, **kwargs):
        entry_price = float(order.average or trade.open_rate)

        reason = str(
            getattr(order, "ft_order_reason", None)
            or getattr(order, "ft_order_tag", None)
            or ""
        ).lower()

        candle_ts = self._index_candle_key(current_time)

        try:
            self._set(trade, 'last_fill_time', self._safe_int(current_time.timestamp()))
        except Exception as e:
            logger.warning(f"[{pair}] 记录 last_fill_time 失败: {e}")

        side_text = self._side_str  # ★ 统一方向文本
        record_base_marker = not self.__class__.__name__.startswith("GridBot")
        is_manual_entry = reason.startswith("force_entry") or reason.startswith("forceenter")
        is_manual_exit = reason.startswith("force_exit") or reason.startswith("forceexit")

        if record_base_marker and order.ft_order_side == self._entry_order_side:
            # ---- 开仓 / 加仓 方向成交 ----
            if is_manual_entry:
                successful_entries = int(getattr(trade, "nr_of_successful_entries", 1) or 1)
                is_existing_trade = (
                    self._get_bool(trade, "initialized", False)
                    or successful_entries > 1
                )
                self._record_chart_marker(
                    event_type="manual_add" if is_existing_trade else "manual_entry",
                    pair=pair, trade_id=trade.id,
                    side=side_text, price=entry_price, amount=order.amount,
                    current_time=current_time,
                    message="手动加仓" if is_existing_trade else "手动开仓",
                    candle_time=candle_ts
                )
            elif reason.startswith("trend_add"):
                self._record_chart_marker(
                    event_type="trend_add", pair=pair, trade_id=trade.id,
                    side=side_text, price=entry_price, amount=order.amount,
                    current_time=current_time, message="趋势加仓",
                    candle_time=candle_ts
                )
            elif reason.startswith("grid_add"):
                self._record_chart_marker(
                    event_type="grid_add", pair=pair, trade_id=trade.id,
                    side=side_text, price=entry_price, amount=order.amount,
                    current_time=current_time, message="网格加仓",
                    candle_time=candle_ts
                )
            elif reason.startswith("dca"):
                self._record_chart_marker(
                    event_type="dca", pair=pair, trade_id=trade.id,
                    side=side_text, price=entry_price, amount=order.amount,
                    current_time=current_time, message="DCA加仓",
                    candle_time=candle_ts
                )

        elif record_base_marker and order.ft_order_side == self._exit_order_side:
            # ---- 减仓 / 止盈 方向成交 ----
            if is_manual_exit:
                trade_amount = float(getattr(trade, "amount", 0) or 0)
                is_full_exit = trade_amount > 0 and float(order.amount or 0) >= trade_amount * 0.99
                self._record_chart_marker(
                    event_type="manual_exit" if is_full_exit else "manual_reduce",
                    pair=pair, trade_id=trade.id,
                    side=side_text, price=entry_price, amount=order.amount,
                    current_time=current_time,
                    message="手动平仓" if is_full_exit else "手动减仓",
                    candle_time=candle_ts
                )
            elif reason == "kdj_reduce_by_trend_added":
                self._record_chart_marker(
                    event_type="kdj_reduce", pair=pair, trade_id=trade.id,
                    side=side_text, price=entry_price, amount=order.amount,
                    current_time=current_time, message="KDJ减仓",
                    candle_time=candle_ts
                )
            elif reason.startswith("tp_afterDCA"):
                self._record_chart_marker(
                    event_type="tp", pair=pair, trade_id=trade.id,
                    side=side_text, price=entry_price, amount=order.amount,
                    current_time=current_time, message="DCA止盈",
                    candle_time=candle_ts
                )
            elif reason.startswith("tp_"):
                self._record_chart_marker(
                    event_type="tp", pair=pair, trade_id=trade.id,
                    side=side_text, price=entry_price, amount=order.amount,
                    current_time=current_time, message="普通止盈",
                    candle_time=candle_ts
                )
            elif reason.startswith("grid_sell"):
                self._record_chart_marker(
                    event_type="grid_sell", pair=pair, trade_id=trade.id,
                    side=side_text, price=entry_price, amount=order.amount,
                    current_time=current_time, message="网格减仓",
                    candle_time=candle_ts
                )

        # =========================
        # 初始化（一次）
        # =========================
        if self._get_bool(trade, "initialized", False):
            return

        cfg = self.get_runtime_config()
        grid_cfg = self._cfg(cfg, "grid", default={})

        upper_pct = self._cfg_float(grid_cfg, "init_upper",
                                    self._cfg_float(grid_cfg, "grid_upper", 2.0))
        lower_pct = self._cfg_float(grid_cfg, "init_lower",
                                    self._cfg_float(grid_cfg, "grid_lower", -2.0))

        flags = {
            'dca_count': 0,
            'tp_count': 0,
            'dca_done': False,
            'last_dca_candle': None,
            'last_dca_time': None,
            'need_rebuy': False,
            'last_tp_time': None,
            'trend_level': 0,
            'last_trend_candle': None,
            'reset_needed': False,
            'grid_anchor_price': 0.0,
            'grid_w': 0,
        }
        for k, v in flags.items():
            self._set(trade, k, v)

        entry_price = float(getattr(order, "average", None) or trade.open_rate or 0)

        # ★ 做多：上沿=止盈、下沿=加仓
        # ★ 做空：上沿=加仓、下沿=止盈
        # 这里 grid_upper / grid_lower 只是记两个价位，具体谁加谁减在 grid_single 里按方向分
        self._set(trade, "grid_upper", entry_price * (1 + upper_pct / 100))
        self._set(trade, "grid_lower", entry_price * (1 + lower_pct / 100))

        self._set(trade, "grid_count", 0)
        self._set(trade, "grid_added_total_usdt", 0.0)
        self._set(trade, "grid_added_total_qty", 0.0)
        self._set(trade, "grid_reduced_total_usdt", 0.0)
        self._set(trade, "initialized", True)

    # ============================================================
    # 序列化辅助
    # ============================================================
    def _serial(self, v):
        if v is None:
            return None
        if isinstance(v, (pd.Timestamp, Timestamp, datetime)):
            return int(pd.Timestamp(v).timestamp())
        try:
            import numpy as np
            if isinstance(v, (np.floating, np.integer)):
                return float(v)
            if isinstance(v, np.bool_):
                return bool(v)
        except ImportError:
            pass
        if isinstance(v, bool):
            return bool(v)
        if isinstance(v, (int, float)):
            return v
        if isinstance(v, str):
            s = v.strip()
            if s.lower() in ("", "null", "none", "nan", "na", "n/a"):
                return None
            try:
                f = float(s)
                if f.is_integer():
                    return int(f)
                return f
            except ValueError:
                return s
        return str(v)

    # ============================================================
    # 指标
    # ============================================================
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        cfg = self.get_runtime_config()
        indicator_cfg = self._cfg(cfg, "indicator", default={}) or {}

        rsi_cfg  = self._cfg(indicator_cfg, "rsi",  default={}) or {}
        bb_cfg   = self._cfg(indicator_cfg, "bb",   default={}) or {}
        macd_cfg = self._cfg(indicator_cfg, "macd", default={}) or {}
        kdj_cfg  = self._cfg(indicator_cfg, "kdj",  default={}) or {}
        ema_cfg  = self._cfg(indicator_cfg, "ema",  default={}) or {}

        rsi_period = self._cfg_int(rsi_cfg, "period", 14)
        bb_period  = self._cfg_int(bb_cfg, "period", 20)
        bb_std     = float(bb_cfg.get("std", 2))

        upper, mid, lower = ta.BBANDS(
            dataframe['close'],
            timeperiod=bb_period, nbdevup=bb_std, nbdevdn=bb_std
        )
        dataframe['bb_upperband'] = upper
        dataframe['bb_midband']   = mid
        dataframe['bb_lowerband'] = lower
        dataframe['rsi'] = ta.RSI(dataframe['close'], timeperiod=rsi_period)

        vol_sma20 = ta.SMA(dataframe['volume'], timeperiod=20)
        dataframe['vol_sma20'] = vol_sma20
        dataframe['vol_ratio'] = dataframe['volume'] / vol_sma20
        dataframe['ret_3'] = (dataframe['close'] / dataframe['close'].shift(3) - 1.0)

        df_tf = dataframe.copy()
        if not df_tf.empty:
            macd, macdsignal, macdhist = ta.MACD(
                df_tf['close'],
                fastperiod=self._cfg_int(macd_cfg, "fast", 12),
                slowperiod=self._cfg_int(macd_cfg, "slow", 26),
                signalperiod=self._cfg_int(macd_cfg, "signal", 9)
            )

            k, d = ta.STOCH(
                df_tf['high'], df_tf['low'], df_tf['close'],
                fastk_period=self._cfg_int(kdj_cfg, "fastk", 5),
                slowk_period=self._cfg_int(kdj_cfg, "slowk", 3),
                slowd_period=self._cfg_int(kdj_cfg, "slowd", 3)
            )
            j = 3 * k - 2 * d

            ema_fast = self._cfg_int(ema_cfg, "fast", 9)
            ema_mid  = self._cfg_int(ema_cfg, "mid", 21)
            ema_slow = self._cfg_int(ema_cfg, "slow", 99)

            series_map = {
                'macd_tf':    macd,
                'macdsig_tf': macdsignal,
                'macdhist_tf': macdhist,
                'k_tf': k, 'd_tf': d, 'j_tf': j,
                f'ema{ema_fast}_tf': ta.EMA(df_tf['close'], timeperiod=ema_fast),
                f'ema{ema_mid}_tf':  ta.EMA(df_tf['close'], timeperiod=ema_mid),
                f'ema{ema_slow}_tf': ta.EMA(df_tf['close'], timeperiod=ema_slow),
            }
            for name, series in series_map.items():
                dataframe[name] = pd.Series(series, index=df_tf.index)

        htf_tf = self._get_htf_timeframe()
        try:
            informative_df = self.dp.get_pair_dataframe(
                pair=metadata['pair'],
                timeframe=htf_tf
            )
            if informative_df is not None and not informative_df.empty:
                informative_df = self._calc_htf_ema(informative_df)
                dataframe = merge_informative_pair(
                    dataframe,
                    informative_df,
                    self.timeframe,
                    htf_tf,
                    ffill=True
                )
            else:
                logger.warning(
                    f"[{metadata['pair']}] HTF {htf_tf} 数据为空，跳过合并"
                )
        except Exception as e:
            logger.error(f"[{metadata['pair']}] HTF {htf_tf} 合并失败: {e}")

        return dataframe

    # ============================================================
    # 入场信号：核心方向分支
    # ============================================================
    def populate_entry_trend(self, dataframe, metadata):
        cfg = self.get_runtime_config()
        entry_cfg = self._cfg(cfg, "entry", default={}) or {}

        rsi_cfg  = self._cfg(entry_cfg, "rsi",  default={}) or {}
        bb_cfg   = self._cfg(entry_cfg, "bb",   default={}) or {}
        macd_cfg = self._cfg(entry_cfg, "macd", default={}) or {}

        rsi_enable  = bool(rsi_cfg.get("enable", True))
        bb_enable   = bool(bb_cfg.get("enable", True))
        macd_enable = bool(macd_cfg.get("enable", True))

        # ★ 默认阈值按方向分：多 35 / 空 65
        default_rsi = 65 if self._is_short else 35
        rsi_value = float(rsi_cfg.get("value", default_rsi) or default_rsi)

        is_short = self._is_short
        cond_map = {}

        if bb_enable:
            cond_map["BB"] = (dataframe['close'] > dataframe['bb_upperband']) if is_short \
                             else (dataframe['close'] < dataframe['bb_lowerband'])
        if rsi_enable:
            cond_map["RSI"] = (dataframe['rsi'] > rsi_value) if is_short \
                              else (dataframe['rsi'] < rsi_value)
        if macd_enable:
            cond_map["MACD"] = (dataframe['macd_tf'] < dataframe['macdsig_tf']) if is_short \
                               else (dataframe['macd_tf'] > dataframe['macdsig_tf'])

        condition_mode = str(entry_cfg.get("condition", "and")).lower()

        if cond_map:
            if condition_mode == "or":
                cond = None
                for c in cond_map.values():
                    cond = c if cond is None else (cond | c)
            else:
                cond = None
                for c in cond_map.values():
                    cond = c if cond is None else (cond & c)
        else:
            cond = pd.Series(False, index=dataframe.index)

        names = list(cond_map.keys())
        tag_matrix = np.column_stack([
            c.values.astype(bool) for c in cond_map.values()
        ]) if cond_map else np.zeros((len(dataframe), 0), dtype=bool)

        enter_tags = [
            "_".join([names[i] for i, v in enumerate(row) if v]) or "NONE"
            for row in tag_matrix
        ]
        tag_prefix = "AND" if condition_mode == "and" else "OR"
        enter_tags = [
            f"{tag_prefix}_{t}" if t != "NONE" else "NONE" for t in enter_tags
        ]
        enter_tags = pd.Series(enter_tags, index=dataframe.index)

        # ★ 写 enter_long / enter_short
        col = "enter_short" if is_short else "enter_long"
        dataframe[col] = cond.astype(int)
        dataframe.loc[cond, "enter_tag"] = enter_tags[cond]

        return dataframe

    def confirm_trade_entry(self, pair, order_type, amount, rate, time_in_force,
                            current_time, entry_tag, side, **kwargs):

        entry_tag_str = str(entry_tag or "").lower()
        is_manual = (
            entry_tag_str.startswith("force_entry")
            or entry_tag_str in ("manual", "manual_entry")
        )

        if not is_manual:
            # Pump 保护
            try:
                cfg = self.get_runtime_config()
                entry_cfg = self._cfg(cfg, "entry", default={}) or {}
                pump_cfg = entry_cfg.get("pump_protect", {}) or {}
                if bool(pump_cfg.get("enable", False)):
                    df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
                    if df is not None and not df.empty:
                        last = df.iloc[-1]
                        if self._pump_protect_blocks(pair, last):
                            return False
            except Exception as e:
                logger.warning(f"[{pair}] Pump 保护检测失败: {e}")

            # HTF 趋势
            try:
                cfg = self.get_runtime_config()
                htf_cfg = self._cfg(cfg, "htf_trend_filter", default={}) or {}
                if bool(htf_cfg.get("enable", False)) and bool(htf_cfg.get("protect_entry", False)):
                    df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
                    if df is not None and not df.empty:
                        last = df.iloc[-1]
                        if self._htf_trend_blocks(trade=None, last=last, htf_cfg=htf_cfg):
                            return False
            except Exception as e:
                logger.warning(f"[{pair}] HTF 趋势过滤检测失败: {e}")

            # ★ 失衡闸门：按方向读 key
            if self._is_short:
                imbalance_enable = self.config.get("imbalance_short_enable", False)
                imbalance_count  = self.config.get("imbalance_short_count", 2)
                dir_cn = "空"
            else:
                imbalance_enable = self.config.get("imbalance_long_enable", False)
                imbalance_count  = self.config.get("imbalance_long_count", 2)
                dir_cn = "多"

            if imbalance_enable:
                state = self._get_direction_state()
                if state:
                    long_count  = int(state.get("long_count", 0) or 0)
                    short_count = int(state.get("short_count", 0) or 0)
                    diff = (short_count - long_count) if self._is_short \
                           else (long_count - short_count)

                    if diff >= imbalance_count:
                        logger.info(
                            f"[{pair}] {YELLOW}持仓差超限，暂停开{dir_cn}{RESET} "
                            f"(多={long_count}, 空={short_count}, "
                            f"差={diff}, 上限={imbalance_count})"
                        )
                        return False

        try:
            lev = float(self.leverage(pair) or 1.0)
        except Exception:
            lev = 1.0
        try:
            notional = float(amount) * float(rate)
        except Exception:
            notional = 0.0
        try:
            stake_amount = notional / lev
        except Exception:
            stake_amount = 0.0

        rsi_value = None
        try:
            df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            if df is not None and not df.empty:
                last = df.iloc[-1]
                rsi_value = float(last.get("rsi")) if last.get("rsi") is not None else None
        except Exception as e:
            logger.warning(f"[{pair}] confirm_trade_entry 读取指标失败: {e}")

        logger.info(
            f"[STRATEGY] [SIGNAL] [{pair}] {GREEN} 开仓信号触发 {RESET}"
            f"entry_tag={entry_tag} 当前价={rate:.4f} "
            f"保证金={stake_amount:.4f} USDT RSI={rsi_value} is_manual={is_manual}"
        )

        if not is_manual:
            candle_ts = self._index_candle_key(current_time)
            if candle_ts is not None:
                self._record_chart_marker(
                    event_type="signal", pair=pair, trade_id=0,
                    side=self._side_str, price=rate, amount=stake_amount,
                    current_time=current_time,
                    message=f"入场信号 {entry_tag}",
                    candle_time=candle_ts
                )

        return True

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # ★ 多空分别写不同列，互不干扰
        if self._is_short:
            dataframe['exit_short'] = 0
        else:
            dataframe['exit_long'] = 0
        return dataframe

    # ============================================================
    # 通用读写辅助
    # ============================================================
    def _clean_val(self, v):
        if v is None:
            return None
        if isinstance(v, str):
            s = v.strip()
            if not s or s.lower() in ("null", "none", "nan", "na", "n/a"):
                return None
            # ★ 新增：自动尝试解析 JSON 字符串
            if (s.startswith("[") and s.endswith("]")) or (s.startswith("{") and s.endswith("}")):
                try:
                    return json.loads(s)
                except Exception:
                    pass
            return s
        try:
            import numpy as np
            if isinstance(v, (np.floating, np.integer)):
                return float(v)
            if isinstance(v, np.bool_):
                return bool(v)
        except ImportError:
            pass
        if isinstance(v, (int, float, bool)):
            return v
        return str(v)

    def _get(self, trade, key, default=None):
        try:
            raw = trade.get_custom_data(key)
        except Exception:
            logger.error(f"_get 失败 key={key}\n{traceback.format_exc()}")
            raw = None
        val = self._clean_val(raw)
        return default if val is None else val

    def _get_float(self, trade, key, default=0.0):
        v = self._get(trade, key, None)
        if v is None:
            return default
        if isinstance(v, bool):
            return 1.0 if v else 0.0
        try:
            f = float(v)
            if not (float('-inf') < f < float('inf')) or pd.isna(f):
                return default
            return f
        except Exception:
            return default

    def _get_int(self, trade, key, default=0):
        value = self._get(trade, key, default)
        if value is None:
            return default
        try:
            f = float(value)
            if pd.isna(f) or not (float('-inf') < f < float('inf')):
                return default
            return int(f)
        except (TypeError, ValueError):
            return default

    def _cfg_int(self, cfg, key, default):
        v = cfg.get(key, default)
        if isinstance(v, bool):
            return int(v)
        try:
            return int(float(v))
        except Exception:
            return default

    def _cfg_float(self, cfg, key, default):
        v = cfg.get(key, default)
        if isinstance(v, bool):
            return 1.0 if v else 0.0
        try:
            f = float(v)
            if not (float('-inf') < f < float('inf')) or pd.isna(f):
                return default
            return f
        except Exception:
            return default

    def _safe_int(self, value, default=0):
        if value is None:
            return default
        try:
            f = float(value)
            if pd.isna(f) or not (float('-inf') < f < float('inf')):
                return default
            return int(f)
        except (TypeError, ValueError):
            return default

    def _index_candle_key(self, value):
        if value is None:
            return None
        try:
            ts = pd.Timestamp(value)
        except Exception:
            try:
                ts = pd.Timestamp(float(value), unit='s')
            except Exception:
                return None
        if ts.tzinfo is None:
            ts = ts.tz_localize('UTC')
        else:
            ts = ts.tz_convert('UTC')
        try:
            ts = ts.floor('min')
        except Exception:
            pass
        try:
            return int(ts.timestamp())
        except Exception:
            return None

    def _get_bool(self, trade, key, default=False):
        v = self._get(trade, key, None)
        if v is None:
            return default
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, float)):
            return bool(v)
        s = str(v).strip().lower()
        if s in ("1", "true", "t", "yes", "y"):
            return True
        if s in ("0", "false", "f", "no", "n"):
            return False
        try:
            return bool(float(s))
        except Exception:
            return default

    def _set(self, trade, key, value):
        value = self._serial(value)
        old = self._get(trade, key, None)
        if isinstance(value, float) and isinstance(old, float):
            if abs(value - old) < 1e-8:
                return
        if old == value:
            return
        if key in ('grid_anchor_price', 'grid_upper', 'grid_lower'):
            try:
                value = float(value)
            except (TypeError, ValueError):
                logger.error(f"_set 价格转换失败 key={key} value={value!r}")
                return
        try:
            trade.set_custom_data(key, value)
        except Exception:
            logger.error(
                f"_set 失败 key={key} value={value!r} type={type(value).__name__}\n"
                f"{traceback.format_exc()}"
            )

    def _get_candle_ts(self, obj):
        candle_key = None
        if isinstance(obj, pd.DataFrame):
            if 'date' in obj.columns:
                candle_key = self._index_candle_key(obj['date'].iloc[-1])
            if candle_key in (None, 0):
                candle_key = self._index_candle_key(obj.index[-1])
        elif isinstance(obj, pd.Series):
            if 'date' in obj.index:
                candle_key = self._index_candle_key(obj.get('date'))
            if candle_key in (None, 0):
                candle_key = self._index_candle_key(obj.name)
        else:
            return None
        if candle_key in (None, 0):
            return None
        return candle_key

    def _collateral_total(self) -> float:
        try:
            return float(self.wallets.get_total('USDT'))
        except Exception:
            return 0.0

    def _pair_position_exceeded(self, trade, current_rate=None) -> bool:
        cfg = self.get_runtime_config()
        pm_cfg = self._cfg(cfg, "pair_max_position", default={}) or {}
        if not bool(pm_cfg.get("enable", False)):
            return False
        try:
            limit_percent = float(pm_cfg.get("percent", 30) or 30)
        except Exception:
            limit_percent = 30.0
        if limit_percent <= 0:
            return False

        collateral = self._collateral_total()
        if collateral <= 0:
            return False

        try:
            qty = abs(float(trade.amount or 0.0))
        except Exception:
            qty = 0.0

        if current_rate and float(current_rate) > 0:
            eval_price = float(current_rate)
        else:
            try:
                eval_price = float(trade.open_rate or 0.0)
            except Exception:
                eval_price = 0.0

        try:
            lev = float(self.leverage(trade.pair) or 1.0)
        except Exception:
            lev = 1.0
        if lev <= 0:
            lev = 1.0

        margin = (qty * eval_price) / lev if eval_price > 0 else 0.0
        used_percent = margin / collateral * 100.0

        if used_percent >= limit_percent:
            if trade.id not in self._pair_limit_logged:
                self._pair_limit_logged.add(trade.id)
                logger.info(
                    f"[{trade.pair}] {YELLOW}单交易对持仓超限 "
                    f"保证金={margin:.2f}, 总资金={collateral:.2f}, "
                    f"占比={used_percent:.2f}% >= 上限={limit_percent:.2f}%{RESET}"
                )
            return True
        self._pair_limit_logged.discard(trade.id)
        return False

    def _htf_trend_blocks(self, trade, last, htf_cfg=None) -> bool:
        if htf_cfg is None:
            cfg = self.get_runtime_config()
            htf_cfg = self._cfg(cfg, "htf_trend_filter", default={}) or {}

        if not bool(htf_cfg.get("enable", False)):
            return False

        htf_tf = str(htf_cfg.get("timeframe", "4h")).lower()
        if htf_tf not in ("4h", "12h", "1d"):
            htf_tf = "4h"

        try:
            ema_f = float(last.get(f'ema_fast_{htf_tf}'))
            ema_m = float(last.get(f'ema_mid_{htf_tf}'))
            ema_s = float(last.get(f'ema_slow_{htf_tf}'))
        except Exception:
            return False

        if pd.isna(ema_f) or pd.isna(ema_m) or pd.isna(ema_s):
            return False

        # ★ 方向判定：多空相反
        if self._is_short:
            adverse = (ema_f > ema_m) and (ema_m > ema_s)
            trend_text = "多头排列"
        else:
            adverse = (ema_f < ema_m) and (ema_m < ema_s)
            trend_text = "空头排列"

        if adverse:
            pair_name = getattr(trade, "pair", None) or "(entry)"
            key = (pair_name, htf_tf)
            if key not in self._htf_block_logged:
                self._htf_block_logged.add(key)
                logger.info(
                    f"[{pair_name}] {YELLOW} [HTF 过滤] {htf_tf} {trend_text} "
                    f"fast={ema_f:.4f}, mid={ema_m:.4f}, slow={ema_s:.4f}，暂停买入 {RESET}"
                )
            return True

        pair_name = getattr(trade, "pair", None) or "(entry)"
        self._htf_block_logged.discard((pair_name, htf_tf))
        return False

    def _pump_protect_blocks(self, pair, last) -> bool:
        try:
            ret_3 = float(last.get('ret_3'))
            vol_ratio = float(last.get('vol_ratio'))
            rsi = float(last.get('rsi'))
        except Exception:
            return False
        if pd.isna(ret_3) or pd.isna(vol_ratio) or pd.isna(rsi):
            return False

        if self._is_short:
            # 空头：防暴跌后追空 → 3 根累计跌幅 ≥10% + 放量 + RSI 超卖
            triggered = (ret_3 <= -0.10) and (vol_ratio >= 3.0) and (rsi <= 25.0)
            desc = (
                f"3根累计跌幅={ret_3 * 100:.2f}%, "
                f"量比={vol_ratio:.2f}, RSI={rsi:.2f}"
            )
        else:
            # 多头：防暴涨后追多 → 3 根累计涨幅 ≥10% + 放量 + RSI 超买
            triggered = (ret_3 >= 0.10) and (vol_ratio >= 3.0) and (rsi >= 75.0)
            desc = (
                f"3根累计涨幅={ret_3 * 100:.2f}%, "
                f"量比={vol_ratio:.2f}, RSI={rsi:.2f}"
            )

        if not triggered:
            self._pump_block_logged.discard(pair)
            return False
        if pair not in self._pump_block_logged:
            self._pump_block_logged.add(pair)
            logger.info(
                f"[{pair}] {YELLOW} [Pump 保护] {desc}，暂停开仓 {RESET}"
            )
        return True

    def _amount_mode(self):
        try:
            cfg = self.get_runtime_config()
            mode = str(cfg.get("amount_mode", "percent")).lower()
            if mode not in ("percent", "amount"):
                return "percent"
            return mode
        except Exception:
            return "percent"

    def _qty_from_usdt(self, usdt, price, lev=None):
        if lev and lev > 0:
            return usdt * lev / price
        return usdt / price

    def _record_add_usdt(self, trade, key, usdt):
        prev = self._get_float(trade, key, 0.0)
        try:
            add = float(usdt)
            if pd.isna(add) or not (float('-inf') < add < float('inf')):
                add = 0.0
        except Exception:
            add = 0.0
        self._set(trade, key, prev + add)

    def _record_add_qty(self, trade, key, qty):
        prev = self._get_float(trade, key, 0.0)
        try:
            add = float(qty)
            if pd.isna(add) or not (float('-inf') < add < float('inf')):
                add = 0.0
        except Exception:
            add = 0.0
        self._set(trade, key, prev + add)

    # ============================================================
    # 趋势加仓：方向分支
    # ============================================================
    def trend_add(self, trade, last, margin, collateral, current_time, current_profit, candle=None):
        cfg = self.get_runtime_config()
        trend_cfg = self._cfg(cfg, "trend_add", default={}) or {}

        trend_enable = bool(trend_cfg.get("enable", True))
        kdj_reduce_cfg = trend_cfg.get("kdj_reduce", {}) or {}
        kdj_reduce_enable = bool(kdj_reduce_cfg.get("enable", True))

        indicator_cfg = self._cfg(cfg, "indicator", default={}) or {}
        ema_cfg = self._cfg(indicator_cfg, "ema", default={}) or {}
        condition_mode = trend_cfg.get("condition", "and")

        if candle in (None, 0):
            candle = self._get_candle_ts(last)
            if candle in (None, 0):
                logger.warning(f"[{trade.pair}] trend_add: candle 无效")
                return None

        last_trend = self._get_int(trade, 'last_trend_candle', 0)
        if candle == last_trend:
            return None
        if not trend_enable:
            return None

        level = self._get_int(trade, 'trend_level', 0)
        reset_needed = self._get_bool(trade, 'reset_needed', False)
        ema_fast = self._cfg_int(ema_cfg, "fast", 9)
        ema_mid  = self._cfg_int(ema_cfg, "mid", 21)
        ema_slow = self._cfg_int(ema_cfg, "slow", 99)
        amount_mode = self._amount_mode()

        try:
            amount_pct = float(trend_cfg.get("amount_percent", 0.5)) / 100
        except Exception:
            amount_pct = 0.005
        try:
            amount_amount = float(trend_cfg.get("amount_amount", 10.0))
        except Exception:
            amount_amount = 10.0

        is_short = self._is_short
        trend_conditions = []

        if bool(trend_cfg.get("macd_enable", True)):
            if is_short:
                trend_conditions.append(last.get('macd_tf', 0) < last.get('macdsig_tf', 0))
            else:
                trend_conditions.append(last.get('macd_tf', 0) > last.get('macdsig_tf', 0))

        if bool(trend_cfg.get("kdj_enable", True)):
            if is_short:
                trend_conditions.append(last.get('k_tf', 0) < last.get('d_tf', 0))
            else:
                trend_conditions.append(last.get('k_tf', 0) > last.get('d_tf', 0))

        if bool(trend_cfg.get("ema_enable", True)):
            if is_short:
                trend_conditions.append(
                    last.get(f'ema{ema_fast}_tf', 0)
                    < last.get(f'ema{ema_mid}_tf', 0)
                    < last.get(f'ema{ema_slow}_tf', 0)
                )
            else:
                trend_conditions.append(
                    last.get(f'ema{ema_fast}_tf', 0)
                    > last.get(f'ema{ema_mid}_tf', 0)
                    > last.get(f'ema{ema_slow}_tf', 0)
                )

        if not trend_conditions:
            is_trend_ok = False
        elif condition_mode == "or":
            is_trend_ok = any(trend_conditions)
        else:
            is_trend_ok = all(trend_conditions)

        price = last.get('close', None)

        def _add_trend_total_usdt(x):
            self._record_add_usdt(trade, 'trend_total_added_usdt', x)

        if level == 0 and not reset_needed and price is not None and is_trend_ok:
            self._set(trade, 'kdj_reduced', False)
            if amount_mode == "amount":
                amt = min(amount_amount, self._available_stake() * 0.8)
            else:
                amt = min(collateral * amount_pct, self._available_stake() * 0.8)

            _add_trend_total_usdt(abs(amt))
            self._set(trade, 'trend_level', level + 1)
            self._set(trade, 'last_trend_candle', candle)

            avg_price = float(trade.open_rate)
            old_qty = abs(float(trade.amount))
            lev = float(self.leverage(trade.pair))
            add_qty = self._qty_from_usdt(amt, price, lev)

            new_avg = avg_price
            if old_qty + add_qty > 0:
                new_avg = (old_qty * avg_price + add_qty * price) / (old_qty + add_qty)

            dir_cn = "空头" if is_short else "多头"
            if amount_mode == "amount":
                logger.info(
                    f"[{trade.pair}] {GREEN}[{dir_cn}趋势加仓 {amt:.2f} USDT]{RESET}, "
                    f"{YELLOW}保证金={margin:.2f}{RESET}, 当前价={price:.4f}, "
                    f"加仓={abs(amt):.4f} USDT, 新均价={new_avg:.4f}"
                )
            else:
                logger.info(
                    f"[{trade.pair}] {GREEN}[{dir_cn}趋势加仓 {amount_pct * 100:.1f}%]{RESET}, "
                    f"{YELLOW}保证金={margin:.2f}{RESET}, 当前价={price:.4f}, "
                    f"加仓={abs(amt):.4f} USDT, 新均价={new_avg:.4f}"
                )

            tag = 'trend_add20_bear' if is_short else 'trend_add20_bull'
            return float(amt), tag

        # KDJ 减仓
        if trend_enable and level > 0 and kdj_reduce_enable:
            kdj_reduced = self._get_bool(trade, 'kdj_reduced', False)

            # ★ 多空反向
            if is_short:
                kdj_trigger = last.get('k_tf', 0) > last.get('d_tf', 0)
            else:
                kdj_trigger = last.get('k_tf', 0) < last.get('d_tf', 0)

            if not kdj_reduced and kdj_trigger:
                if amount_mode == "amount":
                    try:
                        reduce_amount = float(kdj_reduce_cfg.get("reduce_amount", 10.0) or 10.0)
                    except Exception:
                        reduce_amount = 10.0
                    sell_usdt = min(reduce_amount, margin)
                    reduce_text = f"{sell_usdt:.2f} USDT"
                else:
                    reduce_percent = float(kdj_reduce_cfg.get("reduce_percent", 50))
                    sell_usdt = min(collateral * (reduce_percent / 100), margin)
                    reduce_text = f"{reduce_percent:.1f}%"

                amt = -float(sell_usdt)
                self._set(trade, 'trend_level', 0)
                self._set(trade, 'kdj_reduced', True)

                logger.info(
                    f"[{trade.pair}] {RED}[KDJ 减仓 {reduce_text}]{RESET}, "
                    f"{YELLOW}保证金={margin:.2f}{RESET}, 当前价={last.get('close'):.4f}, "
                    f"减仓={abs(amt):.4f} USDT"
                )
                return float(amt), 'kdj_reduce_by_trend_added'

    # ============================================================
    # DCA：方向分支
    # ============================================================
    def dca_add(self, trade, df, last, current_time, current_rate):
        cfg = self.get_runtime_config()
        dca_cfg = self._cfg(cfg, "dca", default={}) or {}
        if not bool(dca_cfg.get("enable", True)):
            return None
        if self._pair_position_exceeded(trade, current_rate):
            return None

        candle_key = self._get_candle_ts(df)
        if candle_key is None:
            return None
        candle_ts = pd.Timestamp(candle_key, unit='s').tz_localize(None).floor('min')

        last_rsi = df['rsi'].iat[-1] if 'rsi' in df.columns else None
        last_j   = df['j_tf'].iat[-1] if 'j_tf' in df.columns else None

        u = self._get_int(trade, 'dca_count', 0)
        levels = dca_cfg.get("levels") or []
        level_cfg = levels[min(u, len(levels) - 1)] if levels else {}
        max_dca = self._cfg_int(dca_cfg, "max_count", 7)
        cooldown_minutes = self._cfg_int(dca_cfg, "cooldown_minutes", 60)

        last_dca = self._get_int(trade, 'last_dca_candle', 0)
        last_dca_ts = Timestamp(self._safe_int(last_dca), unit='s') if last_dca else None
        if last_dca_ts is None or last_dca_ts != candle_ts:
            self._set(trade, 'dca_done', False)
        dca_done = self._get_bool(trade, 'dca_done', False)

        within_dca_cooldown = False
        last_dca_time = self._get_int(trade, 'last_dca_time', 0)
        if last_dca_time:
            try:
                last_dca_dt = datetime.fromtimestamp(self._safe_int(last_dca_time))
                if (current_time - last_dca_dt).total_seconds() < 60 * cooldown_minutes:
                    within_dca_cooldown = True
            except Exception:
                pass

        if u >= max_dca:
            return None

        avg_entry = float(trade.open_rate)

        base_offset = float(dca_cfg.get("price_offset", 1.0))
        price_multiplier = float(dca_cfg.get("price_multiplier", 1.0))
        effective_percent = base_offset * (price_multiplier ** u)

        # ★ 阈值方向
        if self._is_short:
            threshold = avg_entry * (1 + effective_percent / 100)
        else:
            threshold = avg_entry * (1 - effective_percent / 100)

        # ★ 默认 RSI/J 阈值方向
        if self._is_short:
            default_rsi_limit = 80
            default_j_limit = 100
        else:
            default_rsi_limit = 20
            default_j_limit = 0

        try:
            rsi_limit = float(level_cfg.get("rsi_limit", default_rsi_limit) or default_rsi_limit)
        except Exception:
            rsi_limit = float(default_rsi_limit)
        try:
            j_limit = float(level_cfg.get("j_limit", default_j_limit) or default_j_limit)
        except Exception:
            j_limit = float(default_j_limit)

        cond_mode = str(dca_cfg.get("condition", "or")).lower()

        # ★ 条件方向
        if self._is_short:
            cond_j   = (last_j   is not None and last_j   > j_limit)
            cond_rsi = (last_rsi is not None and last_rsi > rsi_limit)
            label_op = ">"
        else:
            cond_j   = (last_j   is not None and last_j   < j_limit)
            cond_rsi = (last_rsi is not None and last_rsi < rsi_limit)
            label_op = "<"

        if cond_mode == "rsi":
            triggered_cond = cond_rsi
            triggered_label = f"RSI{label_op}{rsi_limit:g}"
        elif cond_mode == "j":
            triggered_cond = cond_j
            triggered_label = f"J{label_op}{j_limit:g}"
        elif cond_mode == "and":
            triggered_cond = cond_j and cond_rsi
            triggered_label = f"J{label_op}{j_limit:g} & RSI{label_op}{rsi_limit:g}"
        else:
            triggered_cond = cond_j or cond_rsi
            triggered_label = f"J{label_op}{j_limit:g} 或 RSI{label_op}{rsi_limit:g}"

        # ★ 优先用实时价；实时价拿不到时回退到 K 线收盘价
        try:
            trigger_price = float(current_rate) if current_rate is not None else None
        except Exception:
            trigger_price = None

        if trigger_price is None or trigger_price <= 0:
            try:
                trigger_price = float(last.get('close')) if last.get('close') is not None else None
            except Exception:
                trigger_price = None

        if within_dca_cooldown or dca_done:
            return None

        # ★ 价格触发方向
        if trigger_price is None:
            return None
        price_hit = (trigger_price >= threshold) if self._is_short else (trigger_price <= threshold)

        if not (triggered_cond and price_hit):
            return None

        available = self._available_stake()
        if available <= 0:
            return None

        try:
            margin = float(trade.stake_amount)
        except Exception:
            margin = 0.0

        dca_mode = str(dca_cfg.get("amount_mode", "auto")).lower()
        global_mode = self._amount_mode()
        collateral = self._collateral_total()

        if dca_mode == "auto":
            amount_multiplier = float(dca_cfg.get("amount_multiplier", 1.0) or 1.0)
            if global_mode == "amount":
                base_amt = float(dca_cfg.get("base_amount", 10.0) or 10.0)
                buy_amt = base_amt * (amount_multiplier ** u)
                amount_text = "模式：自动, 固定金额"
                amount_label = f"{buy_amt:.2f} USDT"
            else:
                base_percent = float(dca_cfg.get("base_percent", 2) or 2)
                base_amt = collateral * (base_percent / 100.0)
                buy_amt = base_amt * (amount_multiplier ** u)
                amount_text = "模式：自动, 百分比"
                amount_label = f"{(base_percent * (amount_multiplier ** u)):.2f}%"
        else:
            amount_multiplier = 1.0
            if global_mode == "amount":
                base_amt = float(level_cfg.get("amount", 100) or 100)
                buy_amt = base_amt
                amount_text = f"模式：手动, 本层金额={base_amt}"
                amount_label = f"{buy_amt:.2f} USDT"
            else:
                base_percent = float(level_cfg.get("percent", 2.0) or 2.0)
                buy_amt = collateral * (base_percent / 100.0)
                amount_text = f"模式：手动, 本层百分比={base_percent}"
                amount_label = f"{base_percent:.2f}%"

        try:
            prev_qty = abs(trade.amount)
        except Exception:
            prev_qty = 0.0

        lev = float(self.leverage(trade.pair))
        added_qty = self._qty_from_usdt(buy_amt, trigger_price, lev)

        prev_value = prev_qty * avg_entry
        added_value = added_qty * trigger_price
        new_avg_entry = (prev_value + added_value) / (prev_qty + added_qty)

        self._set(trade, 'dca_count', u + 1)
        self._set(trade, 'dca_done', True)
        self._set(trade, 'last_dca_candle', self._safe_int(candle_ts.timestamp()))
        self._set(trade, 'last_dca_time', self._safe_int(current_time.timestamp()))
        self._set(trade, 'tp_count', 0)

        try:
            rsi_val_text = f"{float(last_rsi):.2f}" if last_rsi is not None else "None"
        except Exception:
            rsi_val_text = "None"
        try:
            j_val_text = f"{float(last_j):.2f}" if last_j is not None else "None"
        except Exception:
            j_val_text = "None"

        logger.info(
            f"[{trade.pair}] {RED}[浮亏 DCA 加仓 {amount_label} {RESET}"
            f"订单规模倍率：{amount_multiplier ** u:.2f})], u=({u}->{u + 1}), "
            f"{amount_text}, 触发条件={triggered_label}, "
            f"RSI={rsi_val_text}, J={j_val_text}, "
            f"触发价={threshold:.4f}, 实时价={trigger_price:.4f}, "
            f"{YELLOW}保证金={margin:.4f}{RESET}, 加仓={buy_amt:.4f} USDT, 新均价={new_avg_entry:.4f}"
        )
        return float(buy_amt), f"dca_u={u + 1}"

    # ============================================================
    # 浮盈加仓（多空逻辑相同，不需要分支）
    # ============================================================
    def profit_rebuy(self, trade, last, collateral):
        cfg = self.get_runtime_config()
        tp_cfg = self._cfg(cfg, "tp", default={}) or {}
        need_rebuy = self._get_bool(trade, 'need_rebuy', False)
        if not need_rebuy or not bool(tp_cfg.get("rebuy_enable", True)):
            return None

        price = last.get('close', None)
        if price is None:
            return None

        try:
            lev = float(self.leverage(trade.pair) or 1.0)
        except Exception:
            lev = 1.0

        try:
            current_qty = abs(float(trade.amount))
        except Exception:
            current_qty = 0.0

        current_value = (current_qty * price / lev) if price else 0.0
        amount_mode = self._amount_mode()

        if amount_mode == "amount":
            try:
                target_value = float(tp_cfg.get("target_wallet_amount", 50.0) or 50.0)
            except Exception:
                target_value = 50.0
            target_text = f"{target_value:.2f} USDT"
        else:
            try:
                target_wallet_percent = float(tp_cfg.get("target_wallet_percent", 5) or 5)
            except Exception:
                target_wallet_percent = 5.0
            target_value = collateral * (target_wallet_percent / 100.0)
            target_text = f"{target_wallet_percent:.0f}%"

        buy_amt = target_value - current_value
        if buy_amt <= 0:
            return None

        n = self._get_int(trade, 'tp_count', 0)
        self._set(trade, 'need_rebuy', False)
        self._set(trade, 'dca_done', False)
        self._set(trade, 'tp_count', n + 1)

        avg_price = float(trade.open_rate or 0.0)
        added_qty = (buy_amt / price) if price else 0
        if current_qty <= 0:
            new_avg = price
        else:
            new_avg = (current_qty * avg_price + added_qty * price) / (current_qty + added_qty)

        logger.info(
            f"[{trade.pair}] {GREEN}[浮盈加仓至 {target_text}]{RESET}, n=({n}->{n + 1}), 当前价={price:.4f}, "
            f"{YELLOW}保证金={current_value:.4f}{RESET}, 加仓={buy_amt:.4f} USDT, 新均价={new_avg:.4f}"
        )
        if amount_mode == "amount":
            tag = "rebuy_to_amount"
        else:
            tag = f"rebuy_to_{target_wallet_percent:.0f}pct"
        return float(buy_amt), tag

    # ============================================================
    # TP 止盈（多空逻辑相同，不需要方向分支）
    # ============================================================
    def tp_reduce(self, trade, last, current_profit, margin, current_rate, current_time):
        cfg = self.get_runtime_config()
        tp_cfg = self._cfg(cfg, "tp", default={}) or {}
        dca_tp_cfg = self._cfg(cfg, "loss_tp", default={}) or {}

        if not bool(tp_cfg.get("enable", True)):
            return None

        amount_mode = self._amount_mode()
        account_profit = float(current_profit)

        last_tp = self._get_int(trade, 'last_tp_time', None)
        if last_tp is not None:
            base_time = datetime.fromtimestamp(self._safe_int(last_tp))
        else:
            base_time = trade.open_date_utc
            if getattr(base_time, 'tzinfo', None):
                base_time = base_time.replace(tzinfo=None)

        elapsed = (current_time - base_time).total_seconds() / 60
        roi_target, roi_minutes = self._roi_target(cfg, elapsed)
        roi_text = (
            f"{roi_target * 100:.2f}%({roi_minutes}min)"
            if roi_target is not None else "None"
        )

        u = self._get_int(trade, 'dca_count', 0)

        try:
            dca_tp_profit = float(dca_tp_cfg.get("dca_tp_profit", 3)) / 100
        except Exception:
            dca_tp_profit = 0.008

        dca_tp_ready = (u > 0) and (account_profit >= dca_tp_profit)

        if u > 0:
            if not dca_tp_ready:
                return None
        else:
            if roi_target is None:
                return None
            if account_profit < roi_target:
                return None

        # ---- 浮亏 DCA 止盈 ----
        if u > 0:
            try:
                current_qty = float(trade.amount)
            except Exception:
                current_qty = 0.0
            current_qty_abs = abs(current_qty)

            try:
                price = float(current_rate) if current_rate is not None else None
            except Exception:
                price = None
            try:
                lev = float(self.leverage(trade.pair) or 1.0)
            except Exception:
                lev = 1.0

            if price is None or price <= 0 or lev <= 0:
                return None

            margin_val = margin
            collateral_total = self._collateral_total()

            # ★ 读取新字段，默认 False（全平）
            is_partial = bool(dca_tp_cfg.get("is_partial", False))

            # ★ 语义：is_partial = False → 全平；True → 部分减仓
            if not is_partial:
                # 全平分支
                self._set(trade, 'dca_count', 0)
                self._set(trade, 'dca_done', False)
                self._set(trade, 'last_tp_time', self._safe_int(current_time.timestamp()))
                logger.info(
                    f"[STRATEGY] [TP] [{trade.pair}] {GREEN}[DCA止盈全平]{RESET}, "
                    f"DCA次数={u}, 当前收益={account_profit * 100:.2f}%, "
                    f"{YELLOW}保证金={margin_val:.2f}{RESET}, 当前价={price:.4f}"
                )
                return float(-margin_val), "tp_afterDCA_close_all"

            # 部分减仓：按目标仓位减仓
            if amount_mode == "amount":
                try:
                    target_usdt = float(dca_tp_cfg.get("target_wallet_amount", 50.0) or 50.0)
                except Exception:
                    target_usdt = 50.0
            else:
                try:
                    target_wallet_percent = float(dca_tp_cfg.get("target_wallet_percent", 5) or 5)
                except Exception:
                    target_wallet_percent = 5.0
                target_usdt = float(collateral_total) * (target_wallet_percent / 100.0)

            target_qty = (target_usdt * lev) / price
            sell_qty = max(0.0, current_qty_abs - target_qty)

            if sell_qty <= 0:
                need_add_usdt = max(0.0, target_usdt - margin_val)
                if need_add_usdt > 0:
                    self._set(trade, 'dca_count', 0)
                    self._set(trade, 'dca_done', False)
                    self._set(trade, 'last_tp_time', self._safe_int(current_time.timestamp()))
                    logger.info(
                        f"[{trade.pair}] {GREEN}[当前仓位过小，浮亏DCA止盈加仓至 "
                        f"{target_usdt:.2f} USDT]{RESET}, "
                        f"保证金={margin_val:.4f}, 加仓={need_add_usdt:.4f} USDT"
                    )
                    return float(need_add_usdt), "tp_afterDCA_rebuy_to_target"
                return None

            try:
                sell_usdt = (sell_qty * price) / lev if lev and price else 0.0
            except Exception:
                sell_usdt = 0.0
            sell_usdt_capped = min(sell_usdt, max(0.0, margin_val))
            if sell_usdt_capped <= 0:
                return None

            self._set(trade, 'dca_count', 0)
            self._set(trade, 'dca_done', False)
            self._set(trade, 'last_tp_time', self._safe_int(current_time.timestamp()))

            if amount_mode == "amount":
                target_text = f"{target_usdt:.2f} USDT"
            else:
                target_text = f"{target_wallet_percent:.0f}%"

            logger.info(
                f"[{trade.pair}] {GREEN}[DCA止盈减仓至 {target_text}]{RESET}, "
                f"DCA次数={u}, DCA止盈目标收益率={dca_tp_profit * 100:.2f}%, "
                f"当前收益={account_profit * 100:.2f}%, "
                f"{YELLOW}保证金={margin:.2f}{RESET}, 当前价={last.get('close'):.4f}, "
                f"减仓={sell_usdt_capped:.4f} USDT"
            )
            return float(-sell_usdt_capped), "tp_afterDCA_sell_keep_target"

        # ---- 浮盈 TP 减仓 ----
        rebuy_enable = bool(tp_cfg.get("rebuy_enable", True))
        reduce_percent = 100.0

        if not rebuy_enable:
            sell_amt = -margin
            reduce_text = f"全平 {margin:.2f} USDT"
        else:
            if amount_mode == "amount":
                try:
                    reduce_amount = float(tp_cfg.get("reduce_amount", 10.0) or 10.0)
                except Exception:
                    reduce_amount = 10.0
                sell_amt = -min(reduce_amount, margin)
                reduce_text = f"{abs(sell_amt):.2f} USDT"
            else:
                try:
                    reduce_percent = float(tp_cfg.get("reduce_percent", 30))
                except Exception:
                    reduce_percent = 30
                sell_amt = -(reduce_percent / 100.0) * margin
                reduce_text = f"{reduce_percent:.0f}%"

        self._set(trade, 'dca_done', False)
        self._set(trade, 'last_tp_time', self._safe_int(current_time.timestamp()))
        self._set(trade, 'last_tp_margin', float(margin))
        self._set(trade, 'need_rebuy', bool(tp_cfg.get("rebuy_enable", True)))

        logger.info(
            f"[STRATEGY] [TP] [{trade.pair}] {GREEN}[浮盈减仓 {reduce_text}]{RESET}, "
            f"持仓时间={elapsed:.0f}min, ROI目标={roi_text}, "
            f"当前收益率={account_profit * 100:.2f}%, "
            f"{YELLOW}保证金={margin:.2f}{RESET}, 当前价={last.get('close'):.4f}, "
            f"减仓={abs(sell_amt):.4f}"
        )
        tp_tag = f"tp_{'amount' if amount_mode == 'amount' else reduce_percent}"
        return float(sell_amt), tp_tag

    # ============================================================
    # 网格：方向分支
    # ============================================================
    def grid_single(self, trade, last, current_time, current_rate, margin=None,
                    htf_blocks=False, htf_cfg=None):
        cfg = self.get_runtime_config()
        grid_cfg = self._cfg(cfg, "grid", default={}) or {}
        if not bool(grid_cfg.get("enable", True)):
            return None

        try:
            price = float(current_rate) if current_rate is not None else None
        except Exception:
            price = None
        if price is None:
            price = last.get('close', None)
        if price is None:
            return None

        if getattr(current_time, 'tzinfo', None):
            current_time = current_time.replace(tzinfo=None)

        anchor = self._get_float(trade, 'grid_anchor_price', None)
        if anchor is None or anchor <= 0:
            try:
                anchor = float(trade.open_rate or 0.0)
            except Exception:
                anchor = None
        if anchor is None or anchor <= 0:
            return None

        grid_lower_pct = self._cfg_float(grid_cfg, "init_lower",
                                          self._cfg_float(grid_cfg, "grid_lower", -2.0))
        grid_upper_pct = self._cfg_float(grid_cfg, "init_upper",
                                          self._cfg_float(grid_cfg, "grid_upper", 2.0))
        grid_lower = anchor * (1 + grid_lower_pct / 100.0)
        grid_upper = anchor * (1 + grid_upper_pct / 100.0)

        collateral = self._collateral_total()
        try:
            cur_margin = float(trade.stake_amount) if margin is None else float(margin)
        except Exception:
            cur_margin = 0.0
        if collateral <= 0 and cur_margin <= 0:
            return None

        last_grid_ts = self._get_int(trade, 'last_grid_action_time', None)
        if last_grid_ts is not None:
            try:
                last_dt = datetime.fromtimestamp(self._safe_int(last_grid_ts))
                cooldown_minutes = self._cfg_int(grid_cfg, "cooldown_minutes", 30)
                if (current_time - last_dt).total_seconds() < 60 * cooldown_minutes:
                    return None
            except Exception:
                pass

        w = self._get_int(trade, 'grid_w', 0)
        max_w = self._cfg_int(grid_cfg, "max_count", 5)
        amount_mode = self._amount_mode()

        try:
            lev = float(self.leverage(trade.pair) or 1.0)
            if not (lev > 0):
                lev = 1.0
        except Exception:
            lev = 1.0

        price_source = "market" if current_rate is not None else "candle_close"
        is_short = self._is_short

        # ★ 加仓触发：多头价跌到 grid_lower，空头价涨到 grid_upper
        add_triggered = (price >= grid_upper) if is_short else (price <= grid_lower)
        # ★ 减仓触发：多头价涨到 grid_upper，空头价跌到 grid_lower
        reduce_triggered = (price <= grid_lower) if is_short else (price >= grid_upper)

        # ---------- 加仓 ----------
        if add_triggered:
            if self._pair_position_exceeded(trade, price):
                return None
            if htf_blocks and htf_cfg and bool(htf_cfg.get("protect_grid", True)):
                return None
            if max_w > 0 and w >= max_w:
                return None

            buy_percent = self._cfg_float(grid_cfg, "buy_percent", 2.0)
            buy_amount  = self._cfg_float(grid_cfg, "buy_amount", 10.0)
            order_scale = self._cfg_float(grid_cfg, "order_scale", 1.0)
            if order_scale <= 0:
                order_scale = 1.0
            scale_factor = order_scale ** w

            if amount_mode == "amount":
                buy_usdt = min(buy_amount * scale_factor, self._available_stake() * 0.8)
                grid_frac = 0.0
            else:
                grid_frac = max(0.01, (buy_percent / 100.0) * scale_factor)
                buy_usdt = min(collateral * grid_frac, self._available_stake() * 0.8)

            if buy_usdt <= 0:
                return None

            added_qty = self._qty_from_usdt(buy_usdt, price, lev)
            if added_qty <= 0:
                return None

            try:
                prev_qty = abs(trade.amount)
            except Exception:
                prev_qty = 0.0
            prev_avg = float(trade.open_rate or 0.0)
            prev_cost = prev_qty * prev_avg

            new_avg = prev_avg
            if (prev_qty + added_qty) > 0:
                new_avg = (prev_cost + buy_usdt * lev) / (prev_qty + added_qty)

            new_w = min(w + 1, max_w) if max_w > 0 else w + 1
            new_anchor = float(price)
            next_add    = new_anchor * (1 + grid_upper_pct / 100.0)
            next_reduce = new_anchor * (1 + grid_lower_pct / 100.0)

            self._set(trade, 'grid_anchor_price', float(new_anchor))
            self._set(trade, 'grid_upper', float(next_add))
            self._set(trade, 'grid_lower', float(next_reduce))
            self._set(trade, 'last_grid_action_time', self._safe_int(current_time.timestamp()))
            self._record_add_usdt(trade, 'grid_added_total_usdt', buy_usdt)
            self._record_add_qty(trade, 'grid_added_total_qty', added_qty)
            self._set(trade, 'grid_count', self._safe_int(self._get_int(trade, 'grid_count', 0) + 1))
            self._set(trade, 'grid_w', self._safe_int(new_w))

            if amount_mode == "amount":
                logger.info(
                    f"[{trade.pair}] {RED}[网格加仓 {buy_usdt:.2f} USDT {RESET}"
                    f"(订单规模倍率：{scale_factor:.2f})], 当前价={price:.4f}, "
                    f"触发价={(grid_upper if is_short else grid_lower):.4f}, "
                    f"{YELLOW}保证金={cur_margin:.2f}{RESET}, 加仓={buy_usdt:.4f} USDT, "
                    f"新均价={new_avg:.4f}, w={new_w}, "
                    f"下次 加仓价={next_add:.4f}, 减仓价={next_reduce:.4f}"
                )
            else:
                logger.info(
                    f"[{trade.pair}] {RED}[网格加仓 {grid_frac * 100:.2f}% {RESET}"
                    f"(订单规模倍率：{scale_factor:.2f})], 当前价={price:.4f}, "
                    f"触发价={(grid_upper if is_short else grid_lower):.4f}, "
                    f"{YELLOW}保证金={cur_margin:.2f}{RESET}, 加仓={buy_usdt:.4f} USDT, "
                    f"新均价={new_avg:.4f}, w={new_w}, "
                    f"下次 加仓价={next_add:.4f}, 减仓价={next_reduce:.4f}"
                )
            return float(buy_usdt), f"grid_add_{grid_frac:.3f}"

        # ---------- 减仓 ----------
        if reduce_triggered:
            sell_percent = self._cfg_float(grid_cfg, "sell_percent", 2.0)
            sell_amount  = self._cfg_float(grid_cfg, "sell_amount", 10.0)

            if amount_mode == "amount":
                sell_usdt = min(sell_amount, cur_margin)
                grid_sell_frac = 0.0
            else:
                grid_sell_frac = max(0.01, sell_percent / 100.0)
                sell_usdt = min(collateral * grid_sell_frac, cur_margin)

            if sell_usdt <= 0:
                return None

            new_w = max(0, w - 1)
            new_anchor = float(price)
            next_add    = new_anchor * (1 + grid_upper_pct / 100.0)
            next_reduce = new_anchor * (1 + grid_lower_pct / 100.0)

            self._record_add_usdt(trade, 'grid_reduced_total_usdt', float(sell_usdt))
            self._set(trade, 'grid_anchor_price', float(new_anchor))
            self._set(trade, 'grid_upper', float(next_add))
            self._set(trade, 'grid_lower', float(next_reduce))
            self._set(trade, 'last_grid_action_time', self._safe_int(current_time.timestamp()))
            self._set(trade, 'grid_count', self._safe_int(self._get_int(trade, 'grid_count', 0) + 1))
            self._set(trade, 'grid_w', self._safe_int(new_w))

            if amount_mode == "amount":
                logger.info(
                    f"[{trade.pair}] {GREEN}[网格减仓 {sell_usdt:.2f} USDT]{RESET} "
                    f"(triggered by {price_source}), 当前价={price:.4f}, "
                    f"触发价={(grid_lower if is_short else grid_upper):.4f}, "
                    f"{YELLOW}保证金={cur_margin:.2f}{RESET}, 减仓={sell_usdt:.4f}, "
                    f"w={new_w}{RESET}, 下次 加仓价={next_add:.4f}, 减仓价={next_reduce:.4f}"
                )
            else:
                logger.info(
                    f"[{trade.pair}] {GREEN}[网格减仓 {grid_sell_frac * 100:.1f}%]{RESET} "
                    f"(triggered by {price_source}), 当前价={price:.4f}, "
                    f"触发价={(grid_lower if is_short else grid_upper):.4f}, "
                    f"{YELLOW}保证金={cur_margin:.2f}{RESET}, 减仓={sell_usdt:.4f}, "
                    f"w={new_w}{RESET}, 下次 加仓价={next_add:.4f}, 减仓价={next_reduce:.4f}"
                )
            return float(-sell_usdt), "grid_sell_20pct"
        return None

    # ============================================================
    # 调度
    # ============================================================
    def adjust_trade_position(self, trade, current_time, current_rate, current_profit, **kwargs):
        try:
            return self._adjust_trade_position_impl(
                trade, current_time, current_rate, current_profit, **kwargs
            )
        except Exception:
            logger.exception(f"[{trade.pair}] adjust_trade_position 异常")
            return None

    def _adjust_trade_position_impl(self, trade, current_time, current_rate, current_profit, **kwargs):
        if trade.has_open_orders:
            return None

        df, _ = self.dp.get_analyzed_dataframe(trade.pair, self.timeframe)
        if df.empty:
            return None
        last = df.iloc[-1]

        try:
            margin = float(trade.stake_amount)
        except Exception:
            margin = 0.0

        if current_time.tzinfo:
            current_time = current_time.replace(tzinfo=None)

        collateral = self._collateral_total()
        if collateral <= 0:
            return None

        candle_ts = self._get_candle_ts(df)
        if candle_ts is None:
            logger.warning(f"[{trade.pair}] 无法获取有效 candle_ts，跳过")
            return None

        cfg = self.get_runtime_config()
        htf_cfg = self._cfg(cfg, "htf_trend_filter", default={}) or {}
        htf_blocks = self._htf_trend_blocks(trade=trade, last=last, htf_cfg=htf_cfg)

        if not (htf_blocks and bool(htf_cfg.get("protect_trend", False))):
            res = self.trend_add(trade, last, margin, collateral, current_time, current_profit, candle_ts)
            if res:
                return res

        if not (htf_blocks and bool(htf_cfg.get("protect_dca", True))):
            res = self.dca_add(trade, df, last, current_time, current_rate)
            if res:
                return res

        if not (htf_blocks and bool(htf_cfg.get("protect_rebuy", True))):
            res = self.profit_rebuy(trade, last, collateral)
            if res:
                return res

        res = self.tp_reduce(trade, last, current_profit, margin, current_rate, current_time)
        if res:
            return res

        res = self.grid_single(
            trade, last, current_time, current_rate, margin,
            htf_blocks=htf_blocks, htf_cfg=htf_cfg
        )
        if res:
            return res

        return None

    # ============================================================
    # custom_exit：多空逻辑相同
    # ============================================================
    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        cfg = self.get_runtime_config()
        sl_cfg = self._cfg(cfg, "sl", default={}) or {}

        if not bool(sl_cfg.get("enable", True)):
            return None

        try:
            stoploss_roi = float(sl_cfg.get("stoploss", -50) or -50) / 100.0
        except Exception:
            stoploss_roi = -0.5

        if current_profit <= stoploss_roi:
            if trade.id not in self._stop_loss_logged:
                self._stop_loss_logged.add(trade.id)
                logger.info(
                    f"[STRATEGY] [SL] [{pair}] {RED}触发ROI止损{RESET} "
                    f"收益率={current_profit * 100:.2f}% "
                    f"持仓价={trade.open_rate:.4f} "
                    f"开仓价={current_rate:.4f}"
                )
                self._record_chart_marker(
                    event_type="stop_loss", pair=pair, trade_id=trade.id,
                    side=self._side_str, price=current_rate,
                    amount=abs(float(trade.amount or 0)),
                    current_time=current_time, message="ROI止损",
                    candle_time=self._index_candle_key(current_time)
                )
            return "stop_loss"

        if self._time_stop_triggered(trade, current_time, current_rate):
            return "time_stop"

        return None

    def custom_stoploss(self, *args, **kwargs) -> float | None:
        return None