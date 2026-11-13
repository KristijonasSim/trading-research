"""Bendras sverto apvalkalas (futures, isolated): kainų atstumai kaip spot.
ROI, stoploss, trailing padauginami iš sverto; į custom_* taisykles pelnas paduodamas be sverto.
Svertas iš aplinkos kintamojo LEV."""
import os
from freqtrade.strategy import IStrategy
LEV = float(os.environ.get("LEV", "3"))


def make(base, module):
    attrs = {"can_short": False, "__module__": module}
    attrs["minimal_roi"] = {k: v * LEV for k, v in base.minimal_roi.items()}
    attrs["stoploss"] = max(base.stoploss * LEV, -0.99)
    for a in ("trailing_stop_positive", "trailing_stop_positive_offset"):
        if getattr(base, a, None):
            attrs[a] = getattr(base, a) * LEV

    def leverage(self, pair, current_time, current_rate, proposed_leverage, max_leverage, entry_tag, side, **kw):
        return min(LEV, max_leverage)
    attrs["leverage"] = leverage

    if base.custom_stoploss is not IStrategy.custom_stoploss and getattr(base, "use_custom_stoploss", False):
        def custom_stoploss(self, pair, trade, current_time, current_rate, current_profit, **kw):
            lev = trade.leverage or 1.0
            sl = base.custom_stoploss(self, pair, trade, current_time, current_rate, current_profit / lev, **kw)
            if sl is None or sl <= -0.99:
                return sl
            return max(sl * lev, -0.99)
        attrs["custom_stoploss"] = custom_stoploss
    for name in ("custom_exit",):
        if getattr(base, name) is not getattr(IStrategy, name):
            def f(self, pair, trade, current_time, current_rate, current_profit, _n=name, **kw):
                return getattr(base, _n)(self, pair, trade, current_time, current_rate, current_profit / (trade.leverage or 1.0), **kw)
            attrs[name] = f
    if base.adjust_trade_position is not IStrategy.adjust_trade_position:
        def adjust_trade_position(self, trade, current_time, current_rate, current_profit, min_stake, max_stake, **kw):
            return base.adjust_trade_position(self, trade, current_time, current_rate, current_profit / (trade.leverage or 1.0),
                                              min_stake, max_stake, **kw)
        attrs["adjust_trade_position"] = adjust_trade_position
    return type(base.__name__ + "_LevBase", (base,), attrs)
