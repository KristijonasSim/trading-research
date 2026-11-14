# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
"""
Chiến lược Giao dịch Định lượng Tiếng Việt: VnSmartTrendStrategy
Thuộc Dự án: Hệ thống Giao dịch Tự động & Ứng dụng Điều khiển Từ xa Tiếng Việt (FreqBot VN Remote)

Tính năng cốt lõi:
1. Kết hợp Đa chỉ báo: EMA (20, 50, 200) + RSI (14) + Bollinger Bands (20, 2.0) + Bộ lọc Khối lượng (Volume SMA 20).
2. Bộ lọc Khung Giờ Giao Dịch theo Múi Giờ Việt Nam (UTC+7, mặc định 03:00-04:00 sáng chỉ lọc chiều Mua mới; canh Thoát lệnh 24/7).
3. Phân bổ Vốn Động theo Rủi ro (stake_size) + Kiểm tra Độ lệch giá khớp & Spread + Hội đồng Cố vấn AI (ChatGPT & Gemini).
4. Cắt lỗ cứng (-3%) kèm Cắt lỗ trượt khóa lợi nhuận (Trailing Stop) và Bộ 4 Lớp Giáp Bảo Vệ Vốn Tự Động (Protections).
5. Luồng thông báo đẩy 100% Tiếng Việt rõ ràng khi Vào lệnh (confirm_trade_entry) và Thoát lệnh (confirm_trade_exit).
"""

from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
from typing import Optional
import numpy as np
import pandas as pd
from pandas import DataFrame

from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter
from freqtrade.persistence import Trade
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
from vn_support import (
    format_entry_tag_vi,
    format_exit_reason_vi,
    in_priority_window,
    in_session,
    number,
    report_allows,
    spread_ratio,
    stake_size,
)

logger = logging.getLogger(__name__)


class VnSmartTrendStrategy(IStrategy):
    """
    Chiến lược giao dịch theo xu hướng thông minh kết hợp bắt nhịp hồi quá bán,
    tích hợp đầy đủ quản trị rủi ro đa tầng, bộ lọc khung giờ VN, cố vấn AI và báo cáo Tiếng Việt.
    """

    INTERFACE_VERSION = 3

    # Khung thời gian giao dịch chính: 5 phút
    timeframe = "5m"

    # Chỉ chạy trên chiều Mua (Spot Long)
    can_short: bool = False

    # Bảng chốt lời tối thiểu theo thời gian giữ lệnh (Minimal ROI)
    minimal_roi = {
        "0": 0.06,     # Chốt lời ngay nếu đạt +6.0%
        "30": 0.035,   # Sau 30 phút: Chốt lời nếu đạt +3.5%
        "60": 0.02,    # Sau 60 phút: Chốt lời nếu đạt +2.0%
        "180": 0.01    # Sau 180 phút: Chốt lời nếu đạt +1.0%
    }

    # Cắt lỗ cứng tối đa -3% cho mỗi vị thế (Kết hợp stoploss_on_exchange trong config.json)
    stoploss = -0.03

    # Cấu hình Cắt lỗ trượt (Trailing Stop-Loss) để khóa lợi nhuận khi giá tăng
    trailing_stop = True
    trailing_only_offset_is_reached = True
    trailing_stop_positive = 0.01          # Giữ khoảng cách cắt lỗ trượt 1.0% dưới mức đỉnh
    trailing_stop_positive_offset = 0.025  # Bắt đầu kích hoạt trượt khi lệnh lãi từ +2.5%

    # Chỉ tính toán trên nến mới để tối ưu CPU
    process_only_new_candles = True

    # Sử dụng tín hiệu thoát lệnh từ populate_exit_trend
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # Số nến lịch sử cần tải khi khởi động để tính chuẩn EMA 200
    startup_candle_count: int = 600

    # Bộ nhớ đệm nhẹ cho báo cáo AI theo dấu thời gian sửa đổi tệp (mtime_ns)
    _report_cache_key: Optional[tuple] = None
    _report_cache_data: Optional[dict] = None

    def bot_start(self, **kwargs) -> None:
        policy = self.config["vn_policy"]
        # Kiểm tra tính hợp lệ của lịch giao dịch ngay khi khởi động Bot
        in_session(datetime.now().astimezone(), policy["schedule"])
        if self._historical() and policy["research"]["mode"] == "required":
            raise ValueError("AI required cannot use today's research in backtests. Use advisory/off baseline.")

    def _historical(self):
        mode = self.config.get("runmode")
        return getattr(mode, "value", mode) in ("backtest", "hyperopt", "edge", "plot")

    def _notify(self, message):
        try:
            self.dp.send_msg(message)
        except Exception:
            logger.warning("Không gửi được thông báo Tiếng Việt; tiếp tục xử lý lệnh.")

    def _read_latest_report(self, path: Path) -> dict:
        stat = path.stat()
        cache_key = (str(path), stat.st_mtime_ns, stat.st_size)
        if self._report_cache_key == cache_key and self._report_cache_data is not None:
            return self._report_cache_data
        report = json.loads(path.read_text(encoding="utf-8"))
        self._report_cache_key = cache_key
        self._report_cache_data = report
        return report

    def _stake(self, proposed, maximum, minimum, now=None):
        equity = self.wallets.get_total_stake_amount()
        used = sum(t.stake_amount for t in Trade.get_trades_proxy(is_open=True))
        schedule = self.config["vn_policy"]["schedule"]
        is_prio = True if now is None else in_priority_window(now, schedule)
        return stake_size(equity, proposed, maximum, minimum, used, self.stoploss,
                          self.config["vn_policy"]["risk"], is_priority_hour=is_prio)

    def custom_stake_amount(self, pair, current_time, current_rate, proposed_stake,
                            min_stake, max_stake, leverage, entry_tag, side, **kwargs):
        try:
            if side != "long" or leverage != 1:
                return 0.0
            return self._stake(proposed_stake, max_stake, min_stake, now=current_time)
        except Exception:
            logger.warning("Không tính được giới hạn vốn động; từ chối mua %s.", pair)
            return 0.0

    def _entry_allowed(self, pair, amount, rate, now, side):
        try:
            policy = self.config["vn_policy"]
            if side != "long" or not in_session(now, policy["schedule"]):
                return False
            cost = number(amount) * number(rate)
            if cost <= 0 or cost > self._stake(cost, cost, None, now=now) + 1e-8:
                return False
            # Chế độ Backtest/Hyperopt không có sổ lệnh trực tiếp hay báo cáo AI hiện tại
            if self._historical():
                return policy["research"]["mode"] != "required"
            frame, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
            candle = frame.iloc[-1]
            age = (now - candle["date"].to_pydatetime() - timedelta(minutes=5)).total_seconds()
            if not 0 <= age <= 600 or number(candle["close"]) <= 0:
                return False
            if abs(number(rate) / number(candle["close"]) - 1) > policy["risk"]["max_entry_deviation"]:
                return False
            book = self.dp.orderbook(pair, 1)
            if spread_ratio(book["bids"][0][0], book["asks"][0][0]) > policy["research"]["max_spread"]:
                return False
            if policy["research"]["mode"] != "off":
                report_file = policy["research"].get("report_file", "latest.json")
                path = Path(self.config["user_data_dir"]) / "research" / report_file
                if not path.is_file() and report_file != "latest.json":
                    path = Path(self.config["user_data_dir"]) / "research" / "latest.json"
                report = self._read_latest_report(path)
                if not report_allows(report, self.config, pair, now):
                    return False
            return True
        except Exception:
            logger.warning("Dữ liệu/chính sách không hợp lệ; từ chối mở lệnh mua %s.", pair)
            return False

    # Tham số có thể tối ưu hóa bằng Hyperopt
    buy_rsi_min = IntParameter(40, 55, default=45, space="buy", optimize=True)
    buy_rsi_max = IntParameter(60, 72, default=68, space="buy", optimize=True)
    oversold_rsi = IntParameter(22, 35, default=30, space="buy", optimize=True)
    sell_rsi_overbought = IntParameter(72, 85, default=78, space="sell", optimize=True)

    @property
    def protections(self):
        """
        Bộ 4 Lớp Giáp Bảo Vệ Vốn Tự Động (Circuit Breakers)
        """
        return [
            {
                # 1. Nghỉ 6 nến 5m (30 phút) sau khi đóng lệnh trên 1 cặp coin
                "method": "CooldownPeriod",
                "stop_duration_candles": 6
            },
            {
                # 2. Hạn mức sụt giảm trên lịch sử lệnh đóng trong cửa sổ trượt 24h (288 nến 5m): vượt 5% -> Khóa Bot 12h
                "method": "MaxDrawdown",
                "lookback_period_candles": 288,
                "trade_limit": 2,
                "stop_duration_candles": 144,
                "max_allowed_drawdown": 0.05
            },
            {
                # 3. Chống sập dây chuyền: Nếu có 3 lệnh cắt lỗ trong cửa sổ 6h (72 nến) -> Khóa Bot 6h
                "method": "StoplossGuard",
                "lookback_period_candles": 72,
                "trade_limit": 3,
                "stop_duration_candles": 72,
                "only_per_pair": False
            },
            {
                # 4. Cách ly cặp coin yếu: Nếu 1 cặp coin có >= 2 lệnh tổng lỗ <= -3% trong 12h -> Khóa cặp đó 6h
                "method": "LowProfitPairs",
                "lookback_period_candles": 144,
                "trade_limit": 2,
                "stop_duration_candles": 72,
                "required_profit": -0.03
            }
        ]

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Tính toán các chỉ báo kỹ thuật cần thiết (EMA, RSI, Bollinger Bands, Volume SMA)
        """
        # 1. Hệ thống đường trung bình động EMA
        dataframe["ema20"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema50"] = ta.EMA(dataframe, timeperiod=50)
        dataframe["ema200"] = ta.EMA(dataframe, timeperiod=200)

        # 2. Chỉ báo động lượng RSI (14)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        # 3. Dải Bollinger Bands (20, 2.0)
        bollinger = qtpylib.bollinger_bands(
            qtpylib.typical_price(dataframe), window=20, stds=2
        )
        dataframe["bb_lowerband"] = bollinger["lower"]
        dataframe["bb_middleband"] = bollinger["mid"]
        dataframe["bb_upperband"] = bollinger["upper"]

        # 4. Khối lượng trung bình 20 phiên
        dataframe["volume_mean_20"] = dataframe["volume"].rolling(20).mean()

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Xác định tín hiệu Mua (enter_long) và gắn nhãn lý do bằng Tiếng Việt (enter_tag)
        """
        dataframe.loc[:, "enter_tag"] = ""
        dataframe.loc[:, "enter_long"] = 0

        # Điều kiện Mua 1: Xu hướng tăng chuẩn (Close > EMA200, EMA20 > EMA50, RSI khỏe, Volume đột biến)
        dk_xu_huong_tang = (
            (dataframe["close"] > dataframe["ema200"])
            & (dataframe["ema20"] > dataframe["ema50"])
            & (dataframe["close"] > dataframe["ema20"])
            & (dataframe["rsi"] >= self.buy_rsi_min.value)
            & (dataframe["rsi"] <= self.buy_rsi_max.value)
            & (dataframe["volume"] > dataframe["volume_mean_20"] * 1.15)
            & (dataframe["volume"] > 0)
        )
        dataframe.loc[dk_xu_huong_tang, ["enter_long", "enter_tag"]] = (
            1,
            "XU_HUONG_TANG_EMA_RSI",
        )

        # Điều kiện Mua 2: Bắt nhịp hồi khi quá bán chạm dải dưới Bollinger trong xu hướng lớn ổn định
        dk_hoi_qua_ban = (
            (dataframe["close"] > dataframe["ema200"])
            & (dataframe["close"] < dataframe["bb_lowerband"] * 1.003)
            & (dataframe["rsi"] < self.oversold_rsi.value)
            & (dataframe["close"] > dataframe["open"])
            & (dataframe["volume"] > dataframe["volume_mean_20"])
            & (dataframe["volume"] > 0)
        )
        dataframe.loc[dk_hoi_qua_ban, ["enter_long", "enter_tag"]] = (
            1,
            "BAT_NHIP_HOI_BOLLINGER_RSI",
        )

        # Thời gian nến là thời điểm MỞ nến (UTC); tín hiệu chỉ hoàn tất tại thời điểm ĐÓNG nến (+5 phút)
        schedule = self.config["vn_policy"]["schedule"]
        sessions = (pd.to_datetime(dataframe["date"], utc=True) + pd.Timedelta(minutes=5)).map(
            lambda date: in_session(date.to_pydatetime(), schedule)
        )
        dataframe.loc[~sessions, ["enter_long", "enter_tag"]] = (0, "")

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Xác định tín hiệu Bán (exit_long) và gắn nhãn lý do thoát lệnh (exit_tag)
        """
        dataframe.loc[:, "exit_tag"] = ""
        dataframe.loc[:, "exit_long"] = 0

        # Điều kiện Bán 1: Chạm vùng quá mua mạnh trên dải Bollinger trên
        dk_qua_mua = (
            (dataframe["rsi"] > self.sell_rsi_overbought.value)
            & (dataframe["close"] >= dataframe["bb_upperband"])
            & (dataframe["volume"] > 0)
        )
        dataframe.loc[dk_qua_mua, ["exit_long", "exit_tag"]] = (
            1,
            "CHOT_LOI_QUA_MUA_RSI_BB",
        )

        # Điều kiện Bán 2: Gãy xu hướng ngắn hạn (EMA20 cắt xuống dưới EMA50 kèm RSI suy yếu)
        dk_gay_xu_huong = (
            qtpylib.crossed_below(dataframe["ema20"], dataframe["ema50"])
            & (dataframe["rsi"] < 42)
            & (dataframe["volume"] > 0)
        )
        dataframe.loc[dk_gay_xu_huong, ["exit_long", "exit_tag"]] = (
            1,
            "GAY_XU_HUONG_EMA20_50",
        )

        return dataframe

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
        **kwargs
    ) -> bool:
        """
        Gửi báo cáo Tiếng Việt rành mạch mỗi khi Bot bắt đầu mở lệnh mới
        """
        if not self._entry_allowed(pair, amount, rate, current_time, side):
            return False
        if self.dp:
            gia_tri_usdt = number(amount) * number(rate)
            self._notify(
                f"🟢 [VÀO LỆNH MỚI]\n"
                f"• Cặp giao dịch: {pair}\n"
                f"• Giá mua dự kiến: {rate:.4f} USDT\n"
                f"• Khối lượng: {amount:.6f} (~{gia_tri_usdt:.2f} USDT)\n"
                f"• Lý do mua (Tín hiệu): {format_entry_tag_vi(entry_tag)}\n"
                f"• Ngưỡng cắt lỗ bảo vệ: {self.stoploss * 100:.1f}%"
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
        **kwargs
    ) -> bool:
        """
        Gửi báo cáo Tiếng Việt mỗi khi Bot đóng lệnh (Chốt lời, Cắt lỗ hoặc Bán khẩn cấp)
        """
        if self.dp:
            profit_ratio = trade.calc_profit_ratio(rate)
            bieu_tuong = "💰 [CHỐT LỜI]" if profit_ratio >= 0 else "🛑 [CẮT LỖ / ĐÓNG LỆNH]"
            self._notify(
                f"{bieu_tuong} {pair}\n"
                f"• Giá mua vào: {trade.open_rate:.4f} USDT\n"
                f"• Giá bán ra: {rate:.4f} USDT\n"
                f"• Tỷ lệ Lãi/Lỗ: {profit_ratio * 100:+.2f}%\n"
                f"• Lý do đóng: {format_exit_reason_vi(exit_reason)}"
            )
        return True
