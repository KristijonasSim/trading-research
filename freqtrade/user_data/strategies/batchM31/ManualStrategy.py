from freqtrade.strategy.interface import IStrategy
from datetime import datetime
from freqtrade.persistence import Trade
from typing import Optional
import logging
logger = logging.getLogger(__name__)

class ManualStrategy(IStrategy):
  minimal_roi = {"0": 1000}
  stoploss = -0.99
  timeframe = "1m"
  trade_max_profit = {}

  process_only_new_candles = False
  use_exit_signal = True
  use_entry_signal = False
  use_custom_exit = True
  startup_candle_count = 1
  
  def populate_indicators(self, dataframe, metadata):
    return dataframe

  def populate_entry_trend(self, dataframe, metadata):
    dataframe["enter_long"] = 0
    dataframe["enter_short"] = 0
    return dataframe

  def populate_exit_trend(self, dataframe, metadata):
    dataframe["exit_long"] = 0
    dataframe["exit_short"] = 0
    return dataframe
  
  @property
  def protections(self):
    return []

  def custom_exit(
    self,
    pair: str,
    trade: Trade,
    current_time: datetime,
    current_rate: float,
    current_profit: float,
    **kwargs
  ) -> Optional[str]:

    if trade.id is None:
      return None

    if current_profit is None:
      return None

    trade_id = trade.id
    
    logger.info(f"In custom_exit method for trade {trade_id}")

    if trade_id not in self.trade_max_profit:
      self.trade_max_profit[trade_id] = current_profit
      return None

    if current_profit > self.trade_max_profit[trade_id]:
      self.trade_max_profit[trade_id] = current_profit
      logger.info(f"Current profit {current_profit} is the max profit")
      return None

    max_profit = self.trade_max_profit[trade_id]
    logger.info(f"Max profit is {max_profit} and current profit is {current_profit}")

    if max_profit < 0.03:
      logger.info(f"Returning because {max_profit} is less than 3%")
      return None

    if current_profit <= max_profit * 0.75:
      logger.info(f"3/4 of the profit is lost already, saving profit...")
      return "half_peak_profit_exit"

    return None

  def on_trade_exit(
    self,
    trade: Trade,
    order_type: str,
    exit_reason: str,
    **kwargs
  ):
    self.trade_max_profit.pop(trade.id, None)

  def leverage(
    self,
    pair: str,
    current_time: datetime,
    current_rate: float,
    proposed_leverage: float,
    max_leverage: float,
    entry_tag: str | None,
    side: str,
    **kwargs,
  ) -> float:
    return 20.0
