"""
TrendReversion4h - 4 Saatlik Hibrit Strateji
=============================================
TrendReversionStrategy'nin 4h timeframe adaptasyonu.
Daha uzun tutma suresi ile buyuk trend hareketlerini yakalamak icin optimize edilmistir.

Mantik:
  1. Gunluk grafikte close > SMA_200 ise BOGA trendi -> sadece LONG izni
  2. 4h grafikte close < BB_lower VE RSI < 30 ise -> LONG giris
  3. Cikis: BB_middle'a donus veya RSI > 70 veya trailing stop

Parametreler (Hyperopt ile optimize edilecek):
  - buy_rsi_threshold: RSI alis esigi (varsayilan: 30)
  - buy_bb_std: Bollinger standart sapma carpani (varsayilan: 2.0)
  - sell_rsi_threshold: RSI satis esigi (varsayilan: 70)
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


class TrendReversion4h(IStrategy):
    """
    Trend Following + Mean Reversion Hibrit Strateji (4h Versiyon)

    - 1d timeframe: SMA_200 ile makro trend yonu
    - 4h timeframe: Bollinger Bands + RSI ile giris/cikis
    - Daha gevsek ROI hedefleri ile buyuk trendleri yakalama
    """

    # Strateji meta bilgileri
    INTERFACE_VERSION = 3
    timeframe = "4h"
    can_short = False  # Sadece LONG

    # ROI (Return on Investment) tablosu
    # 4h mumlar icin daha uzun sureler ve daha yuksek hedefler
    # Dakika: minimum ROI yuzdesi
    minimal_roi = {
        "0": 0.10,    # Hemen %10 kar varsa cik
        "60": 0.06,   # 1 saat sonra %6 kar yeterli
        "180": 0.04,  # 3 saat sonra %4 kar yeterli
        "360": 0.02,  # 6 saat sonra %2 kar yeterli
    }

    # Protections
    protections = [
        {"method": "CooldownPeriod", "stop_duration_candles": 5},
        {"method": "StoplossGuard", "trade_limit": 3, "stop_duration_candles": 12, "only_per_pair": True},
    ]

    # Stop-loss
    stoploss = -0.04  # %4 sabit stop-loss

    # Trailing stop — 4h icin daha gevsek
    trailing_stop = True
    trailing_stop_positive = 0.04   # %4 kar sonrasi trailing aktif
    trailing_stop_positive_offset = 0.06  # %6 kar sonrasi trailing baslasin
    trailing_only_offset_is_reached = True

    # Startup mum sayisi (SMA_200 icin en az 200 mum gerekli)
    # 4h'de 200 mum = ~33 gun, makul
    startup_candle_count = 200

    # Order tipi
    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": True,
    }

    # ==================== Hyperopt Parametreleri ====================

    # Alis parametreleri
    buy_rsi_threshold = IntParameter(20, 40, default=30, space="buy", optimize=True)
    buy_bb_std = DecimalParameter(1.5, 2.5, default=2.0, decimals=1, space="buy", optimize=True)

    # Satis parametreleri
    sell_rsi_threshold = IntParameter(60, 80, default=70, space="sell", optimize=True)

    # Stop-loss parametreleri
    stoploss_atr_multiplier = DecimalParameter(
        1.0, 3.0, default=1.5, decimals=1, space="stoploss", optimize=True
    )

    # ==================== Informatif Ciftler (Multi-Timeframe) ====================

    def informative_pairs(self):
        """1d timeframe verisi icin bilgilendirici ciftler."""
        pairs = self.dp.current_whitelist()
        informative_pairs = [(pair, "1d") for pair in pairs]
        return informative_pairs

    # ==================== Indikator Hesaplama ====================

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Tum teknik indikatorlerin hesaplanmasi."""

        # --- 4h Timeframe Indikatorleri ---

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

        # ATR (stop-loss hesaplamasi icin)
        dataframe["atr"] = ta.ATR(dataframe["high"], dataframe["low"], dataframe["close"], timeperiod=14)

        # Volume SMA
        dataframe["volume_sma_20"] = ta.SMA(dataframe["volume"], timeperiod=20)

        # --- 1d Timeframe Indikatorleri (Makro Trend) ---
        informative = self.dp.get_pair_dataframe(pair=metadata["pair"], timeframe="1d")
        if not informative.empty:
            informative["sma_200"] = ta.SMA(informative["close"], timeperiod=200)
            informative["daily_trend"] = (informative["close"] > informative["sma_200"]).astype(int)

            dataframe = merge_informative_pair(
                dataframe, informative, self.timeframe, "1d", ffill=True
            )

        return dataframe

    # ==================== Giris Sinyali ====================

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """LONG giris kosullari."""

        conditions = []

        # Kosul 1: Makro trend BOGA (1d close > SMA_200)
        if "daily_trend_1d" in dataframe.columns:
            conditions.append(dataframe["daily_trend_1d"] == 1)
        else:
            # Daily trend verisi yoksa sinyal uretme (korumasiz calisma)
            logger.warning(f"Daily trend data missing for {metadata['pair']} - no signals generated")
            return dataframe

        # Kosul 2: Fiyat Bollinger alt bandinin altinda
        conditions.append(dataframe["close"] < dataframe["bb_lower"])

        # Kosul 3: RSI asiri satim bolgesinde
        conditions.append(dataframe["rsi"] < self.buy_rsi_threshold.value)

        # Kosul 4: Hacim ortalamanin ustunde (opsiyonel guclendirici)
        conditions.append(dataframe["volume"] > dataframe["volume_sma_20"])

        # Kosul 5: Mum hacmi sifir degil
        conditions.append(dataframe["volume"] > 0)

        if conditions:
            dataframe.loc[reduce(lambda x, y: x & y, conditions), "enter_long"] = 1

        return dataframe

    # ==================== Cikis Sinyali ====================

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """LONG cikis kosullari."""

        conditions = []

        # Cikis 1: Fiyat Bollinger orta bandina dondu (birincil hedef)
        conditions.append(dataframe["close"] > dataframe["bb_middle"])

        # Cikis 2: RSI asiri alim bolgesinde
        conditions.append(dataframe["rsi"] > self.sell_rsi_threshold.value)

        if conditions:
            # Herhangi bir cikis kosulu saglanirsa cik (OR mantigi)
            dataframe.loc[
                conditions[0] | conditions[1],
                "exit_long",
            ] = 1

        return dataframe

    # ==================== Ozel Stop-Loss (ATR Bazli) ====================

    def custom_stoploss(
        self, pair: str, trade, current_time, current_rate, current_profit, **kwargs
    ) -> float:
        """ATR bazli dinamik stop-loss."""
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)

        if len(dataframe) < 1:
            return self.stoploss

        last_candle = dataframe.iloc[-1]
        atr_value = last_candle.get("atr", 0)

        if atr_value > 0 and trade.open_rate > 0:
            atr_stoploss = (atr_value * self.stoploss_atr_multiplier.value) / trade.open_rate
            return max(-atr_stoploss, self.stoploss)  # Sabit stop-loss'tan daha kotu olamaz

        return self.stoploss

    # ==================== Pozisyon Buyuklugu ====================

    def custom_stake_amount(
        self, current_time, current_rate, proposed_stake, min_stake, max_stake, leverage,
        entry_tag, side, **kwargs
    ) -> float:
        """Kasanin %1-2'si risk altinda olacak sekilde pozisyon buyuklugu."""
        # Toplam bakiyenin max %5'i tek bir trade'e
        total_balance = self.wallets.get_total("USDT")
        max_per_trade = total_balance * 0.05

        return min(proposed_stake, max_per_trade)
