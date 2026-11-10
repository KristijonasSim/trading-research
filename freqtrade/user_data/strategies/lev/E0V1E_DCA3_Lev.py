"""E0V1E_DCA3 su svertu (futures, isolated). Logika ta pati kaip spot:
pelnas į taisykles paduodamas be sverto (padalintas iš sverto), o stop dydžiai padauginti iš sverto,
kad kainos atstumai liktų tokie patys. Svertas imamas iš aplinkos kintamojo LEV (numatyta 10)."""
import os
from E0V1E_DCA3 import E0V1E_DCA3

LEV = float(os.environ.get("LEV", "10"))


class E0V1E_DCA3_Lev(E0V1E_DCA3):
    can_short = False

    def leverage(self, pair, current_time, current_rate, proposed_leverage, max_leverage, entry_tag, side, **kwargs):
        return min(LEV, max_leverage)

    def custom_stoploss(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        lev = trade.leverage or 1.0
        sl = super().custom_stoploss(pair, trade, current_time, current_rate, current_profit / lev, **kwargs)
        if sl <= -0.99:
            return sl
        return max(sl * lev, -0.99)

    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        return super().custom_exit(pair, trade, current_time, current_rate, current_profit / (trade.leverage or 1.0), **kwargs)

    def adjust_trade_position(self, trade, current_time, current_rate, current_profit, min_stake, max_stake, **kwargs):
        return super().adjust_trade_position(trade, current_time, current_rate, current_profit / (trade.leverage or 1.0),
                                             min_stake, max_stake, **kwargs)
