"""
TrendReversionStrategy - Ana Hibrit Strateji
=============================================
Makro Trend Filtresi (1d SMA200) + Mikro Giriş Tetikleyicisi (1h Bollinger + RSI)

Mantık:
  1. Günlük grafikte close > SMA_200 ise BOĞA trendi → sadece LONG izni
  2. Saatlik grafikte close < BB_lower VE RSI < 30 ise → LONG giriş
  3. Çıkış: BB_middle'a dönüş veya RSI > 70 veya trailing stop

Parametreler (Hyperopt ile optimize edilecek):
  - buy_rsi_threshold: RSI alış eşiği (varsayılan: 30)
  - buy_bb_std: Bollinger standart sapma çarpanı (varsayılan: 2.0)
  - sell_rsi_threshold: RSI satış eşiği (varsayılan: 70)
"""

import logging
from functools import reduce

import talib.abstract as ta
from pandas import DataFrame

from freqtrade.strategy import (
    BooleanParameter,
    DecimalParameter,
    IntParameter,
    IStrategy,
    merge_informative_pair,
)

logger = logging.getLogger(__name__)


class TrendReversionStrategy(IStrategy):
    """
    Trend Following + Mean Reversion Hibrit Strateji

    - 1d timeframe: SMA_200 ile makro trend yönü
    - 1h timeframe: Bollinger Bands + RSI ile giriş/çıkış
    """

    # Strateji meta bilgileri
    INTERFACE_VERSION = 3
    timeframe = "1h"
    can_short = False  # Başlangıçta sadece LONG

    # ROI (Return on Investment) tablosu
    # Dakika: minimum ROI yüzdesi
    minimal_roi = {
        "0": 0.08,    # Hemen %8 kar varsa cik (onceki: %5)
        "60": 0.05,   # 1 saat sonra %5 kar yeterli (onceki: 30dk/%3)
        "120": 0.03,  # 2 saat sonra %3 kar yeterli (onceki: 60dk/%2)
        "240": 0.015, # 4 saat sonra %1.5 kar yeterli (onceki: 120dk/%1)
    }

    # Protections
    protections = [
        {"method": "CooldownPeriod", "stop_duration_candles": 5},
        {"method": "StoplossGuard", "trade_limit": 3, "stop_duration_candles": 12, "only_per_pair": True},
    ]

    # Stop-loss
    stoploss = -0.04  # %4 sabit stop-loss (sikiласtirildi, onceki: -0.05)

    # Trailing stop
    trailing_stop = True
    trailing_stop_positive = 0.03   # %3 kar sonrasi trailing aktif (onceki: 0.02)
    trailing_stop_positive_offset = 0.05  # %5 kar sonrasi trailing baslasin (onceki: 0.03)
    trailing_only_offset_is_reached = True

    # Startup mum sayısı (SMA_200 için en az 200 mum gerekli)
    startup_candle_count = 200

    # Order tipi
    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": True,
    }

    # ==================== Hyperopt Parametreleri ====================

    # Alış parametreleri
    buy_rsi_threshold = IntParameter(20, 40, default=30, space="buy", optimize=True)
    buy_bb_std = DecimalParameter(1.5, 2.5, default=2.0, decimals=1, space="buy", optimize=True)

    # Satış parametreleri
    sell_rsi_threshold = IntParameter(60, 80, default=70, space="sell", optimize=True)

    # Stop-loss parametreleri
    stoploss_atr_multiplier = DecimalParameter(
        1.0, 3.0, default=1.5, decimals=1, space="stoploss", optimize=True
    )

    # ==================== İnformatif Çiftler (Multi-Timeframe) ====================

    def informative_pairs(self):
        """1d timeframe verisi için bilgilendirici çiftler."""
        pairs = self.dp.current_whitelist()
        informative_pairs = [(pair, "1d") for pair in pairs]
        return informative_pairs

    # ==================== İndikatör Hesaplama ====================

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Tüm teknik indikatörlerin hesaplanması."""

        # --- 1h Timeframe İndikatörleri ---

        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = ta.BBANDS(
            dataframe["close"],
            timeperiod=20,
            nbdevup=self.buy_bb_std.value,
            nbdevdn=self.buy_bb_std.value,
            matype=0,
        )
        dataframe["bb_upper"] = bb_upper
        dataframe["bb_middle"] = bb_middle
        dataframe["bb_lower"] = bb_lower
        # RSI
        dataframe["rsi"] = ta.RSI(dataframe["close"], timeperiod=14)

        # ATR (stop-loss hesaplaması için)
        dataframe["atr"] = ta.ATR(dataframe["high"], dataframe["low"], dataframe["close"], timeperiod=14)

        # Volume SMA
        dataframe["volume_sma_20"] = ta.SMA(dataframe["volume"], timeperiod=20)

        # --- 1d Timeframe İndikatörleri (Makro Trend) ---
        informative = self.dp.get_pair_dataframe(pair=metadata["pair"], timeframe="1d")
        if not informative.empty:
            informative["sma_200"] = ta.SMA(informative["close"], timeperiod=200)
            informative["daily_trend"] = (informative["close"] > informative["sma_200"]).astype(int)

            dataframe = merge_informative_pair(
                dataframe, informative, self.timeframe, "1d", ffill=True
            )

        return dataframe

    # ==================== Giriş Sinyali ====================

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """LONG giriş koşulları."""

        conditions = []

        # Koşul 1: Makro trend BOĞA (1d close > SMA_200)
        if "daily_trend_1d" in dataframe.columns:
            conditions.append(dataframe["daily_trend_1d"] == 1)
        else:
            # Daily trend verisi yoksa sinyal üretme (korumasız çalışma)
            logger.warning(f"Daily trend data missing for {metadata['pair']} - no signals generated")
            return dataframe

        # Koşul 2: Fiyat Bollinger alt bandının altında
        conditions.append(dataframe["close"] < dataframe["bb_lower"])

        # Koşul 3: RSI aşırı satım bölgesinde
        conditions.append(dataframe["rsi"] < self.buy_rsi_threshold.value)

        # Koşul 4: Hacim ortalamanın üstünde (opsiyonel güçlendirici)
        conditions.append(dataframe["volume"] > dataframe["volume_sma_20"])

        # Koşul 5: Mum hacmi sıfır değil
        conditions.append(dataframe["volume"] > 0)

        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), "enter_long"] = 1

        return dataframe

    # ==================== Çıkış Sinyali ====================

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """LONG çıkış koşulları."""

        conditions = []

        # Çıkış 1: Fiyat Bollinger orta bandına döndü (birincil hedef)
        conditions.append(dataframe["close"] > dataframe["bb_middle"])

        # Çıkış 2: RSI aşırı alım bölgesinde
        conditions.append(dataframe["rsi"] > self.sell_rsi_threshold.value)

        if conditions:
            # Herhangi bir çıkış koşulu sağlanırsa çık (OR mantığı)
            dataframe.loc[
                conditions[0] | conditions[1],
                "exit_long",
            ] = 1

        return dataframe

    # ==================== Özel Stop-Loss (ATR Bazlı) ====================

    def custom_stoploss(
        self, pair: str, trade, current_time, current_rate, current_profit, **kwargs
    ) -> float:
        """ATR bazlı dinamik stop-loss."""
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)

        if len(dataframe) < 1:
            return self.stoploss

        last_candle = dataframe.iloc[-1]
        atr_value = last_candle.get("atr", 0)

        if atr_value > 0 and trade.open_rate > 0:
            atr_stoploss = (atr_value * self.stoploss_atr_multiplier.value) / trade.open_rate
            return max(-atr_stoploss, self.stoploss)  # Sabit stop-loss'tan daha kötü olamaz

        return self.stoploss

    # ==================== Pozisyon Büyüklüğü ====================

    def custom_stake_amount(
        self, current_time, current_rate, proposed_stake, min_stake, max_stake, leverage,
        entry_tag, side, **kwargs
    ) -> float:
        """Kasanın %1-2'si risk altında olacak şekilde pozisyon büyüklüğü."""
        # Toplam bakiyenin max %5'i tek bir trade'e
        total_balance = self.wallets.get_total("USDT")
        max_per_trade = total_balance * 0.05

        return min(proposed_stake, max_per_trade)
